# Paper outline

## Working title

**On Validating Package Hallucinations: Measurement Validity, Replication, and Tail Risk in
Modern Code Models**

Alternatives:

- **Beyond Average Hallucination Rates: Reproducing and Stress-Testing Package
  Recommendations from Code Models**
- **When the Parser Is Part of the Result: A Replication and Modern Benchmark of Package
  Hallucinations**
- **Package Hallucinations Revisited: Measurement Validity, Replication, and Tail Risk in
Modern Code Models**

## One-sentence thesis

Package-hallucination rates are not model-only properties: they depend materially on parser
validity, registry time, response format, and tail behavior, and once those factors are made
visible, modern code models separate into low-diffuse, high-diffuse, and catastrophic-tail
failure regimes.

## Claims the paper can make

1. The historical model ordering and broad rate range reproduce at greater power.
2. Exact DeepSeek replication fails under its appropriate historical family parser; all
   three seed-level confidence intervals exclude the published 16.61% value.
3. Parser choice and registry date are measurement variables, not clerical details.
4. The large earlier cap association does not reproduce systematically or monotonically in
   a deterministic paired diagnostic.
5. Opus, GPT-5.2, and gpt-oss have low, diffuse unregistered-PyPI recommendation rates in
   this protocol.
6. Grok and DeepSeek V4 exhibit catastrophic-tail behavior; DeepSeek Coder V2 exhibits a
   high diffuse rate.
7. Average rate, response coverage, prompt-level risk, and tail concentration are jointly
   necessary to characterize package-recommendation failures.
8. A Churilov-compatible code-import rescore does not collapse Campaign 4 into the reported
   2026 frontier band: dual-registry rates remain 8.30–17.49%, and import-module references
   account for most flagged bridge mentions. Extension rates are 6.51% for Qwen 3.5, 7.38%
   for Kimi K2.7, and 8.37% for Kimi K3.
9. Cross-model overlap is substantially prompt-conditioned: five unregistered names occur
   across all six Campaign 4 models, and four of those five occur across all six on an
   identical prompt.
10. The separately preregistered cloud extension adds a low-rate Qwen 3.5 cell (2.77%) and
    exposes a Kimi K2.7 list-flood failure: its 23.10% aggregate is dominated by 107,955
    Query 2 occurrences, 315 Query 2 cap hits, and a position gradient from about 5% in the
    first ten items to 27.33% after position 100.
11. The pre-outcome-attested Kimi K3 successor test reveals an aggregation reversal: K3 has fewer
    risky prompts and far fewer runaway lists than K2.7, but a worse 33.30% occurrence-weighted
    rate because 46 exact package cap hits contribute 81.02% of its unregistered occurrences.
    Excluding the cap-associated tails only as a post-hoc diagnostic yields nearly identical
    K3 and K2.7 rates (13.11% and 13.18%). The 54 K3 floods contain 8,010 unique normalized
    unregistered names with mean pairwise Jaccard 0.0011, ruling out a repeated fixed catalog
    as the main explanation for the tail.

## Claims to avoid

- “Frontier models have a 1.3–2.2% hallucination rate.” Grok and DeepSeek V4 refute that
  generalization, and gpt-oss is not a hosted frontier model.
- “The cap effect vanished” or “temperature caused the old effect.” The experiment supports
  non-reproduction, not causal elimination.
- “Every unregistered name is fabricated.” Some are real system, apt, npm, Java, Go, or
  other ecosystem names that are not available on PyPI.
- “Seven model pairs are definitively different.” Five survive both bootstrap conventions;
  effect sizes and intervals should be primary.
- “Parser v2 is semantically perfect.” Its grammar is reliable, but strict abstention,
  transport markers, and collapsed no-package tokens remain measurable limitations.
- “Churilov and Campaign 4 agree once extraction is matched.” The completed bridge remains
  above Churilov's Python range; extraction channel alone does not reconcile the studies.
- “Universal names prove shared training data.” Same-prompt elicitation explains four of
  Campaign 4's five all-model names and must be separated from different-prompt overlap.
- “Kimi K2.7 has a model-wide 23.10% ordinary recommendation rate.” That occurrence-weighted
  aggregate is a valid description of the collected output but is not representative of an
  ordinary short response: lists of at most ten parsed packages score 4.95%, and extreme
  Query 2 enumeration supplies nearly the entire denominator.
- “Removing cap-hit responses repairs Kimi K2.7.” The first extension runner retained exact
  cap counts only at phase level, so its exclusion analysis uses an explicitly post-hoc
  longest-response proxy. It diagnoses influence but cannot identify exact rows.
- “Kimi K3 is simply worse than K2.7.” K3 is worse on the prespecified occurrence-weighted
  estimand, but better on prompt risk (21.50% versus 43.00%), response-macro mean (4.18%
  versus 8.36%), and runaway-list frequency. The ranking depends on the operational question.
- “The token cap causes K3 hallucinations.” Exact cap status identifies a highly influential
  tail, but cap membership is post-treatment and cannot distinguish runaway enumeration from
  the boundary that truncates it. A randomized within-prompt cap experiment is still needed.
- “The K2.7 and K3 flood prompts barely overlap, so prompt susceptibility is irrelevant.” The
  22 joint floods exceed the 15.8 expected under independence (odds ratio about 1.7). The low
  Jaccard is partly constrained by the unequal 29.25% and 6.75% marginal flood rates; prompt
  susceptibility contributes, but does not alone determine model-specific flood membership.

## Research questions

**RQ1 — Replication.** Do the published CodeLlama and DeepSeek results reproduce with a
larger fixed prompt set and repeated generation seeds?

**RQ2 — Measurement validity.** How much do parser family, strict grammar, response format,
and registry date alter reported package-hallucination rates?

**RQ3 — Cap sensitivity.** Does package hallucination vary systematically with the package
response token cap when code and prompts are paired and generation is deterministic?

**RQ4 — Modern models.** How do current hosted and local models compare under a common
prompt set, frozen parser, and dual-registry definition?

**RQ5 — Failure shape.** Are aggregate rates driven by diffuse errors or rare catastrophic
recommendation floods?

**RQ6 — Concurrent-work bridge.** When identical Campaign 4 outputs are rescored with
Churilov's code-import extractor, and cross-model overlap is conditioned on prompt identity,
which apparent agreements and disagreements remain?

**RQ7 — Successor and list-volume mechanism.** Do the Kimi K2.7 response-volume and
late-position effects persist in Kimi K3 when finish reason and token use are retained for
every response?

## Abstract: five beats

1. **Problem:** Package hallucinations create correctness and software-supply-chain risk,
   but published rates may conflate model behavior with measurement artifacts.
2. **Design:** Reproduce the historical comparison, validate a grammar-aware parser, run a
   paired cap diagnostic, and benchmark six current hosted/local models on 800 fixed Python
   prompts with two package queries each.
3. **Replication:** CodeLlama reproduces near the published value; DeepSeek preserves the
   ordering and broad magnitude but its family-parser estimates, 13.28–13.54%, fall below
   the published 16.61%.
4. **Modern result:** Primary rates range from 1.31% to 17.91%, but tail analysis reveals
   three qualitatively different regimes. Three responses account for 82.88% of Grok's and
   72.42% of DeepSeek V4's unregistered recommendations. A separately preregistered successor
   cell extends the range to Kimi K3's 33.30%, where only 46 capped package responses supply
   81.02% of unregistered occurrences despite lower prompt-level risk than K2.7.
5. **Conclusion:** Valid evaluation requires registry-versioned scoring, explicit parser
   coverage, cluster uncertainty, and concentration diagnostics; a single average rate is
   inadequate.

Do not write the final abstract until the introduction and results are stable. Keep the
abstract's modern-model wording descriptive rather than treating the six cells as a
representative sample of all frontier or local models.

## 1. Introduction

### 1.1 Motivation

- Explain package hallucination and why an unregistered recommendation can become a
  slopsquatting target.
- Distinguish model fabrication from ecosystem mismatch: both can be unsafe PyPI
  recommendations, but they are different semantic failures.
- Introduce the replication problem: reported rates depend on how free-form model text is
  converted into package tokens and which registry snapshot is treated as truth.

### 1.2 Gap

- Prior work reports average package-level rates.
- Existing replication attempts exposed parser corruption, cap truncation, registry drift,
  and model-artifact ambiguity.
- Average rates do not reveal whether risk is routine or concentrated in rare floods.

### 1.3 Contributions

Use five contributions:

1. A powered, seed-repeated artifact replication separating broad reproduction from exact
   numerical replication.
2. A validated grammar-aware parser with explicit abstention and response-format outcomes.
3. A deterministic paired cap diagnostic that tests a previously suspected mechanism.
4. A six-model modern benchmark with dual registries, prompt-cluster inference, and a new
   diffuse-versus-catastrophic tail characterization.
5. A direct bridge to Churilov's concurrent 2026 study that holds model outputs fixed while
   changing the extractor, plus a prompt-conditioned overlap analysis that distinguishes
   shared elicitation from model-independent names.

### 1.4 Result preview

- CodeLlama generic-parser seed mean: 24.55% versus published 26.12%.
- DeepSeek family-parser seed mean: 13.43% versus published 16.61%; all seed CIs exclude the
  paper value.
- Modern primary rates: 1.31–17.91%, with radically different concentration.
- Cap diagnostic: no systematic or monotone association.
- Code-import bridge: original Campaign 4 cells remain 8.30–17.49% under the dual-registry
  definition; adding Qwen 3.5, Kimi K2.7, and Kimi K3 yields 621 flagged mentions, of which
  608 (97.91%) arise from imports rather than explicit install directives.
- Prompt-conditioned overlap: five names span all six models, but four have same-prompt
  support across all six.
- Cloud extension: Qwen 3.5 is 2.77% (95% cluster interval 2.07–3.54); Kimi K2.7 is 23.10%
  (20.19–26.19) but falls to 4.95% among responses with at most ten parsed packages and rises
  steeply with package position.
- Kimi K3 successor: 33.30% (27.22–38.81) occurrence-weighted, 21.50% prompt risk, and
  4.18% response-macro mean. Its 46 package cap hits provide 51.79% of parsed occurrences and
  81.02% of unregistered occurrences; after diagnostic cap-tail exclusion, K3 is 13.11% and
  K2.7 is 13.18%.

## 2. Background and related work

### 2.1 Package hallucinations and supply-chain risk

- Package recommendation versus generated import.
- Hallucination, unregistered registry name, and ecosystem mismatch.
- Slopsquatting threat model and responsible disclosure.

### 2.2 Evaluation of code-generating models

- Model/version pinning, stochastic repeats, prompt pairing, and cluster dependence.
- Why per-package observations are not independent.

### 2.3 Measurement error in free-form generations

- Parser precision/recall and selective abstention.
- Registry drift and temporal label instability.
- Truncation and control-token leakage as response-format variables.

### 2.4 Concurrent 2026 replication

- Credit Churilov's full-corpus, Python/JavaScript scale, universal-name analysis,
  registrability testing, and coordinated disclosure.
- Distinguish their code-import estimand from Spracklen's three-channel measurement and our
  package-recommendation estimand.
- Note that their reported range compares a five-model frontier cohort with the original
  study's commercial/open-source category averages, not the original model-level extrema.
- Explain the package-mention clustering problem in their Wilson, chi-square, and
  mention-level permutation inference without asserting that corrected results must vanish.
- Treat their training-origin interpretation of Jaccard overlap as one hypothesis; shared
  prompt elicitation, extractor behavior, and corpus composition are alternatives.

End this section with the seven research questions.

## 3. Study design

### 3.1 Two-track design

- **Track A:** historical artifact replication using original model families, sampling
  settings, parsers, and frozen 2024 registry.
- **Track B:** modern benchmark using Parser v2, the fixed prompt set, larger token budgets,
  and both 2024 and 2026 registries.
- **Extension cells:** Qwen 3.5 Cloud and Kimi K2.7 Code Cloud under a separately frozen
  protocol; Kimi K3 under a later successor/mechanism preregistration. These cells extend but
  do not alter Track B's original inferential family.
- For Kimi K3, define “frozen” narrowly and accurately: prompts, parser, registries, model and
  sampling settings, estimands, diagnostics, and comparison family were fixed. Provenance and
  completion-gate code changed during collection, before scoring; the executable pipeline was
  therefore not byte-frozen end to end, and the run remains retrospectively rather than
  cryptographically preregistered.
- State explicitly that Track B is not a scale reproduction of the 2024 paper.

### 3.2 Prompt corpus and unit of analysis

- Four datasets, 200 prompts each, fixed seed and subset.
- Two package queries per prompt; 1,600 package responses per complete cell.
- Prompt is the cluster and pairing unit.

### 3.3 Models and identity capture

- Track A: CodeLlama 7B Instruct and DeepSeek Coder 6.7B Instruct, three seeds each.
- Track B: Claude Opus 5, GPT-5.2, gpt-oss 20B, Grok 4.6, DeepSeek Coder V2 16B, and
  DeepSeek V4 Flash.
- Table exact served IDs, local digests, quantization, reasoning settings, supported/dropped
  sampling parameters, caps, and execution dates.
- Disclose that gpt-oss retained native reasoning behavior; do not say reasoning was
  disabled universally.
- Disclose DeepSeek Coder V2's resumed mixed operational settings.

### 3.4 Parser v2 and response statuses

- Frozen comma/list grammar, anchored marker removal, matched wrappers, deduplication.
- Statuses: list, malformed, empty.
- Malformed responses are abstentions and contribute no package denominator.
- Initial 200-response validation: 98% status accuracy, zero incorrect extractions, 79.75%
  end-to-end semantic recall due mainly to deliberate strict abstention.
- Post-campaign Track B audit: 180/180 frozen-contract agreement, with explicit EOS and
  no-package-sentinel semantic sensitivities.

### 3.5 Registries and categories

- Frozen PyPI snapshot from 2024-01-10 and current snapshot from 2026-08-12.
- Primary metric: absent from both snapshots and not a standard-library module.
- Name it **unregistered-PyPI recommendation rate**, not simply hallucination rate.
- Secondary categories: valid in both, post-snapshot package, deleted-since-snapshot,
  standard-library confusion, unregistered in both.

### 3.6 Outcomes

Co-report:

- unregistered-package occurrences / accepted package occurrences;
- prompt-level probability of at least one unregistered recommendation;
- malformed and empty response rates;
- packages per prompt and per accepted response;
- unique unregistered names;
- top-one/top-three/top-ten shares and leave-top-k-out diagnostics;
- position-band rates for the cap diagnostic.

### 3.7 Statistical analysis

- Dataset-stratified prompt-cluster percentile bootstrap intervals.
- Paired prompt-cluster comparisons across Track B cells.
- Use the same dataset-stratified paired prompt resampling for the post-hoc K2.7/K3 prompt-risk
  and flood-frequency comparisons; do not describe a uniform 800-prompt resample as the house
  standard.
- Holm correction across 15 pairwise comparisons.
- Treat the recentered-null bootstrap as a labeled post-hoc sensitivity.
- Make effect sizes and intervals primary; place p-value tables in a secondary table or
  appendix.
- Report adjusted values at a finite-bootstrap resolution floor as bounds. For the K3 family,
  `8 × (1/50,000) = 0.000160` is written `p ≤ 0.000160`, never as an exact p-value.
- Explain that leave-top-k estimates characterize concentration and are not alternative
  primary estimands.

### 3.8 Churilov bridge and prompt-conditioned overlap

- Rescore frozen Track B code with the public H1-plus-import extractor; do not regenerate.
- Report both frozen-registry absence and dual-registry/non-stdlib rates.
- Preserve Churilov's mention construction: imports deduplicated within generation, with no
  cross-channel deduplication against `pip install` hits.
- Cluster intervals by prompt and stratify by dataset.
- Report ordinary name Jaccard beside aligned Jaccard over
  `(normalized name, dataset, prompt index)` tuples.
- Do not publish candidate package names.

### 3.9 Cloud extension and per-response provenance

- Qwen 3.5 and Kimi K2.7 reuse the fixed 800-prompt subset, Parser v2, dual registries, and
  two-query design, with a separate 13-comparison Holm family involving either new cell.
- Co-report Query 1 and Query 2 volumes: the two prompts are measurement channels, not
  interchangeable replicate responses when a model enumerates hundreds of recommendations.
- Preserve Kimi K2.7's combined preregistered estimate while labeling query-, volume-, and
  position-specific diagnostics post hoc.
- For Kimi K3, require ordered per-response sidecars with finish reason, served model,
  prompt/completion tokens, and exact cap status; fail scoring if any of 2,400 rows is missing.
- Record provider-reported token cost and enforce the maintainer's run-level dollar guard.

## 4. Results

### 4.1 Measurement validation

Lead with the fact that the instrument changed the scientific conclusion.

- Initial validation results and strict-grammar recall cost.
- Hosted-format audit and 100% frozen-contract agreement.
- Grok EOS sensitivity: malformed 12.56% to 1.06%; primary rate 8.22% to 7.91%.
- Collapsed no-package sensitivity: DeepSeek Coder V2 10.30% to 9.89%.
- Registry growth: 500,513 to 869,894 names; explain why dual scoring matters.

### 4.2 Historical replication

- Forest plot for published value and three seed estimates per model.
- CodeLlama: 24.20%, 24.84%, 24.60%; every generic-parser CI contains 26.12%.
- DeepSeek generic: 14.37–14.86%; family parser: 13.28–13.54%.
- All three family-parser CIs exclude 16.61%.
- Conclusion: historical ordering and broad magnitude reproduce; exact DeepSeek result does
  not.

### 4.3 Controlled cap diagnostic

- Plot rate and malformed rate over caps 64, 128, 256, 512, and 2048.
- DeepSeek Coder V2: 7.10–7.48%; every paired delta versus 2048 is at most 0.33 points.
- DeepSeek 6.7B: hump-shaped 5.28%, 5.81%, 6.72%, 5.12%, 4.78% sequence.
- All paired intervals include zero; prefix/divergence diagnostics remain visible.
- Conclusion: the earlier large association is not reproduced as systematic or monotone.

### 4.4 Modern benchmark

Use a primary table with rate, cluster interval, prompt risk, malformed, empty, packages per
prompt, unique names, and top-three share. Never publish the rate without coverage.

- Low cells: Opus 1.31%, GPT-5.2 1.88%, gpt-oss 2.15%.
- High diffuse cell: DeepSeek Coder V2 10.30%.
- Tail-dominated cells: Grok 8.22% and DeepSeek V4 17.91%, both with wide intervals.
- Do not label Opus, GPT, and gpt-oss a “frontier trio.”

### 4.5 Failure regimes and tail risk

This should be the paper's signature result.

- Plot cumulative share of unregistered recommendations against ranked prompts.
- Pair it with a leave-top-k plot for k = 0, 1, 3, and 10.
- Grok: top one 63.06%, top three 82.88%, leave-three rate 1.61%.
- DeepSeek V4: top three 72.42%, leave-three rate 5.71%.
- DeepSeek Coder V2: top three 3.98%, leave-three rate 9.93%.
- Explain that similar-looking averages can imply different operational mitigation: routine
  validation for diffuse failures versus flood detection/output bounds for catastrophic
  tails.

### 4.6 Pairwise sensitivity

- Show effect estimates and intervals in the main paper.
- Report that seven pairs pass the original bootstrap-tail/Holm convention and five pass a
  recentered-null sensitivity.
- Stable findings: Opus versus gpt-oss; each of Opus/GPT/gpt-oss versus DeepSeek Coder V2;
  Opus versus DeepSeek V4.
- GPT and gpt-oss versus V4 are convention-sensitive; Opus versus GPT is inconclusive.
- Avoid a total ordering, particularly for Grok.

### 4.7 Concurrent-work bridge

- Code-only dual-registry rates: GPT-5.2 8.30%, DeepSeek Coder V2 8.87%, DeepSeek V4
  8.89%, Opus 9.52%, gpt-oss 10.61%, and Grok 17.49%.
- Extension bridge rates are Qwen 3.5 6.51%, Kimi K2.7 7.38%, and Kimi K3 8.37%. Only Qwen
  falls inside Churilov's Python range of 5.49–7.27%; there is no exact model overlap, so
  describe rather than test that contrast.
- Across all nine cells, synthetic-prompt rates span 3.70–26.45%, versus 0.00–7.50% on
  Stack Overflow subsets;
  prompt source is a major effect modifier.
- Only 11 of 632 frozen-absence mentions are removed by the current-registry/non-stdlib
  correction, so registry drift does not explain the bridge gap.
- Imports contribute 608 of 621 dual-registry flags. Discuss import-module/distribution-name
  mismatch and project-local imports as remaining semantic-validity risks.
- Across all nine cells, ordinary mean pairwise Jaccard is 0.038; two names span every model,
  one with same-prompt support across all nine. Preserve the original six-cell overlap result
  separately when discussing Campaign 4 alone.

### 4.8 Preregistered Qwen/Kimi cloud extension

- Qwen 3.5: 2.77% unregistered recommendation rate (2.07–3.54), 7.88% prompt risk,
  13.25% malformed, zero package-response cap hits, and 2,782 parsed occurrences.
- Kimi K2.7: 23.10% (20.19–26.19), 43.00% prompt risk, 14.75% malformed, 323
  package-response cap hits, and 111,842 parsed occurrences.
- Split the channels immediately: Kimi Query 1 is 21.82% over 3,887 occurrences and Query 2
  is 23.15% over 107,955. The Query 1 aggregate is itself driven by six responses extending
  beyond position 100; excluding the phase-matched longest-response proxy reduces it to
  3.77%.
- Lists of at most ten packages yield 4.95%; responses above 25 packages supply 106,980
  occurrences at 23.93%.
- The weighting contrast is material: the pooled occurrence rate is 23.10%, versus an
  unweighted 8.36% mean over non-empty parsed responses and an 11.78% prompt-macro mean;
  both macro medians are zero. Report these as descriptive views, not replacements for the
  preregistered estimand.
- Position is the clearest mechanism: Kimi Query 2 is 5.28–5.87% through position 25,
  10.85% at 26–50, 15.03% at 51–100, and 27.33% at 101+. This is a late-enumeration
  validity collapse plus instruction-following failure, not simply a uniform model rate.
- Parser noise is a mediator, not a sufficient explanation. The 323 phase-matched cap proxies
  are malformed at 26.94% versus 11.67% for nonproxies (+15.27 points), and contain 36.86% of
  all Kimi malformed responses. Nevertheless, 236 proxies parse as lists and supply 104,420
  occurrences. After excluding every proxy, Query 2 still rises from roughly 5–7% through
  position 25 to 22.03%, 36.94%, and 41.38% in positions 26–50, 51–100, and 101+; those late
  bins come from only 16, 12, and 10 responses and must be presented as mechanism evidence,
  not precise population rates.
- The 234 Query 2 responses above 100 packages are not copies of a fixed catalog: mean
  pairwise package-set Jaccard is 0.066. Thirty-nine normalized names form a common core,
  but diverse prompt-conditioned tails dominate; paired Query 1/Query 2 mean Jaccard is only
  0.005 for these floods.
- State the provenance limitation: Kimi K2.7 exact cap-hit response ids were not retained;
  the longest-response exclusion is a post-hoc proxy. Kimi K3 corrects that instrumentation.

### 4.9 Kimi K3 successor test

- The separately preregistered 2,400-call cell passed all 12 response-sidecar gates: one
  served id (`kimi-k3`), zero errors or request adjustments, 72 total exact caps (46 package),
  and $16.271841 token-derived analytic spend.
- Primary occurrence-weighted rate: 33.30% (95% prompt-cluster interval 27.22–38.81), with
  21.50% prompt risk, 4.19% malformed responses, and 25,889 parsed occurrences. All eight
  separately adjusted paired comparisons place K3 above its comparator on this primary rate;
  K2.7 minus K3 is -10.20 points (95% percentile interval -16.43 to -3.44).
- Split the task: Query 1 is 1.76% over 1,303 occurrences, whereas Query 2 is 34.97% over
  24,586. K3 therefore follows the requested-code query well but sometimes treats the open
  recommendation query as an unbounded enumeration task.
- Exact cap decomposition: 46 package cap hits—2.88% of package responses—supply 13,408
  occurrences (51.79% of the total) and 6,985 unregistered occurrences (81.02% of the total).
  Their rate is 52.10%; the exact-cap-excluded diagnostic is 13.11%. Keep 33.30% primary and
  label exclusion as post hoc conditioning, not a corrected estimate.
- The comparison with K2.7 is an aggregation reversal. K3 has lower prompt risk (21.50% versus
  43.00%), lower response-macro mean (4.18% versus 8.36%), and only 54 Query 2 responses above
  100 packages versus 234. Yet its rarer capped floods are much more contaminated (52.10%
  versus 23.81% in K2.7's cap proxy), making the pooled occurrence rate worse.
- On 800 shared Query 2 prompts, report the dataset-stratified paired-bootstrap intervals for
  K2.7 minus K3 prompt risk and >100-package response frequency. Twenty-two prompts flood in
  both models versus 15.8 expected under independence (odds ratio about 1.7), so there is shared
  prompt susceptibility. Flood-prompt Jaccard is 0.083 versus a marginal-constrained maximum
  of 0.231; prompt difficulty contributes but does not alone determine the catastrophic tail.
- The 54 K3 floods contain 8,010 unique normalized unregistered names; mean pairwise
  unregistered-name Jaccard is 0.0011 and no name appears in at least 25% of floods. This
  preempts the claim that the tail is merely one repeated catalog or a degenerate loop. It
  does not remove the parser's ordinary validity limitations.
- Late-position degradation remains after exact K3 cap exclusion: Query 2 rises from 2.70–5.62%
  through position 25 to 9.06%, 11.22%, and 36.75% at positions 26–50, 51–100, and 101+.
  The two-stage mechanism is occasional runaway enumeration followed by declining validity;
  the token boundary reveals and censors that process but is not established as its cause.
- Report the K3 eight-comparison Holm family separately from Campaign 4 and the Qwen/K2.7
  extension family. Use `KIMI_K3_EXTENSION_RESULTS.md` for the prespecified K3 result with its
  retrospective-provenance qualifier and
  `KIMI_K2_7_VS_K3_POST_ANALYSIS.md` for the explicitly post-hoc mechanism comparison.

## 5. Discussion

### 5.1 The parser is part of the measurement instrument

- Strict parsing buys precision by selectively abstaining.
- Coverage differences can bias cross-model comparisons if omitted.
- Control tokens should be normalized at the transport layer and logged.

### 5.2 Registry time changes the label space

- A name can move from “hallucinated” to registered without any model change.
- Date and digest registry snapshots just like model artifacts.

### 5.3 Average rates conceal operationally different risks

- Low diffuse, high diffuse, and catastrophic-tail regimes.
- Tail-aware metrics are necessary for security evaluation.
- Recommend flood guards, registry checks, and installation confirmation interfaces.
- Use the K2.7/K3 reversal as the clearest example: K3 is safer on typical-prompt measures but
  worse when every emitted occurrence receives equal weight. Neither estimand subsumes the other.

### 5.4 What the cap diagnostic resolves—and what it does not

- It weakens the proposed cap mechanism for DeepSeek under deterministic measurement.
- It does not identify temperature as the cause and does not establish formal equivalence.
- Exact K3 finish reasons show that cap-associated responses can dominate an aggregate, but
  they do not establish that increasing or decreasing the cap causes the runaway behavior.

### 5.5 Replication as measurement debugging

- Separate artifact fidelity, measurement validity, and contemporary relevance.
- Explain why “broad reproduction with exact numerical failure” is more informative than a
  binary replication verdict.

### 5.6 What the concurrent replication changes

- Churilov establishes breadth and a real registrable cross-model attack surface.
- Our bridge shows that matching the extractor is necessary but not sufficient for rate
  comparability; cohort, prompt source, module-to-distribution mapping, refusal policy, and
  inferential unit remain consequential.
- Prompt-conditioned overlap should become standard before universal-name sets are used to
  infer shared training origins.

## 6. Threats to validity and limitations

- Python only; package-query task rather than general code generation.
- The six-cell Campaign 4 benchmark, two separately frozen extension cells, and one later
  pre-outcome-attested K3 successor are purposive, not representative samples of all
  frontier/local models.
- Kimi K3's scientific design was frozen, but its provenance/completion gates were expanded
  during collection. The finalized manifest's missing later `restored_*` fields corroborate
  that the live process had loaded an earlier pipeline version. Those edits did not affect
  prompts, responses, parsing, or estimands, but “frozen pipeline” would overstate the record.
- The Kimi K3 freeze is supported by a retrospective attestation and later remote commit, not
  by a tamper-evident pre-data commit; the remote history only anchors the state forward from
  publication.
- One fixed prompt subset and one modern generation draw per model.
- Strict parser has 79.75% end-to-end semantic recall in the initial validation sample.
- The Track B audit was AI-reviewed at maintainer direction; no human labeled every record.
- Occurrence rate conditions on accepted grammar-valid package tokens.
- Hosted aliases and provider-side infrastructure can change despite served-ID capture.
- DeepSeek Coder V2 resumed-run metadata are mixed.
- Some package-query responses hit token caps; catastrophic-tail totals may be lower bounds.
- Kimi K2.7's phase-level cap counts cannot be mapped to exact response ids; its cap exclusion
  is a longest-response proxy. Kimi K3 was instrumented prospectively to remove that ambiguity.
- Kimi K2.7's aggregate denominator is overwhelmingly generated by extreme Query 2 lists;
  occurrence-weighted and prompt-level risk answer different operational questions.
- K3 exact cap membership is observed, but cap-excluded conditioning remains post-treatment;
  comparison against K2.7 also mixes exact K3 labels with K2.7's longest-response proxy.
- Unregistered PyPI names include ecosystem mismatches, not only invented strings.
- Post-hoc tail, EOS, sentinel, and recentered-bootstrap analyses must remain labeled post
  hoc.
- The Churilov bridge is post-hoc relative to Campaign 4, the cohorts have no exact model
  match, and generated imports can denote local modules rather than installable packages.
- The Qwen 3.5 Cloud and Kimi K2.7 Code cells are a separately preregistered extension and must not
  be folded retroactively into Campaign 4's original confirmatory family.

## 7. Security, ethics, and responsible artifact release

- Explain the risk of publishing currently unregistered candidate package names.
- Release aggregate and per-prompt counts openly.
- Consider controlled access, hashing, or delayed release for raw unregistered names.
- Preserve raw response hashes, manifests, prompts, model IDs/digests, parser version, and
  registry snapshots.
- State that the work measures unsafe recommendations; it does not validate that a named
  package is malicious.

## 8. Conclusion

Return to three sentences:

1. The historical pattern broadly reproduces, but the exact DeepSeek value does not.
2. Modern models show distinct diffuse and catastrophic-tail failure regimes.
3. Future package-hallucination evaluations should version the registry and parser, report
   response coverage, cluster by prompt, and quantify concentration.

## Tables

1. Model cells, exact identities, protocol settings, and deviations.
2. Parser validation and Track B audit.
3. Track A seed-level replication estimates and historical values.
4. Track B primary outcomes with malformed/empty rates and concentration.
5. Paired effect estimates with original and recentered Holm sensitivities.
6. Name-category composition by model.
7. Churilov code-import bridge with clustered intervals and dataset decomposition.
8. Ordinary versus prompt-aligned overlap summary.
9. Qwen/Kimi extension outcomes with query volume, position profile, and cap sensitivity.
10. Kimi K3 successor outcomes and exact response-metadata audit.
11. K2.7/K3 aggregation decomposition, shared-prompt flood contingency, and cap-tail influence.

## Figures

1. Two-track study design and measurement pipeline.
2. Track A replication forest plot.
3. Cap diagnostic rate and malformed-rate curves with paired intervals.
4. Track B rate forest plot paired with response coverage.
5. Ranked-prompt cumulative concentration curves.
6. Leave-top-k sensitivity plot showing the three failure regimes.
7. Paired ordinary-name versus prompt-aligned overlap comparison.
8. Kimi K2.7 position/volume mechanism: Query 2 position rates, occurrence mass, and
   response-volume quartiles (`Experiments/figures/ollama_extension_position_volume.pdf`).
9. Kimi K2.7 versus K3 mechanism: aggregate metric reversal, cap-tail contribution, and
   cap-diagnostic-excluded position profile
   (`Experiments/figures/kimi_k2_7_vs_k3_mechanism.pdf`).

## Appendices and artifact checklist

- Full preregistration and chronological amendments.
- Frozen Parser v2 grammar and unit tests.
- Initial and Track B audit designs, signed summaries, and hashes.
- Dual-registry construction, dates, counts, and hashes.
- All seed-level Track A tables.
- Full cap pairing and position-band tables.
- All 15 paired comparisons under both bootstrap conventions.
- Prompt-level derived counts sufficient to reproduce every interval without exposing raw
  unregistered package names.
- Raw response archive under an explicit responsible-access policy.
- DeepSeek Coder V2 run-history addendum and aggregate cap-hit correction.
- Churilov-compatible extractor port, dependency versions, tests, and machine-readable
  prompt-cluster bridge output.
- Separately frozen Qwen/Kimi cloud extension protocol and manifests.
- Kimi K2.7 query/volume/position post-analysis with explicit cap-proxy labeling.
- Kimi K3 preregistration, ordered response metadata sidecars, cost ledger, and scoring gate.
- Kimi K2.7/K3 paired post-analysis with exact/proxy distinction and 50,000-replicate,
  dataset-stratified shared-prompt intervals, plus the full flood contingency and diversity
  diagnostics.
- Retrospective provenance stamp with explicit non-cryptographic-preregistration limitation,
  frozen-core digest, containing commit, and raw-artifact hash index.
- Fable review amendment ledger documenting the stratified rerun, finite-bootstrap p-value
  bounds, overlap reinterpretation, mid-run code disclosure, and resume-safe cap gate.

## Recommended writing order

1. Methods and artifact appendix.
2. Results with final tables and figures.
3. Discussion and limitations.
4. Introduction and related work.
5. Abstract and title last.
