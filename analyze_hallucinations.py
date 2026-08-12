"""Characterise the hallucinated package names in a run, beyond the headline rate.

The paper reports two distributional properties that a rate alone does not capture:

* **Figure 9** — the Levenshtein distance from each hallucinated package name to the
  nearest real package in the master list. A hallucination one or two edits away from a
  real name is the dangerous kind: it is what a typosquatting adversary would register,
  and what a developer would fail to notice.
* **Figure 6** — the number of unique package names a model generates, against its
  hallucination rate.

This computes both from a run's ``PACKAGE_NAMES.csv`` and compares the distance
distribution against the paper's published one in ``Plots/Data/figure_9.csv``.

Usage:
    python analyze_hallucinations.py Tests/<run>
    python analyze_hallucinations.py Tests/<run> --top 25
"""

from __future__ import annotations

import argparse
import ast
import os
from collections import Counter

import pandas as pd
from rapidfuzz import process
from rapidfuzz.distance import Levenshtein

import package_detection

HALL_COLUMNS = ["hallucinated_1", "hallucinated_2", "pip_hallucinated", "npm_hallucinated"]
VALID_COLUMNS = ["valid_1", "valid_2", "pip_valid", "npm_valid"]


def parse_cell(cell):
    """PACKAGE_NAMES.csv stores Python list literals as strings."""
    if pd.isna(cell):
        return []
    try:
        value = ast.literal_eval(cell)
    except (ValueError, SyntaxError):
        return []
    return [str(v) for v in value] if isinstance(value, list) else []


def collect(df, columns):
    names = []
    for column in columns:
        if column in df.columns:
            for cell in df[column]:
                names.extend(parse_cell(cell))
    return names


def load_master_list(language):
    data_path = os.path.join("Data", language)
    if language == "Python":
        master = pd.read_csv(os.path.join(data_path, "pypi_package_names.csv"), header=None)
        return set(master[0].apply(package_detection.normalize_python).dropna())
    master = pd.read_csv(os.path.join(data_path, "npm_package_names.csv"), header=None)
    return set(master[0].dropna().astype(str))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", help="A run directory under Tests/")
    parser.add_argument("--top", type=int, default=15,
                        help="How many most-frequent hallucinated names to list")
    args = parser.parse_args()

    names_path = os.path.join(args.run, "PACKAGE_NAMES.csv")
    df = pd.read_csv(names_path)
    language = "Javascript" if "npm_hallucinated" in df.columns else "Python"

    hallucinated = collect(df, HALL_COLUMNS)
    valid = collect(df, VALID_COLUMNS)
    unique_hallucinated = sorted(set(hallucinated))
    unique_all = set(hallucinated) | set(valid)

    print(f"{os.path.basename(args.run)}  [{language}]")
    print("=" * 70)
    print(f"packages recommended        {len(hallucinated) + len(valid):,}")
    print(f"  hallucinated              {len(hallucinated):,}")
    print(f"unique package names        {len(unique_all):,}")
    print(f"  unique hallucinated       {len(unique_hallucinated):,}")
    if hallucinated:
        print(f"repetition                  {len(hallucinated) / len(unique_hallucinated):.2f} "
              f"occurrences per unique hallucinated name")

    if not unique_hallucinated:
        print("\nNo hallucinated packages to characterise.")
        return

    counts = Counter(hallucinated)
    print(f"\nMost frequently hallucinated names:")
    for name, count in counts.most_common(args.top):
        print(f"  {count:5}x  {name}")

    master = sorted(load_master_list(language))
    print(f"\nLevenshtein distance to the nearest real package "
          f"({len(unique_hallucinated):,} unique hallucinated names vs the full "
          f"{len(master):,}-name master list)...")
    distances = []
    nearest = {}
    for name in unique_hallucinated:
        match = process.extractOne(name, master, scorer=Levenshtein.distance)
        distances.append(match[1])
        nearest[name] = (match[0], match[1])

    # Second reference set: the packages this run validly recommended. Searching the full
    # master list finds obscure near-collisions (opencv -> openav at distance 1) rather than
    # the package the model plausibly meant (opencv-python, distance 7), which overstates
    # typosquat proximity. Packages a model actually recommends are a popularity proxy and a
    # better answer to "is this a near-miss of something developers really use?".
    in_use = sorted(set(valid))
    distances_in_use = []
    nearest_in_use = {}
    for name in unique_hallucinated:
        match = process.extractOne(name, in_use, scorer=Levenshtein.distance)
        distances_in_use.append(match[1])
        nearest_in_use[name] = (match[0], match[1])

    print("\n  Nearest real package for the most-repeated hallucinations:")
    print(f"    {'hallucination':<22} {'nearest in master list':<26} {'nearest in-use package':<26}")
    for name, count in counts.most_common(min(args.top, 8)):
        neighbour, distance = nearest[name]
        used, used_distance = nearest_in_use[name]
        print(f"    {name:<22} {neighbour + f' ({distance})':<26} {used + f' ({used_distance})':<26}")

    histogram = Counter(distances)
    total = len(distances)
    within_two = sum(count for distance, count in histogram.items() if distance <= 2)

    paper_path = os.path.join("Plots", "Data", "figure_9.csv")
    paper_share = {}
    if os.path.exists(paper_path):
        paper = pd.read_csv(paper_path)
        paper.columns = ["distance", "count"]
        paper_total = paper["count"].sum()
        paper_share = {int(r.distance): 100 * r.count / paper_total for r in paper.itertuples()}

    print(f"\n  {'dist':>4}  {'count':>7}  {'this run':>9}   {'paper (fig 9)':>13}")
    for distance in sorted(histogram)[:11]:
        share = 100 * histogram[distance] / total
        reference = f"{paper_share[distance]:12.1f}%" if distance in paper_share else " " * 13
        print(f"  {distance:>4}  {histogram[distance]:>7,}  {share:8.1f}%   {reference}")

    in_use_within_two = sum(1 for d in distances_in_use if d <= 2)
    print(f"\n  within 2 edits of a real package: {within_two:,}/{total:,} "
          f"({100 * within_two / total:.1f}%)   [full {len(master):,}-name master list]")
    print(f"  within 2 edits of an in-use package: {in_use_within_two:,}/{total:,} "
          f"({100 * in_use_within_two / total:.1f}%)   [{len(in_use):,} packages this run "
          f"validly recommended]")
    if paper_share:
        paper_within_two = sum(v for k, v in paper_share.items() if k <= 2)
        print(f"  paper, Figure 9:                  {paper_within_two:.1f}% "
              f"(reported as 13.4% of 76,489 in RQ4)")
    print("\n  Names within one or two edits of a real package are the typosquatting-shaped\n"
          "  ones: plausible to a reader, and cheap for an adversary to register.")
    print("\n  CAVEAT: the paper's Figure 9 is NOT a like-for-like comparison. It pools four\n"
          "  models at full scale, and its section heading refers to 'popular valid packages',\n"
          "  so its reference set may be a popularity-filtered subset rather than the full\n"
          "  master list used here. A smaller reference set yields larger distances. Treat\n"
          "  the paper column as context for the shape of the distribution, not as a baseline\n"
          "  this run should match.")


if __name__ == "__main__":
    main()
