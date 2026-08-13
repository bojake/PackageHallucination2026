"""Campaign 4, Phase 5 (v4.1 correction pass) -- assemble all preregistered outcomes.

Produces ``Experiments/campaign4_results.json``. This revision incorporates the second
independent review (prereg Amendment 6): one consistent primary metric everywhere (the
**unregistered-PyPI recommendation rate** -- absent from both registries and not a
standard-library module), dataset-stratified paired bootstraps at 50,000 replicates,
Track A acceptance evaluated under the historical family parser, the conforming n=200
gpt-oss cell, per-phase cap-hit rates, the pip-install heuristic scored separately,
Track A Parser-v2 malformed rates, Phase 2 position bands, and the parser-validation
coverage limitation stated in the artifact itself.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone

import numpy as np

import compare_to_paper as ctp
import package_detection
import parser_v2
import trackb_score
from analyze_hallucinations import ordered_parse

KEYS = ["LLM_Recent", "LLM_All_Time", "Stack_Overflow_Recent", "Stack_Overflow_All_Time"]
REPS_CI = 20000
REPS_PAIR = 50000
RNG = np.random.default_rng(0)

TRACK_A = [("codellama:7b-instruct", "CodeLlama 7B", 26.12,
            [f"trackA_codellama_7b-instruct_s{s}_Python" for s in (101, 102, 103)], False),
           ("deepseek-coder:6.7b-instruct", "DeepSeek 6B", 16.61,
            [f"trackA_deepseek-coder_6_7b-instruct_s{s}_Python" for s in (101, 102, 103)],
            True)]
TRACK_B = [("claude-opus-5", "trackB_anthropic_claude-opus-5_Python"),
           ("gpt-5.2-2025-12-11", "trackB_openai_gpt-5.2_Python"),
           ("gpt-oss:20b", "trackB_gptoss_20b_n200_Python"),
           ("grok-4.6", "trackB_xai_grok-4.6_Python"),
           ("deepseek-coder-v2:16b", "trackB_deepseek-coder-v2_16b_Python"),
           ("deepseek-v4-flash", "trackB_deepseek-v4-flash_Python")]


def prompt_text_map(run_dir):
    mapping = {}
    for key in KEYS:
        with open(os.path.join(run_dir, f"{key}_prompts.json"), encoding="utf-8") as fh:
            for index, line in enumerate(fh):
                if not line.strip():
                    continue
                value = json.loads(line)
                mapping[(key, index)] = (value if isinstance(value, str)
                                         else str(list(value.values())[0]))
    return mapping


def stratified_rates(per_prompt, reps):
    """Vectorized stratified bootstrap: pooled rate per replicate."""
    numerator = np.zeros(reps)
    denominator = np.zeros(reps)
    for key in KEYS:
        rows = sorted((i, v) for (k, i), v in per_prompt.items() if k == key)
        h = np.array([v[0] for _, v in rows])
        t = np.array([v[1] for _, v in rows])
        index = RNG.integers(0, len(h), (reps, len(h)))
        numerator += h[index].sum(axis=1)
        denominator += t[index].sum(axis=1)
    return 100 * numerator / np.maximum(denominator, 1)


def response_statuses(run_dir):
    counts = {"list": 0, "malformed": 0, "empty": 0}
    for key in KEYS:
        for mode in (1, 2):
            with open(os.path.join(run_dir, f"{key}_packages_{mode}.json"),
                      encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        status, _ = parser_v2.classify(str(json.loads(line)))
                        counts[status] += 1
    return counts


def pip_heuristic(run_dir):
    import pandas as pd
    valid = hallucinated = 0
    for prefix in ("LLM_LY", "LLM_AT", "SO_LY", "SO_AT"):
        frame = pd.read_csv(os.path.join(run_dir, f"{prefix}_results.csv"))
        valid += int(frame["pip_valid"].map(ctp._count_cell).sum())
        hallucinated += int(frame["pip_hallucinated"].map(ctp._count_cell).sum())
    total = valid + hallucinated
    return {"valid": valid, "hallucinated": hallucinated,
            "rate_pct": round(100 * hallucinated / total, 2) if total else None}


def cap_hits(run_dir):
    path = os.path.join(run_dir, "run_manifest.json")
    manifest = json.load(open(path, encoding="utf-8"))
    return {phase: stats.get("truncated_new_requests")
            for phase, stats in manifest.get("phases", {}).items()
            if stats.get("truncated_new_requests")} or {}


def family_rescore_with_ci(run_dir, paper_rate):
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
    low, high = ctp.cluster_bootstrap(ctp.prompt_level_counts(copy))
    shutil.rmtree(copy)
    return {"rate_pct": round(result["rate"], 2),
            "cluster_ci": [round(low, 2), round(high, 2)],
            "ci_contains_paper": bool(low <= paper_rate <= high)}


def phase2_position_bands(frozen):
    bands = {}
    raw_dir = os.path.join("Tests", "cap_diagnostic")
    for name in os.listdir(raw_dir):
        model = name.replace(".jsonl", "")
        table = {}
        with open(os.path.join(raw_dir, name), encoding="utf-8") as fh:
            for line in fh:
                record = json.loads(line)
                if record.get("phase") != "package_query":
                    continue
                content = ((record.get("response") or {}).get("message") or {}
                           ).get("content", "") or ""
                status, packages = parser_v2.classify(content)
                if status != "list":
                    continue
                slot = table.setdefault((record["cap"], record["query"]), {})
                for position, pkg in enumerate(packages, 1):
                    band = min(position, 5)
                    cell = slot.setdefault(band, [0, 0])
                    cell[1] += 1
                    cell[0] += package_detection.normalize_python(pkg) not in frozen
        bands[model] = {f"cap={cap}|q{query}": {
                            f"p{band}{'+' if band == 5 else ''}":
                            f"{100 * h / t:.1f}% (n={t})"
                            for band, (h, t) in sorted(slot.items())}
                        for (cap, query), slot in sorted(table.items())}
    return bands


def main():
    frozen = trackb_score.load_registry(os.path.join("Data", "Python",
                                                     "pypi_package_names.csv"))
    current = trackb_score.load_registry(trackb_score.CURRENT_SNAPSHOT)
    validation = json.load(open("Experiments/parser_v2_validation.json", encoding="utf-8"))

    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "revision": "v4.1 correction pass (prereg Amendment 6)",
        "preregistration": "Experiments/PREREGISTRATION_v4.md",
        "primary_metric": ("unregistered-PyPI recommendation rate: named package absent "
                           "from BOTH the frozen 2024-01-10 and current 2026-08-12 "
                           "registries and not a standard-library module. Not every such "
                           "name is invented -- degenerate responses often name real "
                           "system/apt/npm tooling that is simply not installable from "
                           "PyPI."),
        "parser_validation": {"file": "Experiments/parser_v2_validation.json",
                              "status": validation["status"],
                              "coverage_limitation": (
                                  "the labeling sample was drawn from the pre-campaign "
                                  "runs (CodeLlama, DeepSeek 6.7B, gpt-oss) before the "
                                  "hosted cells existed; hosted-model response formats "
                                  "are not represented in the validated sample")},
        "phase2_cap_diagnostic": "Experiments/cap_diagnostic_summary.json",
    }

    # ---------------- Track A ----------------
    track_a = {}
    for model, paper_name, paper_rate, run_names, is_deepseek in TRACK_A:
        seeds = []
        for run_name in run_names:
            run_dir = os.path.join("Tests", run_name)
            legacy = ctp.rate_from_results(os.path.join(run_dir, "FINAL_RESULTS.csv"))
            low, high = ctp.cluster_bootstrap(ctp.prompt_level_counts(run_dir))
            entry = {"run": run_name,
                     "generic_parser": {"rate_pct": round(legacy["rate"], 2),
                                        "cluster_ci": [round(low, 2), round(high, 2)],
                                        "ci_contains_paper":
                                            bool(low <= paper_rate <= high)},
                     "parser_v2_statuses": response_statuses(run_dir),
                     "pip_heuristic": pip_heuristic(run_dir),
                     "cap_hits_per_phase": cap_hits(run_dir)}
            if is_deepseek:
                entry["family_parser"] = family_rescore_with_ci(run_dir, paper_rate)
            seeds.append(entry)
        rates = [s["generic_parser"]["rate_pct"] for s in seeds]
        summary = {"paper": {"name": paper_name, "rate_pct": paper_rate},
                   "seeds": seeds,
                   "seed_mean_pct": round(float(np.mean(rates)), 2),
                   "seed_spread_pp": round(max(rates) - min(rates), 2),
                   "mean_delta_vs_paper_pp":
                       round(float(np.mean(rates)) - paper_rate, 2)}
        if is_deepseek:
            family_rates = [s["family_parser"]["rate_pct"] for s in seeds]
            summary["family_seed_mean_pct"] = round(float(np.mean(family_rates)), 2)
            summary["acceptance_under_historical_parser"] = (
                "ordering and broad magnitude reproduce; exact replication does NOT -- "
                "all three family-parser CIs exclude the published value")
        track_a[model] = summary
    results["track_a"] = track_a

    # ---------------- Track B ----------------
    track_b = {}
    per_cell = {}
    for label, run_name in TRACK_B:
        run_dir = os.path.join("Tests", run_name)
        cell = trackb_score.score(run_dir, frozen, current)
        per_prompt = cell.pop("per_prompt_invented")
        samples = stratified_rates(per_prompt, REPS_CI)
        low, high = np.nanpercentile(samples, [2.5, 97.5])
        cell["unregistered_cluster_ci"] = [round(float(low), 2), round(float(high), 2)]
        cell["pip_heuristic"] = pip_heuristic(run_dir)
        cell["cap_hits_per_phase"] = cap_hits(run_dir)
        texts = prompt_text_map(run_dir)
        per_cell[label] = {(key[0], texts[key]): value
                           for key, value in per_prompt.items()}
        track_b[label] = cell
    results["track_b"] = track_b

    # ------- Paired comparisons: dataset-stratified, 50k replicates, Holm -------
    labels = [label for label, _ in TRACK_B]
    comparisons = []
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            a, b = labels[i], labels[j]
            shared = sorted(set(per_cell[a]) & set(per_cell[b]))
            numerator_a = np.zeros(REPS_PAIR)
            denominator_a = np.zeros(REPS_PAIR)
            numerator_b = np.zeros(REPS_PAIR)
            denominator_b = np.zeros(REPS_PAIR)
            for key in KEYS:
                stratum = [s for s in shared if s[0] == key]
                if not stratum:
                    continue
                a_h = np.array([per_cell[a][s][0] for s in stratum])
                a_t = np.array([per_cell[a][s][1] for s in stratum])
                b_h = np.array([per_cell[b][s][0] for s in stratum])
                b_t = np.array([per_cell[b][s][1] for s in stratum])
                index = RNG.integers(0, len(stratum), (REPS_PAIR, len(stratum)))
                numerator_a += a_h[index].sum(axis=1)
                denominator_a += a_t[index].sum(axis=1)
                numerator_b += b_h[index].sum(axis=1)
                denominator_b += b_t[index].sum(axis=1)
            diffs = (100 * numerator_a / np.maximum(denominator_a, 1)
                     - 100 * numerator_b / np.maximum(denominator_b, 1))
            low, high = np.percentile(diffs, [2.5, 97.5])
            p_raw = max(2 * min((diffs <= 0).mean(), (diffs >= 0).mean()), 1 / REPS_PAIR)
            comparisons.append({"pair": f"{a} vs {b}",
                                "n_shared_prompts": len(shared),
                                "diff_pp": round(float(np.mean(diffs)), 2),
                                "diff_ci": [round(float(low), 2), round(float(high), 2)],
                                "p_raw": round(float(p_raw), 5)})
    comparisons.sort(key=lambda c: c["p_raw"])
    running_max = 0.0
    for rank, comp in enumerate(comparisons):
        adjusted = min(1.0, (len(comparisons) - rank) * comp["p_raw"])
        running_max = max(running_max, adjusted)
        comp["p_holm"] = round(running_max, 4)
        comp["significant_05"] = bool(running_max < 0.05)
    results["track_b_paired_holm"] = comparisons

    # ---------------- Phase 2 position bands ----------------
    results["phase2_position_bands"] = phase2_position_bands(frozen)

    out = os.path.join("Experiments", "campaign4_results.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    print(f"wrote {out}\n")

    print("== Track A ==")
    for model, data in track_a.items():
        seeds = ", ".join(f"{s['generic_parser']['rate_pct']}%" for s in data["seeds"])
        print(f"  {model:30} paper {data['paper']['rate_pct']}%  generic [{seeds}]  "
              f"mean {data['seed_mean_pct']}%  Δ {data['mean_delta_vs_paper_pp']:+}pp")
        if "family_seed_mean_pct" in data:
            fam = ", ".join(f"{s['family_parser']['rate_pct']}% "
                            f"CI{s['family_parser']['cluster_ci']}"
                            for s in data["seeds"])
            print(f"  {'':30} family [{fam}] -- CIs exclude paper: "
                  f"{all(not s['family_parser']['ci_contains_paper'] for s in data['seeds'])}")
    print("\n== Track B (unregistered-PyPI rate, cluster CI) ==")
    for label, cell in sorted(track_b.items(),
                              key=lambda kv: kv[1]["rate_unregistered_pypi_pct"]):
        ci = cell["unregistered_cluster_ci"]
        print(f"  {label:24} {cell['rate_unregistered_pypi_pct']:6.2f}%  "
              f"CI [{ci[0]}, {ci[1]}]  P(prompt≥1) {cell['prompt_level_risk_pct']}%  "
              f"unique {cell['unique_unregistered_names']}  "
              f"top3 {cell['concentration']['top3_responses_share_pct']}%")
    significant = [c for c in comparisons if c["significant_05"]]
    print(f"\n== Holm-significant pairs at 0.05: {len(significant)}/15 ==")
    for comp in significant:
        print(f"  {comp['pair']:44} Δ{comp['diff_pp']:+7.2f}pp  CI {comp['diff_ci']}  "
              f"p_holm={comp['p_holm']}")
    borderline = [c for c in comparisons if not c["significant_05"] and c["p_holm"] < 0.10]
    for comp in borderline:
        print(f"  (borderline) {comp['pair']:31} Δ{comp['diff_pp']:+7.2f}pp  "
              f"p_holm={comp['p_holm']}")


if __name__ == "__main__":
    main()
