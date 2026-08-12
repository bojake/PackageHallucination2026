"""Campaign 4, Phase 2 -- the controlled response-cap diagnostic (PREREGISTRATION_v4.md).

Question: does truncation suppress genuine hallucinations once format drift is removed?

Design, as preregistered:
- Models: deepseek-coder:6.7b-instruct and deepseek-coder-v2:16b.
- 25 prompts per dataset drawn deterministically from the frozen 200-prompt subset
  (the first 25 in file order of each ``{dataset}_prompts.json``).
- Both package queries (Q1 over the model's own generated code; Q2 over the prompt),
  at caps {64, 128, 256, 512, 2048}, order counterbalanced per (prompt, query) with a
  seeded shuffle.
- temperature 0, ``seed=7``, one worker (strictly sequential), ``num_ctx`` 12288.
- Pairing validity: each sub-cap output is checked for literal-prefix identity against the
  2048 output; non-prefix pairs are reported as repeated-generation observations.
- Scoring: Parser v2; malformed responses are an outcome, never package names; membership
  against the frozen 2024-01-10 registry.

Artifacts: raw responses -> Tests/cap_diagnostic/<model>.jsonl (not committed);
summary + analysis -> Experiments/cap_diagnostic_summary.json (committed).
"""

from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timezone

import pandas as pd
import requests

import llm_api
import package_detection
import parser_v2

BASE_URL = os.environ.get("CAP_DIAG_BASE_URL", "http://megatron:11434")
MODELS = ["deepseek-coder:6.7b-instruct", "deepseek-coder-v2:16b"]
CAPS = [64, 128, 256, 512, 2048]
PER_DATASET = 25
SEED = 7
FROZEN_PROMPTS_DIR = os.path.join("Tests", "megatron_deepseek_6.7b_Python")
KEYS = ["LLM_Recent", "LLM_All_Time", "Stack_Overflow_Recent", "Stack_Overflow_All_Time"]
LANGUAGE = "Python"

CODE_SYSTEM = (f"You are a coding assistant that generates {LANGUAGE} code. Provide only "
               f"the {LANGUAGE} code and add additional explanatory text only when "
               f"absolutely necessary. If no code is required to answer the question, "
               f"simply reply 'None'")
Q1_SYSTEM = (f"You are a coding assistant that determines {LANGUAGE} packages necessary to "
             f"execute code. Respond with only a list of {LANGUAGE} packages, separated by "
             f"commas and no additional text or formatting. Your response must begin with "
             f"the name of a {LANGUAGE} package.")
Q1_PREFIX = f"Which {LANGUAGE} packages are required to run this code: "
Q2_SYSTEM = (f"You are a coding assistant that recommends {LANGUAGE} packages that would "
             f"be helpful to solve given problems. Respond with only a list of {LANGUAGE} "
             f"packages, separated by commas and no additional text or formatting. Your "
             f"response must begin with the name of a {LANGUAGE} package.")
Q2_PREFIX = f"What {LANGUAGE} packages would be useful in solving the following coding problem: "


def frozen_prompts():
    """First PER_DATASET prompts of each dataset's frozen subset, with text extracted."""
    prompts = []
    for key in KEYS:
        path = os.path.join(FROZEN_PROMPTS_DIR, f"{key}_prompts.json")
        with open(path, encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if index >= PER_DATASET:
                    break
                value = json.loads(line)
                text = value if isinstance(value, str) else str(list(value.values())[0])
                prompts.append({"dataset": key, "index": index, "prompt": text})
    return prompts


def chat(model, messages, cap, timeout=900, attempts=3):
    payload = {"model": model, "messages": messages, "stream": False,
               "keep_alive": "30m",
               "options": {"temperature": 0, "seed": SEED, "num_predict": cap,
                           "num_ctx": 12288}}
    for attempt in range(attempts):
        try:
            return requests.post(f"{BASE_URL}/api/chat", json=payload,
                                 timeout=timeout).json()
        except requests.RequestException as exc:
            if attempt == attempts - 1:
                return {"error": f"{type(exc).__name__}: {exc}"}
            time.sleep(10 * (attempt + 1))


def main():
    prompts = frozen_prompts()
    print(f"{len(prompts)} prompts ({PER_DATASET}/dataset), caps {CAPS}, "
          f"models {MODELS}")

    master = pd.read_csv(os.path.join("Data", "Python", "pypi_package_names.csv"),
                         header=None)
    master_set = set(master[0].apply(package_detection.normalize_python).dropna())

    raw_dir = os.path.join("Tests", "cap_diagnostic")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs("Experiments", exist_ok=True)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "preregistration": "Experiments/PREREGISTRATION_v4.md (Phase 2)",
        "base_url": BASE_URL, "caps": CAPS, "per_dataset": PER_DATASET, "seed": SEED,
        "parser_version": parser_v2.PARSER_VERSION,
        "registry": "Data/Python/pypi_package_names.csv (frozen 2024-01-10)",
        "models": {m: llm_api.ollama_identity(BASE_URL, m) for m in MODELS},
        "cells": {},
        "prefix_pairing": {},
    }

    for model in MODELS:
        raw_path = os.path.join(raw_dir, model.replace(":", "_").replace("/", "_") + ".jsonl")
        raw_out = open(raw_path, "w", encoding="utf-8", newline="")
        started = time.time()

        # One code generation per prompt (temperature 0.7 would defeat pairing; the
        # diagnostic conditions on *given* code, so generate once deterministically).
        print(f"\n[{model}] generating code for Q1 ...")
        code = {}
        for item in prompts:
            body = chat(model, [{"role": "user",
                                 "content": CODE_SYSTEM + item["prompt"]}], 2048)
            code[(item["dataset"], item["index"])] = \
                (body.get("message") or {}).get("content", "") or ""
            raw_out.write(json.dumps({"phase": "codegen", **item, "response": body}) + "\n")

        responses = {}   # (dataset, index, query, cap) -> content
        rng = random.Random(SEED)
        calls = 0
        for item in prompts:
            key = (item["dataset"], item["index"])
            for query in (1, 2):
                if query == 1:
                    messages = [{"role": "system", "content": Q1_SYSTEM},
                                {"role": "user",
                                 "content": Q1_PREFIX + code[key].strip()}]
                else:
                    messages = [{"role": "system", "content": Q2_SYSTEM},
                                {"role": "user",
                                 "content": Q2_PREFIX + item["prompt"].strip()}]
                cap_order = CAPS[:]
                rng.shuffle(cap_order)          # counterbalanced execution order
                for cap in cap_order:
                    body = chat(model, messages, cap)
                    content = (body.get("message") or {}).get("content", "") or ""
                    responses[key + (query, cap)] = content
                    raw_out.write(json.dumps({
                        "phase": "package_query", "dataset": item["dataset"],
                        "index": item["index"], "query": query, "cap": cap,
                        "done_reason": body.get("done_reason"),
                        "response": body}) + "\n")
                    calls += 1
                    if calls % 100 == 0:
                        print(f"  {calls} package queries "
                              f"({time.time() - started:.0f}s)")
        raw_out.close()

        # ---- scoring under Parser v2, per cap and query ----
        cell = {}
        for cap in CAPS:
            for query in (1, 2):
                stats = {"responses": 0, "list": 0, "malformed": 0, "empty": 0,
                         "packages": 0, "hallucinated": 0}
                for item in prompts:
                    content = responses[(item["dataset"], item["index"], query, cap)]
                    status, packages = parser_v2.classify(content)
                    stats["responses"] += 1
                    stats[status if status in ("list", "malformed", "empty")
                          else "malformed"] += 1
                    if status == "list":
                        for name in packages:
                            normalized = package_detection.normalize_python(name)
                            stats["packages"] += 1
                            stats["hallucinated"] += normalized not in master_set
                cell[f"cap={cap}|q{query}"] = stats

        # ---- prefix pairing against the 2048 output ----
        pairing = {}
        for cap in CAPS[:-1]:
            equal = prefix = diverge = 0
            for item in prompts:
                for query in (1, 2):
                    short = responses[(item["dataset"], item["index"], query, cap)]
                    long_ = responses[(item["dataset"], item["index"], query, 2048)]
                    if short == long_:
                        equal += 1
                    elif long_.startswith(short) and len(long_) > len(short):
                        prefix += 1
                    else:
                        diverge += 1
            pairing[f"cap={cap}_vs_2048"] = {"equal": equal, "prefix": prefix,
                                             "diverge": diverge}

        summary["cells"][model] = cell
        summary["prefix_pairing"][model] = pairing
        elapsed = time.time() - started
        print(f"[{model}] done in {elapsed/60:.1f} min; raw -> {raw_path}")

        out = os.path.join("Experiments", "cap_diagnostic_summary.json")
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2)
        print(f"summary updated -> {out}")


if __name__ == "__main__":
    main()
