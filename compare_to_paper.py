"""Place a run's results on the paper's scale.

Reads one or more ``Tests/<run>/FINAL_RESULTS.csv`` files, computes the hallucination rate
exactly as the paper defines it, and prints the result against the 16 models from Tables 7
and 8 (Appendix E of arXiv:2406.10279v3).

The metric, from §5.1: "a simple ratio of the number of hallucinated packages to the total
number of recommended packages", pooling all three detection heuristics --

    rate = (hallucinated_1 + hallucinated_2 + install_hallucinated)
         / (valid_1 + hallucinated_1 + valid_2 + hallucinated_2 + install_valid
            + install_hallucinated)

-- where `_1` is the query over the model's own generated code, `_2` the query over the
original prompt, and `install_*` the `pip install` / `npm install` commands parsed out of
the generated code. See Baselines/README.md for the derivation and its verification.

Usage
-----
    python compare_to_paper.py                          # every run under Tests/
    python compare_to_paper.py Tests/ollama_codellama_7b_Python
    python compare_to_paper.py --verify-baseline        # self-check, no run needed
    python compare_to_paper.py --csv out.csv            # machine-readable output
"""

from __future__ import annotations

import argparse
import ast
import glob
import json
import math
import os

import numpy as np
import pandas as pd

BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "Baselines", "paper_appendix_e.csv")

# FINAL_RESULTS.csv row labels, grouped the way Tables 7 and 8 group them.
DATASET_GROUPS = {"llm": ["LLM_LY", "LLM_AT"], "so": ["SO_LY", "SO_AT"]}

# Ollama tags for the paper's models, so a run of one of them is reported as a replication
# rather than a cross-model comparison. Matching is substring-based on the model spec, so
# ":7b" also covers ":7b-instruct". These are the closest public equivalents, not proven
# identical checkpoints -- see EXTENSION_NOTES.md for what differs.
PAPER_ALIASES = {
    "CodeLlama 7B": ["codellama:7b"],
    "CodeLlama 13B": ["codellama:13b"],
    "CodeLlama 34B": ["codellama:34b"],
    "DeepSeek 1B": ["deepseek-coder:1.3b"],
    "DeepSeek 6B": ["deepseek-coder:6.7b"],
    "DeepSeek 33B": ["deepseek-coder:33b"],
    "Mistral 7B": ["mistral:7b"],
    "Mixtral 8x7B": ["mixtral:8x7b"],
    "MagiCoder 7B": ["magicoder:7b"],
    "OpenChat 7B": ["openchat:7b"],
    "WizardCoder 33B": ["wizardcoder:33b"],
}


def load_baseline():
    baseline = pd.read_csv(BASELINE)
    baseline["computed_rate"] = 100 * (
        (baseline["llm_hallucinated"] + baseline["so_hallucinated"] + baseline["install_hallucinated"])
        / (baseline["llm_packages"] + baseline["so_packages"] + baseline["install_packages"])
    )
    return baseline


def verify_baseline():
    """Check the transcription against the percentages the paper prints beside the counts."""
    baseline = load_baseline()
    baseline["delta"] = (baseline["computed_rate"] - baseline["paper_rate"]).abs()
    bad = baseline[baseline["delta"] > 0.005]
    print(f"{len(baseline)} baseline rows across {baseline['model'].nunique()} models")
    if bad.empty:
        print("OK: every row's components reproduce the published total to within 0.005 pp")
        return True
    print("MISMATCH:")
    print(bad[["model", "language", "paper_rate", "computed_rate", "delta"]].to_string(index=False))
    return False


def rate_from_results(results_path):
    """Compute the paper's metric from one FINAL_RESULTS.csv."""
    df = pd.read_csv(results_path, index_col=0)
    install_valid = "pip_valid" if "pip_valid" in df.columns else "npm_valid"
    install_hall = "pip_hallucinated" if "pip_valid" in df.columns else "npm_hallucinated"

    missing = [c for c in ("valid_1", "hallucinated_1", "valid_2", "hallucinated_2",
                           install_valid, install_hall) if c not in df.columns]
    if missing:
        raise ValueError(f"{results_path} is missing columns: {missing}")

    parts = {}
    for group, rows in DATASET_GROUPS.items():
        present = [r for r in rows if r in df.index]
        if not present:
            raise ValueError(f"{results_path} has no rows for {rows}")
        block = df.loc[present]
        hallucinated = block[["hallucinated_1", "hallucinated_2"]].to_numpy().sum()
        total = hallucinated + block[["valid_1", "valid_2"]].to_numpy().sum()
        parts[group] = (int(hallucinated), int(total))

    all_rows = df.loc[[r for r in sum(DATASET_GROUPS.values(), []) if r in df.index]]
    install_h = int(all_rows[install_hall].sum())
    parts["install"] = (install_h, install_h + int(all_rows[install_valid].sum()))

    hallucinated = sum(h for h, _ in parts.values())
    total = sum(n for _, n in parts.values())
    return {
        "hallucinated": hallucinated,
        "packages": total,
        "rate": 100 * hallucinated / total if total else float("nan"),
        "parts": parts,
        "language": "Python" if install_valid == "pip_valid" else "Javascript",
    }


def _count_cell(cell):
    """Length of a list stored as a Python literal in a results CSV cell."""
    if pd.isna(cell):
        return 0
    try:
        value = ast.literal_eval(cell)
    except (ValueError, SyntaxError):
        return 0
    return len(value) if isinstance(value, list) else 0


def prompt_level_counts(run_dir):
    """Per-prompt (hallucinated, total) count arrays per dataset, from *_results.csv.

    Returns None when the per-prompt files are not present (they live under Tests/, which
    is not committed -- rerun the experiment to regenerate them).
    """
    counts = {}
    for prefix in (p for group in DATASET_GROUPS.values() for p in group):
        path = os.path.join(run_dir, f"{prefix}_results.csv")
        if not os.path.exists(path):
            return None
        df = pd.read_csv(path)
        install = (("pip_valid", "pip_hallucinated") if "pip_valid" in df.columns
                   else ("npm_valid", "npm_hallucinated"))
        pairs = [("valid_1", "hallucinated_1"), ("valid_2", "hallucinated_2"), install]
        hallucinated = sum(df[h].map(_count_cell) for _, h in pairs)
        total = hallucinated + sum(df[v].map(_count_cell) for v, _ in pairs)
        counts[prefix] = (hallucinated.to_numpy(), total.to_numpy())
    return counts


def cluster_bootstrap(counts, reps=2000, seed=0):
    """Stratified prompt-cluster bootstrap 95% interval for the pooled rate.

    Package recommendations cluster within prompts, so a binomial interval over packages
    understates uncertainty. The prompt is the sampling unit: resample prompts with
    replacement within each of the four datasets, recompute the pooled rate each time.
    """
    rng = np.random.default_rng(seed)
    rates = np.empty(reps)
    for rep in range(reps):
        hallucinated = total = 0
        for h, t in counts.values():
            index = rng.integers(0, len(h), len(h))
            hallucinated += h[index].sum()
            total += t[index].sum()
        rates[rep] = 100 * hallucinated / total if total else float("nan")
    return np.nanpercentile(rates, [2.5, 97.5])


def describe_run(run_dir):
    """Pull model spec, sampling and deviations out of run_manifest.json if it exists."""
    manifest_path = os.path.join(run_dir, "run_manifest.json")
    if not os.path.exists(manifest_path):
        return {}
    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (ValueError, OSError):
        return {}
    return {
        "model_spec": manifest.get("model_spec"),
        "sampling": manifest.get("sampling_requested", {}),
        "deviations": manifest.get("deviations_from_paper", {}),
        "sample": {k: manifest.get(k) for k in ("limit", "sample", "seed") if manifest.get(k)},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="*",
                        help="Run directories under Tests/ (default: all of them)")
    parser.add_argument("--verify-baseline", action="store_true",
                        help="Check the transcribed baseline against the paper, then exit")
    parser.add_argument("--csv", default=None, help="Also write the comparison to this path")
    args = parser.parse_args()

    if args.verify_baseline:
        raise SystemExit(0 if verify_baseline() else 1)

    runs = args.runs or sorted(
        os.path.dirname(p) for p in glob.glob(os.path.join("Tests", "*", "FINAL_RESULTS.csv")))
    if not runs:
        raise SystemExit("No runs found. Expected Tests/<run>/FINAL_RESULTS.csv — pass a "
                         "directory explicitly, or run run_test_api.py first.")

    baseline = load_baseline()
    measured = []
    for run in runs:
        results_path = os.path.join(run, "FINAL_RESULTS.csv")
        if not os.path.exists(results_path):
            print(f"skipping {run}: no FINAL_RESULTS.csv")
            continue
        try:
            result = rate_from_results(results_path)
        except ValueError as exc:
            print(f"skipping {run}: {exc}")
            continue
        result["run"] = os.path.basename(run)
        result.update(describe_run(run))
        measured.append(result)

    if not measured:
        raise SystemExit("No usable results found.")

    for result in measured:
        language = result["language"]
        print()
        print("=" * 78)
        print(f"{result['run']}   [{language}]")
        if result.get("model_spec"):
            print(f"model: {result['model_spec']}")
        if result.get("sample"):
            print(f"subset: {result['sample']}  <- a subset, not the paper's full dataset")
        if result.get("deviations"):
            print(f"deviations from paper settings: "
                  f"{ {k: v['used'] for k, v in result['deviations'].items()} }")
        print("=" * 78)

        print(f"\nHallucination rate: {result['rate']:.2f}%  "
              f"({result['hallucinated']:,}/{result['packages']:,} packages)")

        counts = prompt_level_counts(run)
        p, n = result["rate"] / 100, result["packages"]
        binom = 1.96 * math.sqrt(p * (1 - p) / n) * 100 if n else float("nan")
        if counts is not None:
            low, high = cluster_bootstrap(counts)
            print(f"  95% CI: [{low:.2f}%, {high:.2f}%]  (prompt-cluster bootstrap; "
                  f"package-binomial would be ±{binom:.2f} pp and understates uncertainty)")
        else:
            print(f"  95% CI: ±{binom:.2f} pp package-binomial ONLY -- per-prompt files "
                  f"absent, and packages cluster within prompts, so the true interval is wider")
        print("\n  by heuristic group:")
        labels = {"llm": "LLM-generated prompts", "so": "Stack Overflow prompts",
                  "install": "pip/npm install"}
        for key, (hallucinated, total) in result["parts"].items():
            share = 100 * hallucinated / total if total else float("nan")
            print(f"    {labels[key]:<24} {share:6.2f}%  ({hallucinated:,}/{total:,})")

        scale = baseline[baseline["language"] == language].sort_values("paper_rate")
        if scale.empty:
            print(f"\n  no paper baseline for {language}")
            continue

        print(f"\n  against the paper's {language} results (Table "
              f"{7 if language == 'Python' else 8}):")
        placed = False
        for _, row in scale.iterrows():
            if not placed and result["rate"] < row["paper_rate"]:
                print(f"    {'>>> ' + result['run']:<28} {result['rate']:6.2f}%   <-- this run")
                placed = True
            print(f"    {row['model']:<28} {row['paper_rate']:6.2f}%")
        if not placed:
            print(f"    {'>>> ' + result['run']:<28} {result['rate']:6.2f}%   <-- this run")

        best, worst = scale.iloc[0], scale.iloc[-1]
        print(f"\n  paper range: {best['paper_rate']:.2f}% ({best['model']}) to "
              f"{worst['paper_rate']:.2f}% ({worst['model']}); "
              f"mean {scale['paper_rate'].mean():.2f}%")

        # If the run reproduces a model the paper tested, that is a check on the pipeline
        # itself rather than a comparison between models.
        def normalize(text):
            return "".join(c for c in text.lower() if c.isalnum())

        spec = normalize(f"{result.get('model_spec', '')} {result['run']}")
        for _, row in scale.iterrows():
            keys = [normalize(row["model"])] + [normalize(a) for a in
                                                PAPER_ALIASES.get(row["model"], [])]
            if any(key and key in spec for key in keys):
                delta = result["rate"] - row["paper_rate"]
                print(f"\n  REPLICATION: this run appears to be the paper's "
                      f"'{row['model']}'.\n    paper {row['paper_rate']:.2f}%  vs  "
                      f"this run {result['rate']:.2f}%   (delta {delta:+.2f} pp)")
                break

    if args.csv:
        pd.DataFrame([{
            "run": r["run"], "language": r["language"], "rate": r["rate"],
            "hallucinated": r["hallucinated"], "packages": r["packages"],
            "llm_rate": 100 * r["parts"]["llm"][0] / max(r["parts"]["llm"][1], 1),
            "so_rate": 100 * r["parts"]["so"][0] / max(r["parts"]["so"][1], 1),
            "install_rate": 100 * r["parts"]["install"][0] / max(r["parts"]["install"][1], 1),
            "model_spec": r.get("model_spec", ""),
        } for r in measured]).to_csv(args.csv, index=False)
        print(f"\nWrote {args.csv}")


if __name__ == "__main__":
    main()
