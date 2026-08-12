# Baselines

`paper_appendix_e.csv` — the published per-model results from **Tables 7 and 8 (Appendix E)**
of *We Have a Package for You!* (USENIX Security '25, arXiv:2406.10279v3), transcribed so a
new run can be placed on the same scale. Used by [`compare_to_paper.py`](../compare_to_paper.py).

## The rate metric

§5.1 defines it as "a simple ratio of the number of hallucinated packages to the total
number of recommended packages", pooling all three detection heuristics:

| Heuristic | Column here | Source in `FINAL_RESULTS.csv` |
|---|---|---|
| 1 — `pip install` / `npm install` parsed out of the generated code | `install_*` | `pip_*` / `npm_*` over all four datasets |
| 2 — model asked which packages its own code needs | `llm_*` / `so_*` | `*_1` |
| 3 — model asked which packages would solve the original prompt | `llm_*` / `so_*` | `*_2` |

`llm_*` covers the two LLM-generated prompt datasets, `so_*` the two Stack Overflow ones.
Heuristics 2 and 3 are pooled within each dataset pair, exactly as the paper's tables report
them.

```
rate = (llm_hallucinated + so_hallucinated + install_hallucinated)
     / (llm_packages     + so_packages     + install_packages)
```

## Transcription

Every row was checked against the paper's own printed total: the three components sum to the
`Total Hallucination` numerator and denominator for all 30 rows, and each component's
percentage reproduces from its counts. `compare_to_paper.py --verify-baseline` re-runs both
checks against `paper_rate`.

Three cells were damaged in the PDF text layer and were reconstructed from that identity;
each reconstruction is confirmed independently by the percentage the paper prints alongside:

| Cell | In the PDF | Used here | Confirmed by |
|---|---|---|---|
| GPT-3.5 Turbo, Python, LLM prompts denominator | `41,7` (truncated) | `41,749` | 2,495/41,749 = 5.98% ✓ |
| WizardCoder 33B, Python, Stack Overflow numerator | `2,8523` | `2,853` | 2,853/13,329 = 21.40% ✓ |
| Mixtral 8x7B, Python, Stack Overflow denominator | `19,949` | `19,449` | 4,068/19,449 = 20.92% ✓ |

One value in the paper is internally inconsistent and is **left as published**: GPT-4
JavaScript, Stack Overflow prompts is printed as `3.86% (1,672/23,416)`, but those counts
give 7.14%. The counts are consistent with the row total, so the counts are used and the
printed percentage appears to be a typo. This affects only the `so` sub-rate for that one
model, not its total.

## Note on `Plots/Data/`

`figure_6.csv` matches Table 7 exactly for all 16 models, so the figure data and the
appendix agree there. Two others do not, and this is worth knowing before using them as a
baseline:

- **`figure_2.csv` is inconsistent with Tables 7 and 8.** It gives GPT-4 Turbo 3.35 % Python
  / 5.64 % JavaScript where the appendix gives 3.59 % / 4.00 %, and every model differs by a
  similar margin. The paper's own text (§5.1) quotes the appendix values — 3.59 %, 4.05 %,
  5.76 % — so `figure_2.csv` looks like it predates the final revision. **Tables 7 and 8 are
  used here.**
- **`figure_14.csv` column order is the reverse of the axis labels in `generate_plots.py`.**
  Its first column matches Table 7 (Python) and its second matches Table 8 (JavaScript), but
  `figure_14()` plots the first on an axis labelled "JavaScript Hallucination Rate" and the
  second on "Python Hallucination Rate".
- **`figure_9.csv` is internally inconsistent with the paper's prose** (first noted by the
  independent audit, verified here). The CSV's counts sum to 76,395 observations where §RQ4
  says 76,489; and the prose's "10,263 ... have a Levenshtein distance of 1 or 2" matches the
  CSV only if the 15 distance-**0** entries are included (3,557 + 6,691 + 15 = 10,263).
  Documented rather than reconciled; neither variant changes the paper's qualitative
  conclusion.
