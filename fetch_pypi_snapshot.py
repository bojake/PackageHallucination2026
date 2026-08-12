"""Fetch a dated snapshot of all PyPI project names (Campaign 4, Track B registry #2).

Uses the PyPI Simple JSON API. Writes one name per line, same layout as the frozen
2024-01-10 master list, to ``Data/Python/pypi_package_names_<date>.csv``.
"""

from __future__ import annotations

import datetime
import os

import requests


def main():
    date = datetime.date.today().isoformat()
    out = os.path.join("Data", "Python", f"pypi_package_names_{date}.csv")
    print(f"fetching PyPI simple index (JSON) -> {out}")
    response = requests.get(
        "https://pypi.org/simple/",
        headers={"Accept": "application/vnd.pypi.simple.v1+json",
                 "User-Agent": "PackageHallucination-campaign4 (research; see repo)"},
        timeout=900,
    )
    response.raise_for_status()
    names = [p["name"] for p in response.json()["projects"]]
    with open(out, "w", encoding="utf-8", newline="") as handle:
        for name in names:
            handle.write(name + "\n")
    print(f"wrote {len(names):,} project names ({os.path.getsize(out) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
