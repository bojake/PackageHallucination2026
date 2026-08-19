# Churilov bridge analysis

**Status:** post-hoc analysis of frozen Campaign 4 outputs; no model responses were changed.

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

The bridge rates are not a direct replication of Churilov's model table because the model
cohorts do not overlap exactly and Campaign 4 uses 800 sampled prompts rather than the full
corpus. They do isolate the extraction-channel difference without spending more model calls.

The observed dual-registry bridge range is **8.30%–17.49%**,
which is above Churilov's reported Python range of 5.49%–7.27%. Therefore the code-only
extractor does **not** by itself reconcile the studies. 97.3%
of bridge flags came from imports rather than explicit `pip install` directives, and only
8 frozen-absence mentions were removed
by the current-registry/non-stdlib correction. The live measurement question is now the
semantic validity of mapping an import module directly to a PyPI distribution, together
with genuine model/cohort differences—not registry drift.

The dataset split is pronounced: the model-level dual-registry rates span
**8.25%–26.45%**
on LLM-synthesized datasets and **1.21%–7.50%**
on Stack Overflow datasets. This agrees directionally with Churilov's statement that
synthetic prompts yield higher rates, while showing that dataset composition and prompt
type remain substantial effect modifiers.

## Prompt-conditioned overlap

- Mean ordinary pairwise Jaccard over unique unregistered recommendation names:
  **0.054**.
- Names shared by all 6 models: **5**.
- Universal names emitted by all 6 on at least one identical prompt:
  **4**
  (80.0% of the universal set).

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
