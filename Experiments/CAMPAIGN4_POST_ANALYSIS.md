# Campaign 4 post-campaign analysis

**Status:** Post hoc. Model outputs, Parser v2, registry snapshots, and preregistered
Campaign 4 results remain frozen. This analysis evaluates robustness and interpretation; it
does not replace the primary outcomes in `campaign4_results.json`.

**Machine-readable artifact:** `Experiments/campaign4_post_analysis.json`  
**Reproduction:** `python post_campaign_analysis.py`

## Questions

1. Do response-format differences compromise the modern-model comparison?
2. Are model-level occurrence rates diffuse or dominated by a few extreme responses?
3. How sensitive are the paired comparisons to the construction of bootstrap p-values?
4. What does the paired cap diagnostic actually support?
5. Do the run manifests reveal a provenance problem that changes interpretation?

## Frozen-parser Track B audit

A deterministic 180-response sample was drawn from the six Track B cells: 20 uniformly
random responses and 10 deliberately difficult format/tail cases per model. Codex reviewed
all records against the frozen Parser v2 grammar. The signed sample is retained under the
ignored raw-artifact tree at `Tests/parser_v2_trackb_audit/sample.jsonl`; its SHA-256 is
recorded in the machine-readable post-analysis.

- Frozen-contract status agreement: **180/180**.
- Exact frozen-contract extraction agreement: **180/180**.
- Random core: **120/120** status and extraction agreement.
- Enriched challenge set: **60/60** status and extraction agreement.
- Every model: **30/30** agreement.

This is grammar-contract validation, not a claim of perfect semantic validity. The review
identified nine sample-level semantic or transport anomalies:

- four no-package prose answers deliberately classified as malformed;
- four Grok responses containing a literal trailing `<|eos|>` marker; and
- one DeepSeek Coder V2 response, `NoPythonpackagesrequired`, syntactically accepted as a
  package token although it semantically means that no package is required.

The audit therefore validates the frozen implementation while also showing why parser
coverage and sensitivity outcomes must accompany the occurrence rate.

## Track B robustness and failure shape

| Model | Primary rate (95% cluster CI) | Malformed | Top-three share | Rate after removing top three |
|---|---:|---:|---:|---:|
| Claude Opus 5 | 1.31% (1.04–1.63) | 3.75% | 10.66% | 1.18% |
| GPT-5.2 | 1.88% (1.48–2.30) | 0.56% | 8.09% | 1.74% |
| gpt-oss 20B | 2.15% (1.75–2.58) | 0.44% | 5.22% | 2.05% |
| Grok 4.6 | 8.22% (1.54–18.20) | 12.56% | 82.88% | 1.61% |
| DeepSeek Coder V2 16B | 10.30% (8.76–11.93) | 18.25% | 3.98% | 9.93% |
| DeepSeek V4 Flash | 17.91% (5.72–29.99) | 10.38% | 72.42% | 5.71% |

The aggregate rates describe three different regimes:

1. **Low-rate, diffuse failures:** Opus, GPT-5.2, and gpt-oss. Removing the three worst
   responses changes their rates by only 0.10–0.13 percentage points.
2. **High-rate, diffuse failure:** DeepSeek Coder V2. Its top three responses contribute
   only 3.98% of unregistered recommendations, and removing them leaves a 9.93% rate.
3. **Catastrophic-tail failure:** Grok and DeepSeek V4. One Grok prompt supplies at least
   half its unregistered recommendations; two prompts do so for V4. Removing only three
   responses reduces Grok from 8.22% to 1.61% and V4 from 17.91% to 5.71%.

The paper should not describe Grok and DeepSeek V4 as merely having higher average rates.
Their risk is structurally different: rare recommendation floods dominate the numerator
and produce very wide cluster intervals.

## Parser sensitivity found by the hosted-format audit

### Literal EOS marker

Grok included a literal trailing `<|eos|>` in 184 responses. All 184 are malformed under
the frozen grammar but become valid lists when—and only when—that exact terminal marker is
removed. This sensitivity changes:

- malformed rate from **12.56% to 1.06%**; and
- unregistered-PyPI occurrence rate from **8.22% to 7.91%**.

The large change in malformed rate is a transport-format effect. The small change in the
primary rate occurs because the 262 recovered names are registered or standard-library
names. The frozen result remains primary; the adjusted result should be reported beside it
as a parser/transport sensitivity.

### Collapsed no-package sentinel

DeepSeek Coder V2 produced `NoPythonpackagesrequired` 11 times; gpt-oss produced one
analogous one-token answer. Treating these as no-package answers changes the rates from
10.30% to **9.89%** and from 2.15% to **2.14%**, respectively. This does not change the
model-level interpretation, but it is a concrete semantic false-positive mode that belongs
in the limitations and Parser v2.1 design.

## Pairwise inference sensitivity

The preregistered percentile cluster intervals remain the primary uncertainty measure. The
original campaign formed two-sided bootstrap-tail probabilities from the paired bootstrap
distribution and applied Holm correction. A post-hoc recentered-null cluster bootstrap was
also run with the same 50,000 replicates, dataset strata, prompt pairing, and fixed seed.

- Original bootstrap-tail/Holm convention: **7 of 15** significant pairs.
- Recentered-null/Holm sensitivity: **5 of 15** significant pairs.

The five comparisons that survive both approaches are:

- Opus versus gpt-oss;
- Opus, GPT-5.2, and gpt-oss versus DeepSeek Coder V2; and
- Opus versus DeepSeek V4.

GPT-5.2 and gpt-oss versus DeepSeek V4 pass the original convention but not the recentered
sensitivity (Holm-adjusted p = 0.0596). Opus versus GPT-5.2 remains inconclusive. No pair
involving Grok is stable after correction because its estimate is dominated by a few
prompts.

The paper should lead with effect sizes, cluster intervals, and tail shape. A binary model
ranking based on the seven-test table would be too dependent on an inferential convention
that was not fully specified in the preregistration.

## Paired cap diagnostic

The post-analysis paired every cap with the 2048-token response at the prompt level and
bootstrapped within dataset strata.

For DeepSeek Coder V2, rates are 7.10–7.48% across all five caps. Every point difference
from cap 2048 is at most 0.33 percentage points; all paired intervals include zero. For
DeepSeek Coder 6.7B, the sequence is hump-shaped rather than monotone: 5.28%, 5.81%, 6.72%,
5.12%, and 4.78%. All paired cap-versus-2048 intervals include zero, although the cap-256
interval is wide (-0.04 to 4.29 percentage points).

The supported statement is:

> The large historical cap association did not reproduce as a systematic or monotone
> effect in the deterministic paired diagnostic.

The diagnostic does not prove equivalence or a zero causal effect: no equivalence margin
was preregistered, some paired generations diverged, and temperature was not crossed
factorially with cap.

## Provenance check

Five Track B cells have internally consistent invocation settings. The DeepSeek Coder V2
cell spans four resumed invocations and records worker counts 1 and 2 plus context settings
12,288, 16,384, and 32,768. Its model digest is stable, but its top-level manifest reflects
only the latest invocation. Run history records three aggregate cap hits that are not
represented in the final empty per-phase cap-hit object.

This is an operational reproducibility blemish, not evidence that the rate is wrong. The
paper and artifact manifest should disclose the mixed resumed-run settings and aggregate
cap hits. The cell does not need a full rerun for the paper's substantive conclusions.

## Paper-facing decision

Campaign 4 is ready for paper drafting. No additional model generation is required. The
paper should use the following hierarchy of claims:

1. Measurement validity and registry date materially affect reported package-hallucination
   rates.
2. Historical ordering and broad magnitude reproduce, while exact DeepSeek replication
   fails under the appropriate family parser.
3. The earlier cap association does not reproduce systematically under paired deterministic
   measurement.
4. Modern models occupy distinct failure regimes that averages alone conceal.
5. Cross-model occurrence rates must be published with response coverage, cluster
   uncertainty, and concentration diagnostics.

