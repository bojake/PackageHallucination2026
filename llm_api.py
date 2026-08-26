"""Thin HTTP shim for local (Ollama) and hosted (OpenAI / xAI / Anthropic) chat models.

Design goals
------------
1. **No serving harness.** Plain ``requests`` calls against each provider's documented
   chat endpoint -- no SDKs, no ``text-generation-webui``, no local model loading.
2. **The paper's technique is preserved verbatim.** This module never edits prompts and
   never post-processes model output. It transports messages and returns the raw
   assistant text, exactly as ``tokenizer.decode(...)`` did in ``generate_code.py`` and
   ``generate_package_names.py``.
3. **Honest bookkeeping.** The original experiments used HuggingFace ``model.generate``
   with ``temperature`` / ``top_k`` / ``top_p``. Not every hosted API accepts all three
   (see ``SUPPORTED_PARAMS``), and some models cap output below the requested budget.
   Every parameter that is dropped, renamed or clamped is recorded in
   ``Client.adjustments`` so the run manifest states exactly what the model saw.

Usage
-----
    client = llm_api.Client.from_spec("openai:gpt-4.1")
    text, usage = client.chat(messages, max_tokens=64, temperature=0.01, top_k=20, top_p=0.9)
"""

from __future__ import annotations

import json
import os
import random
import re
import threading
import time

import requests

# A single non-streaming request must be able to finish a long generation. Hosted
# providers drop idle connections at around ten minutes, which is the practical
# ceiling for the no-streaming design (and why response caps stay well under 128k).
DEFAULT_TIMEOUT = 600
DEFAULT_MAX_RETRIES = 5

# Which sampling knobs each provider's chat endpoint accepts at all. Individual models
# may still reject one (newer reasoning models often refuse `temperature`/`top_p`);
# that case is handled at runtime by _degrade_payload().
SUPPORTED_PARAMS = {
    "ollama":    {"temperature", "top_k", "top_p"},   # native /api/chat -> full fidelity
    "openai":    {"temperature", "top_p"},            # no top_k in the OpenAI API
    "xai":       {"temperature", "top_p"},            # OpenAI-compatible, no top_k
    "anthropic": {"temperature", "top_k", "top_p"},   # /v1/messages accepts all three
    "openai_compatible": {"temperature", "top_p"},    # assume the OpenAI schema's subset
}

PROVIDERS = {
    "ollama":    {"base_url": "http://localhost:11434", "key_env": None,                "api": "ollama"},
    "openai":    {"base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY", "api": "openai"},
    "xai":       {"base_url": "https://api.x.ai/v1",       "key_env": "XAI_API_KEY",    "api": "openai"},
    "anthropic": {"base_url": "https://api.anthropic.com/v1", "key_env": "ANTHROPIC_API_KEY", "api": "anthropic"},
    # Escape hatch for anything else that speaks the OpenAI chat schema
    # (vLLM, llama.cpp server, LM Studio, OpenRouter, Together, Groq, ...).
    # Requires --base-url and usually --api-key-env.
    "openai_compatible": {"base_url": None, "key_env": "OPENAI_API_KEY", "api": "openai"},
}

ALIASES = {
    "grok": "xai",
    "claude": "anthropic",
    "gpt": "openai",
    "local": "ollama",
    "compat": "openai_compatible",
    "openai-compatible": "openai_compatible",
}

ANTHROPIC_VERSION = "2023-06-01"


class ProviderError(RuntimeError):
    """Raised when a request cannot be completed after retries, or is misconfigured."""


def load_dotenv(path=".env"):
    """Populate os.environ from a local .env file. Existing env vars win.

    Keeps API keys out of shell history and out of the repo (.env is gitignored).
    """
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def split_spec(spec):
    """Split ``provider:model`` into ``(provider, model)``.

    Only the first colon is consumed, so Ollama tags survive: ``ollama:qwen3-coder:30b``
    -> ``("ollama", "qwen3-coder:30b")``.
    """
    provider, _, model = spec.partition(":")
    provider = ALIASES.get(provider.strip().lower(), provider.strip().lower())
    if provider not in PROVIDERS or not model:
        known = ", ".join(sorted(PROVIDERS)) + ", " + ", ".join(sorted(ALIASES))
        raise ProviderError(
            f"Could not parse model spec {spec!r}. Expected 'provider:model_id', "
            f"e.g. 'ollama:qwen3-coder:30b' or 'anthropic:claude-sonnet-4-5-20250929'. "
            f"Known providers: {known}"
        )
    return provider, model.strip()


def slugify(spec):
    """Filesystem-safe name for a model spec (used for the Tests/ output directory)."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", spec).strip("_")


class Client:
    """One configured provider+model. Thread-safe; share a single instance across workers."""

    def __init__(self, provider, model, base_url=None, api_key=None, key_env=None,
                 timeout=DEFAULT_TIMEOUT, max_retries=DEFAULT_MAX_RETRIES,
                 extra_body=None, strict=False, input_cost_per_million=None,
                 output_cost_per_million=None, budget_usd=None):
        if provider not in PROVIDERS:
            raise ProviderError(f"Unknown provider {provider!r}")
        config = PROVIDERS[provider]

        self.provider = provider
        self.model = model
        self.api = config["api"]
        self.base_url = (base_url or config["base_url"] or "").rstrip("/")
        if not self.base_url:
            raise ProviderError(f"Provider {provider!r} requires --base-url")
        self.key_env = key_env or config["key_env"]
        self.api_key = api_key
        self.supported_params = SUPPORTED_PARAMS.get(provider, SUPPORTED_PARAMS["openai"])
        self.timeout = timeout
        self.max_retries = max_retries
        self.extra_body = extra_body or {}
        self.strict = strict
        self.input_cost_per_million = input_cost_per_million
        self.output_cost_per_million = output_cost_per_million
        self.budget_usd = budget_usd
        if budget_usd is not None and (input_cost_per_million is None
                                       or output_cost_per_million is None):
            raise ProviderError(
                "A dollar budget requires both input and output cost per million tokens."
            )

        self.adjustments = {}      # param name -> why it was dropped, renamed or clamped
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}
        self.restored_usage = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}
        self.restored_accounting_rows = 0
        self.estimated_cost_usd = 0.0
        self.truncated = 0         # responses that hit the token cap
        self.served_models = {}    # model id reported in responses -> count; ties the
                                   # requested alias to what the provider actually served
        self._lock = threading.Lock()
        self._session = requests.Session()

    def restore_accounting(self, metadata_records):
        """Restore prior token spend from ordered response metadata before a resume.

        Restored usage is kept separate from usage generated by this process so run-history
        entries remain invocation-specific. The total dollar estimate includes both and is
        therefore safe to use as a resume-aware budget guard.
        """
        records = [record for record in metadata_records
                   if isinstance(record, dict) and not record.get("metadata_missing")]
        restored = {
            "prompt_tokens": sum(int(record.get("prompt_tokens") or 0) for record in records),
            "completion_tokens": sum(int(record.get("completion_tokens") or 0)
                                     for record in records),
            "calls": len(records),
        }
        with self._lock:
            if self.usage["calls"]:
                raise ProviderError("Cannot restore accounting after new requests have started.")
            self.restored_usage = restored
            self.restored_accounting_rows = len(records)
            if self.input_cost_per_million is not None:
                self.estimated_cost_usd = (
                    restored["prompt_tokens"] * self.input_cost_per_million / 1_000_000
                    + restored["completion_tokens"] * self.output_cost_per_million / 1_000_000
                )
        return restored

    @classmethod
    def from_spec(cls, spec, **kwargs):
        provider, model = split_spec(spec)
        key_env = kwargs.pop("api_key_env", None) or PROVIDERS[provider]["key_env"]
        api_key = os.environ.get(key_env) if key_env else None
        if key_env and not api_key:
            raise ProviderError(
                f"Environment variable {key_env} is not set. Export it or put it in .env "
                f"(see .env.example)."
            )
        return cls(provider, model, api_key=api_key, key_env=key_env, **kwargs)

    # ------------------------------------------------------------------ requests

    def _headers(self):
        if self.api == "anthropic":
            return {
                "content-type": "application/json",
                "x-api-key": self.api_key or "",
                "anthropic-version": ANTHROPIC_VERSION,
            }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _note(self, param, reason):
        with self._lock:
            self.adjustments.setdefault(param, reason)

    def _sampling(self, temperature, top_k, top_p):
        """Filter the paper's sampling parameters down to what this provider accepts."""
        requested = {"temperature": temperature, "top_k": top_k, "top_p": top_p}
        allowed = {}
        for name, value in requested.items():
            if value is None:
                continue
            if name in self.supported_params:
                allowed[name] = value
            else:
                reason = f"not accepted by the {self.provider} API"
                if self.strict:
                    raise ProviderError(
                        f"--strict-sampling: {name}={value} is {reason}. Re-run without "
                        f"--strict-sampling to proceed (the drop is recorded in the manifest), "
                        f"or use a provider that supports it (ollama, anthropic)."
                    )
                self._note(name, reason)
        return allowed

    def _build_payload(self, messages, max_tokens, temperature, top_k, top_p):
        sampling = self._sampling(temperature, top_k, top_p)

        if self.api == "ollama":
            options = {"num_predict": max_tokens}
            options.update(sampling)
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": options,
            }
            url = f"{self.base_url}/api/chat"

        elif self.api == "anthropic":
            system = "\n".join(m["content"] for m in messages if m["role"] == "system")
            payload = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [m for m in messages if m["role"] != "system"],
            }
            if system:
                payload["system"] = system
            payload.update(sampling)
            url = f"{self.base_url}/messages"

        else:  # openai / xai / openai-compatible
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
            }
            payload.update(sampling)
            url = f"{self.base_url}/chat/completions"

        # extra_body merges at the top level, except that an "options" object is merged
        # into Ollama's options block -- that is where its generation knobs live, so
        # --extra-body '{"options": {"num_ctx": 32768}}' does what a user expects.
        extra = dict(self.extra_body)
        nested_options = extra.pop("options", None)
        if nested_options and self.api == "ollama":
            payload["options"].update(nested_options)
        elif nested_options:
            extra["options"] = nested_options
        payload.update(extra)
        return url, payload

    def _degrade_payload(self, payload, body):
        """Drop a single parameter the model just rejected, so the run can continue.

        Newer hosted models refuse ``temperature`` / ``top_p``, and OpenAI renamed
        ``max_tokens`` to ``max_completion_tokens`` for its reasoning models. Rather than
        hard-coding which model ids do what, react to the 400 and record the change.
        Returns True if the payload was changed and the call is worth retrying.
        """
        error = (body or {}).get("error") or {}
        if isinstance(error, str):
            # Ollama returns {"error": "<text>"}; OpenAI-style APIs return an object.
            error = {"message": error}
        message = error.get("message") or json.dumps(body)[:400]

        if "max_completion_tokens" in message and "max_tokens" in payload:
            payload["max_completion_tokens"] = payload.pop("max_tokens")
            self._note("max_tokens", "renamed to max_completion_tokens by the provider")
            return True

        # A model whose own output ceiling is below the requested cap: clamp to the
        # limit the error names rather than dropping the field, so the request still
        # runs with the largest budget that model allows.
        cap_field = next((f for f in ("max_tokens", "max_completion_tokens") if f in payload), None)
        if cap_field and re.search(r"max_?(?:completion_)?tokens", message):
            smaller = [int(n) for n in re.findall(r"\d{2,7}", message) if int(n) < payload[cap_field]]
            if smaller:
                clamped = max(smaller)
                self._note(cap_field, f"clamped {payload[cap_field]} -> {clamped} "
                                      f"by {self.model}'s output ceiling")
                payload[cap_field] = clamped
                return True

        param = error.get("param")
        candidates = [param] if param else []
        candidates += re.findall(r"['\"`]?(temperature|top_p|top_k|max_tokens)['\"`]?", message)
        for name in candidates:
            if name in payload and name != "model":
                payload.pop(name)
                self._note(name, f"rejected by {self.model}: {message.strip()[:180]}")
                return True
        return False

    def _extract(self, body):
        """Pull assistant text + usage out of a provider response."""
        if self.api == "ollama":
            text = (body.get("message") or {}).get("content", "")
            usage = {
                "prompt_tokens": body.get("prompt_eval_count", 0) or 0,
                "completion_tokens": body.get("eval_count", 0) or 0,
            }
            finish = body.get("done_reason", "")
        elif self.api == "anthropic":
            text = "".join(
                block.get("text", "")
                for block in body.get("content", [])
                if block.get("type") == "text"
            )
            raw = body.get("usage") or {}
            usage = {
                "prompt_tokens": raw.get("input_tokens", 0) or 0,
                "completion_tokens": raw.get("output_tokens", 0) or 0,
            }
            finish = body.get("stop_reason", "")
        else:
            choice = (body.get("choices") or [{}])[0]
            text = (choice.get("message") or {}).get("content") or ""
            raw = body.get("usage") or {}
            usage = {
                "prompt_tokens": raw.get("prompt_tokens", 0) or 0,
                "completion_tokens": raw.get("completion_tokens", 0) or 0,
            }
            finish = choice.get("finish_reason", "")
        return text, usage, finish

    def chat(self, messages, max_tokens, temperature=None, top_k=None, top_p=None,
             include_metadata=False):
        """Send one chat request.

        Returns ``(assistant_text, usage_dict)`` by default.  Batch experiments pass
        ``include_metadata=True`` to also receive a serializable third value containing the
        per-response finish reason, served model id, token counts, and truncation flag.  The
        optional third value preserves compatibility with older direct callers while fixing
        the provenance gap that previously retained cap hits only as phase totals.

        Retries on rate limits, 5xx and transport errors with exponential backoff.
        Raises ProviderError once retries are exhausted.
        """
        url, payload = self._build_payload(messages, max_tokens, temperature, top_k, top_p)
        headers = self._headers()
        last_error = None

        for attempt in range(self.max_retries):
            with self._lock:
                if (self.budget_usd is not None
                        and self.estimated_cost_usd >= self.budget_usd):
                    raise ProviderError(
                        f"Cost guard reached ${self.estimated_cost_usd:.4f} against the "
                        f"${self.budget_usd:.2f} run budget. The batch remains resumable."
                    )
            try:
                response = self._session.post(url, headers=headers, json=payload,
                                              timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                self._backoff(attempt)
                continue

            if response.status_code == 200:
                try:
                    body = response.json()
                except ValueError:
                    last_error = f"non-JSON response: {response.text[:200]}"
                    self._backoff(attempt)
                    continue

                text, usage, finish = self._extract(body)
                served = body.get("model")
                with self._lock:
                    self.usage["prompt_tokens"] += usage["prompt_tokens"]
                    self.usage["completion_tokens"] += usage["completion_tokens"]
                    self.usage["calls"] += 1
                    if self.input_cost_per_million is not None:
                        self.estimated_cost_usd += (
                            usage["prompt_tokens"] * self.input_cost_per_million / 1_000_000
                            + usage["completion_tokens"] * self.output_cost_per_million
                            / 1_000_000
                        )
                    if finish in ("length", "max_tokens"):
                        self.truncated += 1
                    if served:
                        self.served_models[served] = self.served_models.get(served, 0) + 1
                metadata = {
                    "finish_reason": finish,
                    "truncated": finish in ("length", "max_tokens"),
                    "served_model": served,
                    "prompt_tokens": usage["prompt_tokens"],
                    "completion_tokens": usage["completion_tokens"],
                }
                if include_metadata:
                    return text, usage, metadata
                return text, usage

            try:
                body = response.json()
            except ValueError:
                body = {"error": {"message": response.text[:400]}}

            if response.status_code == 400 and self._degrade_payload(payload, body):
                continue  # same attempt budget, retried immediately with a valid payload

            last_error = f"HTTP {response.status_code}: {json.dumps(body)[:400]}"

            if response.status_code in (408, 409, 429) or response.status_code >= 500:
                retry_after = response.headers.get("Retry-After")
                self._backoff(attempt, float(retry_after) if _is_number(retry_after) else None)
                continue

            raise ProviderError(f"{self.provider}/{self.model} -> {last_error}")

        raise ProviderError(
            f"{self.provider}/{self.model} failed after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        )

    def _backoff(self, attempt, retry_after=None):
        delay = retry_after if retry_after is not None else min(60, 2 ** attempt)
        time.sleep(delay + random.uniform(0, 0.5))

    # ------------------------------------------------------------------ helpers

    def describe(self):
        """Serializable record of how this client is configured (for the run manifest)."""
        return {
            "provider": self.provider,
            "model": self.model,
            "endpoint": self.base_url,
            "api_schema": self.api,
            "api_key_env": self.key_env,
            "extra_body": self.extra_body,
            "sampling_params_supported": sorted(self.supported_params),
            "request_adjustments": self.adjustments,
            "served_model_ids": dict(self.served_models),
            "cost_tracking": {
                "input_usd_per_million_tokens": self.input_cost_per_million,
                "output_usd_per_million_tokens": self.output_cost_per_million,
                "budget_usd": self.budget_usd,
                "estimated_cost_usd": round(self.estimated_cost_usd, 6),
                "restored_accounting_rows": self.restored_accounting_rows,
                "restored_token_usage": dict(self.restored_usage),
                "note": ("Calculated from provider-reported token usage; a concurrent batch "
                         "can exceed the guard by requests already in flight.")
                        if self.budget_usd is not None else None,
            },
        }


def _is_number(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def ollama_identity(base_url, model):
    """Immutable identity of an Ollama-served model: digest, quantization, server version.

    Mutable tags like ``gpt-oss:20b`` can point at different weights over time; the digest
    pins exactly what was run. Returns whatever could be fetched -- never raises, because
    identity capture must not break an experiment.
    """
    base = (base_url or PROVIDERS["ollama"]["base_url"]).rstrip("/")
    identity = {}
    try:
        identity["ollama_version"] = requests.get(f"{base}/api/version",
                                                  timeout=15).json().get("version")
    except Exception as exc:                                       # noqa: BLE001
        identity["ollama_version_error"] = str(exc)
    try:
        tags = requests.get(f"{base}/api/tags", timeout=15).json().get("models", [])
        entry = next((m for m in tags if m.get("name") == model or m.get("model") == model),
                     None)
        if entry is None and ":" not in model:
            entry = next((m for m in tags if m.get("name") == f"{model}:latest"), None)
        if entry:
            identity["digest"] = entry.get("digest")
            identity["details"] = entry.get("details")
        else:
            identity["note"] = f"{model!r} not present in /api/tags at run time"
    except Exception as exc:                                       # noqa: BLE001
        identity["tags_error"] = str(exc)

    # Cloud aliases often do not appear in /api/tags because no weights are stored on the
    # local daemon. /api/show still resolves their provider-side metadata, which is the
    # strongest identity evidence Ollama exposes for those cells.
    try:
        response = requests.post(f"{base}/api/show", json={"model": model}, timeout=30)
        response.raise_for_status()
        body = response.json()
        identity["show"] = {
            "modified_at": body.get("modified_at"),
            "details": body.get("details"),
            "model_info": body.get("model_info"),
        }
    except Exception as exc:                                       # noqa: BLE001
        identity["show_error"] = str(exc)
    return identity


def list_models(provider, base_url=None, api_key_env=None):
    """Ask a provider which model ids it currently serves.

    Model ids churn faster than papers do -- use this instead of trusting a hard-coded list.
    """
    provider = ALIASES.get(provider.lower(), provider.lower())
    if provider not in PROVIDERS:
        raise ProviderError(f"Unknown provider {provider!r}")
    config = PROVIDERS[provider]
    base = (base_url or config["base_url"] or "").rstrip("/")
    key_env = api_key_env or config["key_env"]
    api_key = os.environ.get(key_env) if key_env else None

    if config["api"] == "ollama":
        body = requests.get(f"{base}/api/tags", timeout=30).json()
        return sorted(m["name"] for m in body.get("models", []))

    headers = ({"x-api-key": api_key or "", "anthropic-version": ANTHROPIC_VERSION}
               if config["api"] == "anthropic"
               else {"Authorization": f"Bearer {api_key or ''}"})
    body = requests.get(f"{base}/models", headers=headers, timeout=30).json()
    return sorted(m.get("id", "") for m in body.get("data", []))
