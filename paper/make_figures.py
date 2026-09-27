"""Generate the manuscript figures in paper/figures/ from the committed result artifacts.

Figures 2, 3, 4, and 6--9 read only Experiments/*.json (Figures 8 and 9 are manuscript-size
renderings of the committed Experiments/figures/ diagnostics from the same JSON sources). Figure 5
(ranked-prompt concentration curves) needs the git-ignored raw responses under Tests/ and reuses
the frozen scoring path of post_campaign_analysis.py; when Tests/ is absent the existing PDF is
left untouched.

Usage (from the repository root, with the pinned analysis interpreter):
    python paper/make_figures.py
"""

from __future__ import annotations

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP = os.path.join(ROOT, "Experiments")
OUT = os.path.join(ROOT, "paper", "figures")
sys.path.insert(0, ROOT)

NAMES = {
    "claude-opus-5": "Claude Opus 5",
    "gpt-5.2-2025-12-11": "GPT-5.2",
    "gpt-oss:20b": "gpt-oss 20B",
    "grok-4.6": "Grok 4.6",
    "deepseek-coder-v2:16b": "DeepSeek Coder V2 16B",
    "deepseek-v4-flash": "DeepSeek V4 Flash",
    "qwen3.5:cloud": "Qwen 3.5 Cloud",
    "kimi-k2.7-code:cloud": "Kimi K2.7 Code",
    "kimi-k3:cloud": "Kimi K3",
}
SHORT = {
    "claude-opus-5": "Opus 5", "gpt-5.2-2025-12-11": "GPT-5.2", "gpt-oss:20b": "gpt-oss 20B",
    "grok-4.6": "Grok 4.6", "deepseek-coder-v2:16b": "DS Coder V2", "deepseek-v4-flash": "DS V4 Flash",
    "qwen3.5:cloud": "Qwen 3.5", "kimi-k2.7-code:cloud": "Kimi K2.7", "kimi-k3:cloud": "Kimi K3",
}
TRACK_B = ["claude-opus-5", "gpt-5.2-2025-12-11", "gpt-oss:20b", "grok-4.6",
           "deepseek-coder-v2:16b", "deepseek-v4-flash"]
EXT = ["qwen3.5:cloud", "kimi-k2.7-code:cloud", "kimi-k3:cloud"]
RUNS = {
    "claude-opus-5": "trackB_anthropic_claude-opus-5_Python",
    "gpt-5.2-2025-12-11": "trackB_openai_gpt-5.2_Python",
    "gpt-oss:20b": "trackB_gptoss_20b_n200_Python",
    "grok-4.6": "trackB_xai_grok-4.6_Python",
    "deepseek-coder-v2:16b": "trackB_deepseek-coder-v2_16b_Python",
    "deepseek-v4-flash": "trackB_deepseek-v4-flash_Python",
    "qwen3.5:cloud": "trackC_ollama_qwen3-5-cloud_Python",
    "kimi-k2.7-code:cloud": "trackC_ollama_kimi-k2-7-code-cloud_Python",
    "kimi-k3:cloud": "trackD_ollama_kimi-k3-cloud_Python",
}
# Colorblind-safe palette (Okabe-Ito) plus two neutrals for the extension cells.
COLORS = {
    "claude-opus-5": "#0072B2", "gpt-5.2-2025-12-11": "#56B4E9", "gpt-oss:20b": "#009E73",
    "grok-4.6": "#E69F00", "deepseek-coder-v2:16b": "#D55E00", "deepseek-v4-flash": "#CC79A7",
    "qwen3.5:cloud": "#7A7A7A", "kimi-k2.7-code:cloud": "#F0E442", "kimi-k3:cloud": "#000000",
}
INK = "#1C2331"

plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.spines.top": False,
    "axes.spines.right": False, "pdf.fonttype": 42, "figure.dpi": 150,
})


def load(name):
    with open(os.path.join(EXP, name), encoding="utf-8") as handle:
        return json.load(handle)


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".pdf"), bbox_inches="tight")
    fig.savefig(os.path.join(OUT, name + ".png"), bbox_inches="tight", dpi=200)
    plt.close(fig)
    print("wrote", os.path.relpath(os.path.join(OUT, name + ".pdf"), ROOT))


# ---------------------------------------------------------------------------------------
# Figure 2: Track A forest plot.
# ---------------------------------------------------------------------------------------
def fig_tracka():
    t = load("campaign4_results.json")["track_a"]
    fig, axes = plt.subplots(2, 1, figsize=(3.4, 3.6), gridspec_kw={"height_ratios": [3, 6]})
    for ax, (model, label) in zip(axes, (("codellama:7b-instruct", "CodeLlama 7B Instruct"),
                                         ("deepseek-coder:6.7b-instruct", "DeepSeek Coder 6.7B Instruct"))):
        cell = t[model]
        paper = cell["paper"]["rate_pct"]
        items = []
        for i, seed in enumerate(cell["seeds"], 1):
            g = seed["generic_parser"]
            items.append((f"seed {100 + i}, generic parser", g["rate_pct"], g["cluster_ci"], "#0072B2"))
        for i, seed in enumerate(cell["seeds"], 1):
            fam = seed.get("family_parser")
            if fam:
                items.append((f"seed {100 + i}, family parser", fam["rate_pct"], fam["cluster_ci"], "#D55E00"))
        y = np.arange(len(items))[::-1]
        for yi, (lab, rate, cie, color) in zip(y, items):
            ax.plot([cie[0], cie[1]], [yi, yi], color=color, lw=1.4)
            ax.plot(rate, yi, "o", color=color, ms=4)
        ax.axvline(paper, color=INK, ls="--", lw=1)
        ax.text(paper, len(items) - 0.35, f"published {paper:.2f}%", ha="center", va="bottom",
                fontsize=7, color=INK)
        ax.set_yticks(y)
        ax.set_yticklabels([it[0] for it in items])
        ax.set_title(label, loc="left")
        ax.set_ylim(-0.7, len(items) + 0.3)
        ax.grid(axis="x", alpha=0.25)
        ax.tick_params(axis="y", labelsize=6.5)
    axes[1].set_xlabel("Hallucination rate (%), frozen 2024 registry")
    fig.tight_layout()
    save(fig, "fig_tracka_forest")


# ---------------------------------------------------------------------------------------
# Figure 3: cap diagnostic curves with paired intervals.
# ---------------------------------------------------------------------------------------
def fig_cap():
    d = load("campaign4_post_analysis.json")["cap_diagnostic_paired_sensitivity"]
    caps = ["64", "128", "256", "512", "2048"]
    fig, axes = plt.subplots(1, 3, figsize=(6.9, 2.2))
    style = {"deepseek-coder-v2_16b": ("DeepSeek Coder V2 16B", "#0072B2", "o"),
             "deepseek-coder_6.7b-instruct": ("DeepSeek Coder 6.7B", "#D55E00", "s")}
    for model, (label, color, marker) in style.items():
        cells = d[model]["cells"]
        rates = [cells[c]["rate_pct"] for c in caps]
        mal = [cells[c]["malformed_rate_pct"] for c in caps]
        axes[0].plot(caps, rates, marker=marker, color=color, lw=1.4, label=label)
        axes[1].plot(caps, mal, marker=marker, color=color, lw=1.4, label=label)
        deltas = [cells[c]["delta_vs_2048_pp"] for c in caps[:-1]]
        lo = [cells[c]["delta_vs_2048_percentile_ci"][0] for c in caps[:-1]]
        hi = [cells[c]["delta_vs_2048_percentile_ci"][1] for c in caps[:-1]]
        x = np.arange(4) + (0.12 if marker == "s" else -0.12)
        axes[2].errorbar(x, deltas, yerr=[np.subtract(deltas, lo), np.subtract(hi, deltas)],
                         fmt=marker, color=color, capsize=2, lw=1.2, ms=4, label=label)
    axes[0].set_ylabel("Unregistered rate (%)")
    axes[0].set_ylim(0, 10)
    axes[0].set_title("A. Rate by cap")
    axes[1].set_ylabel("Malformed responses (%)")
    axes[1].set_ylim(0, 60)
    axes[1].set_title("B. Malformed share by cap")
    axes[2].axhline(0, color=INK, lw=0.8, ls="--")
    axes[2].set_xticks(range(4))
    axes[2].set_xticklabels(caps[:-1])
    axes[2].set_ylabel("Rate minus rate at 2048 (pp)")
    axes[2].set_title("C. Paired delta vs. 2048 tokens")
    for ax in axes:
        ax.set_xlabel("Package-response token cap")
        ax.grid(alpha=0.25)
    axes[0].legend(frameon=False, loc="lower right")
    fig.tight_layout()
    save(fig, "fig_cap_diagnostic")


# ---------------------------------------------------------------------------------------
# Figure 4: nine-cell rate forest with response coverage.
# ---------------------------------------------------------------------------------------
def fig_trackb():
    c4 = load("campaign4_post_analysis.json")["track_b"]
    ext = load("ollama_cloud_extension_results.json")["new_cells"]
    k3 = load("kimi_k3_extension_results.json")["primary"]
    c4r = load("campaign4_results.json")["track_b"]
    rows = []
    for m in TRACK_B:
        rows.append((m, c4[m], c4r[m]["prompt_level_risk_pct"]))
    for m in ("qwen3.5:cloud", "kimi-k2.7-code:cloud"):
        rows.append((m, ext[m], ext[m]["prompt_risk_pct"]))
    rows.append(("kimi-k3:cloud", k3, k3["prompt_risk_pct"]))
    fig, axes = plt.subplots(1, 3, figsize=(6.9, 2.9), gridspec_kw={"width_ratios": [2.2, 1.2, 1.4]},
                             sharey=True)
    y = np.arange(len(rows))[::-1]
    for yi, (m, cell, risk) in zip(y, rows):
        lo, hi = cell["unregistered_rate_cluster_ci"]
        axes[0].plot([lo, hi], [yi, yi], color=COLORS[m], lw=1.6)
        axes[0].plot(cell["unregistered_rate_pct"], yi, "o", color=COLORS[m], ms=4.5,
                     markeredgecolor=INK, markeredgewidth=0.4)
        axes[1].barh(yi, risk, color=COLORS[m], edgecolor=INK, linewidth=0.4)
        st = cell["statuses"]
        n = cell["responses"]
        lst, mal, emp = 100 * st.get("list", 0) / n, 100 * st.get("malformed", 0) / n, 100 * st.get("empty", 0) / n
        axes[2].barh(yi, lst, color="#BBBBBB", edgecolor=INK, linewidth=0.4, label="list" if yi == y[0] else None)
        axes[2].barh(yi, mal, left=lst, color="#E69F00", edgecolor=INK, linewidth=0.4,
                     label="malformed" if yi == y[0] else None)
        axes[2].barh(yi, emp, left=lst + mal, color="#D55E00", edgecolor=INK, linewidth=0.4,
                     label="empty" if yi == y[0] else None)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([NAMES[m] for m, _, _ in rows])
    axes[0].set_xlabel("Unregistered-PyPI recommendation rate (%)")
    axes[0].set_title("A. Primary rate (95% prompt-cluster CI)")
    axes[0].set_xlim(0, 42)
    axes[1].set_xlabel("Prompt risk (%)")
    axes[1].set_title("B. Prompt risk")
    axes[1].set_xlim(0, 50)
    axes[2].set_xlabel("Package responses (%)")
    axes[2].set_title("C. Coverage")
    axes[2].set_xlim(0, 100)
    axes[2].legend(frameon=False, loc="lower left", fontsize=6.5)
    for ax in axes:
        ax.grid(axis="x", alpha=0.25)
    # family separators: between Track B (6) and extension (2) and K3 (1)
    for ax in axes:
        ax.axhline(2.5, color=INK, lw=0.6, ls=":")
        ax.axhline(0.5, color=INK, lw=0.6, ls=":")
    axes[1].text(49, 5.5, "Campaign 4", ha="right", va="center", fontsize=6.5, color=INK)
    axes[1].text(49, 1.5, "cloud ext.", ha="right", va="center", fontsize=6.5, color=INK)
    axes[1].text(49, 0, "K3", ha="right", va="center", fontsize=6.5, color=INK)
    fig.tight_layout()
    save(fig, "fig_trackb_forest")


# ---------------------------------------------------------------------------------------
# Figure 5: ranked-prompt cumulative concentration curves (needs Tests/).
# ---------------------------------------------------------------------------------------
def fig_concentration():
    tests = os.path.join(ROOT, "Tests")
    if not all(os.path.isdir(os.path.join(tests, RUNS[m])) for m in TRACK_B + EXT):
        print("Tests/ raw responses not available; leaving fig_concentration.pdf as committed")
        return
    import post_campaign_analysis as campaign  # frozen scoring path

    frozen = campaign.load_registry(os.path.join(ROOT, "Data", "Python", "pypi_package_names.csv"))
    current = campaign.load_registry(os.path.join(ROOT, "Data", "Python",
                                                  "pypi_package_names_2026-08-12.csv"))
    curves = {}
    for m in TRACK_B + EXT:
        counts = {}
        run_dir = os.path.join(tests, RUNS[m])
        total_h = total_t = 0
        for dataset in campaign.KEYS:
            for mode in (1, 2):
                path = os.path.join(run_dir, f"{dataset}_packages_{mode}.json")
                with open(path, encoding="utf-8") as handle:
                    for index, line in enumerate(handle):
                        if not line.strip():
                            continue
                        text = str(json.loads(line))
                        status, packages = campaign.parser_v2.classify(text)
                        h = sum(1 for p in packages
                                if campaign.normalize(p) not in frozen
                                and campaign.normalize(p) not in current
                                and campaign.normalize(p) not in campaign.STDLIB)
                        counts[(dataset, index)] = counts.get((dataset, index), 0) + h
                        total_h += h
                        total_t += len(packages)
        ranked = np.sort(np.array(list(counts.values())))[::-1]
        curves[m] = (np.cumsum(ranked) / max(ranked.sum(), 1), total_h, total_t)
        print(f"  {m:24} unregistered={total_h} parsed={total_t} rate={100 * total_h / max(total_t, 1):.2f}%")
    fig, axes = plt.subplots(1, 2, figsize=(6.9, 2.5))
    for ax, group, title in ((axes[0], TRACK_B, "A. Campaign 4 cells"),
                             (axes[1], EXT, "B. Extension cells")):
        for m in group:
            share, h, t = curves[m]
            x = np.arange(1, len(share) + 1)
            ax.plot(x, 100 * share, color=COLORS[m], lw=1.5, label=f"{SHORT[m]} ({h:,})")
        ax.set_xscale("log")
        ax.set_xlim(1, 800)
        ax.set_ylim(0, 102)
        ax.set_xlabel("Prompts ranked by unregistered count (log scale)")
        ax.set_ylabel("Cumulative share of" + chr(10) + "unregistered occurrences (%)")
        ax.axhline(50, color=INK, lw=0.6, ls=":")
        ax.set_title(title)
        ax.grid(alpha=0.25, which="both")
        ax.legend(frameon=False, loc="lower right", fontsize=6.2, title="cell (unregistered occurrences)",
                  title_fontsize=6.2)
    fig.tight_layout()
    save(fig, "fig_concentration")


# ---------------------------------------------------------------------------------------
# Figure 6: leave-top-k sensitivity.
# ---------------------------------------------------------------------------------------
def fig_leave_topk():
    c4 = load("campaign4_post_analysis.json")["track_b"]
    ext = load("ollama_cloud_extension_results.json")["new_cells"]
    k3 = load("kimi_k3_extension_results.json")["primary"]
    cells = {m: c4[m] for m in TRACK_B}
    cells.update({m: ext[m] for m in ("qwen3.5:cloud", "kimi-k2.7-code:cloud")})
    cells["kimi-k3:cloud"] = k3
    ks = ["0", "1", "3", "10"]
    fig, ax = plt.subplots(figsize=(3.4, 3.0))
    for m, cell in cells.items():
        t = cell["tail"]
        vals = [cell["unregistered_rate_pct"], t["leave_top1_rate_pct"], t["leave_top3_rate_pct"],
                t["leave_top10_rate_pct"]]
        marker = "o" if m in TRACK_B else "s"
        ls = "-" if m in TRACK_B else "--"
        ax.plot(ks, vals, marker=marker, ls=ls, color=COLORS[m], lw=1.3, ms=4, label=NAMES[m],
                markeredgecolor=INK, markeredgewidth=0.3)
    ax.set_yscale("log")
    ax.set_ylim(0.5, 60)
    ax.set_yticks([0.5, 1, 2, 5, 10, 20, 50])
    ax.set_yticklabels(["0.5", "1", "2", "5", "10", "20", "50"])
    ax.set_xlabel("Worst responses removed (k)")
    ax.set_ylabel("Rate after removal (%, log scale)")
    ax.grid(alpha=0.25, which="both")
    ax.legend(frameon=False, fontsize=6, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    fig.tight_layout()
    save(fig, "fig_leave_topk")


# ---------------------------------------------------------------------------------------
# Figure 7: ordinary versus prompt-aligned overlap.
# ---------------------------------------------------------------------------------------
def fig_overlap():
    o = load("churilov_bridge_analysis.json")["prompt_conditioned_overlap"]
    models = TRACK_B + EXT
    idx = {m: i for i, m in enumerate(models)}
    n = len(models)
    jac = np.full((n, n), np.nan)
    share = np.full((n, n), np.nan)
    for c in o["pairwise"]:
        a, b = c["pair"].split(" vs ")
        i, j = idx[a], idx[b]
        jac[max(i, j), min(i, j)] = c["name_jaccard"]
        share[min(i, j), max(i, j)] = c["same_prompt_share_of_shared_names_pct"]
    fig, axes = plt.subplots(1, 2, figsize=(6.9, 3.1))
    short = ["Opus 5", "GPT-5.2", "gpt-oss", "Grok 4.6", "DS Coder V2", "DS V4 Flash", "Qwen 3.5",
             "Kimi K2.7", "Kimi K3"]
    for ax, mat, title, cmap, fmt, vmax in ((axes[0], jac, "A. Ordinary name Jaccard (lower triangle)",
                                            "Blues", "{:.2f}", 0.2),
                                           (axes[1], share, "B. Same-prompt share of shared names, % (upper triangle)",
                                            "Oranges", "{:.0f}", 100)):
        im = ax.imshow(mat, cmap=cmap, vmin=0, vmax=vmax)
        for i in range(n):
            for j in range(n):
                if not np.isnan(mat[i, j]):
                    ax.text(j, i, fmt.format(mat[i, j]), ha="center", va="center", fontsize=5.5,
                            color="black" if mat[i, j] < 0.6 * vmax else "white")
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(short, rotation=45, ha="right", fontsize=6)
        ax.set_yticklabels(short, fontsize=6)
        ax.set_title(title, fontsize=7.5)
        ax.spines["top"].set_visible(True)
        ax.spines["right"].set_visible(True)
        fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    fig.tight_layout()
    save(fig, "fig_overlap")


# ---------------------------------------------------------------------------------------
# Figure 8: Kimi K2.7 position / volume mechanism (manuscript-size rendering of the committed
# Experiments/figures/ollama_extension_position_volume figure, same JSON source).
# ---------------------------------------------------------------------------------------
def fig_k27_mechanism():
    cells = load("ollama_cloud_extension_post_analysis.json")["cells"]
    colors = {"qwen3.5:cloud": "#7A7A7A", "kimi-k2.7-code:cloud": "#D55E00"}
    labels = [it["position"] for it in cells["kimi-k2.7-code:cloud"]["position_profile_query_2"]]
    x = np.arange(len(labels))
    fig, axes = plt.subplots(1, 3, figsize=(6.9, 2.3))
    for m in ("qwen3.5:cloud", "kimi-k2.7-code:cloud"):
        prof = cells[m]["position_profile_query_2"]
        rates = [it["unregistered_rate_pct"] if it["unregistered_rate_pct"] is not None else np.nan
                 for it in prof]
        axes[0].plot(x, rates, marker="o", lw=1.5, ms=4, color=colors[m], label=SHORT[m])
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=35, ha="right")
    axes[0].set_ylabel("Unregistered rate (%)")
    axes[0].set_xlabel("Package position, Query 2")
    axes[0].set_title("A. Late-list validity collapse")
    axes[0].legend(frameon=False, loc="upper left")
    kp = cells["kimi-k2.7-code:cloud"]["position_profile_query_2"]
    totals = np.array([it["occurrences"] for it in kp])
    unreg = np.array([it["unregistered"] for it in kp])
    axes[1].bar(x, totals, color="#D9D9D9", label="all parsed")
    axes[1].bar(x, unreg, color=colors["kimi-k2.7-code:cloud"], label="unregistered")
    axes[1].set_yscale("log")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=35, ha="right")
    axes[1].set_ylabel("Occurrences (log scale)")
    axes[1].set_xlabel("Package position, Kimi K2.7 Query 2")
    axes[1].set_title("B. Late positions dominate volume")
    axes[1].legend(frameon=False, loc="upper left")
    rows = cells["kimi-k2.7-code:cloud"]["package_volume_quartiles_query_2"]
    qlabels = [f"Q{it['quartile']}\n{it['package_count_min']}-{it['package_count_max']}" for it in rows]
    rates = [it["unregistered_rate_pct"] for it in rows]
    vols = [it["parsed_package_occurrences"] for it in rows]
    bars = axes[2].bar(np.arange(4), rates, color=["#F2C9B6", "#EAA27F", "#E0784E", "#C74D1E"],
                       edgecolor=INK, linewidth=0.4)
    axes[2].set_xticks(np.arange(4))
    axes[2].set_xticklabels(qlabels)
    axes[2].set_ylabel("Unregistered rate (%)")
    axes[2].set_xlabel("Kimi K2.7 Query 2 volume quartile\n(min-max parsed packages)")
    axes[2].set_title("C. Rate by response volume")
    for bar, vol in zip(bars, vols):
        axes[2].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.6, f"n={vol:,}",
                     ha="center", va="bottom", fontsize=6)
    axes[2].set_ylim(0, max(rates) + 7)
    for ax in axes:
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save(fig, "fig_k27_mechanism")


# ---------------------------------------------------------------------------------------
# Figure 9: Kimi K2.7 versus K3 mechanism (manuscript-size rendering of the committed
# Experiments/figures/kimi_k2_7_vs_k3_mechanism figure, same JSON source).
# ---------------------------------------------------------------------------------------
def fig_k3_mechanism():
    data = load("kimi_k2_7_vs_k3_post_analysis.json")
    k2, k3 = data["models"]["kimi_k2_7"], data["models"]["kimi_k3"]
    colors = ["#0072B2", "#D55E00"]
    fig, axes = plt.subplots(1, 3, figsize=(6.9, 2.3))
    metrics = ["Occurrence-\nweighted", "Prompt\nrisk", "Response\nmacro", "Cap tail\nexcluded"]
    k2v = [k2["overall"]["unregistered_rate_pct"], k2["overall"]["prompt_risk_pct"],
           k2["overall"]["macro_rates"]["response_mean_pct"], k2["cap_proxy_excluded"]["unregistered_rate_pct"]]
    k3v = [k3["overall"]["unregistered_rate_pct"], k3["overall"]["prompt_risk_pct"],
           k3["overall"]["macro_rates"]["response_mean_pct"], k3["exact_cap_excluded"]["unregistered_rate_pct"]]
    x = np.arange(len(metrics))
    w = 0.36
    axes[0].bar(x - w / 2, k2v, w, label="Kimi K2.7", color=colors[0], edgecolor=INK, linewidth=0.4)
    axes[0].bar(x + w / 2, k3v, w, label="Kimi K3", color=colors[1], edgecolor=INK, linewidth=0.4)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(metrics, fontsize=6)
    axes[0].set_ylabel("Percent")
    axes[0].set_title("A. Aggregation-sensitive reversal")
    axes[0].legend(frameon=False)
    labels = ["Responses", "Parsed\noccurrences", "Unregistered\noccurrences"]
    k2c, k3c = k2["cap_proxy_contribution"], k3["exact_cap_contribution"]
    k2t = [k2c["response_share_pct"], k2c["occurrence_share_pct"], k2c["unregistered_share_pct"]]
    k3t = [k3c["response_share_pct"], k3c["occurrence_share_pct"], k3c["unregistered_share_pct"]]
    x = np.arange(len(labels))
    axes[1].bar(x - w / 2, k2t, w, color=colors[0], label="K2.7 cap proxy", edgecolor=INK, linewidth=0.4)
    axes[1].bar(x + w / 2, k3t, w, color=colors[1], label="K3 exact caps", edgecolor=INK, linewidth=0.4)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, fontsize=6.5)
    axes[1].set_ylim(0, 105)
    axes[1].set_ylabel("Share of campaign total (%)")
    axes[1].set_title("B. Cap-tail contribution")
    axes[1].legend(frameon=False)
    positions = ["1", "2", "3-5", "6-10", "11-25", "26-50", "51-100", "101+"]
    prof = data["q2_position_rate_cap_excluded"]
    axes[2].plot(positions, [prof["kimi_k2_7_proxy_excluded"][p] for p in positions], marker="o", lw=1.5,
                 ms=4, color=colors[0], label="K2.7, proxy excluded")
    axes[2].plot(positions, [prof["kimi_k3_exact_excluded"][p] for p in positions], marker="s", lw=1.5,
                 ms=4, color=colors[1], label="K3, exact caps excluded")
    axes[2].set_xlabel("Package position, Query 2")
    axes[2].set_ylabel("Unregistered rate (%)")
    axes[2].set_title("C. Late-position degradation persists")
    axes[2].tick_params(axis="x", rotation=35)
    axes[2].legend(frameon=False, loc="upper left")
    for ax in axes:
        ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save(fig, "fig_k3_mechanism")


def main():
    os.makedirs(OUT, exist_ok=True)
    fig_tracka()
    fig_cap()
    fig_trackb()
    fig_leave_topk()
    fig_overlap()
    fig_k27_mechanism()
    fig_k3_mechanism()
    fig_concentration()


if __name__ == "__main__":
    main()
