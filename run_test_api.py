"""Run the full package-hallucination experiment against an API or Ollama model.

This is the API sibling of ``run_test.py``. It runs the identical three-phase protocol
from the paper --

  1. generate code for every prompt in ``Data/<LANG>/`` (temperature 0.7),
  2. ask the model twice which packages are needed (temperature 0.01, 64 tokens):
     once about the code it just wrote, once about the original prompt,
  3. extract package names with the paper's heuristics and check them against the
     PyPI / npm master lists,

-- using the same prompts, the same sampling parameters, the same file layout and the
same detection code. Only the transport changes: ``requests`` calls to a chat endpoint
instead of loading weights with ``transformers``.

Examples
--------
    # local, via Ollama (highest parameter fidelity: temperature + top_k + top_p all apply)
    python run_test_api.py ollama:qwen3-coder:30b --language Python

    # hosted APIs
    python run_test_api.py openai:gpt-4.1              --language Python
    python run_test_api.py anthropic:claude-sonnet-4-5-20250929 --language Javascript
    python run_test_api.py xai:grok-4                  --language Python --workers 8

    # what can I actually call right now?
    python run_test_api.py --list-models ollama

    # 25-prompt smoke test before committing to a full run
    python run_test_api.py openai:gpt-4.1 --limit 25
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
from datetime import datetime, timezone

import aggregate_results
import generate_code_api
import generate_package_names_api
import llm_api
import package_detection

# Same four datasets, same output file names, same order as run_test.py.
DATASETS = {
    "LLM_Recent": "LLM_LY.json",
    "LLM_All_Time": "LLM_AT.json",
    "Stack_Overflow_Recent": "SO_LY.json",
    "Stack_Overflow_All_Time": "SO_AT.json",
}

# (pre, post, style) triples for package_detection. These are the exact combinations
# get_pre_post_info() produces for the paper's models; "auto" picks the parser the paper
# used for its commercial API models, which is the right fit for modern instruction-tuned
# models that honour "respond with only a comma-separated list".
PYTHON_PARSERS = {
    "auto": (False, False, ""),
    "gpt": (False, False, ""),
    "deepseek": (True, True, "DeepSeek"),
    "mistral": (True, True, "Mistral"),
    "wizardcoder": (True, True, "WizardCoder"),
    "openchat": (False, True, "Openchat"),
    "codellama": (False, False, "CodeLlama"),
}
JAVASCRIPT_PARSERS = {
    "auto": (False, False, "GPT"),
    "gpt": (False, False, "GPT"),
    "deepseek": (False, False, "DeepSeek_6B"),
    "deepseek_1b": (False, False, "DeepSeek_1B"),
    "deepseek_6b": (False, False, "DeepSeek_6B"),
    "deepseek_33b": (False, False, "DeepSeek_33B"),
    "mistral": (False, False, "Mistral"),
    "mixtral": (False, False, "Mixtral"),
    "magicoder": (False, False, "Magicoder"),
    "wizardcoder": (False, False, "WizardCoder"),
    "codellama": (False, False, "CodeLlama"),
}


def build_parser():
    parser = argparse.ArgumentParser(
        description="Package hallucination test for API and Ollama models.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(__doc__ or "").split("Examples\n--------\n")[-1],
    )
    parser.add_argument("model", nargs="?", type=str,
                        help="Model spec as provider:model_id, e.g. ollama:qwen3-coder:30b, "
                             "openai:gpt-4.1, anthropic:claude-sonnet-4-5-20250929, xai:grok-4")
    parser.add_argument("--list-models", metavar="PROVIDER", default=None,
                        help="List model ids the provider currently serves, then exit")
    parser.add_argument("--language", default="Python", choices=["Python", "Javascript"], type=str,
                        help="Programming language to be tested")
    parser.add_argument("--logging", type=str, default="verbose",
                        help="Logging level. Set to 'off' to disable logging")

    # Sampling: same defaults as run_test.py.
    parser.add_argument("--code_temp", "--code-temp", dest="code_temp", default=0.7, type=float,
                        help="Temperature for code generation (paper: 0.7)")
    parser.add_argument("--package_temp", "--package-temp", dest="package_temp", default=0.01, type=float,
                        help="Temperature for the package queries (paper: 0.01)")
    parser.add_argument("--top_k", "--top-k", dest="top_k", default=20, type=int,
                        help="Top-K parameter (paper: 20; ignored by OpenAI and xAI)")
    parser.add_argument("--top_p", "--top-p", dest="top_p", default=0.9, type=float,
                        help="Top-P parameter (paper: 0.9)")
    parser.add_argument("--max-code-tokens", default=30000, type=int,
                        help="Response cap for code generation (paper: 2048). The default is "
                             "raised so reasoning models are not truncated -- see --help notes")
    parser.add_argument("--max-package-tokens", default=30000, type=int,
                        help="Response cap for the package queries (paper: 64). The default is "
                             "raised so reasoning models, which spend the budget on hidden "
                             "thinking tokens, still emit an answer")

    # Transport.
    parser.add_argument("--base-url", default=None,
                        help="Override the provider endpoint (required for openai_compatible)")
    parser.add_argument("--api-key-env", default=None,
                        help="Environment variable holding the API key (default: per provider)")
    parser.add_argument("--extra-body", default=None,
                        help="JSON merged into every request body, e.g. "
                             "'{\"reasoning_effort\": \"low\"}'")
    parser.add_argument("--workers", default=None, type=int,
                        help="Concurrent requests (default: 1 for ollama, 4 otherwise). Affects "
                             "wall-clock only -- prompts and sampling are unchanged")
    parser.add_argument("--timeout", default=llm_api.DEFAULT_TIMEOUT, type=int,
                        help="Per-request timeout in seconds")
    parser.add_argument("--max-retries", default=llm_api.DEFAULT_MAX_RETRIES, type=int,
                        help="Retries per request on rate limits / 5xx / transport errors")
    parser.add_argument("--strict-sampling", action="store_true",
                        help="Abort if a sampling parameter cannot be sent to this provider "
                             "instead of dropping it and recording the drop")
    parser.add_argument("--fail-on-error", action="store_true",
                        help="Abort a phase if any request fails after all retries")

    # Experiment control.
    parser.add_argument("--stage", default="all", choices=["all", "code", "packages", "detect"],
                        help="Run only one phase of the pipeline")
    parser.add_argument("--parser-style", default="auto",
                        help="Response parser for package_detection. 'auto' uses the parser the "
                             "paper applied to its commercial API models")
    parser.add_argument("--limit", default=None, type=int,
                        help="Only use the FIRST N prompts of each dataset. Fine for smoke "
                             "tests; use --sample for anything you intend to measure")
    parser.add_argument("--sample", default=None, type=int,
                        help="Randomly sample N prompts per dataset, preserving order. Use "
                             "this rather than --limit when comparing against the paper -- "
                             "the Stack Overflow datasets are ordered by popularity, so a "
                             "prefix is a biased sample")
    parser.add_argument("--seed", default=0, type=int,
                        help="Seed for --sample, recorded in the manifest (default: 0)")
    parser.add_argument("--name", default=None,
                        help="Output directory name under Tests/ (default: derived from the spec)")
    return parser


def resolve_parser_style(style, language):
    table = PYTHON_PARSERS if language == "Python" else JAVASCRIPT_PARSERS
    key = style.strip().lower()
    if key not in table:
        raise SystemExit(
            f"--parser-style {style!r} is not available for {language}. "
            f"Choose one of: {', '.join(sorted(table))}"
        )
    return table[key]


def subset_dataset(source, destination, limit=None, sample=None, seed=0):
    """Write a subset of a prompt file so every phase of the run sees the same rows.

    ``limit`` keeps the first N lines; ``sample`` draws N at random with ``seed`` and keeps
    them in file order. The subset is written once and reused by code generation, both
    package queries and detection, so the row alignment the pipeline depends on holds.
    """
    with open(source, "r", encoding="utf-8") as infile:
        lines = [line for line in infile if line.strip()]

    if sample:
        if sample < len(lines):
            chosen = sorted(random.Random(seed).sample(range(len(lines)), sample))
            lines = [lines[i] for i in chosen]
    elif limit:
        lines = lines[:limit]

    with open(destination, "w", encoding="utf-8", newline="") as outfile:
        for line in lines:
            outfile.write(line if line.endswith("\n") else line + "\n")
    return destination


def main():
    args = build_parser().parse_args()

    llm_api.load_dotenv()

    if args.list_models:
        try:
            for model_id in llm_api.list_models(args.list_models, args.base_url, args.api_key_env):
                print(model_id)
        except Exception as exc:                                   # noqa: BLE001 - user-facing CLI
            raise SystemExit(f"Could not list models for {args.list_models!r}: {exc}")
        return

    if not args.model:
        raise SystemExit("A model spec is required, e.g. 'ollama:qwen3-coder:30b'. "
                         "See --help, or --list-models <provider>.")

    if args.limit and args.sample:
        raise SystemExit("Use --limit or --sample, not both.")

    if args.logging != "off":
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    try:
        extra_body = json.loads(args.extra_body) if args.extra_body else None
    except ValueError as exc:
        raise SystemExit(f"--extra-body must be valid JSON: {exc}")

    try:
        provider, model_id = llm_api.split_spec(args.model)
        workers = args.workers if args.workers is not None else (1 if provider == "ollama" else 4)
        client = llm_api.Client.from_spec(
            args.model,
            base_url=args.base_url,
            api_key_env=args.api_key_env,
            timeout=args.timeout,
            max_retries=args.max_retries,
            extra_body=extra_body,
            strict=args.strict_sampling,
        )
    except llm_api.ProviderError as exc:
        raise SystemExit(str(exc))

    data_path = os.path.join(os.getcwd(), "Data", args.language)
    run_name = args.name or llm_api.slugify(args.model)
    save_path = os.path.join(os.getcwd(), "Tests", f"{run_name}_{args.language}")
    os.makedirs(save_path, exist_ok=True)

    # Mutable tags can be repointed at different weights; record the immutable identity of
    # what is actually being run so results stay attributable months later.
    identity = llm_api.ollama_identity(args.base_url, model_id) if provider == "ollama" else {}

    overrides = resolve_parser_style(args.parser_style, args.language)
    stats = {}

    def prompt_file(key, file_name):
        """Path to the prompt dataset, subset under Tests/ when --limit or --sample is set."""
        source = os.path.join(data_path, file_name)
        if not (args.limit or args.sample):
            return source
        return subset_dataset(source, os.path.join(save_path, f"{key}_prompts.json"),
                              limit=args.limit, sample=args.sample, seed=args.seed)

    def needs_run(output):
        """Redo a phase whose output exists but recorded per-row failures."""
        return not os.path.exists(output) or os.path.exists(f"{output}.errors.json")

    def generate_and_process_code():
        for key, file_name in DATASETS.items():
            input_path = prompt_file(key, file_name)
            output_code = os.path.join(save_path, f"{key}_code.json")
            master_output = os.path.join(save_path, f"{key}_Master.json")

            if os.path.exists(master_output) and not os.path.exists(f"{output_code}.errors.json"):
                logging.info(f"Master file already exists for {key}. Skipping...")
                continue

            if needs_run(output_code):
                logging.info(f"Generating code for {key}...")
                stats[f"{key}_code"] = generate_code_api.generate_code(
                    input_path, output_code, client, args.language,
                    temperature=args.code_temp, top_k=args.top_k, top_p=args.top_p,
                    max_tokens=args.max_code_tokens, workers=workers, limit=args.limit,
                    fail_on_error=args.fail_on_error)
                logging.info(f"Code generation for {key} complete.")
            else:
                logging.info(f"Code files already exist for {key}. Skipping generation.")

            logging.info(f"Merging code with prompts for {key}...")
            if "LLM" in key:
                aggregate_results.combine_code_and_prompt(input_path, output_code, master_output)
            else:
                aggregate_results.combine_SO_prompt_and_code(input_path, output_code, master_output)
            logging.info(f"Merged code with prompts for {key}.")

    def query_package_names():
        for mode in range(1, 3):
            for key in DATASETS:
                master_path = os.path.join(save_path, f"{key}_Master.json")
                output = os.path.join(save_path, f"{key}_packages_{mode}.json")

                if not os.path.exists(master_path):
                    raise SystemExit(f"{master_path} is missing -- run the 'code' stage first.")
                if not needs_run(output):
                    logging.info(f"Query outputs already exist for {key}, Query {mode}. Skipping...")
                    continue

                logging.info(f"Querying {key} with Query {mode}...")
                stats[f"{key}_packages_{mode}"] = generate_package_names_api.generate_packages(
                    mode, master_path, output, client, args.language,
                    temperature=args.package_temp, top_k=args.top_k, top_p=args.top_p,
                    max_tokens=args.max_package_tokens, workers=workers, limit=args.limit,
                    fail_on_error=args.fail_on_error)
                logging.info(f"Query {mode} for {key} complete.")

    logging.info(f"Starting experiment: {args.model} / {args.language} -> {save_path}")
    try:
        if args.stage in ("all", "code"):
            generate_and_process_code()
        if args.stage in ("all", "packages"):
            query_package_names()
        if args.stage in ("all", "detect"):
            package_detection.detect_packages(data_path, save_path, args.model,
                                              args.logging, args.language, overrides=overrides)
    finally:
        write_manifest(save_path, args, client, workers, overrides, stats, identity)

    logging.info("Experiment complete")


PAPER_DEFAULTS = {
    "code_temp": 0.7, "package_temp": 0.01, "top_k": 20, "top_p": 0.9,
    "max_code_tokens": 2048, "max_package_tokens": 64,
}


def paper_deviations(args):
    """Every knob whose value differs from the paper's, stated plainly in the manifest.

    The response caps deviate by default: the paper's 64-token package cap silently
    starves reasoning models, which spend it on hidden thinking tokens and return
    nothing. Pass the paper values explicitly to reproduce the original setup exactly.
    """
    return {name: {"used": getattr(args, name), "paper": paper}
            for name, paper in PAPER_DEFAULTS.items() if getattr(args, name) != paper}


def write_manifest(save_path, args, client, workers, overrides, stats, identity=None):
    """Record exactly what was sent, so results stay interpretable months later.

    Experiments are often run in stages or resumed days apart, so this merges into any
    existing manifest instead of overwriting it: phase stats accumulate and every
    invocation is appended to ``runs``.
    """
    manifest_path = os.path.join(save_path, "run_manifest.json")
    previous = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as handle:
                previous = json.load(handle)
        except (ValueError, OSError):
            previous = {}

    phases = dict(previous.get("phases") or {})
    phases.update(stats)

    cumulative = previous.get("token_usage_cumulative") or {"prompt_tokens": 0,
                                                            "completion_tokens": 0, "calls": 0}
    for field in cumulative:
        cumulative[field] += client.usage.get(field, 0)

    runs = list(previous.get("runs") or [])
    runs.append({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": " ".join(sys.argv),
        "stage": args.stage,
        "token_usage": dict(client.usage),
        "responses_hitting_token_cap": client.truncated,
        "request_adjustments": dict(client.adjustments),
        "model_identity": identity or {},
        "served_model_ids": dict(client.served_models),
    })

    manifest = {
        "model_spec": args.model,
        "language": args.language,
        "client": client.describe(),
        "model_identity": identity or previous.get("model_identity") or {},
        "sampling_requested": {
            "code_temperature": args.code_temp,
            "package_temperature": args.package_temp,
            "top_k": args.top_k,
            "top_p": args.top_p,
            "max_code_tokens": args.max_code_tokens,
            "max_package_tokens": args.max_package_tokens,
        },
        "deviations_from_paper": paper_deviations(args),
        "workers": workers,
        "limit": args.limit,
        "sample": args.sample,
        "seed": args.seed if args.sample else None,
        "parser_style": {"requested": args.parser_style,
                         "resolved_pre_post_style": list(overrides)},
        "token_usage_cumulative": cumulative,
        "phases": phases,
        "runs": runs,
    }
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    if client.adjustments:
        logging.warning("Request parameters adjusted for this model: %s",
                        json.dumps(client.adjustments, indent=2))
    if client.truncated:
        logging.warning(
            "%d responses stopped at the token cap (%d code / %d package tokens). At the "
            "default caps this should be rare -- a large count means responses are being "
            "cut off, so raise the cap or pass --extra-body '{\"reasoning_effort\": \"low\"}' "
            "to stop a reasoning model spending the budget on hidden thinking tokens.",
            client.truncated, args.max_code_tokens, args.max_package_tokens)
    logging.info("Run manifest written to %s", manifest_path)


if __name__ == "__main__":
    main()
