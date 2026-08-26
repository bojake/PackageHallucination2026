"""Plot the Kimi K2.7 versus K3 tail-mechanism diagnostics."""

from __future__ import annotations

import json
import os

import matplotlib.pyplot as plt
import numpy as np


SOURCE = os.path.join("Experiments", "kimi_k2_7_vs_k3_post_analysis.json")
OUT_DIR = os.path.join("Experiments", "figures")


def main() -> None:
    with open(SOURCE, encoding="utf-8") as handle:
        data = json.load(handle)
    k2 = data["models"]["kimi_k2_7"]
    k3 = data["models"]["kimi_k3"]
    colors = ["#5470C6", "#D95F59"]

    plt.rcParams.update({"font.size": 9, "axes.titleweight": "bold"})
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.7), constrained_layout=True)

    # A: the aggregate metric reversal.
    metrics = ["Occurrence\nweighted", "Prompt risk", "Response\nmacro mean", "Cap excluded"]
    k2_values = [
        k2["overall"]["unregistered_rate_pct"],
        k2["overall"]["prompt_risk_pct"],
        k2["overall"]["macro_rates"]["response_mean_pct"],
        k2["cap_proxy_excluded"]["unregistered_rate_pct"],
    ]
    k3_values = [
        k3["overall"]["unregistered_rate_pct"],
        k3["overall"]["prompt_risk_pct"],
        k3["overall"]["macro_rates"]["response_mean_pct"],
        k3["exact_cap_excluded"]["unregistered_rate_pct"],
    ]
    x = np.arange(len(metrics))
    width = 0.36
    axes[0].bar(x - width / 2, k2_values, width, label="Kimi K2.7", color=colors[0])
    axes[0].bar(x + width / 2, k3_values, width, label="Kimi K3", color=colors[1])
    axes[0].set_xticks(x, metrics)
    axes[0].set_ylabel("Percent")
    axes[0].set_title("A. Headline reversal is aggregation-sensitive")
    axes[0].legend(frameon=False)
    axes[0].grid(axis="y", alpha=0.22)

    # B: how a selected tail dominates the occurrence-weighted numerator/denominator.
    labels = ["Responses", "Parsed\noccurrences", "Unregistered\noccurrences"]
    k2c = k2["cap_proxy_contribution"]
    k3c = k3["exact_cap_contribution"]
    k2_tail = [k2c["response_share_pct"], k2c["occurrence_share_pct"],
               k2c["unregistered_share_pct"]]
    k3_tail = [k3c["response_share_pct"], k3c["occurrence_share_pct"],
               k3c["unregistered_share_pct"]]
    x = np.arange(len(labels))
    axes[1].bar(x - width / 2, k2_tail, width, color=colors[0], label="K2.7 cap proxy")
    axes[1].bar(x + width / 2, k3_tail, width, color=colors[1], label="K3 exact caps")
    axes[1].set_xticks(x, labels)
    axes[1].set_ylim(0, 105)
    axes[1].set_ylabel("Share of campaign total (%)")
    axes[1].set_title("B. Rare K3 cap hits dominate its errors")
    axes[1].legend(frameon=False)
    axes[1].grid(axis="y", alpha=0.22)

    # C: position-level degradation remains after cap diagnostic exclusion.
    positions = ["1", "2", "3-5", "6-10", "11-25", "26-50", "51-100", "101+"]
    profiles = data["q2_position_rate_cap_excluded"]
    axes[2].plot(
        positions,
        [profiles["kimi_k2_7_proxy_excluded"][position] for position in positions],
        marker="o", linewidth=2, color=colors[0], label="K2.7 proxy excluded",
    )
    axes[2].plot(
        positions,
        [profiles["kimi_k3_exact_excluded"][position] for position in positions],
        marker="o", linewidth=2, color=colors[1], label="K3 exact caps excluded",
    )
    axes[2].set_xlabel("Package position within Query 2 response")
    axes[2].set_ylabel("Unregistered rate (%)")
    axes[2].set_title("C. Late-position degradation persists")
    axes[2].tick_params(axis="x", rotation=35)
    axes[2].legend(frameon=False, loc="upper left")
    axes[2].grid(alpha=0.22)

    fig.suptitle("Kimi K3 improves typical behavior but retains a catastrophic enumeration tail",
                 fontsize=13, fontweight="bold")
    os.makedirs(OUT_DIR, exist_ok=True)
    png = os.path.join(OUT_DIR, "kimi_k2_7_vs_k3_mechanism.png")
    pdf = os.path.join(OUT_DIR, "kimi_k2_7_vs_k3_mechanism.pdf")
    fig.savefig(png, dpi=220, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    print(f"wrote {png}")
    print(f"wrote {pdf}")


if __name__ == "__main__":
    main()
