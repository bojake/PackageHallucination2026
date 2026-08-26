# Ollama Cloud extension post-analysis

**Status:** post-hoc diagnostic; the preregistered result remains unchanged.

## Main diagnostic

| Model | Query 1 rate | Q1 excluding cap proxy | Q1 parsed packages | Query 2 rate | Q2 parsed packages | Q2 excluding cap proxy | Package cap hits |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen3.5:cloud | 0.33% | 0.33% | 302 | 3.06% | 2,480 | 3.06% | 0 |
| kimi-k2.7-code:cloud | 21.82% | 3.77% | 3,887 | 23.15% | 107,955 | 15.92% | 323 |

Query 1 asks which packages are required by the model's generated code. Query 2 asks which
packages would be useful for the original problem. Kimi's two channels are not behaving like
replicate measurements: Query 1 produced 3,887 parsed
package occurrences, while Query 2 produced 107,955.
Qwen's Query 2 produced 2,480 occurrences.

Kimi recorded 323 package-response cap hits, of which
315
occurred in Query 2. The cap-proxy responses alone contain
104,420 parsed package occurrences at
23.81% unregistered; excluding the proxy changes the combined Kimi rate to
13.18%. Because the first runner retained cap counts only at phase level, this
is a longest-response proxy—not exact cap-hit identification.

Parser sensitivity is present but insufficient as a complete explanation. Among the 323
cap-proxy responses, 87 (26.93%)
are grammar-malformed, compared with 149 of
1,277 (11.67%)
outside the proxy, a 15.27-point difference.
The proxy contains 36.86% of all malformed
Kimi responses. At the same time, the parser accepts 236 proxy
responses containing 104,420 package occurrences. After
excluding every proxy response, Query 2 still rises from
4.87% at position 1 and
6.71% at positions 11–25 to
22.03% at 26–50,
36.94% at 51–100, and
41.38% after 100. The late clean-proxy bins
have only 16,
12, and
10 contributing responses respectively, so
they are mechanism evidence rather than stable population estimates.

Among Kimi responses containing at most 10 parsed packages, the combined unregistered rate is
4.95%; responses above 25 packages
account for 106,980
parsed occurrences at 23.93%.
The pooled 23.10% occurrence rate contrasts with an unweighted mean of
8.36% across non-empty parsed responses
and 11.78% across prompts with a denominator;
the corresponding response and prompt medians are
0.00% and
0.00%.

The 234 Kimi Query 2 responses above 100 packages have mean pairwise
package-set Jaccard 0.066;
39 normalized package names recur in at
least half of those floods. Their paired Query 1/Query 2 mean Jaccard is
0.005. This quantifies whether
the long answers resemble a reused catalog while avoiding publication of candidate names.

## Interpretation

- Qwen is operationally clean: one code cap hit and no package-response cap hits.
- Kimi K2.7's preregistered headline is a real property of the observed outputs, but it is
  dominated by Query 2's extreme list-generation behavior and cannot be interpreted as a
  simple model-quality ranking without the channel-specific results.
- The floods are not copies of one fixed catalog: their mean pairwise Jaccard is only
  0.066. They share a modest 39-name core but
  generate diverse prompt-conditioned tails, while almost never overlapping the paired
  Query 1 answer (mean Jaccard 0.005).
- Truncation can bias in both directions: grammar-malformed tails are excluded, while
  comma-complete truncated lists contribute hundreds of parsed occurrences. The proxy
  sensitivity quantifies influence but does not repair this missing per-response provenance.
- Parser noise therefore mediates Kimi's cap sensitivity, but does not explain it away: the
  proxy is enriched for malformed outputs, yet a steep late-position gradient survives its
  complete exclusion in a small number of nonproxy list floods.
- The defensible paper treatment is to report Query 1 and Query 2 separately, retain the
  preregistered combined result, and label Kimi Query 2 as an instruction-following/list-volume
  failure mode. A future Kimi cell must store finish reason and token usage for every response.

## Position profile

See the machine-readable artifact for occurrence-weighted rates in bins 1, 2, 3–5, 6–10,
11–25, 26–50, 51–100, and 101+, separately for both queries and after the cap proxy exclusion.
This distinguishes an early-list validity gradient from late-response degradation.

## Guardrails

- No raw response, parser decision, registry snapshot, or preregistered estimate was changed.
- The cap proxy is explicitly post-hoc and must not be described as exact.
- Occurrence rates must be co-reported with parsed package volume, list coverage, prompt risk,
  and response-cap counts.
