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


if __name__ == "__main__":
    check_nesting()
    pairs = check_prefix_split()
    rescore_family_parser()
    partition_large_run()
    tail_rate(pairs)
