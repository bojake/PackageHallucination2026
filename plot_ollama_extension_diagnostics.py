"""Render the Qwen/Kimi extension mechanism figure without exposing package names."""

from __future__ import annotations

import json
import os

import matplotlib.pyplot as plt
import numpy as np


SOURCE = os.path.join("Experiments", "ollama_cloud_extension_post_analysis.json")
OUT_DIR = os.path.join("Experiments", "figures")
OUT_PNG = os.path.join(OUT_DIR, "ollama_extension_position_volume.png")
OUT_PDF = os.path.join(OUT_DIR, "ollama_extension_position_volume.pdf")
COLORS = {"qwen3.5:cloud": "#2878B5", "kimi-k2.7-code:cloud": "#D95319"}


def main() -> None:
    with open(SOURCE, encoding="utf-8") as handle:
        result = json.load(handle)
    cells = result["cells"]
    labels = [item["position"]
              for item in cells["kimi-k2.7-code:cloud"]["position_profile_query_2"]]
    x = np.arange(len(labels))

    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.2), constrained_layout=True)

    # A: the central mechanism -- validity declines at late list positions.
    for model in ("qwen3.5:cloud", "kimi-k2.7-code:cloud"):
        profile = cells[model]["position_profile_query_2"]
        rates = [item["unregistered_rate_pct"] if item["unregistered_rate_pct"] is not None
                 else np.nan for item in profile]
        axes[0].plot(x, rates, marker="o", linewidth=2.2, markersize=5.5,
                     label=model.replace(":cloud", ""), color=COLORS[model])
    axes[0].set_xticks(x, labels, rotation=35, ha="right")
    axes[0].set_ylabel("Unregistered recommendations (%)")
    axes[0].set_xlabel("Package position within Query 2 response")
    axes[0].set_title("A. Late-list validity collapse")
    axes[0].grid(axis="y", alpha=0.25)
    axes[0].legend(frameon=False, loc="upper left")

    # B: denominator mass explains why the aggregate is dominated by late positions.
    kimi_profile = cells["kimi-k2.7-code:cloud"]["position_profile_query_2"]
    totals = np.array([item["occurrences"] for item in kimi_profile])
    unregistered = np.array([item["unregistered"] for item in kimi_profile])
    axes[1].bar(x, totals, color="#D9D9D9", label="All parsed")
    axes[1].bar(x, unregistered, color=COLORS["kimi-k2.7-code:cloud"],
                label="Unregistered")
    axes[1].set_yscale("log")
    axes[1].set_xticks(x, labels, rotation=35, ha="right")
    axes[1].set_ylabel("Occurrences (log scale)")
    axes[1].set_xlabel("Package position within Kimi Query 2")
    axes[1].set_title("B. Late positions dominate volume")
    axes[1].grid(axis="y", alpha=0.2, which="both")
    axes[1].legend(frameon=False, loc="upper left")

    # C: mutually exclusive response-volume groups.
    rows = cells["kimi-k2.7-code:cloud"]["package_volume_quartiles_query_2"]
    quartile_labels = [
        f"Q{item['quartile']}\n{item['package_count_min']}–{item['package_count_max']}"
        for item in rows
    ]
    rates = [item["unregistered_rate_pct"] for item in rows]
    volumes = [item["parsed_package_occurrences"] for item in rows]
    bars = axes[2].bar(np.arange(4), rates, color=["#F2C9B6", "#EAA27F", "#E0784E", "#C74D1E"])
    axes[2].set_xticks(np.arange(4), quartile_labels)
    axes[2].set_ylabel("Unregistered recommendations (%)")
    axes[2].set_xlabel("Kimi Query 2 response-volume quartile\n(min–max parsed packages)")
    axes[2].set_title("C. Error rate by response volume")
    axes[2].grid(axis="y", alpha=0.25)
    for bar, volume in zip(bars, volumes):
        axes[2].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.6,
                     f"n={volume:,}", ha="center", va="bottom", fontsize=8, rotation=90)
    axes[2].set_ylim(0, max(rates) + 8)

    fig.suptitle("Kimi K2.7's aggregate is a response-volume and late-position phenomenon",
                 fontsize=13.5, fontweight="bold")
    os.makedirs(OUT_DIR, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=240, bbox_inches="tight")
    fig.savefig(OUT_PDF, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT_PNG}")
    print(f"wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
