"""Verify the checkable claims in codex-experiment.md against the raw run artifacts.

Reproduces, from the artifacts under Tests/:

1. Prompt-subset nesting: the n=100 CodeLlama prompt sample is contained in the n=400
   sample (same seed, larger draw), so the two runs are not independent.
2. The 64- vs 2048-token DeepSeek response relationship (equal / prefix / divergent pairs).
3. A re-score of the DeepSeek runs through the repository's own detection code with the
   original DeepSeek family parser (``overrides=(True, True, "DeepSeek")``).
4. A partition of the n=400 CodeLlama run into prompts repeated from the n=100 run versus
   newly added prompts (regeneration variance vs prompt-composition variance).
5. The hallucination rate of the literal truncated tail, measured only on response pairs
   where the long response is a strict textual extension of the short one.

Requires the run directories under Tests/ (not committed); re-run the experiments to
regenerate them. Nothing here modifies the stored artifacts -- re-scores run on copies.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare_to_paper as ctp
import package_detection
from analyze_hallucinations import ordered_parse

KEYS = ["LLM_Recent", "LLM_All_Time", "Stack_Overflow_Recent", "Stack_Overflow_All_Time"]
KEY_TO_PREFIX = {"LLM_Recent": "LLM_LY", "LLM_All_Time": "LLM_AT",
                 "Stack_Overflow_Recent": "SO_LY", "Stack_Overflow_All_Time": "SO_AT"}
PROMPT_COLUMN = {"LLM_LY": "Prompts", "LLM_AT": "Prompts", "SO_LY": "Questions",
                 "SO_AT": "Questions"}

CL_SMALL = os.path.join("Tests", "ollama_codellama_7b-instruct_Python")
CL_LARGE = os.path.join("Tests", "megatron_codellama_7b-instruct_Python")
DS_64 = os.path.join("Tests", "megatron_deepseek_6.7b_Python")
DS_2048 = os.path.join("Tests", "megatron_deepseek_6.7b_cap2048_Python")


def prompt_texts(run_dir, key):
    """Prompt strings from a {key}_prompts.json subset file (SO lines are {"0": text})."""
    texts = []
    with open(os.path.join(run_dir, f"{key}_prompts.json"), encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            texts.append(value if isinstance(value, str) else str(list(value.values())[0]))
    return texts


def response_lines(run_dir, key, mode):
    with open(os.path.join(run_dir, f"{key}_packages_{mode}.json"), encoding="utf-8") as fh:
        return [str(json.loads(line)) for line in fh if line.strip()]


def check_nesting():
    print("== 1. Prompt-subset nesting (CodeLlama n=100 vs n=400, both seed 0) ==")
    for key in KEYS:
        small = set(prompt_texts(CL_SMALL, key))
        large = set(prompt_texts(CL_LARGE, key))
        print(f"  {key:26} small={len(small):3}  large={len(large):3}  nested={small <= large}")


def check_prefix_split():
    print("\n== 2. DeepSeek 64 vs 2048 response relationship (same code, cap-only change) ==")
    equal = prefix = diverge = 0
    prefix_pairs = []
    for key in KEYS:
        for mode in (1, 2):
            for short, long_ in zip(response_lines(DS_64, key, mode),
                                    response_lines(DS_2048, key, mode)):
                if short == long_:
                    equal += 1
                elif long_.startswith(short) and len(long_) > len(short):
                    prefix += 1
                    prefix_pairs.append((short, long_))
                else:
                    diverge += 1
    total = equal + prefix + diverge
    print(f"  pairs={total}: equal={equal} ({100*equal/total:.1f}%)  "
          f"strict-prefix={prefix} ({100*prefix/total:.1f}%)  "
          f"divergent={diverge} ({100*diverge/total:.1f}%)")
    print("  -> aggregate 64-vs-2048 differences are NOT a literal truncated tail;")
    print("     only the strict-prefix pairs support a direct tail measurement (see 5).")
    return prefix_pairs


def rescore_family_parser():
    print("\n== 3. Re-score DeepSeek runs with the repo's own DeepSeek family parser ==")
    print("   (pre=True, post=True, style='DeepSeek', via package_detection.detect_packages)")
    for src, label in [(DS_64, "cap 64"), (DS_2048, "cap 2048")]:
        copy = os.path.join("Tests", "_rescore_" + os.path.basename(src))
        if os.path.exists(copy):
            shutil.rmtree(copy)
        shutil.copytree(src, copy)
        for name in os.listdir(copy):
            if name.endswith("_results.csv") or name in ("FINAL_RESULTS.csv",
                                                         "PACKAGE_NAMES.csv"):
                os.remove(os.path.join(copy, name))
        package_detection.detect_packages(os.path.join("Data", "Python"), copy,
                                          "DeepSeek_6B", "off", "Python",
                                          overrides=(True, True, "DeepSeek"))
        result = ctp.rate_from_results(os.path.join(copy, "FINAL_RESULTS.csv"))
        print(f"  {label:9} family parser: {result['rate']:6.2f}%  "
              f"({result['hallucinated']:,}/{result['packages']:,})")


def partition_large_run():
    print("\n== 4. CodeLlama n=400 partitioned: repeated prompts vs added prompts ==")
    small_prompts = {key: set(prompt_texts(CL_SMALL, key)) for key in KEYS}
    repeated_h = repeated_t = added_h = added_t = 0
    for key in KEYS:
        prefix = KEY_TO_PREFIX[key]
        df = pd.read_csv(os.path.join(CL_LARGE, f"{prefix}_results.csv"))
        column = PROMPT_COLUMN[prefix]
        pairs = [("valid_1", "hallucinated_1"), ("valid_2", "hallucinated_2"),
                 ("pip_valid", "pip_hallucinated")]
        for _, row in df.iterrows():
            hallucinated = sum(ctp._count_cell(row[h]) for _, h in pairs)
            total = hallucinated + sum(ctp._count_cell(row[v]) for v, _ in pairs)
            if str(row[column]) in small_prompts[key]:
                repeated_h += hallucinated
                repeated_t += total
            else:
                added_h += hallucinated
                added_t += total
    small = ctp.rate_from_results(os.path.join(CL_SMALL, "FINAL_RESULTS.csv"))
    print(f"  n=100 run itself:                {small['rate']:6.2f}%  "
          f"({small['hallucinated']:,}/{small['packages']:,})")
    print(f"  same prompts regenerated (n=400): {100*repeated_h/repeated_t:5.2f}%  "
          f"({repeated_h:,}/{repeated_t:,})")
    print(f"  added prompts only (n=400):       {100*added_h/added_t:5.2f}%  "
          f"({added_h:,}/{added_t:,})")
    print("  -> the aggregate n=100 vs n=400 gap is dominated by prompt composition,")
    print("     not regeneration noise; a universal +/-3pp variance rule is unsupported.")


def tail_rate(prefix_pairs):
    print("\n== 5. Tail hallucination rate, strict-prefix pairs only ==")
    master = pd.read_csv(os.path.join("Data", "Python", "pypi_package_names.csv"),
                         header=None)
    master_set = set(master[0].apply(package_detection.normalize_python).dropna())
    false_positives = set(pd.read_csv(os.path.join("Data", "Python",
                                                   "false_positive_packages.csv"),
                                      header=None)[1])
    qualifying = head_h = head_t = tail_h = tail_t = 0
    for short, long_ in prefix_pairs:
        short_items = ordered_parse(short)
        long_items = ordered_parse(long_)
        if not short_items or long_items[:len(short_items)] != short_items:
            continue  # boundary token completed differently; not a clean extension
        qualifying += 1
        for bucket, items in (("head", long_items[:len(short_items)]),
                              ("tail", long_items[len(short_items):])):
            for name in items:
                if name in false_positives and name not in master_set:
                    continue
                if bucket == "head":
                    head_t += 1
                    head_h += name not in master_set
                else:
                    tail_t += 1
                    tail_h += name not in master_set
    print(f"  qualifying pairs (parsed long is a clean extension of parsed short): "
          f"{qualifying}/{len(prefix_pairs)}")
    if head_t and tail_t:
        print(f"  head (survives the 64-token cap): {100*head_h/head_t:5.2f}%  "
              f"({head_h}/{head_t})")
        print(f"  tail (exists only at cap 2048):   {100*tail_h/tail_t:5.2f}%  "
              f"({tail_h}/{tail_t})")
        print("  -> measured on valid pairs only; small n, so indicative rather than final.")


GPT_OSS = os.path.join("Tests", "megatron_gpt-oss_20b_Python")


def _has_fence(text):
    return "```" in text


def _has_numbered(text):
    return re.search(r"(?m)^\s*\d+\.\s", text) is not None


def _row_counts(row, mode):
    h = ctp._count_cell(row[f"hallucinated_{mode}"])
    return h, h + ctp._count_cell(row[f"valid_{mode}"])


def _rows_with_text(run_dir):
    """Yield (dataset, mode, raw_response_text, hallucinated, total) per response."""
    for key in KEYS:
        prefix = KEY_TO_PREFIX[key]
        df = pd.read_csv(os.path.join(run_dir, f"{prefix}_results.csv"))
        for mode in (1, 2):
            raw = response_lines(run_dir, key, mode)
            assert len(raw) == len(df)
            for text, (_, row) in zip(raw, df.iterrows()):
                h, t = _row_counts(row, mode)
                yield key, mode, text, h, t


def addendum_query_split():
    print("\n== 6. Addendum check: cap effect split by query (DeepSeek) ==")
    for run, label in [(DS_64, "cap 64  "), (DS_2048, "cap 2048")]:
        totals = {1: [0, 0], 2: [0, 0]}
        for _, mode, _, h, t in _rows_with_text(run):
            totals[mode][0] += h
            totals[mode][1] += t
        print(f"  {label}  Q1 {100*totals[1][0]/totals[1][1]:5.2f}% "
              f"({totals[1][0]}/{totals[1][1]})   "
              f"Q2 {100*totals[2][0]/totals[2][1]:5.2f}% ({totals[2][0]}/{totals[2][1]})")


def addendum_contamination():
    print("\n== 7. Addendum check: format drift and the clean-subset diagnostic (DeepSeek Q2) ==")
    for run, label in [(DS_64, "cap 64  "), (DS_2048, "cap 2048")]:
        fence = numbered = n = 0
        all_h = all_t = clean_h = clean_t = 0
        per_row = []
        for _, mode, text, h, t in _rows_with_text(run):
            if mode != 2:
                continue
            n += 1
            fence += _has_fence(text)
            numbered += _has_numbered(text)
            all_h += h
            all_t += t
            if not (_has_fence(text) or _has_numbered(text)):
                clean_h += h
                clean_t += t
            per_row.append(h)
        per_row.sort(reverse=True)
        print(f"  {label}  fences {fence}/{n}  numbered {numbered}/{n}   "
              f"all {100*all_h/all_t:5.2f}% ({all_h}/{all_t})   "
              f"clean {100*clean_h/clean_t:5.2f}% ({clean_h}/{clean_t})   "
              f"top-2 rows contribute {sum(per_row[:2])}")


def normalize_bug():
    print("\n== 8. Addendum check: unanchored numbered-list normalization ==")
    for sample in ("33. docker-container-run", "12. requests", "1. numpy"):
        print(f"  normalize_python({sample!r}) -> "
              f"{package_detection.normalize_python(sample)!r}")


def contamination_other_runs():
    print("\n== 9. Contamination exposure of the OTHER runs (fence/numbered in responses) ==")
    for run, label in [(CL_LARGE, "CodeLlama n=400 (cap 64)"), (GPT_OSS, "gpt-oss:20b (cap 2048)")]:
        stats = {1: [0, 0], 2: [0, 0]}
        all_h = all_t = clean_h = clean_t = 0
        for _, mode, text, h, t in _rows_with_text(run):
            flagged = _has_fence(text) or _has_numbered(text)
            stats[mode][0] += flagged
            stats[mode][1] += 1
            all_h += h
            all_t += t
            if not flagged:
                clean_h += h
                clean_t += t
        print(f"  {label}:")
        print(f"    flagged responses  Q1 {stats[1][0]}/{stats[1][1]}   Q2 {stats[2][0]}/{stats[2][1]}")
        print(f"    pooled queries-only rate: all {100*all_h/all_t:5.2f}% ({all_h}/{all_t})   "
              f"clean subset {100*clean_h/clean_t:5.2f}% ({clean_h}/{clean_t})")


def cleaned_positional_and_tail(prefix_pairs):
    print("\n== 10. Do the v3 ordering measurements survive removing format-failed responses? ==")
    master = pd.read_csv(os.path.join("Data", "Python", "pypi_package_names.csv"), header=None)
    master_set = set(master[0].apply(package_detection.normalize_python).dropna())
    false_positives = set(pd.read_csv(os.path.join("Data", "Python",
                                                   "false_positive_packages.csv"),
                                      header=None)[1])

    position_total = {}
    position_hallucinated = {}
    for key in KEYS:
        for mode in (1, 2):
            path = os.path.join(CL_LARGE, f"{key}_packages_{mode}.json")
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    text = str(json.loads(line))
                    if _has_fence(text) or _has_numbered(text):
                        continue
                    for index, name in enumerate(ordered_parse(text), 1):
                        if name in false_positives and name not in master_set:
                            continue
                        bucket = min(index, 5)
                        position_total[bucket] = position_total.get(bucket, 0) + 1
                        position_hallucinated[bucket] = (position_hallucinated.get(bucket, 0)
                                                         + (name not in master_set))
    gradient = "  ".join(f"p{b}{'+' if b == 5 else ''}:{100*position_hallucinated[b]/position_total[b]:.1f}% "
                         f"(n={position_total[b]})" for b in sorted(position_total))
    print(f"  CodeLlama n=400 positional gradient, clean responses only:\n    {gradient}")

    clean_pairs = [(s, l) for s, l in prefix_pairs
                   if not (_has_fence(l) or _has_numbered(l))]
    head_h = head_t = tail_h = tail_t = qualifying = 0
    for short, long_ in clean_pairs:
        short_items = ordered_parse(short)
        long_items = ordered_parse(long_)
        if not short_items or long_items[:len(short_items)] != short_items:
            continue
        qualifying += 1
        for name in long_items[:len(short_items)]:
            if name in false_positives and name not in master_set:
                continue
            head_t += 1
            head_h += name not in master_set
        for name in long_items[len(short_items):]:
            if name in false_positives and name not in master_set:
                continue
            tail_t += 1
            tail_h += name not in master_set
    print(f"  DeepSeek strict-prefix tail, clean long responses only: "
          f"{qualifying} qualifying pairs")
    if head_t and tail_t:
        print(f"    head {100*head_h/head_t:5.2f}% ({head_h}/{head_t})   "
              f"tail {100*tail_h/tail_t:5.2f}% ({tail_h}/{tail_t})")


if __name__ == "__main__":
    check_nesting()
    pairs = check_prefix_split()
    rescore_family_parser()
    partition_large_run()
    tail_rate(pairs)
    addendum_query_split()
    addendum_contamination()
    normalize_bug()
    contamination_other_runs()
    cleaned_positional_and_tail(pairs)
