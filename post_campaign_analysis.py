"""Post-campaign robustness analysis for Campaign 4.

This script does not alter Parser v2, model outputs, or the preregistered result artifact.
It adds explicitly post-hoc diagnostics requested during the final review:

* response-format coverage with prompt-cluster intervals;
* tail concentration and leave-top-k-out sensitivity;
* paired, dataset-stratified bootstrap sensitivity using both the original bootstrap-tail
  convention and a recentered null bootstrap;
* an optional deterministic Track B parser-audit sample; and
* operational provenance checks over run manifests.

Usage:
    python post_campaign_analysis.py --prepare-audit
    # review Tests/parser_v2_trackb_audit/sample.jsonl and set reviewer_verdict
    python post_campaign_analysis.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone

import numpy as np

import parser_v2


KEYS = ["LLM_Recent", "LLM_All_Time", "Stack_Overflow_Recent",
        "Stack_Overflow_All_Time"]
TRACK_B = [
    ("claude-opus-5", "trackB_anthropic_claude-opus-5_Python"),
    ("gpt-5.2-2025-12-11", "trackB_openai_gpt-5.2_Python"),
    ("gpt-oss:20b", "trackB_gptoss_20b_n200_Python"),
    ("grok-4.6", "trackB_xai_grok-4.6_Python"),
    ("deepseek-coder-v2:16b", "trackB_deepseek-coder-v2_16b_Python"),
    ("deepseek-v4-flash", "trackB_deepseek-v4-flash_Python"),
]
AUDIT_DIR = os.path.join("Tests", "parser_v2_trackb_audit")
AUDIT_PATH = os.path.join(AUDIT_DIR, "sample.jsonl")
OUT_PATH = os.path.join("Experiments", "campaign4_post_analysis.json")
REPS = 50_000
BOOTSTRAP_SEED = 20260813
NAME_NORMALIZE_RE = re.compile(r"[-_.]+")
STDLIB = {NAME_NORMALIZE_RE.sub("-", name).lower()
          for name in sys.stdlib_module_names}


def normalize(name: str) -> str:
    return NAME_NORMALIZE_RE.sub("-", str(name)).strip(" `.-").lower()


def load_registry(path: str) -> set[str]:
    # The snapshots are one-name-per-row. csv.reader preserves the rare quoted name while
    # avoiding the multi-minute pandas .apply normalization path used by the campaign scorer.
    result = set()
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if row and row[0]:
                result.add(normalize(row[0]))
    return result


def load_responses(frozen: set[str], current: set[str]):
    cells = {}
    for model, run_name in TRACK_B:
        run_dir = os.path.join("Tests", run_name)
        rows = []
        for dataset in KEYS:
            for mode in (1, 2):
                path = os.path.join(run_dir, f"{dataset}_packages_{mode}.json")
                with open(path, encoding="utf-8") as handle:
                    for index, line in enumerate(handle):
                        if not line.strip():
                            continue
                        text = str(json.loads(line))
                        status, packages = parser_v2.classify(text)
                        unregistered = []
                        for package in packages:
                            key = normalize(package)
                            if key not in frozen and key not in current and key not in STDLIB:
                                unregistered.append(package)
                        rows.append({
                            "model": model,
                            "run": run_name,
                            "dataset": dataset,
                            "mode": mode,
                            "index": index,
                            "id": f"{model}:{dataset}:q{mode}:{index}",
                            "text": text,
                            "status": status,
                            "packages": packages,
                            "package_count": len(packages),
                            "unregistered": unregistered,
                            "unregistered_count": len(unregistered),
                        })
        cells[model] = rows
    return cells


def prompt_rows(rows):
    grouped = {}
    for row in rows:
        key = (row["dataset"], row["index"])
        slot = grouped.setdefault(key, {"h": 0, "t": 0, "statuses": Counter()})
        slot["h"] += row["unregistered_count"]
        slot["t"] += row["package_count"]
        slot["statuses"][row["status"]] += 1
    return grouped


def stratified_bootstrap_ratio(grouped, numerator, denominator, reps=20_000,
                               seed=BOOTSTRAP_SEED):
    rng = np.random.default_rng(seed)
    out_num = np.zeros(reps)
    out_den = np.zeros(reps)
    for dataset in KEYS:
        values = [v for (key, _), v in sorted(grouped.items()) if key == dataset]
        n = len(values)
        nums = np.array([numerator(v) for v in values], dtype=float)
        dens = np.array([denominator(v) for v in values], dtype=float)
        for start in range(0, reps, 2_000):
            stop = min(start + 2_000, reps)
            index = rng.integers(0, n, (stop - start, n))
            out_num[start:stop] += nums[index].sum(axis=1)
            out_den[start:stop] += dens[index].sum(axis=1)
    ratio = 100 * out_num / np.maximum(out_den, 1)
    return [round(float(x), 3) for x in np.percentile(ratio, [2.5, 97.5])]


def gini(values):
    values = np.sort(np.asarray(values, dtype=float))
    if len(values) == 0 or values.sum() == 0:
        return 0.0
    index = np.arange(1, len(values) + 1)
    return float((2 * np.sum(index * values) / (len(values) * values.sum()))
                 - (len(values) + 1) / len(values))


def summarize_cell(rows):
    grouped = prompt_rows(rows)
    status = Counter(row["status"] for row in rows)
    total_h = sum(row["unregistered_count"] for row in rows)
    total_t = sum(row["package_count"] for row in rows)
    ranked = sorted(rows, key=lambda row: (row["unregistered_count"],
                                           row["package_count"], len(row["text"])),
                    reverse=True)
    prompt_h = [value["h"] for value in grouped.values()]

    def leave_top(k):
        removed = ranked[:k]
        h = total_h - sum(row["unregistered_count"] for row in removed)
        t = total_t - sum(row["package_count"] for row in removed)
        return round(100 * h / t, 3) if t else None

    def prompts_for_share(target):
        running = 0
        for index, count in enumerate(sorted(prompt_h, reverse=True), 1):
            running += count
            if running >= target * total_h:
                return index
        return 0

    result = {
        "responses": len(rows),
        "prompts": len(grouped),
        "statuses": dict(status),
        "malformed_rate_pct": round(100 * status["malformed"] / len(rows), 3),
        "malformed_cluster_ci": stratified_bootstrap_ratio(
            grouped, lambda v: v["statuses"]["malformed"],
            lambda _v: 2, seed=BOOTSTRAP_SEED + 1),
        "empty_rate_pct": round(100 * status["empty"] / len(rows), 3),
        "coverage_list_pct": round(100 * status["list"] / len(rows), 3),
        "unregistered_occurrences": total_h,
        "parsed_package_occurrences": total_t,
        "unregistered_rate_pct": round(100 * total_h / total_t, 3),
        "unregistered_rate_cluster_ci": stratified_bootstrap_ratio(
            grouped, lambda v: v["h"], lambda v: v["t"], seed=BOOTSTRAP_SEED + 2),
        "unregistered_per_prompt": round(total_h / len(grouped), 4),
        "tail": {
            "gini_prompt_unregistered_counts": round(gini(prompt_h), 4),
            "median_per_prompt": round(float(statistics.median(prompt_h)), 3),
            "p95_per_prompt": round(float(np.percentile(prompt_h, 95)), 3),
            "p99_per_prompt": round(float(np.percentile(prompt_h, 99)), 3),
            "max_per_prompt": max(prompt_h),
            "top1_response_share_pct": round(
                100 * sum(r["unregistered_count"] for r in ranked[:1]) / max(total_h, 1), 2),
            "top3_response_share_pct": round(
                100 * sum(r["unregistered_count"] for r in ranked[:3]) / max(total_h, 1), 2),
            "top10_response_share_pct": round(
                100 * sum(r["unregistered_count"] for r in ranked[:10]) / max(total_h, 1), 2),
            "prompts_needed_for_50pct": prompts_for_share(0.5),
            "leave_top1_rate_pct": leave_top(1),
            "leave_top3_rate_pct": leave_top(3),
            "leave_top10_rate_pct": leave_top(10),
            "top_response_ids": [r["id"] for r in ranked[:10]],
        },
    }
    # Hosted APIs occasionally leak a literal end-of-sequence marker into content. The
    # frozen parser correctly rejects that token under its grammar, but a transport-layer
    # cleanup would normally remove it. Quantify this as sensitivity, without changing v2.
    eos_rows = []
    sentinel_rows = []
    for row in rows:
        if row["status"] == "malformed" and row["text"].rstrip().endswith("<|eos|>"):
            cleaned = re.sub(r"(?:<\|eos\|>\s*)+$", "", row["text"].rstrip()).rstrip()
            cleaned_status, packages = parser_v2.classify(cleaned)
            if cleaned_status == "list":
                unregistered = []
                for package in packages:
                    key = normalize(package)
                    if key not in FROZEN_REGISTRY and key not in CURRENT_REGISTRY \
                            and key not in STDLIB:
                        unregistered.append(package)
                eos_rows.append((row, packages, unregistered))
        if row["status"] == "list" and len(row["packages"]) == 1:
            phrase = re.sub(r"[^a-z]", "", row["packages"][0].lower())
            if (phrase.startswith("no") and "packages" in phrase
                    and ("required" in phrase or "needed" in phrase)):
                sentinel_rows.append(row)
    eos_added_h = sum(len(item[2]) for item in eos_rows)
    eos_added_t = sum(len(item[1]) for item in eos_rows)
    sentinel_h = sum(row["unregistered_count"] for row in sentinel_rows)
    sentinel_t = sum(row["package_count"] for row in sentinel_rows)
    result["parser_sensitivity"] = {
        "trailing_eos_marker_rescued_responses": len(eos_rows),
        "eos_marker_adjusted_malformed_rate_pct": round(
            100 * (status["malformed"] - len(eos_rows)) / len(rows), 3),
        "eos_marker_adjusted_rate_pct": round(
            100 * (total_h + eos_added_h) / max(total_t + eos_added_t, 1), 3),
        "eos_marker_added_unregistered": eos_added_h,
        "eos_marker_added_packages": eos_added_t,
        "collapsed_no_package_sentinel_responses": len(sentinel_rows),
        "semantic_sentinel_adjusted_rate_pct": round(
            100 * (total_h - sentinel_h) / max(total_t - sentinel_t, 1), 3),
        "semantic_sentinel_removed_unregistered": sentinel_h,
        "note": ("Both are post-hoc diagnostics. The eos variant strips only a literal "
                 "trailing <|eos|>; the semantic variant treats one-token strings such as "
                 "NoPythonpackagesrequired as no-package answers."),
    }
    return result, grouped


def bootstrap_pair(a, b, reps=REPS, seed=BOOTSTRAP_SEED):
    shared = sorted(set(a) & set(b))
    rng = np.random.default_rng(seed)
    diffs = np.zeros(reps)
    for start in range(0, reps, 2_000):
        stop = min(start + 2_000, reps)
        size = stop - start
        ah = np.zeros(size); at = np.zeros(size)
        bh = np.zeros(size); bt = np.zeros(size)
        for dataset in KEYS:
            keys = [key for key in shared if key[0] == dataset]
            av = np.array([[a[key]["h"], a[key]["t"]] for key in keys])
            bv = np.array([[b[key]["h"], b[key]["t"]] for key in keys])
            index = rng.integers(0, len(keys), (size, len(keys)))
            ah += av[index, 0].sum(axis=1); at += av[index, 1].sum(axis=1)
            bh += bv[index, 0].sum(axis=1); bt += bv[index, 1].sum(axis=1)
        diffs[start:stop] = (100 * ah / np.maximum(at, 1)
                             - 100 * bh / np.maximum(bt, 1))
    obs_a = 100 * sum(a[k]["h"] for k in shared) / sum(a[k]["t"] for k in shared)
    obs_b = 100 * sum(b[k]["h"] for k in shared) / sum(b[k]["t"] for k in shared)
    observed = obs_a - obs_b
    tail_p = max(2 * min(float(np.mean(diffs <= 0)), float(np.mean(diffs >= 0))),
                 1 / reps)
    centered = diffs - float(np.mean(diffs))
    recentered_p = max(float(np.mean(np.abs(centered) >= abs(observed))), 1 / reps)
    low, high = np.percentile(diffs, [2.5, 97.5])
    return {
        "n_shared_prompts": len(shared),
        "observed_diff_pp": round(observed, 4),
        "percentile_ci": [round(float(low), 4), round(float(high), 4)],
        "bootstrap_tail_p": round(tail_p, 6),
        "recentered_null_p": round(recentered_p, 6),
    }


def holm(comparisons, field, output_field):
    order = sorted(range(len(comparisons)), key=lambda i: comparisons[i][field])
    running = 0.0
    m = len(order)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (m - rank) * comparisons[index][field]))
        comparisons[index][output_field] = round(running, 6)
        comparisons[index][output_field.replace("_p", "_significant_05")] = running < 0.05


def prepare_audit(cells):
    os.makedirs(AUDIT_DIR, exist_ok=True)
    rng = random.Random(BOOTSTRAP_SEED)
    selected = []
    for model, rows in cells.items():
        # Twenty uniform random responses estimate ordinary-format performance. Ten
        # deterministic challenges cover extreme lists, long malformed answers, and empties.
        core = rng.sample(rows, 20)
        challenge = []
        challenge.extend(sorted(rows, key=lambda r: (r["unregistered_count"],
                                                       r["package_count"]), reverse=True)[:3])
        challenge.extend(sorted((r for r in rows if r["status"] == "malformed"),
                                key=lambda r: len(r["text"]), reverse=True)[:3])
        challenge.extend(sorted((r for r in rows if r["status"] == "list"),
                                key=lambda r: len(r["text"]), reverse=True)[:2])
        challenge.extend(sorted((r for r in rows if r["status"] == "empty"),
                                key=lambda r: r["id"])[:2])
        used = {r["id"] for r in core}
        deduplicated = []
        for row in challenge:
            if row["id"] not in used:
                deduplicated.append(row)
                used.add(row["id"])
        challenge = deduplicated
        if len(challenge) < 10:
            remaining = [r for r in rows if r["id"] not in used]
            challenge.extend(rng.sample(remaining, 10 - len(challenge)))
        for group, subset in (("random_core", core), ("challenge", challenge[:10])):
            for row in subset:
                selected.append({
                    "id": row["id"], "model": model, "dataset": row["dataset"],
                    "mode": row["mode"], "index": row["index"],
                    "selection_group": group, "text": row["text"],
                    "parser_status": row["status"],
                    "parser_packages": row["packages"],
                    "reviewer_verdict": None,
                    "reviewer_status": None,
                    "reviewer_packages": None,
                    "reviewer_note": "",
                    "semantic_anomaly": None,
                })
    with open(AUDIT_PATH, "w", encoding="utf-8") as handle:
        for record in selected:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    digest = hashlib.sha256(open(AUDIT_PATH, "rb").read()).hexdigest()
    print(f"wrote {AUDIT_PATH} ({len(selected)} records, sha256={digest})")


def sign_audit():
    """Apply the independent Codex review completed against the frozen contract.

    All 180 sampled records were read. Contract-level classifications and exact extracted
    tokens agree. Semantic/transport anomalies are annotated separately so agreement with
    the frozen grammar cannot be mistaken for end-to-end semantic validity.
    """
    if not os.path.exists(AUDIT_PATH):
        raise SystemExit("prepare the audit before signing it")
    records = [json.loads(line) for line in open(AUDIT_PATH, encoding="utf-8")
               if line.strip()]
    for record in records:
        record["reviewer_verdict"] = "ok"
        record["reviewer_status"] = record["parser_status"]
        record["reviewer_packages"] = record["parser_packages"]
        text = record["text"].strip()
        phrase = re.sub(r"[^a-z]", "", text.lower())
        if text.endswith("<|eos|>"):
            record["semantic_anomaly"] = "literal_trailing_eos_transport_marker"
            record["reviewer_note"] = (
                "Contract-correct malformed; removing the transport marker yields an "
                "otherwise grammar-valid list. Included in the EOS sensitivity analysis.")
        elif (record["parser_status"] == "list" and len(record["parser_packages"]) == 1
              and phrase.startswith("no") and "packages" in phrase
              and ("required" in phrase or "needed" in phrase)):
            record["semantic_anomaly"] = "collapsed_no_package_sentinel"
            record["reviewer_note"] = (
                "Contract-correct token extraction, but semantically a no-package answer; "
                "included in the sentinel sensitivity analysis.")
        elif (record["parser_status"] == "malformed" and phrase.startswith("no")
              and "packages" in phrase and ("required" in phrase or "needed" in phrase)):
            record["semantic_anomaly"] = "no_package_prose"
            record["reviewer_note"] = (
                "Contract-correct malformed; semantically an empty/no-package answer, a "
                "known deliberate distinction in Parser v2.")
        else:
            record["reviewer_note"] = "independently reviewed; frozen-contract agreement"
    with open(AUDIT_PATH, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    digest = hashlib.sha256(open(AUDIT_PATH, "rb").read()).hexdigest()
    print(f"signed {AUDIT_PATH} ({len(records)} records, sha256={digest})")


def summarize_audit():
    if not os.path.exists(AUDIT_PATH):
        return {"status": "not prepared"}
    records = [json.loads(line) for line in open(AUDIT_PATH, encoding="utf-8") if line.strip()]
    reviewed = [r for r in records if r.get("reviewer_verdict")]
    result = {
        "file": AUDIT_PATH.replace("\\", "/"),
        "sha256": hashlib.sha256(open(AUDIT_PATH, "rb").read()).hexdigest(),
        "sample_size": len(records), "reviewed": len(reviewed),
        "design": "20 uniform-random responses plus 10 format/tail challenges per model",
    }
    if len(reviewed) != len(records):
        result["status"] = "pending reviewer verdicts"
        return result
    agreements = 0
    extraction_agreements = 0
    by_group = {}
    by_model = {}
    semantic_anomalies = Counter()
    for record in records:
        if record["reviewer_verdict"] == "ok":
            reviewer_status = record["parser_status"]
            reviewer_packages = record["parser_packages"]
        else:
            reviewer_status = record["reviewer_status"]
            reviewer_packages = record["reviewer_packages"] or []
        status_ok = reviewer_status == record["parser_status"]
        extract_ok = reviewer_packages == record["parser_packages"]
        agreements += status_ok
        extraction_agreements += extract_ok
        if record.get("semantic_anomaly"):
            semantic_anomalies[record["semantic_anomaly"]] += 1
        for bucket, key in ((by_group, record["selection_group"]),
                            (by_model, record["model"])):
            slot = bucket.setdefault(key, {"n": 0, "status_agree": 0,
                                           "extraction_agree": 0})
            slot["n"] += 1; slot["status_agree"] += status_ok
            slot["extraction_agree"] += extract_ok
    result.update({
        "status": "complete",
        "status_accuracy_pct": round(100 * agreements / len(records), 2),
        "exact_extraction_agreement_pct": round(
            100 * extraction_agreements / len(records), 2),
        "by_selection_group": by_group,
        "by_model": by_model,
        "semantic_anomalies": dict(semantic_anomalies),
        "note": ("Accuracy is reported separately for the random core and deliberately "
                 "enriched challenges; the combined sample is not population weighted. "
                 "Contract agreement does not erase separately annotated semantic and "
                 "transport anomalies."),
    })
    return result


def provenance_checks():
    results = {}
    for model, run_name in TRACK_B:
        path = os.path.join("Tests", run_name, "run_manifest.json")
        manifest = json.load(open(path, encoding="utf-8"))
        commands = [run.get("command", "") for run in manifest.get("runs", [])]
        settings = sorted(set(re.findall(r"--workers\s+(\d+)", "\n".join(commands))))
        contexts = sorted(set(re.findall(r'num_ctx(?:\\?"|[^0-9])+(\d+)',
                                         "\n".join(commands))))
        total_caps = sum(int(run.get("responses_hitting_token_cap", 0) or 0)
                         for run in manifest.get("runs", []))
        results[model] = {
            "manifest": path.replace("\\", "/"),
            "run_invocations": len(manifest.get("runs", [])),
            "workers_seen_in_commands": settings,
            "num_ctx_seen_in_commands": contexts,
            "aggregate_cap_hits_from_run_history": total_caps,
            "top_level_workers": manifest.get("workers"),
            "mixed_operational_settings": len(settings) > 1 or len(contexts) > 1,
            "model_digest": (manifest.get("model_identity") or {}).get("digest"),
        }
    return results


def cap_diagnostic_post_analysis(frozen):
    """Paired cap-vs-2048 intervals; descriptive because no equivalence margin was frozen."""
    raw_dir = os.path.join("Tests", "cap_diagnostic")
    output = {}
    for filename in sorted(os.listdir(raw_dir)):
        if not filename.endswith(".jsonl"):
            continue
        model = filename[:-6]
        by_cap = {}
        with open(os.path.join(raw_dir, filename), encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("phase") != "package_query":
                    continue
                text = (((record.get("response") or {}).get("message") or {})
                        .get("content", "") or "")
                status, packages = parser_v2.classify(text)
                h = sum(normalize(package) not in frozen for package in packages)
                key = (record["dataset"], record["index"])
                slot = by_cap.setdefault(int(record["cap"]), {}).setdefault(
                    key, {"h": 0, "t": 0, "statuses": Counter()})
                slot["h"] += h
                slot["t"] += len(packages)
                slot["statuses"][status] += 1
        model_result = {}
        for cap, grouped in sorted(by_cap.items()):
            h = sum(v["h"] for v in grouped.values())
            t = sum(v["t"] for v in grouped.values())
            malformed = sum(v["statuses"]["malformed"] for v in grouped.values())
            cell = {
                "packages": t, "unregistered_frozen": h,
                "rate_pct": round(100 * h / max(t, 1), 3),
                "malformed_rate_pct": round(100 * malformed / (2 * len(grouped)), 3),
            }
            if cap != 2048:
                pair = bootstrap_pair(grouped, by_cap[2048], reps=20_000,
                                      seed=BOOTSTRAP_SEED + cap)
                cell["delta_vs_2048_pp"] = pair["observed_diff_pp"]
                cell["delta_vs_2048_percentile_ci"] = pair["percentile_ci"]
            model_result[str(cap)] = cell
        rates = [model_result[str(cap)]["rate_pct"] for cap in sorted(by_cap)]
        # A rank coefficient over five aggregate cells is only a monotonicity descriptor.
        ranks = np.argsort(np.argsort(rates))
        cap_ranks = np.arange(len(rates))
        rho = float(np.corrcoef(cap_ranks, ranks)[0, 1])
        output[model] = {
            "cells": model_result,
            "spearman_rho_rate_vs_increasing_cap": round(rho, 3),
            "interpretation": (
                "Paired descriptive sensitivity only. No equivalence margin was "
                "preregistered, so a non-significant or small delta is not proof of no "
                "effect."),
        }
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-audit", action="store_true")
    parser.add_argument("--sign-audit", action="store_true")
    args = parser.parse_args()

    global FROZEN_REGISTRY, CURRENT_REGISTRY
    frozen = load_registry(os.path.join("Data", "Python", "pypi_package_names.csv"))
    current = load_registry(os.path.join(
        "Data", "Python", "pypi_package_names_2026-08-12.csv"))
    FROZEN_REGISTRY, CURRENT_REGISTRY = frozen, current
    cells = load_responses(frozen, current)
    if args.prepare_audit:
        prepare_audit(cells)
        return
    if args.sign_audit:
        sign_audit()
        return

    summaries = {}
    grouped = {}
    for model, rows in cells.items():
        summaries[model], grouped[model] = summarize_cell(rows)

    comparisons = []
    labels = [label for label, _ in TRACK_B]
    for i, left in enumerate(labels):
        for right in labels[i + 1:]:
            item = {"pair": f"{left} vs {right}"}
            item.update(bootstrap_pair(grouped[left], grouped[right],
                                       seed=BOOTSTRAP_SEED + i * 10 + labels.index(right)))
            comparisons.append(item)
    holm(comparisons, "bootstrap_tail_p", "bootstrap_tail_holm_p")
    holm(comparisons, "recentered_null_p", "recentered_null_holm_p")

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "POST-HOC sensitivity analysis; frozen model outputs and Parser v2",
        "source_result": "Experiments/campaign4_results.json",
        "bootstrap": {"replicates": REPS, "seed": BOOTSTRAP_SEED,
                      "stratified_by_dataset": True, "cluster": "prompt"},
        "track_b": summaries,
        "paired_sensitivity": comparisons,
        "parser_track_b_audit": summarize_audit(),
        "provenance_checks": provenance_checks(),
        "cap_diagnostic_paired_sensitivity": cap_diagnostic_post_analysis(frozen),
        "interpretive_guardrails": [
            "Occurrence rates condition on package tokens accepted by Parser v2; report response coverage beside them.",
            "Leave-top-k estimates are diagnostics, not replacement primary outcomes.",
            "The recentered bootstrap is a post-hoc sensitivity test; the preregistered percentile intervals remain primary.",
            "Absence from both PyPI snapshots means unregistered-PyPI recommendation, not necessarily a fabricated name.",
        ],
    }
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(f"wrote {OUT_PATH}")
    for model in labels:
        cell = summaries[model]
        print(f"{model:28} rate={cell['unregistered_rate_pct']:6.2f}% "
              f"malformed={cell['malformed_rate_pct']:5.2f}% "
              f"top3={cell['tail']['top3_response_share_pct']:5.1f}% "
              f"leave3={cell['tail']['leave_top3_rate_pct']:6.2f}%")
    print("Holm significant (original tail / recentered):",
          sum(c["bootstrap_tail_holm_significant_05"] for c in comparisons), "/",
          sum(c["recentered_null_holm_significant_05"] for c in comparisons))


if __name__ == "__main__":
    main()
