# Response to the Independent Audit

**Audit:** [codex-experiment.md](codex-experiment.md) (OpenAI Codex, 2026-08-12, repository
state through `3c021c0`)
**Response date:** 2026-08-12
**Method:** every checkable audit claim was re-verified against the raw run artifacts before
adoption — verification code is committed as [`verify_audit_findings.py`](verify_audit_findings.py),
and [REPLICATION.md](REPLICATION.md) v3 incorporates the outcome. Nothing was accepted on the
audit's authority alone, and nothing was rejected without a reproduction attempt.

## Summary

The audit is substantially correct. Its four material findings identify three genuine errors
in versions 1–2 of the replication report (an undisclosed parser mismatch, an invalid causal
decomposition, and a variance claim confounded by nested samples) and one framing
inconsistency (cross-protocol comparison of gpt-oss to the paper's scale). All four are
accepted and REPLICATION.md v3 reflects them. One of the audit's central re-computations
could not be reproduced through the repository's own code path — a discrepancy that
*strengthens* the audit's underlying point while superseding its specific figures — and two
of its withdrawal recommendations are amended in light of new measurements it prompted.

## Disposition of the four material findings

### 1. DeepSeek scored with the wrong parser — **accepted, verified**

Confirmed: both DeepSeek manifests record the generic parser (`auto` → `(False, False, "")`),
while `get_pre_post_info()` routes DeepSeek models on Python through `(True, True,
"DeepSeek")`. Versions 1–2 presented the result as a faithful replication without disclosing
this; that was an error. DeepSeek is reclassified in v3 §5.2 as a parser-sensitivity finding,
not a replication.

**Amendment — the audit's re-scored figures did not reproduce.** Running the repository's own
`detect_packages` with the DeepSeek overrides on the same stored responses gives **12.69%**
(cap 64) and **20.76%** (cap 2048), not the audit's 50.78% / 51.23%. The likely cause: the
DeepSeek pre-parser's regexes match *escaped* newline sequences, so its output depends on
whether the text carries literal `\n` or real newlines at parse time — a serialization detail
on which implementations of "the original parser" legitimately differ. Two defensible
implementations disagreeing by 4× on identical bytes is stronger evidence for the audit's own
conclusion (parser choice is a large, uncontrolled variable) than either figure. Consequence
worth noting: under the repo-code family parser the cap effect persists (+8.07 pp); under the
audit's implementation it nearly vanishes. Parser validation against manually labeled
responses must precede everything else, exactly as the audit recommends.

### 2. The cap experiment does not measure a literal truncated tail — **accepted, verified, remeasured**

The audit's pair classification reproduced exactly: 628 identical / 242 strict-prefix / 730
divergent of 1,600. The v2 "discarded tail is 54.06% hallucinated" arithmetic is withdrawn.

**Amendment — the mechanism survives on valid measurements.** Two analyses the audit's
critique prompted, both committed:

- On the 43 pairs where the long response's parsed list cleanly extends the short one's, the
  head runs 4.98% hallucinated and the literal tail **38.78%** (small n; indicative).
- Within single responses (no pairing), CodeLlama's rate rises monotonically from 21.1% at
  position 1 to ~36% at position 5+ (`analyze_hallucinations.py`); DeepSeek is flat under
  generic parsing, where comma-position is a poor proxy for recommendation order.

So "models name well-known packages first" is supported as a qualitative mechanism for at
least CodeLlama, while the audit is right that the v2 effect decomposition was not measured.
The paired cap association itself (+11.5 pp generic / +8.1 pp repo-family parser) stands, and
the audit's own paired bootstrap (+7 to +17 pp) corroborates it. The audit's offline-truncation
design is the correct definitive test; note it requires a runtime that exposes token
sequences, which Ollama's non-streaming API does not.

### 3. The ±3 pp variance claim — **accepted, verified, withdrawn**

Confirmed the n=100 prompt subsets are nested in the n=400 subsets for all four datasets
(same seed, larger draw — the reproducibility choice created the confound). The audit's
partition reproduced to the digit: repeated prompts regenerated at 26.01% (385/1,480) versus
26.43% in the small run; added prompts at 23.17% (1,107/4,778). The aggregate shift was
prompt composition, not regeneration noise. v3 §5.5 replaces the rule with prompt-cluster
intervals; generation variance is explicitly labeled unmeasured.

### 4. gpt-oss framing — **accepted**

"On the paper's scale" and the "five times better" ratio were internally inconsistent with
our own §7 and are removed. v3 §5.6 reports 2.90% (cluster CI [2.18, 3.64]) under the
modernized protocol, with the paper's range given for orientation only and no ranking claims.
One correction of record: REPLICATION.md never called gpt-oss a "frontier" model — that
phrasing appears in the session transcript, not the report, which says "open-weight"
throughout. The audit's underlying point (no hosted frontier results exist under `Tests/`)
is accurate.

## Other audit findings

| Audit item | Disposition |
|---|---|
| Baseline transcription and pooled metric correct | Agreed (mutual verification). |
| CodeLlama = useful approximate replication, low bias | Agreed; now the report's §5.1 framing. |
| Package-binomial CIs understate uncertainty | Accepted. `compare_to_paper.py` now computes stratified prompt-cluster bootstraps by default; our intervals match the audit's within 0.2 pp. |
| Registry staleness | Accepted and verified live: `python-design-patterns` (first upload 2024-10-18) and `pyjpeg` (first upload 2026-06-17) exist on PyPI; gpt-oss adjusts 2.90% → 2.83%. The audit's distinction between a legitimate post-snapshot package and a realized slopsquat is incorporated — `pyjpeg`'s upload postdates the model's release by ~10 months. |
| Levenshtein analysis exploratory; reference set post-hoc | Accepted; §5.7 relabeled, "replicated" claim withdrawn, reference-set sensitivity retained as the finding. `figure_9.csv` discrepancies documented in `Baselines/README.md`. |
| Cap-experiment artifacts missing | Fixed. `cap_experiment.py` is committed and was re-run: summary with input SHA-256, model digests, and server version at `Experiments/cap_experiment_summary.json`; result reproduced (15/15 empty at cap 64, 0 packages). |
| Manifests lack immutable model identity | Fixed. Runs now record the Ollama digest, quantization details, and server version, plus the model id echoed in every response (`served_model_ids`). |
| Per-phase cap-hit counters | Fixed. Each phase's stats now carry `truncated_new_requests`, with resumed-row undercounting documented. |
| `rapidfuzz` missing from requirements | Fixed in `requirements-api.txt`. |
| Artifact prompts vs camera-ready Appendix B | Accepted; v3 §3 says "verbatim from the released artifact" and §6 carries the caveat. |
| Inherited false-positive list | Accepted as a threat (v3 §6); rule-based versioned filters deferred to the next iteration. |
| Gemini not supported | Accurate. Untested possibility: Gemini's OpenAI-compatible endpoint via the `openai_compatible` provider; a native transport or an explicit scope note is deferred to Track B. |

## Raw-artifact policy

The audit asks for raw outputs sufficient for independent reproduction. Raw model responses
contain hallucinated package names, which this repository — following the original study's
security rationale — does not publish. The compromise adopted: committed summaries carry
input hashes, line indices, model digests, and per-condition counts; raw responses are
written to `Tests/` (gitignored) and regenerate deterministically enough for audit purposes
from the committed scripts. An auditor with repository access and a GPU reproduces
everything; nothing sensitive ships. The maintainer can override this trade-off.

## On the audit's questions for the next reviewer

Brief positions, not commitments: the two-track split belongs in one report with two clearly
separated sections (shared metric, different comparability claims). Package-occurrence rate
and prompt-level risk should be co-primary — they answer different security questions.
Package queries should stay natural-language for Track A fidelity and be measured both ways
in Track B, since output format is itself part of the phenomenon being measured. The
historical false-positive list should be frozen into Track A and replaced in Track B.

## Remaining open items

Adopted in principle, not yet executed: manual labeling of response samples for parser
validation; the offline-truncation cap experiment with token capture; repeated fixed-prompt
seeds for generation variance; dual-registry scoring as a standard output; the preregistered
modern-model cohort. These are the audit's "recommended design for the next iteration," and
nothing in this response substitutes for running it.
