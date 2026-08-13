"""Provisional Track B scorer (Campaign 4). PROVISIONAL until the Parser v2 labeling
sample is signed by the maintainer (PREREGISTRATION_v4.md, Amendment 2).

Scores a run's package-query responses with Parser v2 against both registries (frozen
2024-01-10 and the dated current snapshot), and reports the preregistered outcomes:
occurrence rates, prompt-level risk, malformed/empty rates, packages per response, and
concentration (how much of the total the worst responses carry). Query responses only --
the pip-install heuristic is scored separately in Phase 5.

    python trackb_score.py Tests/<run> [Tests/<run> ...]
"""

from __future__ import annotations

import json
import os
import sys

import pandas as pd

import package_detection
import parser_v2

# Standard-library module names, normalized like package names. Mentioning these is
# module-vs-package confusion (its own preregistered category), not registry membership:
# many were squat-registered on PyPI in the frozen 2024 list and purged since, so letting
# either registry decide them scores the same model behaviour oppositely by date.
STDLIB = {package_detection.normalize_python(m) for m in sys.stdlib_module_names}

KEYS = ["LLM_Recent", "LLM_All_Time", "Stack_Overflow_Recent", "Stack_Overflow_All_Time"]
CURRENT_SNAPSHOT = os.path.join("Data", "Python", "pypi_package_names_2026-08-12.csv")


def load_registry(path):
    frame = pd.read_csv(path, header=None)
    return set(frame[0].dropna().astype(str).apply(package_detection.normalize_python))


def score(run_dir, frozen, current):
    per_prompt = {}            # (dataset, index) -> [hallucinated, total] (frozen registry)
    per_prompt_invented = {}   # (dataset, index) -> [invented-both-non-stdlib, total]
    statuses = {"list": 0, "malformed": 0, "empty": 0}
    occurrences = {"frozen": [0, 0], "current": [0, 0]}
    categories = {"valid_both": 0, "stdlib_mention": 0, "post_snapshot_package": 0,
                  "deleted_since_snapshot": 0, "hallucinated_both": 0}
    per_response = []
    for key in KEYS:
        for mode in (1, 2):
            path = os.path.join(run_dir, f"{key}_packages_{mode}.json")
            if not os.path.exists(path):
                return None
            with open(path, encoding="utf-8") as handle:
                for index, line in enumerate(handle):
                    if not line.strip():
                        continue
                    status, packages = parser_v2.classify(str(json.loads(line)))
                    statuses[status] += 1
                    slot = per_prompt.setdefault((key, index), [0, 0])
                    invented_slot = per_prompt_invented.setdefault((key, index), [0, 0])
                    hallucinated_here = 0
                    for name in packages:
                        normalized = package_detection.normalize_python(name)
                        for registry, member_set in (("frozen", frozen),
                                                     ("current", current)):
                            occurrences[registry][1] += 1
                            occurrences[registry][0] += normalized not in member_set
                        in_frozen = normalized in frozen
                        in_current = normalized in current
                        invented_slot[1] += 1
                        invented_slot[0] += (normalized not in frozen
                                             and normalized not in current
                                             and normalized not in STDLIB)
                        if normalized in STDLIB:
                            categories["stdlib_mention"] += 1
                        elif in_frozen and in_current:
                            categories["valid_both"] += 1
                        elif in_current:
                            categories["post_snapshot_package"] += 1
                        elif in_frozen:
                            categories["deleted_since_snapshot"] += 1
                        else:
                            categories["hallucinated_both"] += 1
                        missing = not in_frozen
                        hallucinated_here += missing
                        slot[0] += missing
                        slot[1] += 1
                    if status == "list":
                        per_response.append(hallucinated_here)

    result = {"run": os.path.basename(run_dir), "statuses": statuses,
              "provisional": "labels not yet signed"}
    for registry, (hallucinated, total) in occurrences.items():
        result[f"rate_{registry}"] = {
            "rate_pct": round(100 * hallucinated / total, 2) if total else None,
            "hallucinated": hallucinated, "packages": total}
    result["categories"] = categories
    total_occ = occurrences["frozen"][1] or 1
    result["rate_hallucinated_both_registries_pct"] = round(
        100 * categories["hallucinated_both"] / total_occ, 2)
    prompts_any = sum(1 for h, _ in per_prompt.values() if h)
    result["prompt_level_risk_pct"] = round(100 * prompts_any / len(per_prompt), 2)
    per_response.sort(reverse=True)
    total_h = sum(per_response) or 1
    result["concentration"] = {
        "top3_responses_share_pct": round(100 * sum(per_response[:3]) / total_h, 1),
        "max_single_response": per_response[0] if per_response else 0}
    listed = statuses["list"] or 1
    result["packages_per_list_response"] = round(
        occurrences["frozen"][1] / listed, 2)
    result["per_prompt_invented"] = per_prompt_invented   # popped before printing in main()
    return result


def main():
    frozen = load_registry(os.path.join("Data", "Python", "pypi_package_names.csv"))
    current = load_registry(CURRENT_SNAPSHOT)
    for run_dir in sys.argv[1:]:
        result = score(run_dir, frozen, current)
        if result is None:
            print(f"{run_dir}: response files missing")
            continue
        result.pop("per_prompt_invented", None)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
