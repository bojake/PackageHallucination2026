Package-hallucination update (2026-08-25): the Kimi K3 successor campaign is complete and
protocol-clean—2,400/2,400 calls, zero errors, one served model ID, exact finish/token metadata,
and $16.27 analytic spend ($16.34 including smoke) against the $100 authorization.

The result is a useful surprise. K3's primary occurrence-weighted unregistered-package rate is
33.30% (95% prompt-cluster interval 27.22–38.81), worse than K2.7's 23.10%. But K3 is better on
typical-response measures: 21.50% prompt risk versus 43.00%, 4.18% response-macro mean versus
8.36%, and only 54 Query 2 responses above 100 packages versus 234. The reversal comes from 46
rare capped package responses—2.9% of responses—that contribute 81.0% of K3's unregistered
occurrences at a 52.1% within-tail rate. After excluding exact K3 cap hits and K2.7's documented
cap proxy only as a post-hoc diagnostic, the rates converge almost exactly (13.11% vs 13.18%).

The mechanism now looks two-stage: occasional runaway enumeration creates a huge denominator,
then validity collapses late in the list. K3 floods far less often than K2.7, but its rare floods
are more contaminated. A paired shared-prompt analysis finds only 22 prompts flood in both models
(Jaccard 0.083), so prompt difficulty alone is not the explanation. The late-position gradient
also survives exact K3 cap exclusion, reaching 36.75% after position 100. The cap is an influential
observation boundary, not an established cause.

I kept the preregistered 33.30% result primary, labeled all cap-conditioning post hoc, built the
K2.7/K3 mechanism analysis and figure, updated the paper outline, and content-addressed/verified
all 93 retained cloud-run artifacts. I do not recommend another unconstrained model cell for this
paper. The next targeted experiment should be a within-prompt package-cap × bounded-list factorial
to separate runaway enumeration from truncation and test a practical mitigation.
