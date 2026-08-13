"""Campaign 4, Phase 5 -- assemble every preregistered outcome into one results artifact.

Reads the completed runs under Tests/, scores them per PREREGISTRATION_v4.md, and writes
``Experiments/campaign4_results.json``: Track A (legacy + family parser, per seed, cluster
CIs), Track B (Parser v2, dual registry, categories, concentration, cluster CIs on the
invented-both-non-stdlib rate), pairwise paired-by-prompt Track B comparisons with Holm
correction, the Phase 2 cap-diagnostic table, and the final parser validation.

Labels were signed 2026-08-13 (prereg Amendment 4); nothing here is provisional.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import compare_to_paper as ctp
import package_detection
import trackb_score

KEYS = ["LLM_Recent", "LLM_All_Time", "Stack_Overflow_Recent", "Stack_Overflow_All_Time"]
REPS = 2000
TRACK_A = [("codellama:7b-instruct", "CodeLlama 7B", 26.12,
            ["trackA_codellama_7b-instruct_s101_Python",
             "trackA_codellama_7b-instruct_s102_Python",
             "trackA_codellama_7b-instruct_s103_Python"], False),
           ("deepseek-coder:6.7b-instruct", "DeepSeek 6B", 16.61,
            ["trackA_deepseek-coder_6_7b-instruct_s101_Python",
             "trackA_deepseek-coder_6_7b-instruct_s102_Python",
             "trackA_deepseek-coder_6_7b-instruct_s103_Python"], True)]
TRACK_B = [("claude-opus-5", "trackB_anthropic_claude-opus-5_Python"),
           ("gpt-5.2-2025-12-11", "trackB_openai_gpt-5.2_Python"),
           ("gpt-oss:20b", "megatron_gpt-oss_20b_Python"),
           ("grok-4.6", "trackB_xai_grok-4.6_Python"),
           ("deepseek-coder-v2:16b", "trackB_deepseek-coder-v2_16b_Python"),
           ("deepseek-v4-flash", "trackB_deepseek-v4-flash_Python")]


def prompt_text_map(run_dir):
    """(dataset, index) -> prompt text, so cells with different n pair correctly."""
    mapping = {}
    for key in KEYS:
        path = os.path.join(run_dir, f"{key}_prompts.json")
        with open(path, encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if not line.strip():
                    continue
                value = json.loads(line)
                text = value if isinstance(value, str) else str(list(value.values())[0])
                mapping[(key, index)] = text
    return mapping


def bootstrap_rate(per_prompt, rng):
    """One stratified resample -> pooled rate over {key: (h_arr, t_arr)} per dataset."""
    hallucinated = total = 0
    for h, t in per_prompt.values():
        index = rng.integers(0, len(h), len(h))
        hallucinated += h[index].sum()
        total += t[index].sum()
    return 100 * hallucinated / total if total else np.nan


def split_by_dataset(per_prompt_invented):
    out = {}
    for key in KEYS:
        rows = sorted((i, v) for (k, i), v in per_prompt_invented.items() if k == key)
        out[key] = (np.array([v[0] for _, v in rows]), np.array([v[1] for _, v in rows]))
    return out


def family_rescore(run_dir):
    copy = os.path.join("Tests", "_p5_" + os.path.basename(run_dir))
    if os.path.exists(copy):
        shutil.rmtree(copy)
    shutil.copytree(run_dir, copy)
    for name in os.listdir(copy):
        if name.endswith("_results.csv") or name in ("FINAL_RESULTS.csv",
                                                     "PACKAGE_NAMES.csv"):
            os.remove(os.path.join(copy, name))
    package_detection.detect_packages(os.path.join("Data", "Python"), copy, "DeepSeek_6B",
                                      "off", "Python", overrides=(True, True, "DeepSeek"))
    result = ctp.rate_from_results(os.path.join(copy, "FINAL_RESULTS.csv"))
    shutil.rmtree(copy)
    return result


def main():
    rng = np.random.default_rng(0)
    frozen = trackb_score.load_registry(os.path.join("Data", "Python",
                                                     "pypi_package_names.csv"))
    current = trackb_score.load_registry(trackb_score.CURRENT_SNAPSHOT)
    results = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "preregistration": "Experiments/PREREGISTRATION_v4.md",
               "parser_validation": "Experiments/parser_v2_validation.json (FINAL, signed)",
               "phase2_cap_diagnostic": "Experiments/cap_diagnostic_summary.json"}

    # ---------------- Track A ----------------
    track_a = {}
    for model, paper_name, paper_rate, run_names, is_deepseek in TRACK_A:
        seeds = []
        for run_name in run_names:
            run_dir = os.path.join("Tests", run_name)
            legacy = ctp.rate_from_results(os.path.join(run_dir, "FINAL_RESULTS.csv"))
            counts = ctp.prompt_level_counts(run_dir)
            low, high = ctp.cluster_bootstrap(counts)
            entry = {"run": run_name, "legacy_rate_pct": round(legacy["rate"], 2),
                     "cluster_ci": [round(low, 2), round(high, 2)],
                     "packages": legacy["packages"],
                     "ci_contains_paper": bool(low <= paper_rate <= high)}
            if is_deepseek:
                family = family_rescore(run_dir)
                entry["family_parser_rate_pct"] = round(family["rate"], 2)
            seeds.append(entry)
        rates = [s["legacy_rate_pct"] for s in seeds]
        track_a[model] = {"paper": {"name": paper_name, "rate_pct": paper_rate},
                          "seeds": seeds,
                          "seed_mean_pct": round(float(np.mean(rates)), 2),
                          "seed_spread_pp": round(max(rates) - min(rates), 2),
                          "mean_delta_vs_paper_pp": round(float(np.mean(rates)) - paper_rate, 2)}
    results["track_a"] = track_a

    # ---------------- Track B ----------------
    track_b = {}
    per_cell_prompt_data = {}
    for label, run_name in TRACK_B:
        run_dir = os.path.join("Tests", run_name)
        cell = trackb_score.score(run_dir, frozen, current)
        per_prompt = cell.pop("per_prompt_invented")
        arrays = split_by_dataset(per_prompt)
        samples = np.array([bootstrap_rate(arrays, rng) for _ in range(REPS)])
        low, high = np.nanpercentile(samples, [2.5, 97.5])
        cell["invented_cluster_ci"] = [round(float(low), 2), round(float(high), 2)]
        texts = prompt_text_map(run_dir)
        per_cell_prompt_data[label] = {texts[key]: value
                                       for key, value in per_prompt.items()}
        track_b[label] = cell
    results["track_b"] = track_b

    # ---------------- Paired Track B comparisons, Holm-corrected ----------------
    labels = [label for label, _ in TRACK_B]
    comparisons = []
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            a, b = labels[i], labels[j]
            shared = sorted(set(per_cell_prompt_data[a]) & set(per_cell_prompt_data[b]))
            a_h = np.array([per_cell_prompt_data[a][t][0] for t in shared])
            a_t = np.array([per_cell_prompt_data[a][t][1] for t in shared])
            b_h = np.array([per_cell_prompt_data[b][t][0] for t in shared])
            b_t = np.array([per_cell_prompt_data[b][t][1] for t in shared])
            diffs = np.empty(REPS)
            for rep in range(REPS):
                index = rng.integers(0, len(shared), len(shared))
                ra = 100 * a_h[index].sum() / max(a_t[index].sum(), 1)
                rb = 100 * b_h[index].sum() / max(b_t[index].sum(), 1)
                diffs[rep] = ra - rb
            low, high = np.percentile(diffs, [2.5, 97.5])
            p_raw = 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())
            p_raw = max(p_raw, 1 / REPS)
            comparisons.append({"pair": f"{a} vs {b}", "n_shared_prompts": len(shared),
                                "diff_pp": round(float(np.mean(diffs)), 2),
                                "diff_ci": [round(float(low), 2), round(float(high), 2)],
                                "p_raw": round(float(p_raw), 4)})
    comparisons.sort(key=lambda c: c["p_raw"])
    m = len(comparisons)
    running_max = 0.0
    for rank, comp in enumerate(comparisons):
        adjusted = min(1.0, (m - rank) * comp["p_raw"])
        running_max = max(running_max, adjusted)
        comp["p_holm"] = round(running_max, 4)
        comp["significant_05"] = bool(running_max < 0.05)
    results["track_b_paired_holm"] = comparisons

    out = os.path.join("Experiments", "campaign4_results.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    print(f"wrote {out}\n")

    print("== Track A (legacy parser, paper protocol) ==")
    for model, data in track_a.items():
        seeds = ", ".join(f"{s['legacy_rate_pct']}%" for s in data["seeds"])
        fam = ""
        if "family_parser_rate_pct" in data["seeds"][0]:
            fam = "  family: " + ", ".join(f"{s['family_parser_rate_pct']}%"
                                           for s in data["seeds"])
        print(f"  {model:30} paper {data['paper']['rate_pct']}%  seeds [{seeds}]  "
              f"mean {data['seed_mean_pct']}%  Δ {data['mean_delta_vs_paper_pp']:+}pp{fam}")
    print("\n== Track B (Parser v2, invented-both-non-stdlib, cluster CI) ==")
    order = sorted(track_b.items(),
                   key=lambda kv: kv[1]["rate_hallucinated_both_registries_pct"])
    for label, cell in order:
        ci = cell["invented_cluster_ci"]
        print(f"  {label:24} {cell['rate_hallucinated_both_registries_pct']:6.2f}%  "
              f"CI [{ci[0]}, {ci[1]}]  malformed {cell['statuses']['malformed']:>3}  "
              f"top3-share {cell['concentration']['top3_responses_share_pct']}%")
    print("\n== Paired comparisons surviving Holm at 0.05 ==")
    for comp in comparisons:
        if comp["significant_05"]:
            print(f"  {comp['pair']:44} Δ{comp['diff_pp']:+6.2f}pp  "
                  f"CI {comp['diff_ci']}  p_holm={comp['p_holm']}")


if __name__ == "__main__":
    main()
