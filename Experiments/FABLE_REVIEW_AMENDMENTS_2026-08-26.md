# Fable review amendments — 2026-08-26

**Status:** post-analysis corrections and disclosure improvements. No model response, parser
classification, primary estimate, or preregistered comparison family changed.

This record responds to the second part of Fable's review of the Kimi K3 extension. It is a
prospective amendment to the paper materials and code, not an attempt to rewrite the historical
execution record locked at commit `8bcde486a3dbd1d1bffe45410465748bfc173f3e` (now `2850472…`
after the 2026-09-27 history rewrite; see
[HISTORY_REWRITE_2026-09-27.md](../HISTORY_REWRITE_2026-09-27.md)).

## Dispositions

| Review point | Disposition | Effect on conclusions |
|---|---|---|
| Mid-run pipeline edits | The results report, README, critical analysis, and paper outline now define “frozen” as the scientific design—not an end-to-end byte-frozen executable. The live process used an earlier collector; provenance/completion gates were expanded before scoring and did not alter outcomes. | Disclosure strengthened; no numerical change. |
| Holm p-values at the bootstrap floor | The K3 table now renders values at `8 × (1/50,000) = 0.000160` as `p ≤ 0.000160`. The JSON records the replicate count, family size, floor, and reporting rule. | No decision or effect-size change. |
| Uniform post-hoc K2.7/K3 bootstrap | The comparison now resamples paired prompts independently within each of the four 200-prompt datasets, matching the primary machinery. | Reported 95% intervals are unchanged at three decimals: prompt-risk difference 20.625 pp (16.500–24.750); flood-frequency difference 22.500 pp (19.000–26.000). |
| “Weak overlap” wording | The full contingency and marginal constraints are now reported: 22 joint floods versus 15.795 expected under independence, odds ratio 1.732; observed Jaccard 0.0827 versus maximum 0.2308 given the marginals. | Revised conclusion: shared prompt susceptibility exists, but does not alone determine each model's catastrophic tail. |
| Numerator concentration | The paper materials retain the primary occurrence estimand while co-reporting prompt risk, macro means, and post-hoc cap conditioning. | Fragility remains intrinsic and explicit; no replacement estimand is introduced. |
| Parser-noise/repetition alternative | The 54 K3 floods contain 8,010 unique normalized unregistered names; mean pairwise unregistered-name Jaccard is 0.0011, and no name appears in at least 25% of floods. | Strong evidence against one repeated catalog or a degenerate repetition loop; not proof that every extraction is semantically a package. |
| Cost label | The result row now says “analytic pay-go cost (smoke excluded).” README gives $16.271841 analytic and $16.341030 smoke-inclusive spend. | Label correction only. |
| Resume-sensitive cap gate | Batch stats now retain `truncated_total_rows` from the complete ordered sidecar in addition to `truncated_new_requests`. The scorer uses the total field for resumed phases and accepts the historical fallback only when `resumed == 0`. | Prevents false failure on future legitimate resumes; the historical K3 run was never resumed and is unchanged. |

## Paper wording to carry forward

The K3 occurrence-weighted estimate is unusually influential: 46 of 1,600 package responses
(2.875%) supply 81.023% of its unregistered-occurrence numerator. This is not hidden by a
cap-excluded “correction”; 33.30% remains primary, while 21.50% prompt risk, 4.18% response-macro
mean, and the 13.11% exact-cap-excluded diagnostic describe different operational questions.

The flood contingency supports a qualified mechanism statement. Prompt susceptibility is
positively associated across K2.7 and K3, but the model-specific transition into runaway
enumeration remains substantial. Once a K3 flood occurs, the near-zero overlap among its 8,010
unique unregistered names shows a diverse invented tail rather than a fixed memorized catalog.
The next causal test remains the preregistered within-prompt cap-by-bounded-list factorial.
