# Preregistration — Churilov bridge and Ollama Cloud extension

**Status: FROZEN 2026-08-14, before Qwen/Kimi response collection.** The maintainer
authorized the extension after reviewing the Churilov comparison. Campaign 4 remains frozen;
these cells and analyses are reported as a separately dated extension.

## Questions

1. How do Campaign 4's conclusions change when the same generated code is measured with
   Churilov's code-only extractor (`pip install` plus top-level imports)?
2. How much apparent cross-model overlap remains when a shared unregistered name must be
   emitted on the same prompt?
3. Where do the newest Qwen and Kimi cloud models fall under Campaign 4's modern protocol?

## Analysis A — frozen-output Churilov bridge

- Inputs: the six completed Campaign 4 Track B code outputs. No regeneration.
- Extractor: the public Churilov artifact's Python design—H1 `pip install` regex plus
  AST-first, tree-sitter-fallback top-level import extraction. Imports are deduplicated
  within a generation; H1 and import hits are not deduplicated against each other, matching
  the artifact's mention table.
- Exact bridge outcome: extracted mentions absent from the frozen 2024 PyPI list.
- Corrected bridge outcome: extracted mentions absent from both 2024 and 2026-08-12 PyPI
  snapshots and not a Python 3.11 standard-library name.
- Uncertainty: 50,000-replicate dataset-stratified prompt-cluster bootstrap interval.
- Coverage: prompts with at least one extracted reference, prompt risk, extraction-channel
  counts, and unique unregistered names.
- This is post-hoc relative to Campaign 4 and cannot be called a preregistered Campaign 4
  outcome.

## Analysis B — prompt-conditioned overlap

- Base set: dual-registry, non-stdlib unregistered recommendations accepted by Parser v2.
- Report ordinary unique-name Jaccard and aligned occurrence Jaccard over
  `(normalized name, dataset, prompt index)` tuples.
- For pairwise and all-model intersections, report how many shared names occur on at least
  one identical prompt across the relevant models.
- Do not publish the candidate names; counts and proportions are sufficient for the
  methodological result.

## Analysis C — new Ollama Cloud cells

Catalog and `/api/show` metadata were checked on 2026-08-14 before execution:

| Cell | Requested tag | Resolved architecture | Parameters | Context | Quantization |
|---|---|---:|---:|---:|---:|
| Qwen 3.5 Cloud | `qwen3.5:cloud` | `qwen3.5` | 397B | 262,144 | BF16 |
| Kimi K2.7 Code Cloud | `kimi-k2.7-code:cloud` | `kimi-k2` | 1.042T | 262,144 | INT4 |

Both cells use:

- the Campaign 4 fixed Python subset: 200 prompts from each of four datasets, seed 0;
- code cap 4,096 and package-query cap 2,048;
- code temperature 0.7, package temperature 0.01, top-k 20, top-p 0.9 where accepted;
- `think: false` so the measured response is the direct answer rather than a reasoning trace;
- Parser v2 and both registry snapshots;
- the prompt as the clustering and pairing unit;
- raw responses, served model IDs, `/api/show` metadata, cap hits, errors, and any rejected
  sampling parameters recorded in the manifest.

Primary outcomes are the same co-reported Track B outcomes: dual-registry non-stdlib
unregistered recommendation rate, prompt risk, malformed and empty response rates, package
volume, unique names, and tail concentration. The code-only bridge is secondary.

The two new cells are compared with each other and with the six frozen Campaign 4 cells by
paired prompt-cluster bootstrap. Holm correction is applied once across the 13 comparisons
that involve at least one new cell. No new multiplicity claim is made for the original 15
Campaign 4 comparisons.

## Execution gate

`run_ollama_cloud_extension.ps1 -Mode smoke` runs one prefix prompt per dataset solely to
verify access, output shape, reasoning control, and manifest identity. Smoke responses are
stored under separate names and never enter the analysis. Full collection begins only with
`-Mode full`; the runner is resumable.

An access or quota failure is an execution limitation, not an outcome. A model substitution
must be recorded here before any analytic responses are collected under the replacement.

## Amendments

1. **2026-08-19 (before full analytic collection) — Kimi K3 replaced with Kimi K2.7
   Code at maintainer direction.** The Kimi K3 smoke gate on 2026-08-14 returned HTTP 402
   before every attempted generation because the account had no extra-usage balance. It
   produced zero successful responses and never entered an analytic cell. The maintainer
   selected `kimi-k2.7-code:cloud`, the current coding-specific Kimi model, on 2026-08-19.
   A fresh `/api/show` probe resolved architecture `kimi-k2`, 1.042T parameters, 262,144
   context, INT4, provider modification timestamp `2026-06-12T00:00:00Z`. All prompts,
   settings, outcomes, inference, and the 13-comparison Holm family remain unchanged.

## Execution log

- **2026-08-14 smoke gate:** Qwen 3.5 Cloud completed 12/12 transport calls, served as
  `qwen3.5`, with `/api/show` metadata matching the frozen table and no cap hits or sampling
  adjustments. Kimi K3 resolved its metadata but every attempted call returned HTTP 402
  before generation because the account's extra-usage balance was empty. Kimi therefore has
  zero successful or billable responses and remains pending. Enabling billing or substituting
  another Kimi model requires maintainer action; the runner does neither automatically.
- **2026-08-19 replacement smoke gate:** Kimi K2.7 Code completed 12/12 transport calls,
  served as `kimi-k2.7-code`, with metadata matching Amendment 1 and no request errors or
  sampling adjustments. One `Stack_Overflow_All_Time` query-2 response hit the frozen
  2,048-token package cap. The cap and response are retained unchanged as an observed
  tail-format outcome; full collection proceeds under the preregistered settings.
- **2026-08-19 full-run launch:** The first wrapper launch stopped before generation because
  a clean PowerShell process resolved the base Conda interpreter, which lacked `pandas`.
  It created no analytic responses; its stdout and stderr are retained as
  `ollama_cloud_extension_run.log` and `ollama_cloud_extension_run.err.log`. The campaign was
  relaunched at 16:30 PDT as process 45208 with the explicitly pinned, smoke-tested interpreter
  `C:\Users\JacobAnderson\miniconda3\envs\trading\python.exe`; progress was verified from
  successful Qwen generations. Its live logs are `ollama_cloud_extension_run2.log` and
  `ollama_cloud_extension_run2.err.log`.
- **2026-08-19 completion:** Both cells completed 2,400/2,400 calls with zero request errors
  and no sampling adjustments. Qwen served as `qwen3.5`, used 731,235 prompt and 92,619
  completion tokens, and recorded one code-response cap hit and zero package-response cap
  hits. Kimi served as `kimi-k2.7-code`, used 1,026,611 prompt and 1,134,677 completion
  tokens, and recorded 10 code-response plus 323 package-response cap hits. All 12 raw phase
  files per model contain exactly 200 ordered rows and no error sidecars. The frozen scorer
  and Churilov bridge completed automatically.
- **2026-08-25 post-hoc diagnostic:** Kimi's cap and response-volume mechanism is quantified
  without altering the preregistered result in
  `Experiments/OLLAMA_CLOUD_EXTENSION_POST_ANALYSIS.md`. The first runner did not retain exact
  cap-hit response ids, so that artifact labels its longest-response exclusion as a proxy.
- **2026-08-25 bootstrap implementation audit:** Pairwise comparisons already used the frozen
  50,000 replicates, but `summarize_cell` inherited a 20,000-replicate default for cell-level
  cluster intervals while the result artifact labeled the analysis 50,000. The default was
  corrected to 50,000 and affected summaries regenerated. Point estimates and inferential
  decisions are unchanged; Qwen's interval moved from 2.06–3.55 to 2.07–3.54 and Kimi's from
  20.20–26.15 to 20.19–26.19. The Campaign 4 post-analysis metadata now separately records
  50,000 cell/pairwise replicates and the 20,000-replicate cap diagnostic.
