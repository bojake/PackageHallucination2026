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
| Kimi K3 Cloud | `kimi-k3:cloud` | `kimi-k3` | 2.812T | 1,048,576 | MXFP4 |

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

Kimi K3 currently requires an Ollama Pro or Max account and consumes extra usage credits.
An access or quota failure is an execution limitation, not an outcome, and must not be
replaced by a different Kimi version without an amendment recorded here first.

## Amendments

None.

## Execution log

- **2026-08-14 smoke gate:** Qwen 3.5 Cloud completed 12/12 transport calls, served as
  `qwen3.5`, with `/api/show` metadata matching the frozen table and no cap hits or sampling
  adjustments. Kimi K3 resolved its metadata but every attempted call returned HTTP 402
  before generation because the account's extra-usage balance was empty. Kimi therefore has
  zero successful or billable responses and remains pending. Enabling billing or substituting
  another Kimi model requires maintainer action; the runner does neither automatically.
