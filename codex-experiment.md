# Independent Audit of the Package-Hallucination Replication and Extension

**Audit date:** 2026-08-12  
**Auditor:** OpenAI Codex  
**Repository state reviewed:** commits through `3c021c0` on `main`

## Executive summary

The provider-agnostic experiment runner is a useful foundation, and several parts of the
analysis are sound. In particular, the transcription of the original paper's appendix,
reconstruction of its pooled hallucination-rate metric, and the arithmetic reported for the
stored runs all check out. The larger CodeLlama run is also a useful approximate replication.

The current report is not yet ready to support its strongest methodological or comparative
claims, however. Four issues materially change the interpretation:

1. The DeepSeek runs were scored with the generic parser, not the DeepSeek-specific parser
   used by the original pipeline. Re-scoring from the raw response JSON changes the package
   universe and reduces, but does not eliminate, the apparent cap effect. This prevents the
   current run from being called a parser-faithful replication.
2. The 64-token and 2048-token package responses were independently sampled. Most differing
   pairs are not prefix-related, so subtracting their aggregate counts does not identify a
   literal "discarded tail." The cap may have a large effect, but the claimed 54.06% tail rate
   and its proposed ordering mechanism were not measured by this experiment.
3. The two CodeLlama runs do not establish ±3 percentage-point run-to-run variance. The smaller
   prompt set is nested inside the larger one, and the repeated portion differs by only 0.42 pp.
   The additional prompts, not demonstrated stochastic variance, account for most of the
   aggregate difference.
4. The gpt-oss run uses different response caps from the paper and therefore is not "on the
   paper's scale." Its 2.90% result is encouraging under the modernized protocol, but it cannot
   support a "five times better" comparison to a 64-token historical baseline.

The recommended next iteration should explicitly separate an **artifact-replication track**
from a **modern-model benchmark track**, isolate cap effects deterministically, treat prompts
as statistical clusters, record immutable model identities, and score modern results against
both frozen and current package-registry snapshots.

## Scope and audit method

This review covered:

- `REPLICATION.md`, `EXTENSION_NOTES.md`, `README.md`, and `compare-to-paper.md`;
- the original and API generation paths;
- package parsing, normalization, validation, and aggregation;
- every stored run manifest and `FINAL_RESULTS.csv`;
- row-level raw outputs for the DeepSeek cap experiment;
- the CodeLlama prompt subsets and their row-level results;
- the baseline appendix transcription and its internal arithmetic;
- uncertainty estimates recomputed with prompt-cluster bootstrapping;
- current PyPI status for the names flagged by the gpt-oss run; and
- the camera-ready USENIX paper and current official model documentation.

No experiment outputs or source files were modified during the audit. The independent figures
below were computed from the committed raw artifacts.

## Findings that validate

### 1. The paper metric and baseline transcription are correct

The original paper defines its headline rate as the number of hallucinated package
recommendations divided by all package recommendations. Its appendix tables show that the two
model-query heuristics and `pip install`/`npm install` extraction are pooled as raw counts.

`Baselines/paper_appendix_e.csv` reproduces:

- all 30 model-by-language printed totals within 0.005 percentage points;
- 440,445 hallucinated occurrences out of 2,235,642 recommendations, or 19.70%; and
- mean per-model rates of 15.87% for Python and 21.38% for JavaScript, consistent with the
  paper's rounded 15.8% and 21.3%.

This part of the project can be retained. The appendix is a better baseline than
`Plots/Data/figure_2.csv`, which appears to reflect a different revision of the results.

Primary source: [Spracklen et al., USENIX Security 2025](https://www.usenix.org/system/files/usenixsecurity25-spracklen.pdf).

### 2. The stored headline rates are arithmetically correct

Recomputing the pooled metric from each `FINAL_RESULTS.csv` reproduces the report:

| Run | Hallucinated | Recommendations | Rate |
|---|---:|---:|---:|
| CodeLlama 7B, 400 prompts/dataset | 1,492 | 6,258 | 23.84% |
| CodeLlama 7B, 100 prompts/dataset | 387 | 1,464 | 26.43% |
| DeepSeek 6.7B, 64-token cap, generic parser | 411 | 3,064 | 13.41% |
| DeepSeek 6.7B, 2048-token cap, generic parser | 1,063 | 4,270 | 24.89% |
| gpt-oss:20b, raised caps | 89 | 3,071 | 2.90% |

The dispute is therefore not arithmetic. It concerns whether the chosen parser, generation
design, comparison baseline, and statistical model license the interpretations attached to
those counts.

### 3. The larger CodeLlama run is useful approximate evidence

CodeLlama's 23.84% is 2.28 pp below the paper's 26.12%. The checkpoint, quantization format,
chat template, serving stack, sample size, and stochastic generations are not identical, so
bit-exact agreement should not be expected. The direction and broad magnitude are consistent
with the historical result, and CodeLlama uses the same no-preprocessing Python parser in both
the original and API paths.

The appropriate claim is:

> The API/Ollama path produces a CodeLlama result in the same broad range as the original
> artifact, but the evidence does not establish exact cross-implementation equivalence.

## Findings requiring correction or a new experiment

### 1. DeepSeek was not scored with the original DeepSeek parser

For Python, `package_detection.get_pre_post_info()` routes a DeepSeek model through:

```text
(pre=True, post=True, style="DeepSeek")
```

The API runner instead defaults `--parser-style auto` to:

```text
(pre=False, post=False, style="")
```

Both committed DeepSeek manifests confirm the generic parser was used. This contradicts the
claim that package extraction was left unchanged for the DeepSeek replication.

Re-scoring the raw response JSON without regenerating it gives:

| Cap | Reported generic-parser result | Original DeepSeek-parser result |
|---|---:|---:|
| 64 | 13.41% (411/3,064) | **12.69% (466/3,672)** |
| 2048 | 24.89% (1,063/4,270) | **20.76% (1,208/5,820)** |

The historical parser therefore changes the cap contrast from 11.48 percentage points to
8.07 points. It extracts substantially more candidate names from both runs and is not thereby
proved semantically correct for the Ollama response format. Parser choice remains an
uncontrolled measurement variable, but it is not the dominant explanation for the anomaly.

**Correction to an earlier audit calculation:** the previously reported 50.78% and 51.23%
figures were invalid. They resulted from applying the parser a second time to list-valued
fields already serialized in `*_results.csv`, rather than rebuilding those files from the raw
`*_packages_{1,2}.json` responses. The corrected figures above were reproduced through
`package_detection.detect_packages()` on clean copies of the raw run directories.

Recommended correction:

- remove DeepSeek from the replication-validation claim until rerun;
- report both original-family and canonical-modern parsing as a sensitivity analysis; and
- create a manually labeled response sample to determine which parser better recovers actual
  package recommendations from each response format.

Relevant code and artifacts:

- `run_test_api.py`, parser tables and `resolve_parser_style()`;
- `package_detection.py`, `get_pre_post_info()`;
- `Tests/megatron_deepseek_6.7b_Python/run_manifest.json`; and
- `Tests/megatron_deepseek_6.7b_cap2048_Python/run_manifest.json`.

### 2. The cap experiment does not measure a literal truncated tail

The prompt, generated-code, and master files in the 64- and 2048-token DeepSeek directories
have matching SHA-256 hashes. That is good: the package queries were conditioned on identical
code. However, each package response was generated in a separate stochastic call.

Across the 1,600 paired package-query outputs:

| Relationship | Pairs | Share |
|---|---:|---:|
| Exactly equal | 628 | 39.3% |
| Long response strictly starts with the complete short response | 242 | 15.1% |
| Responses diverge before the short response ends | **730** | **45.6%** |

Consequently, the aggregate difference between the two scored runs is a mixture of:

- the larger output budget;
- new stochastic samples;
- different packages selected before the nominal truncation boundary; and
- parser behavior on longer or more verbose responses.

The following current claims should be withdrawn pending a controlled rerun:

- the extra 1,206 packages are the packages "discarded by the cap";
- that discarded tail has a 54.06% hallucination rate;
- models generally name valid packages first and hallucinations later; and
- this measured mechanism explains the historical DeepSeek replication gap.

The observed association remains noteworthy: using the current generic parser, the two runs
differ by 11.48 pp. A paired prompt-cluster bootstrap gives an approximate 95% interval of
**+7.22 to +16.62 pp**. That supports further study of cap sensitivity, but not the current
causal decomposition.

### 3. The run-to-run variance claim confounds sample composition and regeneration

The 100-prompt CodeLlama subset is completely nested inside the 400-prompt subset for every
dataset. Partitioning the larger run gives:

| Portion | Hallucinated | Recommendations | Rate |
|---|---:|---:|---:|
| Small run | 387 | 1,464 | 26.43% |
| Same prompts regenerated within large run | 385 | 1,480 | **26.01%** |
| Additional prompts in large run | 1,107 | 4,778 | **23.17%** |

On the prompts that were actually repeated, the difference is only 0.42 pp. Most of the 2.6 pp
aggregate shift arises from the added prompt sample. The current experiment therefore does not
show that run-to-run variance exceeds the package-binomial interval, and it provides no basis
for a universal ±3 pp rule.

Recommended correction:

- remove §5.4's variance conclusion and every later argument that relies on ±3 pp;
- retain the two CodeLlama runs as evidence of prompt-sample sensitivity; and
- estimate generation variance with repeated runs over the exact same prompts, model digest,
  model seed policy, serving configuration, and parser.

### 4. Package-level binomial intervals understate uncertainty

Package recommendations from one prompt are correlated. The number of recommendations per
prompt also varies substantially, so the observations are neither independent nor equally
weighted. The report acknowledges this but still uses package-binomial intervals in result
tables and comparisons.

A stratified nonparametric bootstrap that resamples prompts within each of the four datasets
produces:

| Run | Rate | Reported package-binomial 95% CI | Prompt-cluster 95% interval |
|---|---:|---:|---:|
| CodeLlama, 400/dataset | 23.84% | 22.79–24.90% | **22.22–25.48%** |
| CodeLlama, 100/dataset | 26.43% | 24.18–28.69% | **23.08–29.91%** |
| DeepSeek, 64/generic parser | 13.41% | 12.21–14.62% | **11.60–15.41%** |
| DeepSeek, 2048/generic parser | 24.89% | 23.60–26.19% | **20.30–30.35%** |
| gpt-oss | 2.90% | 2.30–3.49% | **2.17–3.67%** |

The modern experiment should use prompt-cluster inference by default. When the same prompts are
sent to multiple models or conditions, comparisons should be paired by prompt.

### 5. gpt-oss is encouraging, but not comparable to the paper as currently framed

The gpt-oss result is measured with 4096 code tokens and 2048 package tokens, versus the
paper's 2048 and 64. The report correctly acknowledges elsewhere that raised-cap results are
not directly comparable to the paper, but nevertheless describes gpt-oss as being on the
paper's scale and roughly five times better than DeepSeek 1B.

Those statements are internally inconsistent. The safe result is:

> Under the modern raised-cap protocol and frozen January 2024 PyPI list, gpt-oss:20b produced
> 89 flagged recommendations out of 3,071, or 2.90%, with a prompt-cluster interval of roughly
> 2.17–3.67%.

Official OpenAI documentation currently categorizes `gpt-oss-20b` as an open-weight model, not
as part of its frontier-model family. The report should not call it a "2026 frontier model."
Current catalog: [OpenAI model documentation](https://developers.openai.com/api/docs/models).

No hosted frontier-model results are committed under `Tests/`. The project currently proves
that the runner can target several providers and contains one modern local-model result; it
does not yet contain a modern frontier-model experiment.

### 6. Registry time changes the meaning of “hallucination”

The January 10, 2024 list is correct for historical replication. It is not sufficient as the
only ground truth for a 2026 security measurement.

Checking all 59 unique gpt-oss names flagged by the frozen list against PyPI on 2026-08-12
found two currently registered names, each appearing once:

- `python-design-patterns`, released after the frozen snapshot; and
- `pyjpeg`, first released in 2026.

Simply reclassifying those two occurrences changes 89/3,071 (2.90%) to 87/3,071
(**2.83%**). The numerical impact is small in this run, so the broad gpt-oss result is robust
to ordinary registry staleness. The semantics remain important: a name registered after a
model could have learned it may be a new legitimate dependency, while a name registered after
it was first hallucinated could represent realization of the slopsquatting risk. A current
registry lookup alone cannot distinguish those cases.

Sources: [python-design-patterns on PyPI](https://pypi.org/project/python-design-patterns/),
[pyjpeg on PyPI](https://pypi.org/project/pyjpeg/).

### 7. The Levenshtein analysis is exploratory, not a replication

The "packages validly recommended by this run" reference set is selected after observing the
run and is not a stable definition of popularity. Its size and composition vary with model,
sample, cap, parser, and random generation. A smaller reference set mechanically increases
nearest-neighbor distances, so proximity to the paper's 13.4% is not independent validation.

There is also an upstream inconsistency: `Plots/Data/figure_9.csv` sums to 76,395 observations,
whereas the paper's prose uses 76,489. The plot's counts at distances 0, 1, and 2 sum to 10,263,
even though the prose calls that numerator distances 1 or 2. These discrepancies should be
documented rather than silently reconciled.

For the next iteration, choose the comparison universe before running models. A defensible
option is a dated top-K package list based on download counts, with sensitivity analyses over
several predeclared K values and the full registry.

## Secondary reproducibility issues

These do not overturn the stored rates, but they should be resolved before the next run:

- The 15-query reasoning-cap experiment and its CodeLlama control have no raw output artifacts
  or manifest in the repository, so the table cannot be independently reproduced.
- Ollama manifests record mutable tags such as `gpt-oss:20b`, but not the model digest,
  quantization, Modelfile/template, or Ollama version.
- Hosted response metadata is not retained, so a requested alias cannot be tied to the actual
  provider snapshot returned for each call.
- `responses_hitting_token_cap` is aggregated across code and package phases and excludes work
  recovered from pre-existing partial files. It cannot support the report's per-phase cap-hit
  denominators.
- `rapidfuzz` is required by `analyze_hallucinations.py` but absent from
  `requirements-api.txt`; the documented clean installation path cannot run that analysis.
- The released source prompts are not identical in every detail to the camera-ready paper's
  Appendix B figures. The report should distinguish "verbatim from the released artifact"
  from "verbatim from the paper."
- Applying the historical false-positive list to new models may silently suppress genuine new
  outputs. Parser noise filters should be rule-based, versioned, and validated against a
  manually labeled set rather than inherited indefinitely as a global name blocklist.

## Recommended design for the next iteration

### Track A: historical artifact replication

**Purpose:** determine whether the HTTP/Ollama transport reproduces the released artifact when
all observable choices are held as close as possible.

1. Select CodeLlama 7B and DeepSeek Coder 6.7B.
2. Pin and record complete model identities: source repository/revision, weight digest,
   quantization, chat template, serving runtime, and runtime version.
3. Use the released artifact's exact prompt construction, family parser, normalization,
   false-positive list, and 2048/64 caps.
4. Use one fixed prompt subset for all repeated runs. Do not change sample size when estimating
   generation variance.
5. Run at least three independent generation seeds per model. If the serving API cannot honor a
   seed, record that fact and treat provider randomness as part of the estimand.
6. Report prompt-cluster intervals and the distribution across repeated runs.
7. Score each run twice where useful: once with the historical family parser and once with a
   manually validated canonical parser. Treat parser sensitivity as a result.

**Acceptance criterion:** both models reproduce the historical ordering and broad magnitude
under the historical parser, and parser/manual-audit precision and recall are reported.

### Track B: modern-model benchmark

**Purpose:** compare models under a protocol suited to current reasoning and instruction-tuned
systems. These results should not be labeled direct reproductions of the 2024 scale.

1. Choose a preregistered model cohort with at least three hosted providers and two local
   open-weight models. As of the audit date, reasonable hosted candidates include current
   pinned releases from OpenAI, Anthropic, Google, and xAI. Official catalogs should be queried
   immediately before execution because aliases and availability change:
   [OpenAI](https://developers.openai.com/api/docs/models),
   [Anthropic](https://platform.claude.com/docs/en/about-claude/models/overview),
   [Google](https://ai.google.dev/gemini-api/docs/models), and
   [xAI](https://docs.x.ai/developers/grok-4-5).
2. Add a Gemini transport or explicitly narrow the provider claim; the current runner does not
   support Gemini.
3. Use the same prompt set, response budgets, reasoning-effort policy, and parser-validation
   rules for every model. When a provider cannot honor a setting, define the handling policy in
   advance rather than degrading silently during the run.
4. Use a package response budget high enough that cap hits are negligible. Report cap-hit rates
   separately for code, visible answer, and reasoning tokens where available.
5. Preserve raw provider responses and metadata, including returned model ID, finish reason,
   usage fields, and request parameters.
6. Score against both the frozen 2024 registry and a dated current registry snapshot.
7. Report multiple outcomes rather than one pooled rate:
   - package-occurrence hallucination rate;
   - prompt-level probability of at least one hallucination;
   - unique hallucinated names;
   - repeated/persistent hallucinations across seeds;
   - recommendations per prompt;
   - empty/refused/malformed response rate; and
   - package, stdlib-module, post-snapshot package, deleted package, and parser-noise categories.

### Controlled cap experiment

The cap question is worth pursuing, but it needs an isolation design.

Preferred design:

1. Pin a model, tokenizer, template, prompt set, and generation seed.
2. Generate one maximum-budget package response per prompt and retain the complete generated
   token sequence, including reasoning tokens if the runtime exposes them.
3. Produce counterfactual 64-, 128-, 256-, 512-, and 2048-token views by truncating that same
   sequence offline at model-token boundaries.
4. Run the package extractor on each view.
5. Measure hallucination rate by package position and the incremental rate of each newly exposed
   token band.
6. Repeat for at least three model families and both query heuristics.

If hidden reasoning prevents offline reconstruction, use paired online calls with an identical
per-prompt seed and verify that every short output is a prefix of its long counterpart. Exclude
or separately report non-prefix pairs.

This design can directly test whether later-listed packages are more likely to be hallucinated,
whether the effect varies with model verbosity, and whether a fixed response cap confounds
cross-model comparisons.

### Statistical analysis plan

1. Treat the prompt as the sampling cluster.
2. Stratify by the four source datasets and language.
3. Pair models and conditions by prompt wherever the same prompts are used.
4. Use a stratified prompt-cluster bootstrap for rate intervals and pairwise differences.
5. Use repeated model seeds to estimate generation variance separately from prompt-sampling
   variance.
6. Correct multiple model comparisons, preferably with Holm's procedure.
7. Publish effect sizes and uncertainty rather than ranking models on point estimates alone.
8. Predeclare primary and secondary outcomes, parser, cap policy, registry snapshots, exclusion
   rules, and minimum sample sizes before running the frontier cohort.

## Suggested implementation order

1. Fix and test parser selection; add parser sensitivity and manual-label tooling.
2. Expand manifests to immutable model/runtime identity and phase-level request statistics.
3. Add cluster-bootstrap and paired-comparison analysis code.
4. Re-run the two historical models on one common, repeated prompt subset.
5. Run the controlled cap experiment.
6. Freeze a modern registry snapshot and add package-category labeling.
7. Add any missing provider transport, especially Gemini if it remains in scope.
8. Execute the preregistered modern cohort.
9. Rewrite `REPLICATION.md` around the two-track distinction and newly supported conclusions.

## Claims disposition

| Current claim | Disposition |
|---|---|
| Baseline appendix and pooled metric are reconstructed correctly | **Keep** |
| CodeLlama approximately reproduces the historical magnitude | **Keep, with caveats** |
| DeepSeek 13.41% is a parser-faithful replication | **Withdraw; raw re-score is 12.69% with the historical parser** |
| The cap changes the measured rate substantially | **Retain as a hypothesis/association** |
| The discarded tail is 54.06% hallucinated | **Withdraw** |
| Models list valid packages first and hallucinations later | **Withdraw pending position-level experiment** |
| The cap explains the historical replication gap | **Withdraw pending controlled evidence** |
| Run-to-run variance is approximately ±3 pp | **Withdraw** |
| gpt-oss measures 2.90% under the stored protocol | **Keep** |
| gpt-oss is on the paper's scale or five times better than the best historical open model | **Withdraw** |
| Registry staleness materially threatens modern interpretation | **Keep; quantify with dual snapshots** |
| Levenshtein proximity depends strongly on the reference universe | **Keep as exploratory** |
| The paper's 13.4% Levenshtein result was replicated | **Relabel as unsupported/exploratory** |

## Questions for the next reviewer

The next review should challenge, in particular:

1. Is a two-track historical/modern design the right conceptual split, or should this become two
   separate reports?
2. What is the most defensible primary estimand: package-occurrence rate, prompt-level risk, or
   both as co-primary outcomes?
3. Should modern package queries remain natural-language comma lists for historical continuity,
   or use provider-independent constrained JSON with a separately maintained legacy analysis?
4. What model cohort gives the best scientific value per dollar while representing distinct
   providers, reasoning styles, and local deployment classes?
5. How many repeated seeds and prompts are needed to resolve differences of practical interest,
   such as 1, 2, or 5 percentage points?
6. What time-aware definition best separates a post-snapshot legitimate package from a
   hallucinated name later registered by an unrelated party?
7. Should the historical false-positive list be preserved only in Track A and replaced by a
   reproducible rule-based classifier in Track B?

## DeepSeek cap-sensitivity forensic addendum

This addendum follows a query- and response-level inspection prompted by the position analysis.
It supersedes the earlier suggestion that the DeepSeek cap result was merely unexplained after
the lack of a position gradient. The dominant mechanism is now identifiable.

### Finding: most of the dramatic effect is parser contamination after format failure

The cap contrast is almost entirely confined to Query 2, which asks for packages useful for
solving the original problem:

| Query | Cap 64 | Cap 2048 | Difference |
|---|---:|---:|---:|
| Query 1: packages required by generated code | 11.18% (165/1,476) | 13.96% (233/1,669) | +2.78 pp |
| Query 2: packages useful for the problem | 15.88% (221/1,392) | 33.47% (805/2,405) | **+17.59 pp** |

The longer Query 2 responses frequently stop obeying the requested comma-list grammar. Code
fences appear in 132/800 short responses and 338/800 long responses; numbered lists appear in
130/800 and 208/800, respectively. The evaluator still splits these responses on commas and
treats every surviving one-word fragment as a package candidate. As a result, function
arguments, string literals, hostnames, field names, numeric values, and fragments of prose can
be scored as hallucinated packages.

This is not a small edge case:

- Long Query 2 responses containing a code fence contribute 448 hallucinations among 599
  extracted candidates, a 74.79% apparent rate. Responses without a code fence score 19.77%.
- One numbered Docker response contributes 94 hallucinations. The unanchored normalization
  regex `\d\. ` turns `33. docker-container-run` into `3docker-container-run` and similarly
  corrupts multi-digit list items.
- One prose-plus-code response contributes 77 hallucinations because real names such as
  `"kafka-python"` and `"openpyxl"` retain quotation marks under the generic parser.
- Those two responses alone contribute 171/805, or 21.2%, of all reported long-Query-2
  hallucinations.

As a diagnostic sensitivity analysis, exclude responses with an obvious code fence or a
numbered-list marker while otherwise retaining the stored generic-parser classifications:

| Query 2 subset | Cap 64 | Cap 2048 |
|---|---:|---:|
| All responses | 15.88% (221/1,392) | 33.47% (805/2,405) |
| No code fence or numbered-list marker | **15.09% (195/1,292)** | **14.03% (216/1,540)** |

This clean-subset comparison is diagnostic, not a replacement headline estimate: format
compliance is itself affected by the cap, so conditioning on it can introduce selection bias.
It nevertheless demonstrates that the claimed cap sensitivity is not robust to separating
malformed responses from package-list responses. The main cap effect is that a larger budget
lets DeepSeek continue into verbose explanations, numbered inventories, and code; the generic
parser then mistakes the new syntax for package names.

The flat position curve does not contradict this explanation. The current positional analyzer
uses the same comma splitting and one-word filter, so a "position" inside a code block may be a
function argument rather than a package. Format contamination occurs throughout a response,
including the first extracted slot, and therefore need not produce a valid-first gradient.
Position analysis should be restricted to grammar-valid package lists and reported separately
for Query 1 and Query 2.

### The two cap runs are not a causal comparison

The historical pair still has 730/1,600 responses that diverge before the short response ends.
The package temperature is 0.01 rather than greedy, no inference seed was sent to Ollama, two
workers were used, and the calls were executed hours apart. Accordingly, the first-position
jump in long Query 2 cannot be attributed to `num_predict` alone.

A targeted 12-prompt probe used the same prompt, model, explicit seed, and sampling settings
for paired 64- and 2048-token calls. Eleven short calls hit the cap; only two were exact
prefixes of their long partner and nine diverged. On a repeated single-prompt test, temperature
0.01 produced one warm/cache-state divergence and then stable prefixes, while temperature 0
produced identical short replicates that were prefixes of the long response. This small,
purposively selected probe is not an effect estimate. It shows that seed alone is insufficient
to guarantee paired trajectories in this Ollama configuration and that a greedy, single-worker
prefix audit is required before treating online calls as counterfactual caps.

### Exact model identity and what “newer DeepSeek” should mean

The local run is not a modern DeepSeek model. It used:

- `deepseek-coder:6.7b-instruct`;
- Ollama digest
  `ce298d984115b93bb1b191b47fee6b39e4fbd5f18e651c02f9fa74e0edcd13`;
- a 7B GGUF quantized at Q4_0, approximately 3.8 GB;
- a 16,384-token context configuration; and
- Ollama's `### Instruction` / `### Response` template.

This is the original DeepSeek Coder generation, not the newer coder-specific release. Keep it
in Track A for historical continuity, but add a newer model rather than silently replacing it:

1. **Local DeepSeek extension:** `DeepSeek-Coder-V2-Lite-Instruct` (16B total, 2.4B active).
   The official release reports 128K context; Ollama's current `deepseek-coder-v2:16b` artifact
   is about 8.9 GB. Pin its full digest and quantization. This is the cleanest local successor
   to the 6.7B coder model.
2. **Current hosted DeepSeek:** use `deepseek-v4-flash` in non-thinking mode for a current
   DeepSeek frontier cell, optionally adding `deepseek-v4-pro`. DeepSeek's official April 2026
   changelog says V4 replaced the legacy `deepseek-chat`/`deepseek-reasoner` aliases, which were
   scheduled for retirement on July 24, 2026. Pin the returned model identity and run date.
3. **Do not use `deepseek-r1:latest` as the primary successor.** Local R1 tags are reasoning
   distillations based on Qwen or Llama checkpoints, and a 64-token budget can be consumed by
   reasoning before a package list appears. If included, place it in a separate reasoning-model
   stratum with an adequate budget and separately recorded reasoning and visible-output tokens.

Official references:
[DeepSeek-Coder-V2 release](https://github.com/deepseek-ai/DeepSeek-Coder-V2),
[DeepSeek-Coder-V2-Lite-Instruct model card](https://huggingface.co/deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct),
[Ollama DeepSeek-Coder-V2 tags](https://ollama.com/library/deepseek-coder-v2/tags), and
[DeepSeek API changelog](https://api-docs.deepseek.com/updates/).

### Required DeepSeek follow-up

The next DeepSeek experiment should be a compact diagnostic before another full 800-prompt run:

1. Use 50-100 fixed prompts, stratified across all four datasets and both package queries.
2. Run the 6.7B historical model and Coder-V2 Lite 16B with one worker, temperature 0, explicit
   seed, pinned digest/template/runtime, and counterbalanced cap order.
3. For the cleanest cap estimand, generate one 2048-token trajectory and create 64/128/256/512
   views offline at exact tokenizer boundaries. Report head and incremental-band results.
4. Separately repeat online hard-cap calls at the paper's temperature across at least five
   seeds. Verify prefix identity; treat non-prefix pairs as repeated-generation observations,
   not truncated tails.
5. Replace permissive comma splitting with a grammar-aware parser. Strip only anchored list
   numbering and balanced wrappers; reject code/prose fragments. Unit-test at least
   `33. docker-container-run`, `"openpyxl"`, and `port=3306`.
6. Report malformed-response rate as an outcome, not as hallucinated package names. Publish
   package-occurrence, prompt-level, macro response-level, and outlier-robust rates.
7. Manually label a stratified sample containing compliant lists, numbered lists, prose, and
   code. Report parser precision and recall before using it for model comparisons.

**Forensic verdict:** there is no evidence here of provider or model tampering. There is strong
evidence of an evaluator interaction: a longer cap greatly increases DeepSeek's format drift,
and the generic parser converts that drift into false package candidates. A smaller genuine
model-quality or cap effect may remain, but the present runs cannot identify it causally.

## Bottom line

The project has a credible base: the historical arithmetic is correct, the provider abstraction
is useful, raw artifacts are sufficiently rich to uncover important methodological sensitivity,
and the gpt-oss result warrants a better-controlled follow-up. The next iteration should not
spend its budget merely increasing sample size. Its first priority should be controlling parser,
cap, model identity, registry time, and prompt-level dependence. Once those are fixed, a modern
multi-provider run can produce conclusions substantially stronger than the present report.
