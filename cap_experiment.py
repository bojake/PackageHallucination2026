"""Controlled test: the paper's 64-token package-query cap on a reasoning model.

Takes N real generated code samples from an existing run, issues the paper's Query 1
verbatim, and varies only the response cap -- reasoning model and non-reasoning control.
An instrument that returns empty content at the paper's cap scores a model as
"recommended no packages", which reads downstream as a near-zero hallucination rate.

Artifacts:
- ``Experiments/cap_experiment_summary.json`` (committed): per-condition counts, input
  provenance (source file + SHA-256 + line indices), model digests, server version.
- ``Tests/cap_experiment/raw_responses.jsonl`` (NOT committed): every raw response body.
  Kept out of the repository deliberately -- responses contain hallucinated package
  names, which this repository does not publish (see Security & Ethics in the README).
  Auditors reproduce the raw file by re-running this script.

Run only when nothing else is using the GPU: it loads two models in turn, and on a 24 GB
box a concurrent workload forces eviction thrashing.

    python cap_experiment.py --base-url http://megatron:11434
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone

import requests

import custom_parse_python
import llm_api
import package_detection

LANGUAGE = "Python"
# Verbatim from generate_package_names.py, mode 1.
SYSTEM = (f"You are a coding assistant that determines {LANGUAGE} packages necessary to "
          f"execute code. Respond with only a list of {LANGUAGE} packages, separated by "
          f"commas and no additional text or formatting. Your response must begin with the "
          f"name of a {LANGUAGE} package.")
PREFIX = f"Which {LANGUAGE} packages are required to run this code: "


def parse_like_paper(text):
    """The default Python path in package_detection: split, normalize, keep single words."""
    items = [package_detection.normalize_python(p) for p in str(text).split(",")]
    items = [i for i in items if len(i.split()) == 1]
    return custom_parse_python.delete_dupes_and_empty(items)


def call(base_url, model, code, cap, num_ctx, timeout, attempts=3):
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": PREFIX + code.strip()}],
        "stream": False,
        "keep_alive": "15m",
        "options": {"temperature": 0.01, "top_k": 20, "top_p": 0.9,
                    "num_predict": cap, "num_ctx": num_ctx},
    }
    for attempt in range(attempts):
        try:
            return requests.post(f"{base_url}/api/chat", json=payload, timeout=timeout).json()
        except requests.RequestException as exc:
            if attempt == attempts - 1:
                return {"error": f"{type(exc).__name__}: {exc}"}
            time.sleep(5 * (attempt + 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--code-file",
                        default=os.path.join("Tests", "ollama_codellama_7b-instruct_Python",
                                             "LLM_Recent_code.json"),
                        help="JSON-lines file of generated code samples from a prior run")
    parser.add_argument("--n", type=int, default=15)
    parser.add_argument("--reasoning-model", default="gpt-oss:20b")
    parser.add_argument("--control-model", default="codellama:7b-instruct")
    parser.add_argument("--caps", type=int, nargs="+", default=[64, 2048])
    parser.add_argument("--num-ctx", type=int, default=12288)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    with open(args.code_file, "rb") as handle:
        raw = handle.read()
    source_sha = hashlib.sha256(raw).hexdigest()
    samples = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    used = [(index, text) for index, text in enumerate(samples) if str(text).strip()][:args.n]
    print(f"{len(used)} code samples from {args.code_file} (sha256 {source_sha[:16]}...)\n")

    raw_dir = os.path.join("Tests", "cap_experiment")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs("Experiments", exist_ok=True)
    raw_path = os.path.join(raw_dir, "raw_responses.jsonl")

    models = [(args.reasoning_model, "reasoning"), (args.control_model, "control")]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base_url": args.base_url,
        "query": {"system": SYSTEM, "prefix": PREFIX,
                  "sampling": {"temperature": 0.01, "top_k": 20, "top_p": 0.9,
                               "num_ctx": args.num_ctx}},
        "input": {"file": args.code_file, "sha256": source_sha,
                  "line_indices": [index for index, _ in used]},
        "models": {name: {"role": role,
                          "identity": llm_api.ollama_identity(args.base_url, name)}
                   for name, role in models},
        "raw_responses": f"{raw_path} (not committed -- contains hallucinated names; "
                         f"regenerate by re-running this script)",
        "conditions": {},
    }

    with open(raw_path, "w", encoding="utf-8") as raw_out:
        for model, role in models:
            print(f"{model}  ({role})")
            for cap in args.caps:
                stats = {"empty": 0, "hit_cap": 0, "packages_extracted": 0, "failed": 0,
                         "n": len(used)}
                started = time.time()
                for index, code in used:
                    body = call(args.base_url, model, code, cap, args.num_ctx, args.timeout)
                    raw_out.write(json.dumps({"model": model, "cap": cap,
                                              "source_line": index, "response": body}) + "\n")
                    if "error" in body and "message" not in body:
                        stats["failed"] += 1
                        continue
                    content = (body.get("message") or {}).get("content", "") or ""
                    if not content.strip():
                        stats["empty"] += 1
                    if body.get("done_reason") == "length":
                        stats["hit_cap"] += 1
                    stats["packages_extracted"] += len(parse_like_paper(content))
                stats["seconds"] = round(time.time() - started, 1)
                summary["conditions"][f"{model}|cap={cap}"] = stats
                print(f"    cap={cap:<5} empty={stats['empty']}/{stats['n']}  "
                      f"hit_cap={stats['hit_cap']}/{stats['n']}  "
                      f"packages_extracted={stats['packages_extracted']}  "
                      f"failed={stats['failed']}  ({stats['seconds']}s)")
            print()

    out = os.path.join("Experiments", "cap_experiment_summary.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    print(f"summary  -> {out}")
    print(f"raw      -> {raw_path} (kept locally, not committed)")


if __name__ == "__main__":
    main()
