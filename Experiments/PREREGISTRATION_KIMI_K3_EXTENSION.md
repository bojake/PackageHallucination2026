# Preregistration — Kimi K3 mechanism and frontier extension

**Frozen:** 2026-08-25 before any successful Kimi K3 analytic response.

## Motivation

The preregistered Qwen 3.5 / Kimi K2.7 extension found a Kimi-specific response-volume
failure mode. Kimi K2.7 produced 323 package-response cap hits, including 315/800 Query 2
responses, and 106,980 parsed occurrences came from responses containing more than 25
packages. Its unregistered rate rose sharply at late list positions. This extension tests
whether that behavior persists in the successor Kimi architecture; it is not a repair or
replacement of the Kimi K2.7 cell.

## Model identity and price

- Requested tag: `kimi-k3:cloud`
- `/api/show` probe date: 2026-08-25
- Resolved architecture/family: `kimi-k3`
- Parameters: 2.812T
- Context: 1,048,576 tokens
- Quantization: MXFP4
- Provider modification timestamp: `2026-07-27T08:00:00-07:00`
- Identity snapshot: `Experiments/kimi_k3_api_show_2026-08-25.json`
- Ollama library price checked 2026-08-25: $3.00 / 1M input tokens and $15.00 / 1M
  output tokens. Source: <https://ollama.com/library/kimi-k3:cloud>

## Collection

- Python only.
- The Campaign 4 fixed subset: 200 prompts from each of four datasets, seed 0.
- 800 code generations, 800 Query 1 responses, and 800 Query 2 responses.
- Code response cap 4,096 tokens; package-query cap 2,048 tokens.
- Code temperature 0.7; package temperature 0.01; top-k 20; top-p 0.9.
- `think: false` so the measured content is the direct answer.
- Two workers; raw Ollama `/api/chat`; no OpenCode or agent wrapper.
- Parser v2, the frozen PyPI registry, the 2026-08-12 registry snapshot, and Python stdlib
  exclusions remain unchanged.
- Every response must have an ordered sidecar recording finish reason, cap status, served
  model id, prompt tokens, and completion tokens. Missing sidecar rows fail the scoring gate.

Smoke collection uses one prefix prompt from each dataset and is stored separately. It tests
access, response shape, identity, sidecar integrity, and budget accounting only. Smoke output
never enters analysis.

## Outcomes

The primary outcome is the combined dual-registry, non-stdlib unregistered recommendation
occurrence rate over Parser v2 list responses, co-reported with prompt risk, coverage,
malformed/empty rates, parsed package volume, and cap hits.

The following mechanism outcomes are prespecified secondary diagnostics because the Kimi K2.7
finding is known before this collection:

1. Query 1 and Query 2 rates and package volumes reported separately.
2. Package-position bins 1, 2, 3–5, 6–10, 11–25, 26–50, 51–100, and 101+.
3. Exact cap-hit versus non-cap-hit summaries using response sidecars.
4. Response package-count distribution and descriptive subsets at at most 10, at most 25,
   and more than 25 parsed packages.
5. Dataset-specific rates and prompt risk.

No candidate unregistered package names are published.

## Inference

Kimi K3 is compared with the six frozen Campaign 4 Track B cells and the two completed Ollama
Cloud extension cells. The eight combined-rate comparisons involving Kimi K3 form a new Holm
family. Dataset-stratified paired prompt-cluster bootstrap uses 50,000 replicates. Query- and
mechanism-specific results are descriptive with intervals where available; they do not create
additional multiplicity claims.

## Budget gate

The maintainer authorized an aggregate $100 pay-go inference budget. The Kimi K3 smoke has a
$0.50 run guard and the analytic run has a $94.50 guard, leaving at least $5 for in-flight
requests and accounting uncertainty. Cost is calculated from provider-reported input/output
tokens and the frozen prices above. The runner stops launching requests when its guard is
reached and preserves resumable partial output. No other paid model cell may be started until
the Kimi K3 actual cost is known and remaining budget is recorded.

## Execution log

- **2026-08-25 identity gate:** `/api/show` resolved the model metadata recorded above. No
  generation was performed by the identity probe.
- **2026-08-25 smoke gate:** The v2 smoke completed 12/12 calls with served id `kimi-k3`,
  no sampling adjustments, ordered metadata for every response, and estimated cost $0.069189.
  One `Stack_Overflow_All_Time` Query 2 response ended with exact finish reason `length` at
  2,048 completion tokens. This is retained as an observed output and does not change the
  frozen cap or prompts.
- **2026-08-25 analytic launch:** Full collection began at 17:26 PDT as process 84224 with
  stdout/stderr retained in `Experiments/kimi_k3_extension_run.log` and
  `Experiments/kimi_k3_extension_run.err.log`. Successful responses and ordered metadata were
  verified in the first phase before the run was left unattended. The analytic runner uses
  the $94.50 guard frozen above.
- **2026-08-25 pre-scoring integrity hardening:** While the first code phase was still
  collecting, and before any analytic responses were parsed or scored, the completion gate
  was expanded to enforce the frozen model/sampling/pricing configuration, exactly 200 final
  output rows and 200 ordered sidecar rows per phase, zero phase errors, all five required
  metadata fields, served id `kimi-k3`, cumulative token equality, and independently
  recomputed cost equality. This is a provenance check only; no outcome, prompt, cap, parser,
  or inferential rule changed. A fixture test verifies both acceptance and identity-drift
  rejection.
- **2026-08-25 artifact-retention hardening:** Because `Tests/` is intentionally git-ignored,
  the successful full-run path now rebuilds and verifies a content-addressed raw-artifact
  index after scoring. The index stores paths, byte sizes, non-empty row counts, and SHA-256
  digests but no response content or candidate names. This post-collection provenance step
  does not inspect or alter outcomes. The already-running process parsed the earlier runner,
  so its index will also be regenerated and verified manually at completion.
- **2026-08-25 first analytic phase gate:** `LLM_Recent` code finalized at 18:52 PDT with
  exactly 200 response rows, 200 ordered metadata rows, and 200 master rows. All five required
  metadata fields were present, the sole served id was `kimi-k3`, no response was blank, and
  finish reason agreed with exact cap status on every row. The phase recorded 14 cap hits,
  32,414 prompt tokens, 277,162 completion tokens, and $4.254672 token-derived spend. No
  package response was parsed or scored at this checkpoint.
- **2026-08-25 second analytic phase gate:** `LLM_All_Time` code finalized at 19:42 PDT with
  exactly 200 response, metadata, and master rows; ordered indices; no missing fields or blank
  outputs; sole served id `kimi-k3`; and complete finish/cap agreement. It recorded eight cap
  hits, 31,293 prompt tokens, 262,905 completion tokens, and $4.037454 spend. The two sealed
  code phases therefore total 400 responses, 22 cap hits, and $8.292126. No package response
  was parsed or scored at this checkpoint.
- **2026-08-25 third analytic phase gate:** `Stack_Overflow_Recent` code finalized at 19:49
  PDT with exactly 200 response, metadata, and master rows; ordered indices; no missing fields
  or blanks; sole served id `kimi-k3`; and complete finish/cap agreement. It recorded two cap
  hits, 173,155 prompt tokens, 64,509 completion tokens, and $1.487100 spend. The three sealed
  code phases total 600 responses, 24 cap hits, and $9.779226. No package response was parsed
  or scored at this checkpoint.
- **2026-08-25 fourth analytic phase gate:** `Stack_Overflow_All_Time` code finalized at
  19:56 PDT with exactly 200 response, metadata, and master rows; ordered indices; no missing
  fields or blanks; and sole served id `kimi-k3`. It recorded two cap hits, 76,749 prompt
  tokens, 44,534 completion tokens, and $0.898257 spend. All four sealed code phases therefore
  total 800 responses, 26 cap hits, 313,611 prompt tokens, 649,110 completion tokens, and
  $10.677483. No package response was parsed or scored at this checkpoint.
- **2026-08-25 first package-phase gate:** `LLM_Recent` Query 1 finalized with exactly 200
  response rows and 200 ordered metadata rows, no missing required metadata, and sole served
  id `kimi-k3`. It recorded no exact cap hits, 304,054 prompt tokens, 2,697 completion tokens,
  and $0.952617 spend. Only file shape, provenance, cap status, and budget were checked; no
  package response was parsed or scored.
- **2026-08-25 Query 1 gate:** All four Query 1 phases finalized with 800 response rows and
  800 ordered metadata rows, no missing required metadata, sole served id `kimi-k3`, and zero
  exact cap hits. They total 756,485 prompt tokens, 10,089 completion tokens, and $2.420790.
  The 1,600 sealed campaign calls therefore total $13.098273. Only operational integrity and
  budget were checked; package responses remain unparsed and unscored until campaign close.
- **2026-08-25 first Query 2 gate:** `LLM_Recent` Query 2 finalized with 200 response rows and
  200 ordered metadata rows, no missing required metadata, and sole served id `kimi-k3`. It
  recorded 12 exact cap hits, 39,014 prompt tokens, 38,731 completion tokens, and $0.698007.
  Sealed campaign spend is $13.796280. No package response was parsed or scored.
- **2026-08-25 campaign-close gate:** All four Query 2 phases and all 12 analytic phases
  finalized at 20:28 PDT. Query 2 recorded 46 exact cap hits, 340,011 prompt tokens, 143,569
  completion tokens, and $3.173568. The complete campaign contains 2,400 ordered response and
  metadata rows, zero errors or partial files, no request adjustments, sole served id
  `kimi-k3`, 72 total exact cap hits, 1,410,107 prompt tokens, 802,768 completion tokens, and
  $16.271841 token-derived analytic spend. Including the excluded smoke, pay-go spend was
  $16.341030 of the authorized $100.
- **2026-08-25 scoring gate:** The automated scorer and an independent rerun both passed the
  frozen configuration, identity, row-order, phase, token, cap, and cost checks. The primary
  occurrence-weighted estimate is 33.30% (95% prompt-cluster interval 27.22–38.81), with
  21.50% prompt risk. Query 1 is 1.76% and Query 2 is 34.97%. The 46 exact package cap hits
  supply 81.02% of all unregistered occurrences; excluding them is retained only as a
  post-hoc diagnostic (13.11%), not a replacement estimand.
- **2026-08-25 retention gate:** The content-addressed artifact index was rebuilt after the
  live process exited and independently verified all 93 indexed files across Qwen 3.5,
  Kimi K2.7, and Kimi K3. No response content or candidate name is stored in the index.
