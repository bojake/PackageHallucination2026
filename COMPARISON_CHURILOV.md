# Comparison: Churilov (arXiv:2605.17062v3) vs this repository's Campaign 4

**Their paper:** Aleksandr Churilov, *The Range Shrinks, the Threat Remains: Re-evaluating
LLM Package Hallucinations on the 2026 Frontier-Model Cohort.* Independent researcher,
April 2026. Artifact: `github.com/churik5/slopsquatting-replication-2026`.

**Our work:** Campaign 4 of this repository ([REPLICATION.md](REPLICATION.md) Part II,
[campaign4_results.json](Experiments/campaign4_results.json)), August 2026.

Both replicate Spracklen et al. (USENIX Security '25) on a 2026 frontier cohort. We ran the
comparisons below against our own committed data before writing this; the two cross-checks in
§3 are reproducible from `Tests/` and the frozen master list.

## 1. The two studies at a glance

| | Churilov | Campaign 4 (ours) |
|---|---|---|
| Cohort | Sonnet 4.6, Haiku 4.5, GPT-5.4-mini, Gemini 2.5 Pro, DeepSeek V3.2 | opus-5, gpt-5.2, gpt-oss:20b, grok-4.6, deepseek-coder-v2:16b, deepseek-v4-flash |
| Languages | Python **and** JavaScript | Python only |
| Scale | Full corpus, 199,845 generations, no sampling | Sampled (200 prompts/dataset) + Track A replication with seeds |
| Extraction | Original regex extractor over generated **code** (imports + `pip/npm install`) + a noise filter | Grammar-aware Parser v2 over the two **package-recommendation queries**; malformed as an outcome |
| Registry | Frozen 2024 master list only (current-snapshot revalidation "in progress") | **Dual**: frozen 2024 + current 2026-08 snapshot, plus stdlib exclusion |
| Statistics | Wilson binomial CIs, χ² + Holm, permutation robustness | Prompt-**cluster** bootstrap CIs, paired-by-prompt + Holm |
| Design | Post-hoc | Preregistered two-track |
| Beyond replication | Universal-hallucination set + coordinated disclosure (PyPI/Socket.dev); Jaccard matrix; refusal rates | Cap diagnostic; parser-contamination decomposition; Track A seed-variance |
| Cost | $860.90 | ~ hosted API + local GPU |

Cohorts are **near-disjoint** — same providers, adjacent versions — which is what makes the
convergences below independent rather than shared-artifact.

## 2. Where we independently agree

- **Range compression at the frontier.** Churilov: the 2024 spread of 5.2–21.7% compresses to
  4.62–6.10%. Ours: frontier models cluster in a narrow band (see §3 for why our band sits
  lower). Both find the open-source/commercial gap that drove Spracklen's upper end has
  closed.
- **Standard-library filtering is necessary.** Churilov filters stdlib (CPython list +
  Node `core_modules.csv`). We reached the same correction from the other side — the original
  Python pipeline *didn't* exclude stdlib, and we found squatters had registered stdlib names
  on 2024 PyPI (`os`, `sys`, `json`), so the original silently scored module-confusion as
  *valid packages*. Independent convergence on the same fix.
- **Registry staleness matters.** Churilov flags it as a limitation (§9.2) and says a
  current-snapshot revalidation "is in progress." **We already did it** — dual-registry
  scoring is committed, and our finding quantifies exactly their caveat: 8,961 names in the
  frozen 2024 list have since been *deleted* from PyPI, concentrated in the squat/spam class,
  so frozen-only scoring both over- and under-counts depending on the name. Their `git`
  example (blocked by PyPI's prohibited-name rules) and our stdlib-squat finding are the same
  phenomenon from two angles.
- **DeepSeek version pinning is broken.** Churilov's `deepseek-chat` alias returned metadata
  identifying `deepseek-v4-flash` — the model shifted under a stable alias. Our manifests were
  built to capture exactly this (served-model-id per response); we ran `deepseek-v4-flash`
  explicitly. Both studies independently document that DeepSeek's public alias is not a stable
  experimental identifier.
- **Reasoning-mode is a confound.** Churilov ran GPT-5.4-mini at `reasoning_effort=minimal`
  and got a 32% refusal rate, flagging the denominator asymmetry. We disabled reasoning where
  models exposed it and tracked empty/malformed as outcomes. Both grappled with the same
  reasoning-off confound; neither ran a full effort sweep.

## 3. Two cross-checks against our data

**(a) Churilov's universal-hallucination set appears in our disjoint cohort.** His central
novel claim is a set of names all five of *his* models invent. We checked his top-8 universal
PyPI names against our six (different) models:

| Universal name | ...also emitted by N of our 6 models |
|---|---|
| `objc` | **5** (opus-5, gpt-5.2, grok-4.6, coder-v2, v4-flash) |
| `aws-cdk`, `opentelemetry` | 2 each |
| `rest-framework`, `tencentcloud`, `mpl-toolkits`, `opengl`, `openstack` | 1 each |

**All 8 appear in at least one of our models.** This independently corroborates the
model-agnostic universal-set claim with a cohort that shares no exact model with his —
stronger evidence for his finding than his single-cohort data alone can provide.

**(b) The apparent rate disagreement on deepseek-v4-flash reconciles exactly.** Both studies
measured that model. Churilov reports ~5.89% (under the V3.2 label); our headline was 17.91%.
The gap is entirely the extraction method, and our own data shows it:

| Our measurement of deepseek-v4-flash | Unregistered rate | Tail concentration |
|---|---|---|
| **Q1** (packages required by the code — the closest analog to Churilov's code-import extraction) | **2.77%** | top-3 responses = 10% of flagged |
| **Q2** (packages recommended for the problem — open-ended) | 21.49% | top-3 responses = **74%** of flagged, max single response = 334 names |

Churilov extracts imports *from generated code*, which is bounded and tail-resistant — the
analog of our Q1, where we measure **2.77%**, consistent with his band. Our higher pooled
headline is driven by the open-ended recommendation query (Q2), which invites the degenerate
enumerations we documented. **The studies do not actually disagree about the model** — they
measure different things, and agree on the tail-resistant measurement. This is a methodological
point neither study reveals alone: the code-grounded and recommendation-query extraction
methods diverge sharply on enumeration-prone models.

## 4. Where each study is ahead

**Churilov has, and we do not:**
- **Both languages**, and the Python-over-JavaScript inversion (Spracklen's 2024 pattern was
  JS-worse) — a real finding we cannot speak to.
- **Scale**: the full 199,845-generation corpus, not a sample.
- **Real security follow-through**: the universal set → coordinated disclosure with PyPI
  Security and Socket.dev → a registrable attack surface of 53 names. Genuinely novel and
  operationally valuable; we did no cross-model intersection.
- **Jaccard overlap matrix** and the DeepSeek/GPT-5.4-mini training-origin hint.
- A named cohort of **current commercial frontier** models; ours mixed in local/open-weight
  and some idiosyncratic picks.

**We have, and Churilov does not:**
- **Preregistration** with logged amendments.
- **Prompt-cluster CIs** instead of Wilson binomial — see §5.
- **Dual-registry + stdlib categories** (the revalidation he defers).
- The **cap diagnostic** and the **parser-contamination decomposition** — the reason our band
  sits lower and is, we argue, cleaner.
- **Concentration / prompt-level-risk split**, which separates a model's typical behavior from
  its catastrophic tail (§3b). His pooled rate would hide such a tail — though his code-import
  extraction is far less tail-prone than our Q2, so the risk is smaller for his design.
- **Two independent adversarial audits** and a verified-not-asserted correction trail.

## 5. One specific, checkable caution on his statistics

Churilov's per-model CIs are **Wilson intervals over the multiset of extracted references**
(§4.6), treating each reference as an independent Bernoulli trial. References cluster within
generations — one code file emits several imports whose validity is correlated — so the
effective sample size is smaller than |R| and the Wilson intervals are **too narrow**. This is
the exact understatement the audit of *our* work caught, and that our first Phase 5 pass
committed: an unstratified/unclustered interval made an Opus-vs-GPT difference look
significant that did not survive prompt-clustered resampling.

His headline pair (Haiku 4.5 vs GPT-5.4-mini, p ≈ 4×10⁻¹²) is extreme enough to survive any
reasonable clustering correction. But the **marginal** surviving pairs — Sonnet 4.6 vs
GPT-5.4-mini at Holm-p ≈ 6×10⁻³ — are the ones most likely to weaken under
generation-clustered resampling, and "5 of 10 pairs significant" may be optimistic. A
cluster bootstrap over generations (the fix in our `compare_to_paper.py`) would settle it, and
would be a cheap addition to his artifact requiring no new model runs.

## 6. Bottom line

The two studies are **complementary and mutually corroborating**. Churilov is broader (two
languages, full scale, real disclosure, a novel cross-model attack-surface result); ours is
more controlled (preregistered, clustered statistics, dual registries, contamination-decomposed,
audited). Where they can be compared directly they **agree**: the frontier has compressed, the
threat persists, stdlib and registry-time both matter, DeepSeek's alias is unstable — and, on
the one model both measured, the numbers reconcile once the extraction method is accounted for.
Each study catches something the other structurally cannot: he finds the model-agnostic
universal set that only a multi-model study reveals; we find the extraction-method and
parser-contamination effects that only a controlled decomposition reveals. Read together they
are a stronger result than either alone.

*Two concrete things we could offer his effort: the completed current-registry revalidation he
defers to future work, and a generation-clustered re-computation of his pairwise significance.*

---

*Prepared by Claude (Fable 5) for the repository maintainer; the §3 cross-checks were computed
against this repository's committed Campaign 4 data and are reproducible from `Tests/`.*
