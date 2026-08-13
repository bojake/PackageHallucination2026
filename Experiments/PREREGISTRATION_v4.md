# Preregistration — Campaign 4 (two-track)

**Status: FROZEN as of 2026-08-12 (maintainer sign-off below). Deviations are logged in the
Amendments section before analysis.**

Successor to the v1–v3.1 replication work ([REPLICATION.md](../REPLICATION.md)), implementing
the design recommended by the independent audit ([codex-experiment.md](../codex-experiment.md))
and accepted in [AUDIT_RESPONSE.md](../AUDIT_RESPONSE.md). Two tracks with different
comparability claims; shared metric; nothing in Track B is a reproduction of the 2024 scale.

## Shared, frozen decisions

- **Prompt set:** Python, all four datasets, `--sample 200 --seed 0` — one fixed subset used
  by every cell, seed, and phase. No cell changes sample size.
- **Model identity:** every run records Ollama digest, quantization, template source, and
  server version (automatic in manifests since `3d9be86`). Cloud cells additionally record
  the served model id from responses.
- **Parser v2 (gating item, built and validated before any scored run):** a grammar-aware
  list parser that (a) accepts only responses conforming to a comma-list grammar, with
  anchored numbered-list stripping and balanced-wrapper stripping; (b) classifies
  non-conforming responses as **malformed** — reported as an outcome, never scored as
  package names; (c) passes unit tests including `33. docker-container-run` → 
  `docker-container-run`, `"openpyxl"` → `openpyxl`, and `port=3306` → rejected.
  Validation: a stratified 200-response sample (compliant lists / numbered lists / prose /
  code, across models and queries), labels drafted by the assistant and **reviewed by the
  maintainer**, with parser precision and recall reported before any cross-model comparison.
  Legacy generic-parser scores are also published for continuity.
- **Registries:** frozen 2024-01-10 master list (primary for Track A) and a dated current
  PyPI snapshot fetched at campaign start (primary for Track B). Both reported for every
  Track B cell.
- **Statistics:** prompt-cluster bootstrap intervals (2,000 reps, stratified by dataset);
  cross-cell comparisons paired by prompt; Holm correction across Track B pairwise
  comparisons; point estimates never reported without intervals.
- **Outcomes, all cells:** package-occurrence rate; prompt-level P(≥1 hallucination); unique
  hallucinated names; packages per prompt; malformed-response rate; empty-response rate;
  cap-hit rate per phase; name categories (stdlib-module confusion / post-snapshot package /
  other) for hallucinated names.

## Phase 1 — Parser v2 + labeling

Build, test, label, freeze. Acceptance: unit tests pass; precision and recall on the labeled
sample reported; maintainer signs the labels.

## Phase 2 — Controlled cap diagnostic

**Question:** does truncation suppress genuine hallucinations once format drift is removed?

- Models: `deepseek-coder:6.7b-instruct` and `deepseek-coder-v2:16b` (probe: perfect list
  compliance, deterministic at temperature 0 with a seed).
- 100 prompts (25/dataset drawn from the frozen set), both package queries, over
  **counterbalanced caps {64, 128, 256, 512, 2048}**, temperature 0, `seed=7`, one worker.
- Pairing validity: verify short outputs are literal prefixes of long ones; non-prefix pairs
  reported separately as repeated-generation observations, never as truncated tails.
- Outcomes: rate by cap under parser v2; malformed rate by cap; position-band hallucination
  rates on grammar-valid responses, split by query.
- ~2,000 calls, est. 1–2 h on megatron.

## Phase 3 — Track A: historical artifact replication, powered properly

- Cells: `codellama:7b-instruct` and `deepseek-coder:6.7b-instruct`.
- Paper protocol exactly: caps 2048/64, temperature 0.7/0.01, top-k 20, top-p 0.9 — plus
  `seed ∈ {101, 102, 103}` (three independent generation repeats on the fixed prompt set),
  one worker.
- Scoring: family parser and generic parser (dual), plus parser v2 diagnostics
  (malformed rate); frozen registry.
- Acceptance criterion (audit's): both models reproduce the historical ordering and broad
  magnitude under the historical parser; parser sensitivity reported as a result.
- Est. 12–18 h on megatron; resumable, run in background.

## Phase 4 — Track B: modern-model benchmark

- Protocol: caps 4096/2048; paper sampling where the provider accepts it (drops recorded);
  `think: false` for hybrid-reasoning models via `--extra-body`; n=200/dataset (frozen set);
  scored against both registries with parser v2.
- Cells now runnable:
  | Cell | Spec | Note |
  |---|---|---|
  | gpt-oss:20b | `ollama:gpt-oss:20b` | re-scored under parser v2 (existing responses reusable) |
  | DeepSeek Coder V2 Lite | `ollama:deepseek-coder-v2:16b` | digest `63fb193b3a9b...` |
  | DeepSeek V4 Flash | `ollama:deepseek-v4-flash:cloud` + `{"think": false}` | probe: clean lists, 0 thinking chars; optional secondary cell with `think: true` at a large cap |
- Reserved slots pending API keys in `.env`: `openai:*`, `anthropic:*`, `xai:*` (one current
  pinned release each; ids chosen from provider catalogs at execution time and recorded).
- Est. 6–8 h for the three runnable cells.

## Phase 5 — Analysis and REPLICATION v4

Cluster intervals, paired deltas, category tables, parser precision/recall, malformed rates;
REPLICATION.md v4 written strictly from preregistered outcomes; anything exploratory labeled
as such.

## Sign-off

- Maintainer: __JWA__________  Date: ___8/12/2026_________

## Amendments

1. **2026-08-12 (pre-execution) — hosted cohort pinned from live catalogs, with per-cell
   config set by probe.** OpenAI: `gpt-5.2-2025-12-11` with `{"reasoning_effort": "none"}`
   (probe: `"minimal"` rejected; valid set is none/low/medium/high/xhigh; `max_tokens`
   auto-renamed). Anthropic: `claude-opus-5` with `{"thinking": {"type": "disabled"}}`
   (probe: `temperature`/`top_k`/`top_p` deprecated-rejected and dropped, recorded in
   manifests). xAI: `grok-4.6` (only `top_k` dropped). All three answered the 64-token probe
   correctly. The `deepseek-v4-flash:cloud` cell executes in the hosted parallel batch — its
   compute is Ollama cloud, not megatron's GPU.
2. **2026-08-12 (pre-execution) — label-review timing.** Generation phases run before label
   sign-off; "validated before any scored run" is interpreted as: no Phase 5 scoring is
   final until the maintainer signs the labeling sample. Any scores computed earlier are
   marked provisional.
3. **2026-08-12 (pre-execution) — current registry snapshot recorded.**
   `Data/Python/pypi_package_names_2026-08-12.csv`, 869,894 names (the frozen 2024-01-10
   list has 500,513 — a 74% larger namespace, so Track B dual-registry deltas are expected
   to be material).
4. **2026-08-13 (post-collection) — label review delegated.** The maintainer delegated the
   Parser v2 labeling-sample review to OpenAI Codex, which verified and signed all 200
   records (`maintainer_verdict: ok` throughout). The reviewer is a different AI system from
   the parser's author and label drafter; no human read all 200 records — recorded plainly
   in `parser_v2_validation.json`, which the maintainer's delegation makes final. Corrected
   recall decomposition and one new v2.1 candidate rule (cap-hit trailing items) recorded
   there. Phase 5 scoring is no longer provisional.
5. **2026-08-13 (post-analysis) — v4.1 correction pass, from the second independent
   review.** Accepted and applied: (a) one consistent primary metric everywhere, named
   the **unregistered-PyPI recommendation rate** (absent from both registries,
   non-stdlib) — prompt-level risk and concentration previously mixed frozen-registry
   absence into these outcomes; (b) paired bootstraps re-run **stratified by dataset** as
   frozen (the first pass pooled strata) at 50,000 replicates — the opus-5 vs gpt-5.2
   comparison does **not** reliably survive Holm correction (verified: raw p≈0.008,
   Holm≈0.06–0.07), so seven, not eight, pairwise comparisons are significant;
   (c) Track A acceptance evaluated under the **historical family parser**, where all
   three DeepSeek seed CIs exclude the published value (verified) — ordering and
   magnitude reproduce, exact replication does not; (d) missing preregistered outcomes
   added (unique names, packages per prompt, per-phase cap hits, Track A Parser-v2
   malformed rates, Phase 2 position bands, separate pip-install heuristic); (e) the
   pre-campaign gpt-oss cell ran at n=100/dataset, violating the frozen 200-prompt
   clause — an unlogged deviation, now replaced by a conforming n=200 rerun with
   identity capture; (f) stale "provisional" markers removed now that labels are signed;
   (g) parser-validation coverage limitation (sample predates hosted cells) disclosed in
   the results artifact.
6. **2026-08-12 (pre-execution) — cap-diagnostic code generation is deterministic.** Phase 2
   generates each model's code once at temperature 0 with `seed=7` (not the paper's 0.7),
   because the diagnostic conditions on *given* code and pairing requires determinism. This
   deviates from the paper's code-generation setting by design; Phase 2 is not a Track A
   cell.
