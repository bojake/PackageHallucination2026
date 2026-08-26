"""Score the preregistered Qwen/Kimi Ollama Cloud extension.

The script does not modify Campaign 4 artifacts. It reuses the frozen Parser v2,
dual-registry definition, prompt-cluster summaries, and paired bootstrap implementation.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import post_campaign_analysis as campaign


NEW_MODELS = [
    ("qwen3.5:cloud", "trackC_ollama_qwen3-5-cloud_Python"),
    ("kimi-k2.7-code:cloud", "trackC_ollama_kimi-k2-7-code-cloud_Python"),
]
OUT_JSON = os.path.join("Experiments", "ollama_cloud_extension_results.json")
OUT_MD = os.path.join("Experiments", "OLLAMA_CLOUD_EXTENSION_RESULTS.md")


def required_paths(run_name: str) -> list[str]:
    files = [os.path.join("Tests", run_name, "run_manifest.json")]
    for dataset in campaign.KEYS:
        files.append(os.path.join("Tests", run_name, f"{dataset}_code.json"))
        files.extend(os.path.join("Tests", run_name, f"{dataset}_packages_{mode}.json")
                     for mode in (1, 2))
    return files


def load_cell(model: str, run_name: str, frozen: set[str], current: set[str]):
    rows = []
    for dataset in campaign.KEYS:
        for mode in (1, 2):
            path = os.path.join("Tests", run_name, f"{dataset}_packages_{mode}.json")
            with open(path, encoding="utf-8") as handle:
                for index, line in enumerate(handle):
                    if not line.strip():
                        continue
                    text = str(json.loads(line))
                    status, packages = campaign.parser_v2.classify(text)
                    unregistered = []
                    for package in packages:
                        name = campaign.normalize(package)
                        if name not in frozen and name not in current and name not in campaign.STDLIB:
                            unregistered.append(package)
                    rows.append({
                        "model": model, "run": run_name, "dataset": dataset,
                        "mode": mode, "index": index,
                        "id": f"{model}:{dataset}:q{mode}:{index}",
                        "text": text, "status": status, "packages": packages,
                        "package_count": len(packages), "unregistered": unregistered,
                        "unregistered_count": len(unregistered),
                    })
    return rows


def manifest_summary(run_name: str) -> dict:
    path = os.path.join("Tests", run_name, "run_manifest.json")
    manifest = json.load(open(path, encoding="utf-8"))
    return {
        "path": path.replace("\\", "/"),
        "model_spec": manifest.get("model_spec"),
        "model_identity": manifest.get("model_identity"),
        "served_model_ids": (manifest.get("client") or {}).get("served_model_ids"),
        "sampling_requested": manifest.get("sampling_requested"),
        "deviations_from_paper": manifest.get("deviations_from_paper"),
        "request_adjustments": (manifest.get("client") or {}).get("request_adjustments"),
        "token_usage_cumulative": manifest.get("token_usage_cumulative"),
        "runs": manifest.get("runs"),
    }


def write_pending(missing: dict[str, list[str]]) -> None:
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "pending model collection",
        "preregistration": "Experiments/PREREGISTRATION_OLLAMA_CLOUD_EXTENSION.md",
        "missing": missing,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(f"wrote pending status to {OUT_JSON}")


def write_markdown(result: dict) -> None:
    rows = []
    for model, cell in result["new_cells"].items():
        ci = "–".join(f"{value:.2f}" for value in cell["unregistered_rate_cluster_ci"])
        rows.append(
            f"| {model} | {cell['unregistered_rate_pct']:.2f}% ({ci}) | "
            f"{cell['prompt_risk_pct']:.2f}% | {cell['malformed_rate_pct']:.2f}% | "
            f"{cell['empty_rate_pct']:.2f}% | {cell['tail']['top3_response_share_pct']:.1f}% |"
        )
    significant_tail = sum(item["bootstrap_tail_holm_significant_05"]
                           for item in result["paired_comparisons"])
    significant_centered = sum(item["recentered_null_holm_significant_05"]
                               for item in result["paired_comparisons"])
    md = f"""# Ollama Cloud extension results

**Status:** preregistered extension to frozen Campaign 4.

| Model | Unregistered recommendation rate (95% CI) | Prompt risk | Malformed | Empty | Top-3 share |
|---|---:|---:|---:|---:|---:|
{os.linesep.join(rows)}

Intervals are dataset-stratified prompt-cluster bootstrap intervals. Pairwise inference uses
the 13 comparisons involving Qwen 3.5 Cloud or Kimi K2.7 Code Cloud; Holm correction is isolated
from Campaign 4's original family. {significant_tail} comparisons survive the original
bootstrap-tail convention and {significant_centered} survive the recentered-null sensitivity.

These are extension cells, not retroactive members of the frozen Campaign 4 cohort. Model
identity, served aliases, sampling adjustments, token use, cap hits, and errors are retained
in the machine-readable artifact and run manifests.
"""
    with open(OUT_MD, "w", encoding="utf-8", newline="") as handle:
        handle.write(md)


def main() -> None:
    missing = {model: [path for path in required_paths(run) if not os.path.exists(path)]
               for model, run in NEW_MODELS}
    missing = {model: paths for model, paths in missing.items() if paths}
    if missing:
        write_pending(missing)
        return

    frozen = campaign.load_registry(os.path.join("Data", "Python", "pypi_package_names.csv"))
    current = campaign.load_registry(os.path.join(
        "Data", "Python", "pypi_package_names_2026-08-12.csv"))
    campaign.FROZEN_REGISTRY, campaign.CURRENT_REGISTRY = frozen, current

    existing_cells = campaign.load_responses(frozen, current)
    new_rows = {model: load_cell(model, run, frozen, current) for model, run in NEW_MODELS}
    all_cells = {**existing_cells, **new_rows}
    grouped = {model: campaign.prompt_rows(rows) for model, rows in all_cells.items()}

    labels = list(all_cells)
    new_labels = {model for model, _ in NEW_MODELS}
    comparisons = []
    comparison_index = 0
    for left_index, left in enumerate(labels):
        for right in labels[left_index + 1:]:
            if left not in new_labels and right not in new_labels:
                continue
            item = {"pair": f"{left} vs {right}"}
            item.update(campaign.bootstrap_pair(
                grouped[left], grouped[right],
                seed=campaign.BOOTSTRAP_SEED + 100 + comparison_index))
            comparisons.append(item)
            comparison_index += 1
    campaign.holm(comparisons, "bootstrap_tail_p", "bootstrap_tail_holm_p")
    campaign.holm(comparisons, "recentered_null_p", "recentered_null_holm_p")

    new_summaries = {}
    for model, rows in new_rows.items():
        summary = campaign.summarize_cell(rows)[0]
        prompt_groups = campaign.prompt_rows(rows)
        summary["prompt_risk_pct"] = round(
            100 * sum(value["h"] > 0 for value in prompt_groups.values())
            / len(prompt_groups), 3)
        new_summaries[model] = summary

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "complete preregistered Ollama Cloud extension",
        "preregistration": "Experiments/PREREGISTRATION_OLLAMA_CLOUD_EXTENSION.md",
        "registries": {"frozen": "Data/Python/pypi_package_names.csv",
                       "current": "Data/Python/pypi_package_names_2026-08-12.csv"},
        "bootstrap": {"cluster": "prompt", "stratified_by_dataset": True,
                      "cell_interval_replicates": campaign.REPS,
                      "paired_comparison_replicates": campaign.REPS,
                      "seed_family": campaign.BOOTSTRAP_SEED},
        "new_cells": new_summaries,
        "paired_comparisons": comparisons,
        "manifests": {model: manifest_summary(run) for model, run in NEW_MODELS},
        "guardrails": [
            "These cells extend rather than alter frozen Campaign 4.",
            "Holm correction covers only the 13 comparisons involving a new cell.",
            "Raw rates remain conditional on Parser v2-accepted package tokens.",
            "Report response coverage and tail concentration with every occurrence rate.",
        ],
    }
    with open(OUT_JSON, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    write_markdown(result)
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
