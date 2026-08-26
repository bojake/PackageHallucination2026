"""Post-hoc diagnostics for the Qwen 3.5 / Kimi K2.7 Ollama Cloud extension.

The preregistered scorer and its headline results remain untouched.  This script asks
whether response truncation, query type, extreme list volume, or package position explain
the Kimi K2.7 result.  The first campaign runner recorded cap-hit counts per phase but not
per-response finish reasons, so the cap sensitivity deliberately uses a labeled proxy:
within each phase, the N longest responses are marked where N is that phase's recorded
cap-hit count.  It must not be described as exact cap-hit identification.
"""

from __future__ import annotations

import json
import os
import statistics
from collections import Counter
from itertools import combinations
from datetime import datetime, timezone

import numpy as np

import post_campaign_analysis as campaign


CELLS = [
    ("qwen3.5:cloud", "trackC_ollama_qwen3-5-cloud_Python"),
    ("kimi-k2.7-code:cloud", "trackC_ollama_kimi-k2-7-code-cloud_Python"),
]
OUT_JSON = os.path.join("Experiments", "ollama_cloud_extension_post_analysis.json")
OUT_MD = os.path.join("Experiments", "OLLAMA_CLOUD_EXTENSION_POST_ANALYSIS.md")
POSITION_BINS = [
    ("1", 1, 1),
    ("2", 2, 2),
    ("3-5", 3, 5),
    ("6-10", 6, 10),
    ("11-25", 11, 25),
    ("26-50", 26, 50),
    ("51-100", 51, 100),
    ("101+", 101, None),
]


def load_rows(model: str, run_name: str, frozen: set[str], current: set[str]) -> list[dict]:
    rows: list[dict] = []
    run_dir = os.path.join("Tests", run_name)
    for dataset in campaign.KEYS:
        for mode in (1, 2):
            path = os.path.join(run_dir, f"{dataset}_packages_{mode}.json")
            with open(path, encoding="utf-8") as handle:
                for index, line in enumerate(handle):
                    if not line.strip():
                        continue
                    text = str(json.loads(line))
                    status, packages = campaign.parser_v2.classify(text)
                    flags = []
                    unregistered = []
                    for package in packages:
                        key = campaign.normalize(package)
                        flag = (key not in frozen and key not in current
                                and key not in campaign.STDLIB)
                        flags.append(flag)
                        if flag:
                            unregistered.append(package)
                    rows.append({
                        "model": model,
                        "run": run_name,
                        "dataset": dataset,
                        "mode": mode,
                        "index": index,
                        "id": f"{model}:{dataset}:q{mode}:{index}",
                        "text": text,
                        "char_count": len(text),
                        "status": status,
                        "packages": packages,
                        "unregistered_flags": flags,
                        "package_count": len(packages),
                        "unregistered_count": len(unregistered),
                        "cap_proxy": False,
                    })
    return rows


def phase_cap_counts(run_name: str) -> tuple[dict[tuple[str, int], int], dict]:
    path = os.path.join("Tests", run_name, "run_manifest.json")
    with open(path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    caps = {}
    for dataset in campaign.KEYS:
        for mode in (1, 2):
            phase = manifest["phases"][f"{dataset}_packages_{mode}"]
            caps[(dataset, mode)] = int(phase.get("truncated_new_requests", 0))
    code_caps = {
        dataset: int(manifest["phases"][f"{dataset}_code"].get(
            "truncated_new_requests", 0))
        for dataset in campaign.KEYS
    }
    return caps, code_caps


def mark_cap_proxy(rows: list[dict], cap_counts: dict[tuple[str, int], int]) -> list[str]:
    marked = []
    for phase, count in cap_counts.items():
        if not count:
            continue
        candidates = [row for row in rows if (row["dataset"], row["mode"]) == phase]
        candidates.sort(key=lambda row: (row["char_count"], row["package_count"]), reverse=True)
        for row in candidates[:count]:
            row["cap_proxy"] = True
            marked.append(row["id"])
    return marked


def percentile(values: list[int], q: float) -> float:
    return round(float(np.percentile(values, q)), 3) if values else 0.0


def summarize(rows: list[dict]) -> dict:
    statuses = Counter(row["status"] for row in rows)
    h = sum(row["unregistered_count"] for row in rows)
    t = sum(row["package_count"] for row in rows)
    packages = [row["package_count"] for row in rows]
    chars = [row["char_count"] for row in rows]
    prompt_keys = {(row["dataset"], row["index"]) for row in rows}
    risky = {(row["dataset"], row["index"]) for row in rows
             if row["unregistered_count"] > 0}
    response_rates = [100 * row["unregistered_count"] / row["package_count"]
                      for row in rows if row["package_count"]]
    prompt_totals = {}
    for row in rows:
        key = (row["dataset"], row["index"])
        slot = prompt_totals.setdefault(key, {"h": 0, "t": 0})
        slot["h"] += row["unregistered_count"]
        slot["t"] += row["package_count"]
    prompt_rates = [100 * value["h"] / value["t"]
                    for value in prompt_totals.values() if value["t"]]
    return {
        "responses": len(rows),
        "prompts": len(prompt_keys),
        "statuses": dict(statuses),
        "list_coverage_pct": round(100 * statuses["list"] / max(len(rows), 1), 3),
        "malformed_rate_pct": round(100 * statuses["malformed"] / max(len(rows), 1), 3),
        "parsed_package_occurrences": t,
        "unregistered_occurrences": h,
        "unregistered_rate_pct": round(100 * h / t, 3) if t else None,
        "prompt_risk_pct": round(100 * len(risky) / max(len(prompt_keys), 1), 3),
        "macro_rates": {
            "response_mean_pct": round(float(np.mean(response_rates)), 3)
                                 if response_rates else None,
            "response_median_pct": round(float(np.median(response_rates)), 3)
                                   if response_rates else None,
            "response_p90_pct": percentile(response_rates, 90) if response_rates else None,
            "prompt_mean_pct": round(float(np.mean(prompt_rates)), 3)
                               if prompt_rates else None,
            "prompt_median_pct": round(float(np.median(prompt_rates)), 3)
                                 if prompt_rates else None,
            "prompts_with_denominator": len(prompt_rates),
        },
        "packages_per_response": {
            "median": round(float(statistics.median(packages)), 3) if packages else 0,
            "p90": percentile(packages, 90),
            "p95": percentile(packages, 95),
            "p99": percentile(packages, 99),
            "max": max(packages, default=0),
            "responses_ge_25": sum(value >= 25 for value in packages),
            "responses_ge_50": sum(value >= 50 for value in packages),
            "responses_ge_100": sum(value >= 100 for value in packages),
            "responses_ge_200": sum(value >= 200 for value in packages),
        },
        "characters_per_response": {
            "median": round(float(statistics.median(chars)), 3) if chars else 0,
            "p95": percentile(chars, 95),
            "max": max(chars, default=0),
        },
    }


def position_profile(rows: list[dict]) -> list[dict]:
    output = []
    for label, low, high in POSITION_BINS:
        h = 0
        t = 0
        response_ids = set()
        for row in rows:
            for position, flag in enumerate(row["unregistered_flags"], 1):
                if position < low or (high is not None and position > high):
                    continue
                t += 1
                h += int(flag)
                response_ids.add(row["id"])
        output.append({
            "position": label,
            "occurrences": t,
            "unregistered": h,
            "unregistered_rate_pct": round(100 * h / t, 3) if t else None,
            "contributing_responses": len(response_ids),
        })
    return output


def length_quartiles(rows: list[dict]) -> list[dict]:
    list_rows = [row for row in rows if row["status"] == "list"]
    if not list_rows:
        return []
    ordered = sorted(list_rows, key=lambda row: (row["package_count"], row["char_count"]))
    chunks = np.array_split(np.array(ordered, dtype=object), 4)
    output = []
    for index, chunk in enumerate(chunks, 1):
        values = list(chunk)
        summary = summarize(values)
        output.append({
            "quartile": index,
            "responses": len(values),
            "package_count_min": min(row["package_count"] for row in values),
            "package_count_max": max(row["package_count"] for row in values),
            "parsed_package_occurrences": summary["parsed_package_occurrences"],
            "unregistered_rate_pct": summary["unregistered_rate_pct"],
        })
    return output


def normalized_set(row: dict, unregistered_only: bool = False) -> set[str]:
    pairs = zip(row["packages"], row["unregistered_flags"])
    return {
        campaign.normalize(package)
        for package, flag in pairs
        if not unregistered_only or flag
    }


def pairwise_set_reuse(rows: list[dict]) -> dict:
    sets = [normalized_set(row) for row in rows if row["package_count"]]
    unregistered_sets = [normalized_set(row, True) for row in rows if row["package_count"]]

    def summarize_jaccard(values: list[set[str]]) -> dict:
        scores = []
        for left, right in combinations(values, 2):
            union = left | right
            scores.append(len(left & right) / len(union) if union else 0.0)
        return {
            "pairs": len(scores),
            "mean": round(float(np.mean(scores)), 4) if scores else None,
            "median": round(float(np.median(scores)), 4) if scores else None,
            "p95": round(float(np.percentile(scores, 95)), 4) if scores else None,
        }

    frequency = Counter(name for values in sets for name in values)
    unregistered_frequency = Counter(name for values in unregistered_sets for name in values)
    n = len(sets)
    return {
        "responses": n,
        "package_set_jaccard": summarize_jaccard(sets),
        "unregistered_set_jaccard": summarize_jaccard(unregistered_sets),
        "unique_normalized_packages": len(frequency),
        "unique_normalized_unregistered": len(unregistered_frequency),
        "packages_in_at_least_25pct_responses": sum(count >= 0.25 * n
                                                    for count in frequency.values()),
        "packages_in_at_least_50pct_responses": sum(count >= 0.50 * n
                                                    for count in frequency.values()),
        "unregistered_in_at_least_25pct_responses": sum(
            count >= 0.25 * n for count in unregistered_frequency.values()
        ),
        "unregistered_in_at_least_50pct_responses": sum(
            count >= 0.50 * n for count in unregistered_frequency.values()
        ),
    }


def paired_query_overlap(rows: list[dict]) -> dict:
    keyed = {(row["dataset"], row["index"], row["mode"]): row for row in rows}
    all_scores = []
    long_q2_scores = []
    short_q2_scores = []
    for dataset in campaign.KEYS:
        for index in range(200):
            q1 = keyed.get((dataset, index, 1))
            q2 = keyed.get((dataset, index, 2))
            if not q1 or not q2:
                continue
            left, right = normalized_set(q1), normalized_set(q2)
            union = left | right
            score = len(left & right) / len(union) if union else 0.0
            all_scores.append(score)
            (long_q2_scores if q2["package_count"] > 100 else short_q2_scores).append(score)

    def summary(scores: list[float]) -> dict:
        return {
            "prompts": len(scores),
            "mean_jaccard": round(float(np.mean(scores)), 4) if scores else None,
            "median_jaccard": round(float(np.median(scores)), 4) if scores else None,
            "p95_jaccard": round(float(np.percentile(scores, 95)), 4) if scores else None,
        }

    return {"all": summary(all_scores), "query_2_gt_100": summary(long_q2_scores),
            "query_2_le_100": summary(short_q2_scores)}


def analyze_cell(model: str, run_name: str, frozen: set[str], current: set[str]) -> dict:
    rows = load_rows(model, run_name, frozen, current)
    cap_counts, code_caps = phase_cap_counts(run_name)
    proxy_ids = mark_cap_proxy(rows, cap_counts)

    by_mode = {f"query_{mode}": summarize([row for row in rows if row["mode"] == mode])
               for mode in (1, 2)}
    by_dataset = {
        dataset: summarize([row for row in rows if row["dataset"] == dataset])
        for dataset in campaign.KEYS
    }
    by_dataset_mode = {}
    for dataset in campaign.KEYS:
        by_dataset_mode[dataset] = {
            f"query_{mode}": summarize([
                row for row in rows if row["dataset"] == dataset and row["mode"] == mode
            ])
            for mode in (1, 2)
        }

    proxy_rows = [row for row in rows if row["cap_proxy"]]
    nonproxy_rows = [row for row in rows if not row["cap_proxy"]]
    proxy_malformed = sum(row["status"] == "malformed" for row in proxy_rows)
    nonproxy_malformed = sum(row["status"] == "malformed" for row in nonproxy_rows)
    total_malformed = proxy_malformed + nonproxy_malformed
    query1 = [row for row in rows if row["mode"] == 1]
    query1_nonproxy = [row for row in query1 if not row["cap_proxy"]]
    query2 = [row for row in rows if row["mode"] == 2]
    query2_nonproxy = [row for row in query2 if not row["cap_proxy"]]
    volume_sensitivity = {}
    for label, subset in (("overall", rows), ("query_1", query1), ("query_2", query2)):
        volume_sensitivity[label] = {
            "packages_le_10": summarize([row for row in subset if row["package_count"] <= 10]),
            "packages_le_25": summarize([row for row in subset if row["package_count"] <= 25]),
            "packages_gt_25": summarize([row for row in subset if row["package_count"] > 25]),
        }
    result = {
        "overall": summarize(rows),
        "by_query": by_mode,
        "by_dataset": by_dataset,
        "by_dataset_and_query": by_dataset_mode,
        "recorded_package_response_cap_hits": {
            f"{dataset}:q{mode}": count for (dataset, mode), count in cap_counts.items()
        },
        "recorded_code_response_cap_hits": code_caps,
        "recorded_package_cap_hits_total": sum(cap_counts.values()),
        "cap_proxy_method": (
            "Within each dataset/query phase, mark the N longest responses where N is the "
            "manifest's phase-level cap-hit count. Exact cap-hit response IDs were not "
            "retained by the first runner."
        ),
        "cap_proxy_ids": proxy_ids,
        "cap_proxy_only": summarize(proxy_rows),
        "cap_proxy_excluded": summarize(nonproxy_rows),
        "cap_proxy_parser_contrast": {
            "proxy_responses": len(proxy_rows),
            "proxy_malformed": proxy_malformed,
            "proxy_malformed_rate_pct": round(
                100 * proxy_malformed / len(proxy_rows), 3
            ) if proxy_rows else None,
            "nonproxy_responses": len(nonproxy_rows),
            "nonproxy_malformed": nonproxy_malformed,
            "nonproxy_malformed_rate_pct": round(
                100 * nonproxy_malformed / len(nonproxy_rows), 3
            ) if nonproxy_rows else None,
            "malformed_rate_difference_pp": round(
                100 * proxy_malformed / len(proxy_rows)
                - 100 * nonproxy_malformed / len(nonproxy_rows), 3
            ) if proxy_rows and nonproxy_rows else None,
            "share_of_all_malformed_in_proxy_pct": round(
                100 * proxy_malformed / total_malformed, 3
            ) if total_malformed else None,
        },
        "query_1_cap_proxy_excluded": summarize(query1_nonproxy),
        "query_2_cap_proxy_excluded": summarize(query2_nonproxy),
        "volume_sensitivity": volume_sensitivity,
        "position_profile_overall": position_profile(rows),
        "position_profile_query_1": position_profile(query1),
        "position_profile_query_1_cap_proxy_excluded": position_profile(query1_nonproxy),
        "position_profile_query_2": position_profile(query2),
        "position_profile_query_2_cap_proxy_excluded": position_profile(query2_nonproxy),
        "package_volume_quartiles_overall": length_quartiles(rows),
        "package_volume_quartiles_query_2": length_quartiles(query2),
        "catalog_reuse": {
            "query_2_packages_le_10": pairwise_set_reuse([
                row for row in query2 if row["package_count"] <= 10
            ]),
            "query_2_packages_gt_100": pairwise_set_reuse([
                row for row in query2 if row["package_count"] > 100
            ]),
        },
        "paired_query_overlap": paired_query_overlap(rows),
        "largest_response_ids": [row["id"] for row in sorted(
            rows, key=lambda row: (row["package_count"], row["char_count"]), reverse=True
        )[:20]],
    }
    return result


def fmt_rate(summary: dict) -> str:
    rate = summary["unregistered_rate_pct"]
    return "n/a" if rate is None else f"{rate:.2f}%"


def write_markdown(result: dict) -> None:
    qwen = result["cells"]["qwen3.5:cloud"]
    kimi = result["cells"]["kimi-k2.7-code:cloud"]
    rows = []
    for model, cell in result["cells"].items():
        q1 = cell["by_query"]["query_1"]
        q2 = cell["by_query"]["query_2"]
        q1clean = cell["query_1_cap_proxy_excluded"]
        q2clean = cell["query_2_cap_proxy_excluded"]
        rows.append(
            f"| {model} | {fmt_rate(q1)} | {fmt_rate(q1clean)} | "
            f"{q1['parsed_package_occurrences']:,} | "
            f"{fmt_rate(q2)} | {q2['parsed_package_occurrences']:,} | "
            f"{fmt_rate(q2clean)} | {cell['recorded_package_cap_hits_total']} |"
        )

    kimi_q2 = kimi["by_query"]["query_2"]
    kimi_q1 = kimi["by_query"]["query_1"]
    kimi_proxy = kimi["cap_proxy_only"]
    kimi_clean = kimi["cap_proxy_excluded"]
    qwen_q2 = qwen["by_query"]["query_2"]
    kimi_catalog = kimi["catalog_reuse"]["query_2_packages_gt_100"]
    parser_contrast = kimi["cap_proxy_parser_contrast"]
    q2_clean_position = {
        item["position"]: item
        for item in kimi["position_profile_query_2_cap_proxy_excluded"]
    }
    md = f"""# Ollama Cloud extension post-analysis

**Status:** post-hoc diagnostic; the preregistered result remains unchanged.

## Main diagnostic

| Model | Query 1 rate | Q1 excluding cap proxy | Q1 parsed packages | Query 2 rate | Q2 parsed packages | Q2 excluding cap proxy | Package cap hits |
|---|---:|---:|---:|---:|---:|---:|---:|
{os.linesep.join(rows)}

Query 1 asks which packages are required by the model's generated code. Query 2 asks which
packages would be useful for the original problem. Kimi's two channels are not behaving like
replicate measurements: Query 1 produced {kimi_q1['parsed_package_occurrences']:,} parsed
package occurrences, while Query 2 produced {kimi_q2['parsed_package_occurrences']:,}.
Qwen's Query 2 produced {qwen_q2['parsed_package_occurrences']:,} occurrences.

Kimi recorded {kimi['recorded_package_cap_hits_total']} package-response cap hits, of which
{sum(v for k, v in kimi['recorded_package_response_cap_hits'].items() if k.endswith(':q2'))}
occurred in Query 2. The cap-proxy responses alone contain
{kimi_proxy['parsed_package_occurrences']:,} parsed package occurrences at
{fmt_rate(kimi_proxy)} unregistered; excluding the proxy changes the combined Kimi rate to
{fmt_rate(kimi_clean)}. Because the first runner retained cap counts only at phase level, this
is a longest-response proxy—not exact cap-hit identification.

Parser sensitivity is present but insufficient as a complete explanation. Among the 323
cap-proxy responses, {parser_contrast['proxy_malformed']} ({parser_contrast['proxy_malformed_rate_pct']:.2f}%)
are grammar-malformed, compared with {parser_contrast['nonproxy_malformed']} of
{parser_contrast['nonproxy_responses']:,} ({parser_contrast['nonproxy_malformed_rate_pct']:.2f}%)
outside the proxy, a {parser_contrast['malformed_rate_difference_pp']:.2f}-point difference.
The proxy contains {parser_contrast['share_of_all_malformed_in_proxy_pct']:.2f}% of all malformed
Kimi responses. At the same time, the parser accepts {kimi_proxy['statuses']['list']} proxy
responses containing {kimi_proxy['parsed_package_occurrences']:,} package occurrences. After
excluding every proxy response, Query 2 still rises from
{q2_clean_position['1']['unregistered_rate_pct']:.2f}% at position 1 and
{q2_clean_position['11-25']['unregistered_rate_pct']:.2f}% at positions 11–25 to
{q2_clean_position['26-50']['unregistered_rate_pct']:.2f}% at 26–50,
{q2_clean_position['51-100']['unregistered_rate_pct']:.2f}% at 51–100, and
{q2_clean_position['101+']['unregistered_rate_pct']:.2f}% after 100. The late clean-proxy bins
have only {q2_clean_position['26-50']['contributing_responses']},
{q2_clean_position['51-100']['contributing_responses']}, and
{q2_clean_position['101+']['contributing_responses']} contributing responses respectively, so
they are mechanism evidence rather than stable population estimates.

Among Kimi responses containing at most 10 parsed packages, the combined unregistered rate is
{fmt_rate(kimi['volume_sensitivity']['overall']['packages_le_10'])}; responses above 25 packages
account for {kimi['volume_sensitivity']['overall']['packages_gt_25']['parsed_package_occurrences']:,}
parsed occurrences at {fmt_rate(kimi['volume_sensitivity']['overall']['packages_gt_25'])}.
The pooled 23.10% occurrence rate contrasts with an unweighted mean of
{kimi['overall']['macro_rates']['response_mean_pct']:.2f}% across non-empty parsed responses
and {kimi['overall']['macro_rates']['prompt_mean_pct']:.2f}% across prompts with a denominator;
the corresponding response and prompt medians are
{kimi['overall']['macro_rates']['response_median_pct']:.2f}% and
{kimi['overall']['macro_rates']['prompt_median_pct']:.2f}%.

The {kimi_catalog['responses']} Kimi Query 2 responses above 100 packages have mean pairwise
package-set Jaccard {kimi_catalog['package_set_jaccard']['mean']:.3f};
{kimi_catalog['packages_in_at_least_50pct_responses']} normalized package names recur in at
least half of those floods. Their paired Query 1/Query 2 mean Jaccard is
{kimi['paired_query_overlap']['query_2_gt_100']['mean_jaccard']:.3f}. This quantifies whether
the long answers resemble a reused catalog while avoiding publication of candidate names.

## Interpretation

- Qwen is operationally clean: one code cap hit and no package-response cap hits.
- Kimi K2.7's preregistered headline is a real property of the observed outputs, but it is
  dominated by Query 2's extreme list-generation behavior and cannot be interpreted as a
  simple model-quality ranking without the channel-specific results.
- The floods are not copies of one fixed catalog: their mean pairwise Jaccard is only
  {kimi_catalog['package_set_jaccard']['mean']:.3f}. They share a modest 39-name core but
  generate diverse prompt-conditioned tails, while almost never overlapping the paired
  Query 1 answer (mean Jaccard {kimi['paired_query_overlap']['query_2_gt_100']['mean_jaccard']:.3f}).
- Truncation can bias in both directions: grammar-malformed tails are excluded, while
  comma-complete truncated lists contribute hundreds of parsed occurrences. The proxy
  sensitivity quantifies influence but does not repair this missing per-response provenance.
- Parser noise therefore mediates Kimi's cap sensitivity, but does not explain it away: the
  proxy is enriched for malformed outputs, yet a steep late-position gradient survives its
  complete exclusion in a small number of nonproxy list floods.
- The defensible paper treatment is to report Query 1 and Query 2 separately, retain the
  preregistered combined result, and label Kimi Query 2 as an instruction-following/list-volume
  failure mode. A future Kimi cell must store finish reason and token usage for every response.

## Position profile

See the machine-readable artifact for occurrence-weighted rates in bins 1, 2, 3–5, 6–10,
11–25, 26–50, 51–100, and 101+, separately for both queries and after the cap proxy exclusion.
This distinguishes an early-list validity gradient from late-response degradation.

## Guardrails

- No raw response, parser decision, registry snapshot, or preregistered estimate was changed.
- The cap proxy is explicitly post-hoc and must not be described as exact.
- Occurrence rates must be co-reported with parsed package volume, list coverage, prompt risk,
  and response-cap counts.
"""
    with open(OUT_MD, "w", encoding="utf-8", newline="") as handle:
        handle.write(md)


def main() -> None:
    frozen = campaign.load_registry(os.path.join("Data", "Python", "pypi_package_names.csv"))
    current = campaign.load_registry(os.path.join(
        "Data", "Python", "pypi_package_names_2026-08-12.csv"))
    campaign.FROZEN_REGISTRY, campaign.CURRENT_REGISTRY = frozen, current
    cells = {
        model: analyze_cell(model, run_name, frozen, current)
        for model, run_name in CELLS
    }
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "post-hoc diagnostic; preregistered estimates unchanged",
        "source": "Experiments/ollama_cloud_extension_results.json",
        "cells": cells,
        "guardrails": [
            "Cap response IDs are a longest-response proxy because only phase counts were retained.",
            "Query-specific results are post-hoc diagnostics.",
            "Candidate unregistered package names are not published in this artifact.",
        ],
    }
    with open(OUT_JSON, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    write_markdown(result)
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
