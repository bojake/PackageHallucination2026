# Extension Notes — the API / Ollama runner

This document records how `run_test_api.py` and its supporting modules came to exist: what
was asked for, what was decided, what deviates from the paper, and what was actually
verified. It is kept in the repository so anyone reading results produced by this code can
see the reasoning behind it rather than reverse-engineering it from diffs.

**Date:** 2026-08-11
**Author:** written by Claude (Opus 5) running in Claude Code, directed by the repository
owner in an interactive session. Every design decision below was either specified by the
owner or is flagged as a judgment call made on their behalf.

The original experiment code (`run_test.py`, `generate_code.py`, `generate_package_names.py`,
`package_detection.py`, `custom_parse_*.py`, `aggregate_results.py`) is the work of the
paper's authors and is unchanged apart from the two-line addition noted below.

---

## 1. The request

> "Review this repository and suggest a new method where we can run the analysis against
> local models (ollama) and api models (openai/grok/claude). No harness work, just api
> calls and preserve their technique verbatim, just new modern models."

Followed by:

> "Fix that token cap and open it up to 30k so we don't have to do streaming support."

The motivation: `run_test.py` loads model weights locally with `transformers`, which limits
the study to models that fit on the machine running it. The paper's model list is from 2024.
Extending it to current models means calling them over HTTP.

## 2. What the original pipeline does

Three phases, all joined **by row position** — `aggregate_results` uses
`pd.concat(..., axis=1)`, so response *n* must be on line *n* of every intermediate file.
This is the single most important invariant in the codebase and everything below respects it.

1. **`generate_code.py`** — code for ~4,900 prompts × 4 datasets, `temperature=0.7`,
   `top_k=20`, `top_p=0.9`.
2. **`generate_package_names.py`** — two queries per sample at `temperature=0.01`: "which
   packages does this code need" over the model's own output, and "which packages would
   solve this problem" over the original prompt.
3. **`package_detection.py`** — a per-model-family regex parser, then normalisation, then
   set membership against the PyPI / npm master lists.

## 3. Design decisions

| Decision | Why |
|---|---|
| **New files alongside the originals, not edits to them** | `run_test.py` still reproduces the paper exactly. The API path is additive; if it is wrong, the published results are unaffected. |
| **Plain `requests`, no provider SDKs** | Three SDKs would be three dependency trees and three release cadences for what is one POST per provider. `requests` was already a dependency of `Mitigation/`. |
| **Ollama's native `/api/chat`, not its OpenAI-compatible endpoint** | The native endpoint accepts `top_k`; the compatibility shim does not. Local models are therefore the **highest-fidelity** path — all three of the paper's sampling parameters apply. |
| **Prompts copied verbatim, including their quirks** | Code generation folds the "system" instruction into the **user** turn with no separator and no `system` role. JavaScript runs say "Javascript" in the prompt. Both look like bugs; both are what the paper's models saw, so both are preserved. |
| **`--parser-style auto` maps to the paper's commercial-API parser** | `get_pre_post_info()` returns no parser for unknown model names, which crashes the JavaScript path. Modern instruction-tuned models produce the same clean comma-separated lists that GPT-4 / GPT-3.5 did in the paper, so they are routed through the parser the paper used for those models. |
| **Ordered, resumable batch execution** | A full run is ~59,000 requests per model per language. Losing a run to one rate-limit wall would be expensive; concurrency without ordering would silently corrupt the position-based join. |
| **A run manifest per experiment** | Provider APIs change and models are updated in place. Without a record of what was actually sent, results become uninterpretable within months. |

### The one change to the authors' code

`package_detection.detect_packages()` gained an optional `overrides=None` keyword argument
carrying a `(pre, post, style)` tuple. When `None` — the default, and what every original
call site passes — behaviour is bit-for-bit unchanged. The API runner uses it to select a
response parser explicitly instead of inferring one from the model name, which matters
because the name-matching in `get_pre_post_info()` would, for example, treat an Ollama model
named `deepseek-coder-v2` as the paper's quantised `DeepSeek_33B`.

## 4. Fidelity: what could not be preserved

**`top_k` cannot be sent to OpenAI or xAI.** It has no equivalent in those APIs. Ollama and
Anthropic accept all three sampling parameters; OpenAI and xAI accept `temperature` and
`top_p` only. This is a real difference from the paper's setup for those two providers and
is recorded in every run manifest under `request_adjustments`. `--strict-sampling` aborts
rather than proceeding.

**Response caps were deliberately raised** — 2048 → 30,000 for code generation and 64 →
30,000 for the package queries. The paper's caps predate reasoning models, which spend the
budget on hidden thinking tokens and then return empty content. An empty answer reads
downstream as "recommended no packages", producing a hallucination rate near zero that is a
measurement artifact rather than a result. 30,000 keeps a plain non-streaming HTTP request
viable: it is far below every current model's output ceiling (128k, or 64k on Haiku 4.5), so
no provider requires streaming to answer, and the request timeout was raised to 600 s to
match. The cap only binds where a model would otherwise have been truncated mid-answer.

Both are recorded per run in `run_manifest.json` under `deviations_from_paper`, and the
paper's exact caps are one flag away:

```bash
python run_test_api.py <model> --max-code-tokens 2048 --max-package-tokens 64
```

**Runs are not deterministic.** `temperature=0.7` sampling plus provider-side model updates
mean repeat runs differ. This was equally true of the original setup; the manifest records
the date and exact model id so a result can at least be situated in time.

## 5. Failure handling

Choices here affect the numbers, so they are stated explicitly:

- A request that exhausts its retries writes an **empty response** for that row, preserving
  the position-based join, and records the failure in `<file>.errors.json`. Re-running the
  same command retries exactly those rows. `--fail-on-error` aborts instead.
- Empty responses count as "no packages recommended", which *understates* the hallucination
  rate. This is why failures are written to disk and surfaced as a warning rather than
  silently absorbed.
- When a model rejects a parameter at request time, the runner reacts to the API's 400,
  fixes the request, retries, and records what it changed: dropping an unsupported
  `temperature`/`top_p`, renaming `max_tokens` to `max_completion_tokens`, or clamping a cap
  to the ceiling named in the error.

## 6. What was verified

All verification was performed against a **mock HTTP server** implementing the OpenAI,
Ollama and Anthropic response schemas — not against live providers. It exercises the
plumbing, not model behaviour, and no cost or rate-limit characteristics were measured.

- 22 automated checks covering: all three provider schemas; system-message placement for
  Anthropic; parameter degradation (drop, rename, clamp); `--strict-sampling`; output
  ordering under concurrency, including resume from a partially complete file; row alignment
  when requests fail; `provider:model` parsing with Ollama tags; and `--list-models`.
- Full end-to-end pipelines for **Python** and **JavaScript** at `--limit 5`, producing
  `FINAL_RESULTS.csv` and `PACKAGE_NAMES.csv` through the authors' unmodified detection code.
- A live 1,200-call run against Ollama reproducing one of the paper's own models (§8) — the
  only verification here that exercises a real model rather than a mock.
- `compare_to_paper.py` fed the paper's own CodeLlama 7B counts through the
  `FINAL_RESULTS.csv` layout, returning 26.12% with all three sub-rates matching Table 7.
- Staged execution (`--stage code` → `packages` → `detect`) with manifest merging.
- CLI error paths: unknown provider, missing API key, malformed `--extra-body`, invalid
  `--parser-style`.

**Not verified:** live API calls to OpenAI, xAI, Anthropic or a real Ollama server; any full
run; whether the `auto` parser is the right choice for any specific modern model. Spot-check
`PACKAGE_NAMES.csv` on a `--limit` run before trusting a full one — a parser mismatch shows
up as prose fragments counted as hallucinated packages.

## 7. Scoring against the paper

Added after the initial port, once the published paper (arXiv:2406.10279v3) was available.

**The metric.** §5.1 defines the hallucination rate as "a simple ratio of the number of
hallucinated packages to the total number of recommended packages", pooling all three
detection heuristics. Tables 7 and 8 (Appendix E) break each model down into LLM-generated
prompts, Stack Overflow prompts and `pip`/`npm install`, and for all 30 model×language rows
those three components sum exactly to the published total — confirming the metric is
additive over heuristics and datasets, with no weighting or per-query normalisation.

**The baseline.** `Baselines/paper_appendix_e.csv` transcribes both tables. Verified three
ways: every row's components reproduce its published percentage; the totals reproduce the
paper's headline figures (440,445 hallucinated of 2,235,642 packages = 19.7%); and the
per-language means come out at 15.87% / 21.38% against the paper's stated 15.8% / 21.3%.
Three cells damaged in the PDF text layer were reconstructed and independently confirmed —
see `Baselines/README.md`.

**Two inconsistencies found in `Plots/Data/`.** `figure_6.csv` matches Table 7 exactly, but
`figure_2.csv` disagrees with Tables 7 and 8 for every model (GPT-4 Turbo 3.35 % / 5.64 %
versus the appendix's 3.59 % / 4.00 %), and the paper's own text quotes the appendix values —
so `figure_2.csv` appears to predate the final revision. Separately, `figure_14.csv`'s
columns are the reverse of the axis labels in `generate_plots.py`. The appendix tables are
used as the baseline.

**Sampling.** `--sample N --seed S` was added because `--limit` takes a prefix and the Stack
Overflow datasets are ordered by popularity, which would bias any measured rate. Since the
unit of analysis is packages rather than prompts, a few hundred prompts per dataset still
produces thousands of packages.

## 8. Replication check

Comparing a current model against the paper's 2024 list only shows that models changed. To
check that this pipeline measures what the paper measured, one of the paper's own models was
re-run through it: **CodeLlama 7B**, available on Ollama, at the paper's exact settings
(`--max-code-tokens 2048 --max-package-tokens 64`, temperature 0.7 / 0.01, top-k 20,
top-p 0.9) on a random sample of 100 prompts per dataset.

The paper's parser for CodeLlama 7B on Python is the default path — `get_pre_post_info()`
returns `(False, False, "")` for that model name, so no family-specific pre/post processing
is applied — which is exactly what `--parser-style auto` does. The parsing is therefore
identical, not merely equivalent.

### Result

> **[REPLICATION.md](REPLICATION.md) is the authoritative write-up.** This section records the
> first result and how it was superseded, because the revision is itself a finding.

The first run — CodeLlama 7B, 100 prompts per dataset, 1,464 packages — measured **26.43%**
against the paper's 26.12%, a delta of +0.31 pp with the confidence interval containing the
published value. That looked like a clean replication.

It did not survive more data. Re-running the same model with the same settings and seed at 400
prompts per dataset gave **23.84%** (6,258 packages), 2.28 pp *below* the published figure and
with an interval excluding it. A second model, DeepSeek 6.7B, came in 3.20 pp low. Both
replications are biased low; the initial agreement was a small sample landing well.

Version 3 revised this account again after an independent audit (§10): the "discarded tail"
arithmetic behind the cap explanation was invalid (the paired responses are separate samples,
not truncations of one sequence), the "±3 pp run-to-run variance" rule conflated prompt
composition with regeneration noise, and the DeepSeek run had been scored with the generic
parser where the original pipeline selects a DeepSeek-specific one. The cap effect itself
survives (+8 to +11.5 pp paired shift depending on parser; tail measured at 38.8% vs 5.0% on
the pairs where a literal tail exists), but the authoritative statement of every result is
now REPLICATION.md v3, not this file.

### Known differences from the original setup

These bound how close a match is meaningful:

- **Quantization.** The paper used GPTQ 4-bit via HuggingFace `transformers`; Ollama serves
  a Q4_0 GGUF.
- **Chat template.** The paper called `tokenizer.apply_chat_template`; Ollama applies its own
  template for the model.
- **Model variant.** `codellama:7b-instruct` is the instruction-tuned variant, matching the
  paper's use of a chat template, but is not provably the same checkpoint.
- **Sampling.** `temperature=0.7` with no seed control; repeat runs differ.
- **Subset.** 100 prompts per dataset against the paper's ~4,800.

Reproduce it with:

```bash
python run_test_api.py ollama:codellama:7b-instruct --language Python --sample 100 --seed 0 --max-code-tokens 2048 --max-package-tokens 64
python compare_to_paper.py Tests/ollama_codellama_7b-instruct_Python
```

Sampling is not seed-controlled at the model, so the rate will differ from run to run; the
prompt subset is fixed by `--seed 0`.

## 9. Independent audit (2026-08-12)

OpenAI Codex audited the repository at commit `3c021c0` ([codex-experiment.md](codex-experiment.md)).
Its material findings — an undisclosed parser mismatch in the DeepSeek replication, an invalid
causal decomposition in the cap experiment, a variance claim confounded by nested prompt
samples, and inconsistent cross-protocol framing of the gpt-oss result — were each verified
against the raw artifacts ([verify_audit_findings.py](verify_audit_findings.py)) and accepted.
One audit re-computation did not reproduce through the repository's own code path (the
DeepSeek family-parser re-score: 12.69%/20.76% here vs 50.78%/51.23% in the audit), a
discrepancy that itself demonstrates the parser-sensitivity finding. Point-by-point
disposition: [AUDIT_RESPONSE.md](AUDIT_RESPONSE.md). Report: REPLICATION.md v3.

Changes landed with the response: prompt-cluster bootstrap intervals in `compare_to_paper.py`
(default on), positional-gradient analysis in `analyze_hallucinations.py`, the cap experiment
promoted to a committed script (`cap_experiment.py`) with provenance and digests, immutable
model identity in run manifests, per-phase truncation counters, and `rapidfuzz` in
`requirements-api.txt`.

## 10. Pre-existing issues noted during review

Found while reading the repository, **not fixed** — they predate this work and are the
authors' call:

- No `LICENSE` file, though the README badge and link both state MIT.
- `requirements.txt` is UTF-16 encoded and contains conda `file:///` paths, so
  `pip install -r requirements.txt` fails. `requirements-api.txt` covers the API path only.
- `run_test.py` has both generation phases commented out (lines 96–97), so following the
  README runs detection against files that do not exist yet.
- `Mitigation/run_model_SD.py` imports `webui_api_package_query_RAG_DG`, which is not in the
  repository; the file present is `webui_api_package_query_RAG_SD.py`.
- The README points at `Plots/reproduce_figures.py`; the file is `Plots/generate_plots.py`.
- `Mitigation/webui_api_package_query_combined.py:126` passes `verify=False` to `requests`.
- `Data/Javascript/npm_package_names.csv` ships zipped but detection expects the `.csv`; the
  unzip step is now documented in the README.
