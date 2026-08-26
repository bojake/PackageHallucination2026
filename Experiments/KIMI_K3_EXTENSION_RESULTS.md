# Kimi K3 extension results

**Status:** complete preregistered extension.

| Outcome | Result |
|---|---:|
| Combined unregistered recommendation rate (95% CI) | 33.30% (27.22–38.81) |
| Prompt risk | 21.50% |
| List coverage / malformed / empty | 95.81% / 4.19% / 0.00% |
| Query 1 rate / parsed occurrences | 1.76% / 1,303 |
| Query 2 rate / parsed occurrences | 34.97% / 24,586 |
| Exact response cap hits (all phases) | 72 |
| Exact package-response cap hits | 46 |
| Exact package cap-hit rate / occurrences | 52.10% / 13,408 |
| Excluding exact package cap hits | 13.11% / 12,481 occurrences |
| Estimated pay-go cost | $16.27 |

All 2,400 responses passed the ordered metadata-sidecar gate. The machine-readable artifact
contains the prespecified position, response-volume, query, dataset, and exact cap diagnostics,
plus the eight-comparison Holm family involving Kimi K3. Additional catalog-reuse, query-overlap,
and quartile summaries are explicitly stored as descriptive rather than prespecified.

## Position profile

| Position | Q1 occurrences | Q1 rate | Q1 rate excluding exact caps | Q2 occurrences | Q2 rate | Q2 rate excluding exact caps |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 587 | 0.852% | 0.852% | 779 | 2.567% | 2.703% |
| 2 | 322 | 3.416% | 3.416% | 762 | 4.593% | 4.564% |
| 3-5 | 311 | 1.929% | 1.929% | 2,044 | 3.131% | 2.958% |
| 6-10 | 74 | 1.351% | 1.351% | 2,114 | 3.784% | 3.648% |
| 11-25 | 9 | 0.000% | 0.000% | 1,360 | 6.250% | 5.619% |
| 26-50 | 0 | n/a | n/a | 1,554 | 7.722% | 9.064% |
| 51-100 | 0 | n/a | n/a | 2,900 | 15.897% | 11.217% |
| 101+ | 0 | n/a | n/a | 13,073 | 59.152% | 36.745% |

## Paired comparisons

Differences are comparator minus Kimi K3 in percentage points. Each row uses all 800 shared
prompts. Both Holm columns adjust the separately frozen eight-comparison K3 family.

| Pair | Difference (pp) | 95% percentile CI | Holm bootstrap-tail p | Holm recentered-null p |
|---|---:|---:|---:|---:|
| claude-opus-5 vs kimi-k3:cloud | -31.985 | -37.403 to -25.930 | 0.000160 | 0.000160 |
| gpt-5.2-2025-12-11 vs kimi-k3:cloud | -31.417 | -36.964 to -25.323 | 0.000160 | 0.000160 |
| gpt-oss:20b vs kimi-k3:cloud | -31.147 | -36.652 to -25.064 | 0.000160 | 0.000160 |
| grok-4.6 vs kimi-k3:cloud | -25.082 | -34.682 to -13.286 | 0.000360 | 0.000180 |
| deepseek-coder-v2:16b vs kimi-k3:cloud | -23.000 | -28.676 to -16.700 | 0.000160 | 0.000160 |
| deepseek-v4-flash vs kimi-k3:cloud | -15.394 | -28.508 to -1.998 | 0.025200 | 0.020720 |
| qwen3.5:cloud vs kimi-k3:cloud | -30.532 | -36.110 to -24.350 | 0.000160 | 0.000160 |
| kimi-k2.7-code:cloud vs kimi-k3:cloud | -10.198 | -16.425 to -3.442 | 0.006800 | 0.004200 |
