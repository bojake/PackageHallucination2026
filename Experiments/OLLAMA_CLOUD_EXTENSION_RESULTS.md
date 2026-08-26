# Ollama Cloud extension results

**Status:** preregistered extension to frozen Campaign 4.

| Model | Unregistered recommendation rate (95% CI) | Prompt risk | Malformed | Empty | Top-3 share |
|---|---:|---:|---:|---:|---:|
| qwen3.5:cloud | 2.77% (2.07–3.54) | 7.88% | 13.25% | 0.00% | 13.0% |
| kimi-k2.7-code:cloud | 23.10% (20.19–26.19) | 43.00% | 14.75% | 0.00% | 4.6% |

Intervals are dataset-stratified prompt-cluster bootstrap intervals. Pairwise inference uses
the 13 comparisons involving Qwen 3.5 Cloud or Kimi K2.7 Code Cloud; Holm correction is isolated
from Campaign 4's original family. 10 comparisons survive the original
bootstrap-tail convention and 9 survive the recentered-null sensitivity.

These are extension cells, not retroactive members of the frozen Campaign 4 cohort. Model
identity, served aliases, sampling adjustments, token use, cap hits, and errors are retained
in the machine-readable artifact and run manifests.
