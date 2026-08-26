# Experiment completion audit

**Audit date:** 2026-08-25
**Status:** complete; all scientific and repository gates passed.

This checklist ties each requested outcome to authoritative evidence. A checked item is
complete only where the cited artifact or verifier establishes the full requirement.

## Completed requirements

- [x] **Sign the Parser v2 validation sample.** All 200 records in
  `Tests/parser_v2_labeling/sample.jsonl` have `maintainer_verdict: "ok"`; none are missing or
  corrected. The four parser/draft status disagreements are therefore intentional validated
  errors rather than unresolved annotations. Evidence: the signed JSONL and
  `Tests/parser_v2_labeling/README.md`.
- [x] **Preserve the original review.** The maintainer-facing assessment remains in
  `codex-experiment.md`; later work extends rather than rewrites its conclusions.
- [x] **Complete the Qwen 3.5 and Kimi K2.7 cloud extension.** Both manifests contain 12
  phases, 2,400 calls, 2,400 saved items, zero phase errors, no request adjustments, and a
  single served identity across all calls. Qwen recorded one code cap and no package caps;
  Kimi recorded 333 total caps, 323 in package responses. Evidence:
  `Tests/trackC_ollama_qwen3-5-cloud_Python/run_manifest.json`,
  `Tests/trackC_ollama_kimi-k2-7-code-cloud_Python/run_manifest.json`, and
  `Experiments/ollama_cloud_extension_results.json`.
- [x] **Content-address the git-ignored raw extension artifacts.** `Tests/` is intentionally
  excluded from Git, so `build_ollama_artifact_index.py` records SHA-256, byte size, and
  non-empty row count for every retained file in the two completed cloud runs. The generated
  index contains no response text or candidate names and can verify a separately archived raw
  bundle. `python build_ollama_artifact_index.py --verify` currently verifies all 93 indexed
  files across Qwen 3.5, Kimi K2.7, and Kimi K3. Evidence:
  `Experiments/ollama_cloud_artifact_index.json`.
- [x] **Correctly score the extension.** The separately preregistered results report Qwen at
  2.768% (95% prompt-cluster interval 2.067–3.543) and Kimi K2.7 at 23.102%
  (20.192–26.187). The 50,000-replicate cell and paired bootstrap labels were audited and
  corrected before paper use. Evidence: `Experiments/OLLAMA_CLOUD_EXTENSION_RESULTS.md`,
  `Experiments/ollama_cloud_extension_results.json`, and
  `Experiments/PREREGISTRATION_OLLAMA_CLOUD_EXTENSION.md`.
- [x] **Resolve the Kimi K2.7 / parser nuance.** Query, volume, position, cap-proxy, macro,
  and prompt-conditioned overlap analyses are reproducible in
  `post_ollama_extension_analysis.py`. Parser noise is measurable—26.935% malformed in the
  323 phase-matched cap proxies versus 11.668% elsewhere—but cannot explain away the result:
  236 proxies parse as lists and supply 104,420 occurrences, while a steep late-position
  gradient survives complete proxy exclusion in a small number of nonproxy floods. Evidence:
  `Experiments/OLLAMA_CLOUD_EXTENSION_POST_ANALYSIS.md` and
  `Experiments/ollama_cloud_extension_post_analysis.json`.
- [x] **Compare fairly with Churilov et al.** The code-import bridge now includes Qwen 3.5
  (6.51% dual-registry), Kimi K2.7 (7.38%), and Kimi K3 (8.37%). The nine-cell bridge overlaps
  Churilov's 5.49–7.27% Python band only at the lower end; the original six Campaign 4 cells
  remain 8.30–17.49%. This is partial cohort-sensitive convergence, not full reconciliation.
  Evidence: `COMPARISON_CHURILOV.md`, `Experiments/CHURILOV_BRIDGE_ANALYSIS.md`, and
  `Experiments/churilov_bridge_analysis.json`.
- [x] **Preserve provenance and enforce the pay-go guard.** The runner can retain ordered
  per-response finish reason, cap status, served identity, prompt/completion tokens, and exact
  cost; interrupted runs restore and deduplicate prior spend before launching new calls.
  Six focused tests cover response shape, ordered sidecars, price requirements, restored
  accounting, resume deduplication, and K3 identity-drift rejection. Evidence: `llm_api.py`,
  `api_batch.py`, `run_test_api.py`, `score_kimi_k3_extension.py`, and
  `test_api_response_metadata.py`.
- [x] **Preregister the justified successor cell before analysis.** Kimi K3 identity, frozen
  prompts/settings, primary and mechanism estimands, separate eight-comparison Holm family,
  exact metadata gate, and $94.50 analytic stop guard were recorded before analytic responses
  were parsed or scored. The 12-call smoke cost $0.069189 and is excluded from analysis.
  Evidence: `Experiments/PREREGISTRATION_KIMI_K3_EXTENSION.md` and
  `Experiments/kimi_k3_api_show_2026-08-25.json`.
- [x] **Prepare the paper structure and current figures.** The outline carries claims to make
  and avoid, methods, inferential families, K2.7 mechanism results, Churilov comparison,
  limitations, tables, figures, and artifact checklist. The Qwen/K2.7 position-volume figure
  has PNG/PDF outputs. Evidence: `PAPER_OUTLINE.md` and `Experiments/figures/`.
- [x] **Reject unjustified extra cells.** OpenCode Zen / DeepSeek produced unusable blank final
  content followed by a free-tier limit, so it was not promoted into the campaign and consumed
  none of the authorized pay-go budget. No second paid cell is being launched before K3's
  actual cost and scientific value are known. Evidence: `Experiments/ZEN_DEEPSEEK_FEASIBILITY.md`.
- [x] **Finish Kimi K3 collection.** All 12 response files and sidecars contain 200 ordered
  rows. The manifest records 2,400 calls, zero errors, no partials, one `kimi-k3` served id,
  no request adjustments, 72 exact cap hits, and $16.271841 analytic spend. Including smoke,
  the paid total is $16.341030 of the authorized $100. Evidence:
  `Tests/trackD_ollama_kimi-k3-cloud_Python/run_manifest.json` and the verified artifact index.
- [x] **Pass K3 scoring and inference.** The automated scorer and an independent rerun passed
  the strict configuration/provenance gate. K3 scores 33.30% (27.22–38.81), 21.50% prompt
  risk, and 4.18% response-macro mean. Query 1 is 1.76% and Query 2 is 34.97%; all eight
  separately adjusted paired comparisons are retained. Evidence:
  `Experiments/KIMI_K3_EXTENSION_RESULTS.md` and
  `Experiments/kimi_k3_extension_results.json`.
- [x] **Resolve the K2.7/K3 aggregation reversal.** The exact K3 cap decomposition and paired
  shared-prompt diagnostics show that K3 floods less often but has a more contaminated rare
  tail: 46 exact package cap hits supply 81.02% of its unregistered occurrences. Exact-cap-
  excluded K3 is 13.11% versus 13.18% for K2.7's proxy-excluded diagnostic, while the
  late-position gradient persists. Evidence: `post_kimi_k3_analysis.py`,
  `Experiments/KIMI_K2_7_VS_K3_POST_ANALYSIS.md`, and the mechanism figure.
- [x] **Integrate K3 without outcome relabeling.** Paper section 4.9, abstract/result preview,
  claims, limitations, README, audit addendum, and Slack draft now retain 33.30% as primary
  and label cap exclusion as post hoc conditioning. Prespecified and additional descriptive
  fields remain separate in the machine-readable result.
- [x] **Retrospectively lock the uncommitted campaign evidence.** The K3 preregistration was
  not committed before inference, so the repository does not claim cryptographic
  preregistration. `PROVENANCE_STAMP_2026-08-26.md/.json` instead hash the attested pre-outcome
  design core, local timeline evidence, every commit-candidate file, and the 93-file raw
  artifact index; they state that local mtimes and the retrospective digest are corroborating,
  not independent proof. The containing Git commit makes this exact state tamper-evident from
  the commit forward.

## Pending gates

- [x] **Run the final repository audit.** Six focused metadata/provenance tests pass; all
  modified analysis, runner, scoring, plotting, and bridge scripts compile; four principal
  JSON and five Markdown artifacts reload and are non-empty; the final mechanism figure was
  visually inspected; all 93 raw artifacts reverify; and source/document whitespace checks
  pass. Three trailing spaces emitted in retained raw run-log lines are deliberately preserved
  byte-for-byte and excluded from the source/document check.

## External communication

- [ ] **Post a meaningful update to Slack room “Da Boss,” if the surface becomes available.**
  The in-app browser denied Slack access and the host forbids requesting approval, so no post
  is claimed. `Experiments/SLACK_UPDATE_DRAFT.md` contains the final update. The maintainer's
  wording made Slack optional; browser-security policy forbids trying an alternate surface
  after the denial.

## Completion rule

Do not declare the project complete while any scientific or repository gate above remains
unchecked. Slack access is an external optional limitation and must be disclosed rather than
worked around or falsely reported as posted.
