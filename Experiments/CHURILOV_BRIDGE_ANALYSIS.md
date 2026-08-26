# Churilov bridge analysis

**Status:** post-hoc analysis of frozen Campaign 4 and extension outputs; no model responses
were changed.

## Code-only bridge

This analysis applies Churilov's public Python extraction design—`pip install` tokens plus
top-level imports—to Campaign 4's existing generated code. The first rate uses the frozen
registry for the closest artifact-level bridge. The second uses this project's stricter
dual-registry, non-stdlib definition. Intervals are dataset-stratified prompt-cluster
bootstrap intervals (50,000 replicates), not mention-level
Wilson intervals.

| Model | Extracted mentions | Frozen-absence rate (95% CI) | Dual-registry rate (95% CI) | Code-reference coverage | Prompt risk |
|---|---:|---:|---:|---:|---:|
| claude-opus-5 | 788 | 9.52% (6.04–13.71) | 9.52% (6.04–13.71) | 50.5% | 6.1% |
| gpt-5.2-2025-12-11 | 759 | 8.30% (5.66–11.41) | 8.30% (5.66–11.41) | 49.2% | 6.0% |
| gpt-oss:20b | 782 | 10.74% (8.34–13.28) | 10.61% (8.22–13.14) | 52.9% | 8.5% |
| grok-4.6 | 766 | 18.15% (12.45–23.92) | 17.49% (11.91–23.18) | 48.5% | 7.0% |
| deepseek-coder-v2:16b | 778 | 9.13% (7.02–11.38) | 8.87% (6.80–11.08) | 56.0% | 7.9% |
| deepseek-v4-flash | 742 | 8.89% (6.73–11.23) | 8.89% (6.73–11.23) | 52.0% | 7.4% |
| qwen3.5:cloud | 169 | 7.10% (3.57–11.05) | 6.51% (3.12–10.38) | 14.1% | 1.4% |
| kimi-k2.7-code:cloud | 745 | 7.38% (5.50–9.46) | 7.38% (5.50–9.46) | 53.2% | 6.5% |
| kimi-k3:cloud | 777 | 8.62% (6.57–10.84) | 8.37% (6.33–10.57) | 52.6% | 7.2% |

The bridge rates are not a direct replication of Churilov's model table because the model
cohorts do not overlap exactly and Campaign 4 uses 800 sampled prompts rather than the full
corpus. They do isolate the extraction-channel difference without spending more model calls.

The observed dual-registry bridge range is **6.51%–17.49%**,
which overlaps Churilov's reported Python range of 5.49%–7.27% at its lower end but extends
far above it. Qwen 3.5 falls inside that band, Kimi K2.7 is 0.11 points above its upper edge,
and Kimi K3 is 8.37%; the original six Campaign 4 cells remain 8.30%–17.49%. Thus the
extensions provide cohort-sensitive partial convergence, while the code-only extractor does
**not** by itself reconcile the original benchmark. 97.9%
of bridge flags came from imports rather than explicit `pip install` directives, and only
11 frozen-absence mentions were removed
by the current-registry/non-stdlib correction. The live measurement question is now the
semantic validity of mapping an import module directly to a PyPI distribution, together
with genuine model/cohort differences—not registry drift.

The dataset split is pronounced: the model-level dual-registry rates span
**3.70%–26.45%**
on LLM-synthesized datasets and **0.00%–7.50%**
on Stack Overflow datasets. This agrees directionally with Churilov's statement that
synthetic prompts yield higher rates, while showing that dataset composition and prompt
type remain substantial effect modifiers.

## Prompt-conditioned overlap

- Mean ordinary pairwise Jaccard over unique unregistered recommendation names:
  **0.038**.
- Names shared by all 9 models: **2**.
- Universal names emitted by all 9 on at least one identical prompt:
  **1**
  (50.0% of the universal set).

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
