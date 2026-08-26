"""Score the preregistered Kimi K3 extension and validate response provenance."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import post_campaign_analysis as campaign
import post_ollama_extension_analysis as diagnostics
import score_ollama_cloud_extension as extension


MODEL = "kimi-k3:cloud"
SERVED_MODEL = "kimi-k3"
RUN = "trackD_ollama_kimi-k3-cloud_Python"
OUT_JSON = os.path.join("Experiments", "kimi_k3_extension_results.json")
OUT_MD = os.path.join("Experiments", "KIMI_K3_EXTENSION_RESULTS.md")
PRIOR_EXTENSION = [
    ("qwen3.5:cloud", "trackC_ollama_qwen3-5-cloud_Python"),
    ("kimi-k2.7-code:cloud", "trackC_ollama_kimi-k2-7-code-cloud_Python"),
]


def validate_metadata(run: str = RUN, expected_rows_per_phase: int = 200) -> dict:
    manifest_path = os.path.join("Tests", run, "run_manifest.json")
    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    expected_sampling = {
        "code_temperature": 0.7,
        "package_temperature": 0.01,
        "top_k": 20,
        "top_p": 0.9,
        "max_code_tokens": 4096,
        "max_package_tokens": 2048,
    }
    client = manifest.get("client") or {}
    cost = client.get("cost_tracking") or {}
    configuration_checks = {
        "model_spec": manifest.get("model_spec") == f"ollama:{MODEL}",
        "language": manifest.get("language") == "Python",
        "workers": manifest.get("workers") == 2,
        "sampling": manifest.get("sampling_requested") == expected_sampling,
        "think_disabled": client.get("extra_body") == {"think": False},
        "no_request_adjustments": client.get("request_adjustments") == {},
        "input_price": cost.get("input_usd_per_million_tokens") == 3.0,
        "output_price": cost.get("output_usd_per_million_tokens") == 15.0,
        "full_sample": (
            manifest.get("sample") == 200 and manifest.get("seed") == 0
            if expected_rows_per_phase == 200
            else manifest.get("limit") == expected_rows_per_phase
        ),
    }
    failed_configuration = [name for name, passed in configuration_checks.items()
                            if not passed]
    if failed_configuration:
        raise SystemExit(
            "Kimi K3 manifest violates the frozen configuration: "
            + ", ".join(failed_configuration)
        )
    totals = {"rows": 0, "truncated": 0, "prompt_tokens": 0,
              "completion_tokens": 0, "missing": 0}
    phases = {}
    for dataset in campaign.KEYS:
        for suffix in ["code", "packages_1", "packages_2"]:
            phase_name = f"{dataset}_{suffix}"
            path = os.path.join("Tests", run, f"{phase_name}.json.request_metadata.jsonl")
            if not os.path.exists(path):
                raise SystemExit(f"missing response metadata sidecar: {path}")
            with open(path, encoding="utf-8") as handle:
                records = [json.loads(line) for line in handle if line.strip()]
            output_path = os.path.join("Tests", run, f"{phase_name}.json")
            with open(output_path, encoding="utf-8") as handle:
                output_rows = [json.loads(line) for line in handle if line.strip()]
            if len(output_rows) != expected_rows_per_phase:
                raise SystemExit(
                    f"wrong response row count for {output_path}: "
                    f"{len(output_rows)} != {expected_rows_per_phase}"
                )
            if [record.get("index") for record in records] != list(
                    range(expected_rows_per_phase)):
                raise SystemExit(f"unordered or incomplete response metadata: {path}")
            required_fields = {
                "finish_reason", "truncated", "served_model",
                "prompt_tokens", "completion_tokens",
            }
            invalid_rows = []
            for record in records:
                fields_present = required_fields <= set(record)
                valid = (
                    fields_present
                    and not record.get("metadata_missing")
                    and isinstance(record.get("finish_reason"), str)
                    and bool(record.get("finish_reason"))
                    and isinstance(record.get("truncated"), bool)
                    and record.get("served_model") == SERVED_MODEL
                    and isinstance(record.get("prompt_tokens"), int)
                    and record.get("prompt_tokens") > 0
                    and isinstance(record.get("completion_tokens"), int)
                    and record.get("completion_tokens") >= 0
                )
                if not valid:
                    invalid_rows.append(record.get("index"))
            missing = len(invalid_rows)
            truncated = sum(bool(record.get("truncated")) for record in records)
            phase = manifest["phases"][phase_name]
            if (phase.get("items") != expected_rows_per_phase
                    or phase.get("errors") != 0
                    or phase.get("response_metadata_rows") != expected_rows_per_phase):
                raise SystemExit(f"manifest phase gate failed for {phase_name}: {phase}")
            if "truncated_total_rows" in phase:
                expected = int(phase["truncated_total_rows"])
            elif int(phase.get("resumed") or 0) == 0:
                # Historical never-resumed K3 manifest predates the total-row field.
                expected = int(phase["truncated_new_requests"])
            else:
                raise SystemExit(
                    f"resume-aware cap total unavailable for {phase_name}; "
                    "a complete sidecar cannot be compared with truncated_new_requests"
                )
            if missing or truncated != expected:
                raise SystemExit(
                    f"metadata gate failed for {phase_name}: invalid_rows={invalid_rows}, "
                    f"sidecar_cap_hits={truncated}, manifest_cap_hits={expected}"
                )
            item = {
                "path": path.replace("\\", "/"),
                "rows": len(records),
                "truncated": truncated,
                "prompt_tokens": sum(int(record.get("prompt_tokens") or 0)
                                     for record in records),
                "completion_tokens": sum(int(record.get("completion_tokens") or 0)
                                         for record in records),
                "served_model_ids": sorted({record.get("served_model") for record in records}),
            }
            phases[phase_name] = item
            for field in totals:
                if field in item:
                    totals[field] += item[field]
            totals["missing"] += missing
    usage = manifest["token_usage_cumulative"]
    if (totals["rows"] != expected_rows_per_phase * 12
            or usage.get("calls") != expected_rows_per_phase * 12
            or totals["prompt_tokens"] != usage["prompt_tokens"]
            or totals["completion_tokens"] != usage["completion_tokens"]):
        raise SystemExit(
            f"metadata totals do not match manifest: sidecars={totals}, manifest={usage}"
        )
    recomputed_cost = round(
        (3.0 * totals["prompt_tokens"] + 15.0 * totals["completion_tokens"]) / 1_000_000,
        6,
    )
    if abs(recomputed_cost - float(cost.get("estimated_cost_usd", -1))) > 1e-6:
        raise SystemExit(
            "token-derived cost does not match manifest: "
            f"recomputed={recomputed_cost}, manifest={cost.get('estimated_cost_usd')}"
        )
    return {
        "passed": True,
        "configuration_checks": configuration_checks,
        "totals": totals,
        "estimated_cost_usd_recomputed": recomputed_cost,
        "phases": phases,
    }


def exact_package_cap_diagnostics(frozen: set[str], current: set[str], run: str = RUN) -> dict:
    rows = diagnostics.load_rows(MODEL, run, frozen, current)
    lookup = {(row["dataset"], row["mode"], row["index"]): row for row in rows}
    for row in rows:
        row["exact_cap_hit"] = False
    for dataset in campaign.KEYS:
        for mode in (1, 2):
            path = os.path.join(
                "Tests", run, f"{dataset}_packages_{mode}.json.request_metadata.jsonl"
            )
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    record = json.loads(line)
                    lookup[(dataset, mode, int(record["index"]))]["exact_cap_hit"] = bool(
                        record.get("truncated")
                    )
    hit = [row for row in rows if row["exact_cap_hit"]]
    clean = [row for row in rows if not row["exact_cap_hit"]]
    result = {
        "exact_package_cap_hits": len(hit),
        "cap_hit_only": diagnostics.summarize(hit),
        "cap_hit_excluded": diagnostics.summarize(clean),
    }
    for mode in (1, 2):
        mode_rows = [row for row in rows if row["mode"] == mode]
        mode_hit = [row for row in mode_rows if row["exact_cap_hit"]]
        mode_clean = [row for row in mode_rows if not row["exact_cap_hit"]]
        result[f"query_{mode}"] = {
            "exact_cap_hits": len(mode_hit),
            "cap_hit_only": diagnostics.summarize(mode_hit),
            "cap_hit_excluded": diagnostics.summarize(mode_clean),
            "position_profile_cap_hit_excluded": diagnostics.position_profile(mode_clean),
        }
    return result


def main() -> None:
    missing = [path for path in extension.required_paths(RUN) if not os.path.exists(path)]
    if missing:
        raise SystemExit("Kimi K3 collection incomplete:\n" + "\n".join(missing))
    provenance = validate_metadata()

    frozen = campaign.load_registry(os.path.join("Data", "Python", "pypi_package_names.csv"))
    current = campaign.load_registry(os.path.join(
        "Data", "Python", "pypi_package_names_2026-08-12.csv"))
    campaign.FROZEN_REGISTRY, campaign.CURRENT_REGISTRY = frozen, current

    cells = campaign.load_responses(frozen, current)
    for model, run in PRIOR_EXTENSION:
        cells[model] = extension.load_cell(model, run, frozen, current)
    k3_rows = extension.load_cell(MODEL, RUN, frozen, current)
    grouped_k3 = campaign.prompt_rows(k3_rows)

    comparisons = []
    for index, (model, rows) in enumerate(cells.items()):
        item = {"pair": f"{model} vs {MODEL}"}
        item.update(campaign.bootstrap_pair(
            campaign.prompt_rows(rows), grouped_k3,
            seed=campaign.BOOTSTRAP_SEED + 300 + index,
        ))
        comparisons.append(item)
    campaign.holm(comparisons, "bootstrap_tail_p", "bootstrap_tail_holm_p")
    campaign.holm(comparisons, "recentered_null_p", "recentered_null_holm_p")

    primary = campaign.summarize_cell(k3_rows)[0]
    grouped = campaign.prompt_rows(k3_rows)
    primary["prompt_risk_pct"] = round(
        100 * sum(value["h"] > 0 for value in grouped.values()) / len(grouped), 3
    )
    mechanism = diagnostics.analyze_cell(MODEL, RUN, frozen, current)
    exact_caps = exact_package_cap_diagnostics(frozen, current)
    prespecified_mechanism = {
        "overall_response_and_volume_summary": mechanism["overall"],
        "by_query": mechanism["by_query"],
        "by_dataset": mechanism["by_dataset"],
        "by_dataset_and_query": mechanism["by_dataset_and_query"],
        "volume_sensitivity": mechanism["volume_sensitivity"],
        "position_profile_overall": mechanism["position_profile_overall"],
        "position_profile_query_1": mechanism["position_profile_query_1"],
        "position_profile_query_2": mechanism["position_profile_query_2"],
        "exact_package_cap_diagnostics": exact_caps,
    }
    additional_descriptive = {
        "package_volume_quartiles_overall": mechanism[
            "package_volume_quartiles_overall"
        ],
        "package_volume_quartiles_query_2": mechanism[
            "package_volume_quartiles_query_2"
        ],
        "catalog_reuse": mechanism["catalog_reuse"],
        "paired_query_overlap": mechanism["paired_query_overlap"],
        "largest_response_ids": mechanism["largest_response_ids"],
    }
    with open(os.path.join("Tests", RUN, "run_manifest.json"), encoding="utf-8") as handle:
        manifest = json.load(handle)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": (
            "complete Kimi K3 extension; scientific design attested as pre-outcome, "
            "with retrospective provenance limitation"
        ),
        "preregistration": "Experiments/PREREGISTRATION_KIMI_K3_EXTENSION.md",
        "primary": primary,
        "prespecified_mechanism_diagnostics": prespecified_mechanism,
        "additional_descriptive_diagnostics": additional_descriptive,
        "exact_package_cap_diagnostics": exact_caps,
        "paired_comparisons": comparisons,
        "paired_comparison_p_value_reporting": {
            "bootstrap_replicates": campaign.REPS,
            "holm_family_size": len(comparisons),
            "smallest_resolvable_holm_adjusted_p": round(
                len(comparisons) / campaign.REPS, 6
            ),
            "note": (
                "Values at the Monte Carlo/Holm resolution floor are reported as upper "
                "bounds (<=), not exact p-values, in the human-readable table."
            ),
        },
        "response_metadata_gate": provenance,
        "manifest": extension.manifest_summary(RUN),
        "estimated_cost_usd": manifest["client"]["cost_tracking"]["estimated_cost_usd"],
    }
    with open(OUT_JSON, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)

    q1 = mechanism["by_query"]["query_1"]
    q2 = mechanism["by_query"]["query_2"]
    exact_response_caps = provenance["totals"]["truncated"]
    ci = primary["unregistered_rate_cluster_ci"]
    cap_only = exact_caps["cap_hit_only"]
    cap_excluded = exact_caps["cap_hit_excluded"]

    def rate(summary: dict) -> str:
        value = summary.get("unregistered_rate_pct")
        return "n/a" if value is None else f"{value:.2f}%"

    def position_rate(item: dict) -> str:
        value = item.get("unregistered_rate_pct")
        return "n/a" if value is None else f"{value:.3f}%"

    positions_q1 = {item["position"]: item
                    for item in mechanism["position_profile_query_1"]}
    positions_q2 = {item["position"]: item
                    for item in mechanism["position_profile_query_2"]}
    clean_q1 = {item["position"]: item for item in
                exact_caps["query_1"]["position_profile_cap_hit_excluded"]}
    clean_q2 = {item["position"]: item for item in
                exact_caps["query_2"]["position_profile_cap_hit_excluded"]}
    position_rows = []
    for label, _low, _high in diagnostics.POSITION_BINS:
        position_rows.append(
            f"| {label} | {positions_q1[label]['occurrences']:,} | "
            f"{position_rate(positions_q1[label])} | "
            f"{position_rate(clean_q1[label])} | "
            f"{positions_q2[label]['occurrences']:,} | "
            f"{position_rate(positions_q2[label])} | "
            f"{position_rate(clean_q2[label])} |"
        )

    holm_floor = len(comparisons) / campaign.REPS

    def adjusted_p(value: float) -> str:
        return f"≤{holm_floor:.6f}" if value <= holm_floor else f"{value:.6f}"

    comparison_rows = []
    for item in comparisons:
        low, high = item["percentile_ci"]
        comparison_rows.append(
            f"| {item['pair']} | {item['observed_diff_pp']:.3f} | "
            f"{low:.3f} to {high:.3f} | "
            f"{adjusted_p(item['bootstrap_tail_holm_p'])} | "
            f"{adjusted_p(item['recentered_null_holm_p'])} |"
        )
    md = f"""# Kimi K3 extension results

**Status:** complete extension under a pre-outcome-attested scientific design; the missing
pre-run commit prevents a cryptographic preregistration claim.

| Outcome | Result |
|---|---:|
| Combined unregistered recommendation rate (95% CI) | {primary['unregistered_rate_pct']:.2f}% ({ci[0]:.2f}–{ci[1]:.2f}) |
| Prompt risk | {primary['prompt_risk_pct']:.2f}% |
| List coverage / malformed / empty | {primary['coverage_list_pct']:.2f}% / {primary['malformed_rate_pct']:.2f}% / {primary['empty_rate_pct']:.2f}% |
| Query 1 rate / parsed occurrences | {q1['unregistered_rate_pct']:.2f}% / {q1['parsed_package_occurrences']:,} |
| Query 2 rate / parsed occurrences | {q2['unregistered_rate_pct']:.2f}% / {q2['parsed_package_occurrences']:,} |
| Exact response cap hits (all phases) | {exact_response_caps} |
| Exact package-response cap hits | {exact_caps['exact_package_cap_hits']} |
| Exact package cap-hit rate / occurrences | {rate(cap_only)} / {cap_only['parsed_package_occurrences']:,} |
| Excluding exact package cap hits | {rate(cap_excluded)} / {cap_excluded['parsed_package_occurrences']:,} occurrences |
| Estimated analytic pay-go cost (smoke excluded) | ${result['estimated_cost_usd']:.2f} |

All 2,400 responses passed the ordered metadata-sidecar gate. The machine-readable artifact
contains the prespecified position, response-volume, query, dataset, and exact cap diagnostics,
plus the eight-comparison Holm family involving Kimi K3. Additional catalog-reuse, query-overlap,
and quartile summaries are explicitly stored as descriptive rather than prespecified.

## Position profile

| Position | Q1 occurrences | Q1 rate | Q1 rate excluding exact caps | Q2 occurrences | Q2 rate | Q2 rate excluding exact caps |
|---|---:|---:|---:|---:|---:|---:|
{os.linesep.join(position_rows)}

## Paired comparisons

Differences are comparator minus Kimi K3 in percentage points. Each row uses all 800 shared
prompts. Both Holm columns adjust the separately specified eight-comparison K3 family.
Values shown as ≤0.000160 reached the 50,000-replicate Monte Carlo/Holm resolution floor and
must not be read as exact p-values.

| Pair | Difference (pp) | 95% percentile CI | Holm bootstrap-tail p | Holm recentered-null p |
|---|---:|---:|---:|---:|
{os.linesep.join(comparison_rows)}

## Protocol and implementation provenance

“Frozen” applies to the scientific design: prompts, parser, registries, model and sampling
settings, primary estimand, mechanism summaries, bootstrap plan, and comparison family.
Provenance and completion-gate code was expanded while collection was in flight, before package
responses were scored. The live collector had already loaded the earlier implementation—visible
because its finalized manifest lacks fields added later to `llm_api.py`—so the executable
pipeline was not byte-frozen end to end. These edits recorded identity, cap, cost, completeness,
and artifact hashes; they did not change prompts, responses, parser decisions, or outcome
calculations. The retrospective provenance stamp preserves this limitation and does not convert
the run into a cryptographic pre-data preregistration.
"""
    with open(OUT_MD, "w", encoding="utf-8", newline="") as handle:
        handle.write(md)
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
