"""Post-hoc comparison of Kimi K2.7 and Kimi K3 failure mechanisms.

The K3 preregistered score remains the primary result. This script decomposes that
occurrence-weighted result into typical-response and catastrophic-list behavior. K3
uses exact response cap metadata; K2.7 uses the previously documented longest-response
proxy because its original runner retained phase cap counts but not response IDs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import numpy as np

import post_campaign_analysis as campaign
import post_ollama_extension_analysis as diagnostics


K2_MODEL = "kimi-k2.7-code:cloud"
K2_RUN = "trackC_ollama_kimi-k2-7-code-cloud_Python"
K3_MODEL = "kimi-k3:cloud"
K3_RUN = "trackD_ollama_kimi-k3-cloud_Python"
OUT_JSON = os.path.join("Experiments", "kimi_k2_7_vs_k3_post_analysis.json")
OUT_MD = os.path.join("Experiments", "KIMI_K2_7_VS_K3_POST_ANALYSIS.md")
BOOTSTRAP_REPS = 50_000
BOOTSTRAP_SEED = 260_825


def mark_k3_exact_caps(rows: list[dict]) -> None:
    lookup = {(row["dataset"], row["mode"], row["index"]): row for row in rows}
    for row in rows:
        row["cap_hit"] = False
    for dataset in campaign.KEYS:
        for mode in (1, 2):
            path = os.path.join(
                "Tests", K3_RUN,
                f"{dataset}_packages_{mode}.json.request_metadata.jsonl",
            )
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    record = json.loads(line)
                    lookup[(dataset, mode, int(record["index"]))]["cap_hit"] = bool(
                        record["truncated"]
                    )


def contribution(rows: list[dict], field: str) -> dict:
    selected = [row for row in rows if row[field]]
    total_packages = sum(row["package_count"] for row in rows)
    total_unregistered = sum(row["unregistered_count"] for row in rows)
    selected_packages = sum(row["package_count"] for row in selected)
    selected_unregistered = sum(row["unregistered_count"] for row in selected)
    return {
        "selected_responses": len(selected),
        "response_share_pct": round(100 * len(selected) / len(rows), 3),
        "selected_parsed_occurrences": selected_packages,
        "occurrence_share_pct": round(100 * selected_packages / total_packages, 3),
        "selected_unregistered_occurrences": selected_unregistered,
        "unregistered_share_pct": round(
            100 * selected_unregistered / total_unregistered, 3
        ),
    }


def q2_prompt_map(rows: list[dict]) -> dict[tuple[str, int], dict]:
    return {
        (row["dataset"], row["index"]): row
        for row in rows if row["mode"] == 2
    }


def paired_bootstrap(k2: dict, k3: dict) -> dict:
    keys = sorted(k2)
    if keys != sorted(k3) or len(keys) != 800:
        raise RuntimeError("K2.7/K3 shared-prompt gate failed")
    k2_risk = np.array([k2[key]["unregistered_count"] > 0 for key in keys], dtype=float)
    k3_risk = np.array([k3[key]["unregistered_count"] > 0 for key in keys], dtype=float)
    k2_flood = np.array([k2[key]["package_count"] > 100 for key in keys], dtype=float)
    k3_flood = np.array([k3[key]["package_count"] > 100 for key in keys], dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    risk_diffs = np.empty(BOOTSTRAP_REPS)
    flood_diffs = np.empty(BOOTSTRAP_REPS)
    for start in range(0, BOOTSTRAP_REPS, 2_000):
        size = min(2_000, BOOTSTRAP_REPS - start)
        indices = rng.integers(0, len(keys), size=(size, len(keys)))
        risk_diffs[start:start + size] = (
            k2_risk[indices].mean(axis=1) - k3_risk[indices].mean(axis=1)
        ) * 100
        flood_diffs[start:start + size] = (
            k2_flood[indices].mean(axis=1) - k3_flood[indices].mean(axis=1)
        ) * 100

    def metric(a: np.ndarray, b: np.ndarray, draws: np.ndarray) -> dict:
        diff = 100 * (a.mean() - b.mean())
        low, high = np.percentile(draws, [2.5, 97.5])
        return {
            "k2_7_pct": round(100 * a.mean(), 3),
            "k3_pct": round(100 * b.mean(), 3),
            "k2_7_minus_k3_pp": round(float(diff), 3),
            "paired_prompt_cluster_bootstrap_95_ci": [
                round(float(low), 3), round(float(high), 3)
            ],
        }

    flood_counts = {
        "both": int(np.sum((k2_flood == 1) & (k3_flood == 1))),
        "k2_7_only": int(np.sum((k2_flood == 1) & (k3_flood == 0))),
        "k3_only": int(np.sum((k2_flood == 0) & (k3_flood == 1))),
        "neither": int(np.sum((k2_flood == 0) & (k3_flood == 0))),
    }
    union = flood_counts["both"] + flood_counts["k2_7_only"] + flood_counts["k3_only"]
    flood_counts["prompt_set_jaccard"] = round(flood_counts["both"] / union, 4)
    return {
        "q2_prompt_risk": metric(k2_risk, k3_risk, risk_diffs),
        "q2_responses_over_100_packages": metric(k2_flood, k3_flood, flood_diffs),
        "over_100_prompt_contingency": flood_counts,
        "bootstrap_replicates": BOOTSTRAP_REPS,
        "seed": BOOTSTRAP_SEED,
    }


def position_table(rows: list[dict]) -> dict[str, float | None]:
    return {
        item["position"]: item["unregistered_rate_pct"]
        for item in diagnostics.position_profile(rows)
    }


def main() -> None:
    frozen = campaign.load_registry(os.path.join("Data", "Python", "pypi_package_names.csv"))
    current = campaign.load_registry(os.path.join(
        "Data", "Python", "pypi_package_names_2026-08-12.csv"
    ))
    campaign.FROZEN_REGISTRY, campaign.CURRENT_REGISTRY = frozen, current

    k2 = diagnostics.load_rows(K2_MODEL, K2_RUN, frozen, current)
    k3 = diagnostics.load_rows(K3_MODEL, K3_RUN, frozen, current)
    k2_cap_counts, _ = diagnostics.phase_cap_counts(K2_RUN)
    diagnostics.mark_cap_proxy(k2, k2_cap_counts)
    for row in k2:
        row["cap_hit"] = bool(row["cap_proxy"])
    mark_k3_exact_caps(k3)

    k2_hit = [row for row in k2 if row["cap_hit"]]
    k2_clean = [row for row in k2 if not row["cap_hit"]]
    k3_hit = [row for row in k3 if row["cap_hit"]]
    k3_clean = [row for row in k3 if not row["cap_hit"]]
    k2_q2_clean = [row for row in k2_clean if row["mode"] == 2]
    k3_q2_clean = [row for row in k3_clean if row["mode"] == 2]

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete post-hoc mechanism comparison",
        "measurement_note": (
            "K3 cap membership is exact. K2.7 cap membership is the frozen within-phase "
            "longest-response proxy and must not be described as exact. Cap exclusion is a "
            "diagnostic conditioning analysis, not a causal estimate."
        ),
        "models": {
            "kimi_k2_7": {
                "overall": diagnostics.summarize(k2),
                "cap_proxy_only": diagnostics.summarize(k2_hit),
                "cap_proxy_excluded": diagnostics.summarize(k2_clean),
                "cap_proxy_contribution": contribution(k2, "cap_hit"),
            },
            "kimi_k3": {
                "overall": diagnostics.summarize(k3),
                "exact_cap_only": diagnostics.summarize(k3_hit),
                "exact_cap_excluded": diagnostics.summarize(k3_clean),
                "exact_cap_contribution": contribution(k3, "cap_hit"),
            },
        },
        "paired_q2_diagnostics": paired_bootstrap(q2_prompt_map(k2), q2_prompt_map(k3)),
        "q2_position_rate_cap_excluded": {
            "kimi_k2_7_proxy_excluded": position_table(k2_q2_clean),
            "kimi_k3_exact_excluded": position_table(k3_q2_clean),
        },
    }

    k2o = result["models"]["kimi_k2_7"]["overall"]
    k3o = result["models"]["kimi_k3"]["overall"]
    k2c = result["models"]["kimi_k2_7"]["cap_proxy_excluded"]
    k3c = result["models"]["kimi_k3"]["exact_cap_excluded"]
    k2h = result["models"]["kimi_k2_7"]["cap_proxy_only"]
    k3h = result["models"]["kimi_k3"]["exact_cap_only"]
    k2con = result["models"]["kimi_k2_7"]["cap_proxy_contribution"]
    k3con = result["models"]["kimi_k3"]["exact_cap_contribution"]
    paired = result["paired_q2_diagnostics"]
    pos2 = result["q2_position_rate_cap_excluded"]

    def ci(value: dict) -> str:
        lo, hi = value["paired_prompt_cluster_bootstrap_95_ci"]
        return f"{value['k2_7_minus_k3_pp']:.3f} ({lo:.3f} to {hi:.3f})"

    position_rows = "\n".join(
        f"| {label} | {pos2['kimi_k2_7_proxy_excluded'][label] if pos2['kimi_k2_7_proxy_excluded'][label] is not None else 'n/a'} | "
        f"{pos2['kimi_k3_exact_excluded'][label] if pos2['kimi_k3_exact_excluded'][label] is not None else 'n/a'} |"
        for label, _, _ in diagnostics.POSITION_BINS
    )
    flood = paired["over_100_prompt_contingency"]
    md = f"""# Kimi K2.7 versus Kimi K3 post-analysis

**Status:** complete post-hoc mechanism comparison. The K3 preregistered score remains primary.

## Main finding

K3 is better on typical responses but worse on the occurrence-weighted headline because a
small catastrophic tail dominates its denominator. Its raw rate is {k3o['unregistered_rate_pct']:.3f}%
versus K2.7's {k2o['unregistered_rate_pct']:.3f}%. After excluding recorded K3 package cap hits
and the frozen K2.7 cap proxy, the rates nearly coincide: {k3c['unregistered_rate_pct']:.3f}%
versus {k2c['unregistered_rate_pct']:.3f}%. This conditioning is diagnostic, not causal.

| Diagnostic | Kimi K2.7 | Kimi K3 |
|---|---:|---:|
| Raw occurrence-weighted rate | {k2o['unregistered_rate_pct']:.3f}% | {k3o['unregistered_rate_pct']:.3f}% |
| Prompt risk | {k2o['prompt_risk_pct']:.3f}% | {k3o['prompt_risk_pct']:.3f}% |
| Response-macro mean | {k2o['macro_rates']['response_mean_pct']:.3f}% | {k3o['macro_rates']['response_mean_pct']:.3f}% |
| Package cap hits/proxies | {len(k2_hit)} | {len(k3_hit)} |
| Cap-hit/proxy-only rate | {k2h['unregistered_rate_pct']:.3f}% | {k3h['unregistered_rate_pct']:.3f}% |
| Cap-hit/proxy-excluded rate | {k2c['unregistered_rate_pct']:.3f}% | {k3c['unregistered_rate_pct']:.3f}% |
| Responses with at least 100 packages | {k2o['packages_per_response']['responses_ge_100']} | {k3o['packages_per_response']['responses_ge_100']} |

K3's 46 exact package cap hits are only {k3con['response_share_pct']:.3f}% of package responses,
but supply {k3con['occurrence_share_pct']:.3f}% of parsed occurrences and
{k3con['unregistered_share_pct']:.3f}% of all unregistered occurrences. K2.7's 323 proxy-marked
responses supply {k2con['occurrence_share_pct']:.3f}% of occurrences and
{k2con['unregistered_share_pct']:.3f}% of unregistered occurrences. K2.7 floods often; K3 floods
far less often, but its rare cap-hit floods are much more contaminated ({k3h['unregistered_rate_pct']:.3f}%
versus {k2h['unregistered_rate_pct']:.3f}%).

## Shared-prompt diagnostics

| Paired Query 2 measure (K2.7 minus K3, pp) | Difference (95% CI) |
|---|---:|
| Prompt risk | {ci(paired['q2_prompt_risk'])} |
| Responses over 100 packages | {ci(paired['q2_responses_over_100_packages'])} |

For >100-package responses, the shared-prompt contingency is: both {flood['both']}, K2.7 only
{flood['k2_7_only']}, K3 only {flood['k3_only']}, neither {flood['neither']}; prompt-set Jaccard
is {flood['prompt_set_jaccard']:.4f}. The weak overlap argues against prompt difficulty alone as
the source of the catastrophic tail.

## Query 2 position rate after cap diagnostic exclusion

| Position | K2.7 proxy-excluded (%) | K3 exact-cap-excluded (%) |
|---|---:|---:|
{position_rows}

Both models retain a steep late-position gradient after the cap diagnostic. K3 is lower through
positions 26–100, but both become unreliable after position 100. The practical mechanism is
therefore two-stage: an occasional runaway enumeration creates a long tail, and package validity
then degrades sharply within that tail. A token cap determines which part is observed; it is not
the root cause by itself.

## Interpretation guardrails

- Preserve the preregistered raw K3 result as primary; do not replace it with cap-excluded rates.
- Report prompt risk and response-macro summaries beside the occurrence-weighted rate. They answer
  different deployment questions and reveal K3's better typical response behavior.
- Treat K2.7 cap membership as a proxy. Exact K3 metadata supports stronger claims only for K3.
- The next experiment should vary the package token cap within model and prompt, and should add a
  bounded-list instruction arm. That factorial separates runaway enumeration from token-boundary
  truncation and tests a practical mitigation.
"""
    with open(OUT_JSON, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    with open(OUT_MD, "w", encoding="utf-8") as handle:
        handle.write(md)
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
