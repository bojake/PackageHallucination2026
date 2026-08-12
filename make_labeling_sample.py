"""Build the Parser v2 validation sample (Campaign 4, Phase 1).

Draws a stratified sample of raw package-query responses from the existing runs, classifies
each with Parser v2, and writes a labeling file. The assistant drafts labels; the maintainer
reviews and signs them; precision/recall are computed against the signed labels before any
Phase 5 scoring.

Output (under Tests/, not committed -- responses contain hallucinated names):
    Tests/parser_v2_labeling/sample.jsonl   one record per response
    Tests/parser_v2_labeling/README.md      review instructions

Record fields: id, run, dataset, mode, text, parser_status, parser_packages, plus empty
draft_* fields (assistant) and maintainer_verdict ("" -> "ok" or corrected label).
"""

from __future__ import annotations

import json
import os
import random

import parser_v2

RUNS = [
    ("ds64", os.path.join("Tests", "megatron_deepseek_6.7b_Python")),
    ("ds2048", os.path.join("Tests", "megatron_deepseek_6.7b_cap2048_Python")),
    ("cl400", os.path.join("Tests", "megatron_codellama_7b-instruct_Python")),
    ("gptoss", os.path.join("Tests", "megatron_gpt-oss_20b_Python")),
]
KEYS = ["LLM_Recent", "LLM_All_Time", "Stack_Overflow_Recent", "Stack_Overflow_All_Time"]
TARGET_PER_RUN = 50   # 25 list-classified + 25 malformed/empty where available
SEED = 4


def main():
    rng = random.Random(SEED)
    records = []
    for run_label, run_dir in RUNS:
        pool = {"list": [], "other": []}
        for key in KEYS:
            for mode in (1, 2):
                path = os.path.join(run_dir, f"{key}_packages_{mode}.json")
                if not os.path.exists(path):
                    continue
                with open(path, encoding="utf-8") as handle:
                    for index, line in enumerate(handle):
                        if not line.strip():
                            continue
                        text = str(json.loads(line))
                        status, packages = parser_v2.classify(text)
                        bucket = "list" if status == "list" else "other"
                        pool[bucket].append((key, mode, index, text, status, packages))
        half = TARGET_PER_RUN // 2
        chosen = (rng.sample(pool["list"], min(half, len(pool["list"])))
                  + rng.sample(pool["other"], min(half, len(pool["other"]))))
        deficit = TARGET_PER_RUN - len(chosen)
        if deficit > 0:
            spare = [x for x in pool["list"] + pool["other"] if x not in chosen]
            chosen += rng.sample(spare, min(deficit, len(spare)))
        for key, mode, index, text, status, packages in chosen:
            records.append({
                "id": f"{run_label}:{key}:q{mode}:{index}",
                "run": run_label, "dataset": key, "mode": mode,
                "text": text,
                "parser_status": status,
                "parser_packages": packages,
                "draft_status": "",
                "draft_packages": [],
                "draft_note": "",
                "maintainer_verdict": "",
            })

    rng.shuffle(records)
    out_dir = os.path.join("Tests", "parser_v2_labeling")
    os.makedirs(out_dir, exist_ok=True)
    sample_path = os.path.join(out_dir, "sample.jsonl")
    with open(sample_path, "w", encoding="utf-8", newline="") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")

    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as handle:
        handle.write(
            "# Parser v2 labeling sample\n\n"
            "One JSON record per line in `sample.jsonl`. For each record the question is:\n"
            "what packages did this response actually recommend?\n\n"
            "- `parser_status` / `parser_packages`: what Parser v2 extracted.\n"
            "- `draft_status` / `draft_packages`: the assistant's independent reading of the\n"
            "  response (filled in before review).\n"
            "- `maintainer_verdict`: set to `ok` to accept the draft, or write the corrected\n"
            "  status/packages. Precision/recall are computed against the signed labels.\n\n"
            "Statuses: `list` (a package list; packages listed), `malformed` (prose/code/\n"
            "mixed -- no clean package list), `empty`.\n")

    by_run = {}
    for record in records:
        key = (record["run"], record["parser_status"])
        by_run[key] = by_run.get(key, 0) + 1
    print(f"wrote {len(records)} records -> {sample_path}")
    for (run_label, status), count in sorted(by_run.items()):
        print(f"  {run_label:8} {status:10} {count}")


if __name__ == "__main__":
    main()
