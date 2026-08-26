# Kimi K2.7 versus Kimi K3 post-analysis

**Status:** complete post-hoc mechanism comparison. The prespecified K3 score remains primary;
its scientific design is attested as pre-outcome but was not committed before collection.

## Main finding

K3 is better on typical responses but worse on the occurrence-weighted headline because a
small catastrophic tail dominates its denominator. Its raw rate is 33.300%
versus K2.7's 23.102%. After excluding recorded K3 package cap hits
and the frozen K2.7 cap proxy, the rates nearly coincide: 13.108%
versus 13.177%. This conditioning is diagnostic, not causal.

| Diagnostic | Kimi K2.7 | Kimi K3 |
|---|---:|---:|
| Raw occurrence-weighted rate | 23.102% | 33.300% |
| Prompt risk | 43.000% | 21.500% |
| Response-macro mean | 8.357% | 4.179% |
| Package cap hits/proxies | 323 | 46 |
| Cap-hit/proxy-only rate | 23.808% | 52.096% |
| Cap-hit/proxy-excluded rate | 13.177% | 13.108% |
| Responses with at least 100 packages | 240 | 54 |

K3's 46 exact package cap hits are only 2.875% of package responses,
but supply 51.790% of parsed occurrences and
81.023% of all unregistered occurrences. K2.7's 323 proxy-marked
responses supply 93.364% of occurrences and
96.215% of unregistered occurrences. K2.7 floods often; K3 floods
far less often, but its rare cap-hit floods are much more contaminated (52.096%
versus 23.808%).

## Shared-prompt diagnostics

| Paired Query 2 measure (K2.7 minus K3, pp) | Difference (95% CI) |
|---|---:|
| Prompt risk | 20.625 (16.500 to 24.750) |
| Responses over 100 packages | 22.500 (19.000 to 26.000) |

For >100-package responses, the shared-prompt contingency is: both 22, K2.7 only
212, K3 only 32, neither 534. The 22
joint floods exceed the 15.795 expected under independence
(odds ratio 1.732), so there is shared prompt susceptibility. Prompt-set
Jaccard is 0.0827, against a maximum of
0.2308 given the unequal marginal flood rates. Prompt
difficulty therefore contributes, but cannot alone explain which prompts enter each model's
catastrophic tail.

The 54 K3 floods contain
8,010 unique normalized unregistered names. Their mean
pairwise unregistered-name Jaccard is only
0.0011, with no unregistered name appearing in at
least 25% of floods. This diverse tail is inconsistent with a repeated fixed catalog or a
degenerate parser/repetition loop, although it does not by itself validate every extracted name.

## Query 2 position rate after cap diagnostic exclusion

| Position | K2.7 proxy-excluded (%) | K3 exact-cap-excluded (%) |
|---|---:|---:|
| 1 | 4.867 | 2.703 |
| 2 | 5.593 | 4.564 |
| 3-5 | 5.079 | 2.958 |
| 6-10 | 5.412 | 3.648 |
| 11-25 | 6.711 | 5.619 |
| 26-50 | 22.029 | 9.064 |
| 51-100 | 36.935 | 11.217 |
| 101+ | 41.379 | 36.745 |

Both models retain a steep late-position gradient after the cap diagnostic. K3 is lower through
positions 26–100, but both become unreliable after position 100. The practical mechanism is
therefore two-stage: an occasional runaway enumeration creates a long tail, and package validity
then degrades sharply within that tail. A token cap determines which part is observed; it is not
the root cause by itself.

## Interpretation guardrails

- Preserve the prespecified raw K3 result as primary; do not replace it with cap-excluded rates.
- Report prompt risk and response-macro summaries beside the occurrence-weighted rate. They answer
  different deployment questions and reveal K3's better typical response behavior.
- Treat K2.7 cap membership as a proxy. Exact K3 metadata supports stronger claims only for K3.
- The paired intervals above resample prompts within each of the four 200-prompt dataset strata,
  matching the primary bootstrap machinery.
- The next experiment should vary the package token cap within model and prompt, and should add a
  bounded-list instruction arm. That factorial separates runaway enumeration from token-boundary
  truncation and tests a practical mitigation.
