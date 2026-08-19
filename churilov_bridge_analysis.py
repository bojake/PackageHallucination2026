"""Bridge Campaign 4 to Churilov's code-import measurement.

This post-hoc analysis uses only frozen model outputs. It applies the extraction logic in
Churilov et al.'s public artifact (pip-install H1 plus top-level Python imports), scores the
result against both repository snapshots, and quantifies cross-model overlap with and
without prompt alignment.

Outputs:
    Experiments/churilov_bridge_analysis.json
    Experiments/CHURILOV_BRIDGE_ANALYSIS.md
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
import re
import sys
import warnings
from collections import Counter
from datetime import datetime, timezone

import numpy as np

import parser_v2


DATASETS = ["LLM_Recent", "LLM_All_Time", "Stack_Overflow_Recent",
            "Stack_Overflow_All_Time"]
MODELS = [
    ("claude-opus-5", "trackB_anthropic_claude-opus-5_Python"),
    ("gpt-5.2-2025-12-11", "trackB_openai_gpt-5.2_Python"),
    ("gpt-oss:20b", "trackB_gptoss_20b_n200_Python"),
    ("grok-4.6", "trackB_xai_grok-4.6_Python"),
    ("deepseek-coder-v2:16b", "trackB_deepseek-coder-v2_16b_Python"),
    ("deepseek-v4-flash", "trackB_deepseek-v4-flash_Python"),
]
EXTENSION_MODELS = [
    ("qwen3.5:cloud", "trackC_ollama_qwen3-5-cloud_Python"),
    ("kimi-k3:cloud", "trackC_ollama_kimi-k3-cloud_Python"),
]
FROZEN_PATH = os.path.join("Data", "Python", "pypi_package_names.csv")
CURRENT_PATH = os.path.join("Data", "Python", "pypi_package_names_2026-08-12.csv")
FALSE_POSITIVE_PATH = os.path.join("Data", "Python", "false_positive_packages.csv")
OUT_JSON = os.path.join("Experiments", "churilov_bridge_analysis.json")
OUT_MD = os.path.join("Experiments", "CHURILOV_BRIDGE_ANALYSIS.md")
BOOTSTRAP_SEED = 20260814
BOOTSTRAP_REPS = 50_000

NAME_NORMALIZE_RE = re.compile(r"[-_.]+")
PIP_INSTALL_RE = re.compile(r"pip\s+install\s+(?P<package>\S+)")
VERSION_SPEC_RE = re.compile(r"([^=<>!~]+)([=<>!~]{1,2}[\d.]+)?")
PUNCT_STRIP = str.maketrans("", "", "()[]`")
FENCE_RE = re.compile(r"```(?:python|py|)\s*\n?([\s\S]+?)```", re.IGNORECASE)

try:
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser

    TS_PARSER = Parser(Language(tspython.language()))
except Exception:  # pragma: no cover - dependency absence is recorded in the artifact
    TS_PARSER = None


def normalize(name: str) -> str:
    """Churilov/Spracklen Python normalization."""
    if not name:
        return ""
    name = str(name).translate(PUNCT_STRIP)
    if re.search(r"[+@:\"',{}/*]", name):
        return ""
    match = VERSION_SPEC_RE.match(name)
    if match:
        name = match.group(1).strip()
    if name.startswith("--") or "requirements" in name:
        return ""
    name = re.sub(r"\d\. ", "", name)
    return NAME_NORMALIZE_RE.sub("-", name).strip(' "`.-').lower()


def load_registry(path: str) -> set[str]:
    names = set()
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if row and row[0]:
                value = normalize(row[0])
                if value:
                    names.add(value)
    return names


def load_false_positives(path: str) -> set[str]:
    result = set()
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) >= 2:
                result.add(row[1])
    return result


def stdlib_names() -> set[str]:
    try:
        from stdlib_list import stdlib_list

        names = set(stdlib_list("3.11"))
        source = "stdlib-list 3.11 (matching Churilov artifact)"
    except Exception:
        names = set(sys.stdlib_module_names)
        source = f"sys.stdlib_module_names fallback ({sys.version.split()[0]})"
    names.update({"__future__", "typing", "collections", "importlib", "urllib", "xml",
                  "email", "http", "concurrent", "asyncio", "logging",
                  "multiprocessing", "_thread", "itertools", "functools"})
    return names, source


def pip_mentions(text: str) -> list[str]:
    return [raw for raw in PIP_INSTALL_RE.findall(text or "") if not raw.startswith("-")]


def ast_imports(tree: ast.AST) -> list[str]:
    output = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            output.extend(alias.name.split(".")[0] for alias in node.names if alias.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            output.append(node.module.split(".")[0])
    return output


def parse_ast(text: str) -> ast.AST:
    # Generated code frequently contains invalid string escapes. They do not affect import
    # extraction, so suppress the interpreter's forward-compatibility warning here.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        return ast.parse(text)


def tree_sitter_imports(code: str) -> list[str]:
    if TS_PARSER is None:
        return []
    try:
        tree = TS_PARSER.parse(code.encode("utf-8", errors="ignore"))
    except Exception:
        return []
    output = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "import_statement":
            for child in node.children:
                if child.type in {"dotted_name", "aliased_import"}:
                    first = child.children[0] if child.children else child
                    value = code[first.start_byte:first.end_byte].split(".")[0].strip()
                    if value:
                        output.append(value)
        elif node.type == "import_from_statement":
            for child in node.children:
                if child.type in {"dotted_name", "relative_import"}:
                    value = code[child.start_byte:child.end_byte].split(".")[0].strip()
                    if value and not value.startswith("."):
                        output.append(value)
                    break
        stack.extend(node.children)
    return output


def import_mentions(text: str, stdlib: set[str]) -> list[str]:
    """Port of Churilov's AST-first, tree-sitter-fallback extractor."""
    if not text:
        return []
    try:
        raw = ast_imports(parse_ast(text))
    except SyntaxError:
        fences = FENCE_RE.findall(text)
        raw = []
        any_ast_ok = False
        for block in fences:
            try:
                raw.extend(ast_imports(parse_ast(block)))
                any_ast_ok = True
            except SyntaxError:
                raw.extend(tree_sitter_imports(block))
        if not any_ast_ok and not fences:
            raw.extend(tree_sitter_imports(text))

    seen = set()
    output = []
    for name in raw:
        if name not in seen and name not in stdlib:
            seen.add(name)
            output.append(name)
    return output


def read_json_strings(path: str) -> list[str]:
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(str(json.loads(line)))
    return rows


def cluster_ci(grouped: dict, numerator: str, denominator: str,
               reps: int = BOOTSTRAP_REPS, seed: int = BOOTSTRAP_SEED) -> list[float]:
    rng = np.random.default_rng(seed)
    out_num = np.zeros(reps)
    out_den = np.zeros(reps)
    for dataset in DATASETS:
        values = [value for (name, _), value in sorted(grouped.items()) if name == dataset]
        nums = np.asarray([value[numerator] for value in values], dtype=float)
        dens = np.asarray([value[denominator] for value in values], dtype=float)
        for start in range(0, reps, 2_000):
            stop = min(start + 2_000, reps)
            indexes = rng.integers(0, len(values), (stop - start, len(values)))
            out_num[start:stop] += nums[indexes].sum(axis=1)
            out_den[start:stop] += dens[indexes].sum(axis=1)
    ratios = 100 * out_num / np.maximum(out_den, 1)
    return [round(float(value), 3) for value in np.percentile(ratios, [2.5, 97.5])]


def bridge_cell(run_name: str, frozen: set[str], current: set[str],
                false_positives: set[str], stdlib: set[str]) -> dict:
    grouped = {}
    channels = Counter()
    frozen_by_channel = Counter()
    dual_by_channel = Counter()
    unique_dual = set()
    for dataset in DATASETS:
        path = os.path.join("Tests", run_name, f"{dataset}_code.json")
        for index, text in enumerate(read_json_strings(path)):
            raw = [(name, "pip_install") for name in pip_mentions(text)]
            raw += [(name, "import") for name in import_mentions(text, stdlib)]
            accepted = []
            for name, channel in raw:
                value = normalize(name)
                if not value or value in false_positives:
                    continue
                accepted.append((value, channel))
                channels[channel] += 1
            frozen_h = sum(name not in frozen for name, _ in accepted)
            dual_h = sum(name not in frozen and name not in current and name not in stdlib
                         for name, _ in accepted)
            for name, channel in accepted:
                if name not in frozen:
                    frozen_by_channel[channel] += 1
                if name not in frozen and name not in current and name not in stdlib:
                    dual_by_channel[channel] += 1
            unique_dual.update(name for name, _ in accepted
                               if name not in frozen and name not in current
                               and name not in stdlib)
            grouped[(dataset, index)] = {
                "mentions": len(accepted), "frozen_h": frozen_h, "dual_h": dual_h,
                "has_reference": int(bool(accepted)), "has_dual_h": int(dual_h > 0),
            }

    mentions = sum(value["mentions"] for value in grouped.values())
    frozen_h = sum(value["frozen_h"] for value in grouped.values())
    dual_h = sum(value["dual_h"] for value in grouped.values())
    prompts = len(grouped)
    by_dataset = {}
    for dataset in DATASETS:
        values = [value for (name, _), value in grouped.items() if name == dataset]
        dataset_mentions = sum(value["mentions"] for value in values)
        dataset_frozen = sum(value["frozen_h"] for value in values)
        dataset_dual = sum(value["dual_h"] for value in values)
        by_dataset[dataset] = {
            "prompts": len(values), "mentions": dataset_mentions,
            "frozen_absence_rate_pct": round(
                100 * dataset_frozen / max(dataset_mentions, 1), 3),
            "dual_registry_nonstdlib_rate_pct": round(
                100 * dataset_dual / max(dataset_mentions, 1), 3),
        }
    return {
        "prompts": prompts,
        "extracted_mentions": mentions,
        "channel_mentions": dict(channels),
        "frozen_absence_by_channel": dict(frozen_by_channel),
        "dual_registry_nonstdlib_by_channel": dict(dual_by_channel),
        "prompts_with_any_extracted_reference": sum(v["has_reference"] for v in grouped.values()),
        "reference_coverage_pct": round(100 * sum(v["has_reference"] for v in grouped.values()) / prompts, 3),
        "churilov_compatible_frozen_absence_count": frozen_h,
        "churilov_compatible_frozen_absence_rate_pct": round(100 * frozen_h / max(mentions, 1), 3),
        "churilov_compatible_frozen_cluster_ci": cluster_ci(grouped, "frozen_h", "mentions"),
        "dual_registry_nonstdlib_unregistered_count": dual_h,
        "dual_registry_nonstdlib_unregistered_rate_pct": round(100 * dual_h / max(mentions, 1), 3),
        "dual_registry_nonstdlib_cluster_ci": cluster_ci(grouped, "dual_h", "mentions"),
        "prompt_risk_pct": round(100 * sum(v["has_dual_h"] for v in grouped.values()) / prompts, 3),
        "unique_dual_registry_nonstdlib_names": len(unique_dual),
        "by_dataset": by_dataset,
        "denominator_note": ("Package mentions, not generations. Import names are deduplicated "
                             "within a generation; pip-install and import channels are not "
                             "deduplicated against each other, matching Churilov's artifact."),
    }


def recommendation_name_map(run_name: str, frozen: set[str], current: set[str],
                            stdlib: set[str]) -> dict[str, set[tuple[str, int]]]:
    mapping = {}
    for dataset in DATASETS:
        for mode in (1, 2):
            path = os.path.join("Tests", run_name, f"{dataset}_packages_{mode}.json")
            for index, text in enumerate(read_json_strings(path)):
                status, packages = parser_v2.classify(text)
                if status != "list":
                    continue
                for package in packages:
                    name = normalize(package)
                    if name and name not in frozen and name not in current and name not in stdlib:
                        mapping.setdefault(name, set()).add((dataset, index))
    return mapping


def available_models() -> list[tuple[str, str]]:
    """Include extension cells only after every required response file exists."""
    result = list(MODELS)
    for model, run_name in EXTENSION_MODELS:
        paths = []
        for dataset in DATASETS:
            paths.append(os.path.join("Tests", run_name, f"{dataset}_code.json"))
            paths.extend(os.path.join("Tests", run_name, f"{dataset}_packages_{mode}.json")
                         for mode in (1, 2))
        if all(os.path.exists(path) for path in paths):
            result.append((model, run_name))
    return result


def jaccard(left: set, right: set) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def overlap_analysis(model_cells: list[tuple[str, str]], frozen: set[str],
                     current: set[str], stdlib: set[str]) -> dict:
    maps = {model: recommendation_name_map(run, frozen, current, stdlib)
            for model, run in model_cells}
    labels = list(maps)
    pairs = []
    for index, left in enumerate(labels):
        for right in labels[index + 1:]:
            left_names = set(maps[left])
            right_names = set(maps[right])
            shared = left_names & right_names
            same_prompt = sum(bool(maps[left][name] & maps[right][name]) for name in shared)
            left_occurrences = {(name, prompt) for name, prompts in maps[left].items()
                                for prompt in prompts}
            right_occurrences = {(name, prompt) for name, prompts in maps[right].items()
                                 for prompt in prompts}
            pairs.append({
                "pair": f"{left} vs {right}",
                "shared_unique_names": len(shared),
                "name_jaccard": round(jaccard(left_names, right_names), 5),
                "shared_names_with_same_prompt_support": same_prompt,
                "same_prompt_share_of_shared_names_pct": round(100 * same_prompt / max(len(shared), 1), 3),
                "prompt_aligned_occurrence_jaccard": round(jaccard(left_occurrences, right_occurrences), 5),
            })

    universal = set.intersection(*(set(value) for value in maps.values()))
    same_prompt_universal = 0
    for name in universal:
        common_prompts = set.intersection(*(maps[model][name] for model in labels))
        same_prompt_universal += bool(common_prompts)
    return {
        "model_unique_name_counts": {model: len(mapping) for model, mapping in maps.items()},
        "pairwise": pairs,
        "mean_pairwise_name_jaccard": round(float(np.mean([p["name_jaccard"] for p in pairs])), 5),
        "all_model_universal_name_count": len(universal),
        "all_model_same_prompt_universal_name_count": same_prompt_universal,
        "same_prompt_share_of_universal_names_pct": round(100 * same_prompt_universal / max(len(universal), 1), 3),
        "security_note": ("Names are intentionally omitted. Counts show how much apparent "
                          "cross-model universality can be induced by the same prompt."),
    }


def write_markdown(result: dict) -> None:
    rows = []
    for model, cell in result["code_bridge"].items():
        frozen_ci = "–".join(f"{value:.2f}" for value in cell["churilov_compatible_frozen_cluster_ci"])
        dual_ci = "–".join(f"{value:.2f}" for value in cell["dual_registry_nonstdlib_cluster_ci"])
        rows.append(
            f"| {model} | {cell['extracted_mentions']:,} | "
            f"{cell['churilov_compatible_frozen_absence_rate_pct']:.2f}% ({frozen_ci}) | "
            f"{cell['dual_registry_nonstdlib_unregistered_rate_pct']:.2f}% ({dual_ci}) | "
            f"{cell['reference_coverage_pct']:.1f}% | {cell['prompt_risk_pct']:.1f}% |"
        )
    overlap = result["prompt_conditioned_overlap"]
    model_count = result["model_count"]
    bridge_summary = result["bridge_summary"]
    md = f"""# Churilov bridge analysis

**Status:** post-hoc analysis of frozen Campaign 4 outputs; no model responses were changed.

## Code-only bridge

This analysis applies Churilov's public Python extraction design—`pip install` tokens plus
top-level imports—to Campaign 4's existing generated code. The first rate uses the frozen
registry for the closest artifact-level bridge. The second uses this project's stricter
dual-registry, non-stdlib definition. Intervals are dataset-stratified prompt-cluster
bootstrap intervals ({result['bootstrap']['replicates']:,} replicates), not mention-level
Wilson intervals.

| Model | Extracted mentions | Frozen-absence rate (95% CI) | Dual-registry rate (95% CI) | Code-reference coverage | Prompt risk |
|---|---:|---:|---:|---:|---:|
{os.linesep.join(rows)}

The bridge rates are not a direct replication of Churilov's model table because the model
cohorts do not overlap exactly and Campaign 4 uses 800 sampled prompts rather than the full
corpus. They do isolate the extraction-channel difference without spending more model calls.

The observed dual-registry bridge range is **{bridge_summary['dual_rate_range_pct'][0]:.2f}%–{bridge_summary['dual_rate_range_pct'][1]:.2f}%**,
which is above Churilov's reported Python range of 5.49%–7.27%. Therefore the code-only
extractor does **not** by itself reconcile the studies. {bridge_summary['import_share_of_dual_flags_pct']:.1f}%
of bridge flags came from imports rather than explicit `pip install` directives, and only
{bridge_summary['removed_by_current_registry_or_stdlib']} frozen-absence mentions were removed
by the current-registry/non-stdlib correction. The live measurement question is now the
semantic validity of mapping an import module directly to a PyPI distribution, together
with genuine model/cohort differences—not registry drift.

The dataset split is pronounced: the model-level dual-registry rates span
**{bridge_summary['llm_dataset_rate_range_pct'][0]:.2f}%–{bridge_summary['llm_dataset_rate_range_pct'][1]:.2f}%**
on LLM-synthesized datasets and **{bridge_summary['stackoverflow_dataset_rate_range_pct'][0]:.2f}%–{bridge_summary['stackoverflow_dataset_rate_range_pct'][1]:.2f}%**
on Stack Overflow datasets. This agrees directionally with Churilov's statement that
synthetic prompts yield higher rates, while showing that dataset composition and prompt
type remain substantial effect modifiers.

## Prompt-conditioned overlap

- Mean ordinary pairwise Jaccard over unique unregistered recommendation names:
  **{overlap['mean_pairwise_name_jaccard']:.3f}**.
- Names shared by all {model_count} models: **{overlap['all_model_universal_name_count']}**.
- Universal names emitted by all {model_count} on at least one identical prompt:
  **{overlap['all_model_same_prompt_universal_name_count']}**
  ({overlap['same_prompt_share_of_universal_names_pct']:.1f}% of the universal set).

This distinction matters: ordinary overlap does not identify whether a shared name reflects
shared training data, a common package misconception, or direct elicitation by the same
prompt. The aligned-prompt result demonstrates that prompt induction is a live alternative
explanation and should be measured before attributing overlap to training-corpus similarity.

Package names are deliberately excluded from this artifact because they can be actionable
slopsquatting targets.

## Interpretation

1. Churilov's code-import metric and Campaign 4's package-recommendation metric are distinct
   estimands; the bridge makes that difference quantitative on identical outputs.
2. Registry time still changes classifications after holding the extractor fixed.
3. Mention-level intervals are inappropriate for these data because references cluster
   within generated responses; the prompt-cluster intervals are the defensible comparison.
4. Cross-model overlap should be decomposed into same-prompt and different-prompt support
   before it is used as evidence about shared training origins.
"""
    with open(OUT_MD, "w", encoding="utf-8", newline="") as handle:
        handle.write(md)


def main() -> None:
    frozen = load_registry(FROZEN_PATH)
    current = load_registry(CURRENT_PATH)
    false_positives = load_false_positives(FALSE_POSITIVE_PATH)
    stdlib, stdlib_source = stdlib_names()
    campaign_stdlib = {NAME_NORMALIZE_RE.sub("-", name).lower()
                       for name in sys.stdlib_module_names}
    model_cells = available_models()
    bridge = {
        model: bridge_cell(run, frozen, current, false_positives, stdlib)
        for model, run in model_cells
    }
    dual_rates = [cell["dual_registry_nonstdlib_unregistered_rate_pct"]
                  for cell in bridge.values()]
    all_dataset_rates = {
        dataset: [cell["by_dataset"][dataset]["dual_registry_nonstdlib_rate_pct"]
                  for cell in bridge.values()]
        for dataset in DATASETS
    }
    total_frozen = sum(cell["churilov_compatible_frozen_absence_count"]
                       for cell in bridge.values())
    total_dual = sum(cell["dual_registry_nonstdlib_unregistered_count"]
                     for cell in bridge.values())
    dual_imports = sum(cell["dual_registry_nonstdlib_by_channel"].get("import", 0)
                       for cell in bridge.values())
    bridge_summary = {
        "dual_rate_range_pct": [min(dual_rates), max(dual_rates)],
        "total_frozen_absence_mentions": total_frozen,
        "total_dual_registry_nonstdlib_mentions": total_dual,
        "removed_by_current_registry_or_stdlib": total_frozen - total_dual,
        "import_share_of_dual_flags_pct": round(100 * dual_imports / max(total_dual, 1), 3),
        "llm_dataset_rate_range_pct": [
            min(all_dataset_rates["LLM_Recent"] + all_dataset_rates["LLM_All_Time"]),
            max(all_dataset_rates["LLM_Recent"] + all_dataset_rates["LLM_All_Time"]),
        ],
        "stackoverflow_dataset_rate_range_pct": [
            min(all_dataset_rates["Stack_Overflow_Recent"]
                + all_dataset_rates["Stack_Overflow_All_Time"]),
            max(all_dataset_rates["Stack_Overflow_Recent"]
                + all_dataset_rates["Stack_Overflow_All_Time"]),
        ],
    }
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "POST-HOC bridge analysis; frozen Campaign 4 outputs",
        "model_count": len(model_cells),
        "source": "Churilov public artifact extraction design, ported with attribution",
        "extractor": {
            "pip_regex": PIP_INSTALL_RE.pattern,
            "imports": "AST first; fenced-block AST then tree-sitter fallback",
            "tree_sitter_available": TS_PARSER is not None,
            "stdlib_source": stdlib_source,
            "false_positive_sha256": hashlib.sha256(open(FALSE_POSITIVE_PATH, "rb").read()).hexdigest(),
        },
        "registries": {"frozen": FROZEN_PATH.replace("\\", "/"),
                       "current": CURRENT_PATH.replace("\\", "/")},
        "bootstrap": {"cluster": "prompt", "stratified_by_dataset": True,
                      "replicates": BOOTSTRAP_REPS, "seed": BOOTSTRAP_SEED},
        "code_bridge": bridge,
        "bridge_summary": bridge_summary,
        "prompt_conditioned_overlap": overlap_analysis(
            model_cells, frozen, current, campaign_stdlib),
        "guardrails": [
            "No Campaign 4 model exactly overlaps Churilov's five-model cohort.",
            "The bridge uses Campaign 4's sampled prompts, not Churilov's full corpus.",
            "Extracted references are package mentions; the inferential cluster is the prompt.",
            "No candidate unregistered package names are published in this artifact.",
        ],
    }
    with open(OUT_JSON, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    write_markdown(result)
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    for model, cell in bridge.items():
        print(f"{model:28} frozen={cell['churilov_compatible_frozen_absence_rate_pct']:6.2f}% "
              f"dual={cell['dual_registry_nonstdlib_unregistered_rate_pct']:6.2f}%")


if __name__ == "__main__":
    main()
