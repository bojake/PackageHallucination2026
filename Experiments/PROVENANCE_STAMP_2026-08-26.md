# Retrospective provenance stamp — 2026-08-26

**Status:** retrospective evidence stamp; **not** a cryptographic preregistration.

> **Note added 2026-09-27:** the repository history was rewritten after this stamp was made (see
> [HISTORY_REWRITE_2026-09-27.md](../HISTORY_REWRITE_2026-09-27.md)). Commit ids quoted below refer
> to the pre-rewrite history; `eac1434…` is now `a212e05…`. File-content hashes are unaffected.

The Kimi K3 preregistration, scorer, and outcomes were not committed before inference. No
post-run artifact can repair that historical fact. This stamp instead locks the evidence that
exists now, states the maintainer/operator attestation narrowly, and makes later modifications
detectable through the containing Git commit.

## Attested pre-outcome design core

The attested design core is the current Kimi K3 preregistration from its first byte through the
line immediately before `## Execution log`, normalized to LF. Its SHA-256 is:

`e36d1f78a536c8da5fc4d1df0f46578076b5511687424703a62908e4ef341930`

This digest is **retrospectively derived**. The maintainer and experiment operator attest that
the substantive core preceded outcome inspection, but the digest itself was created after the
run and is not independent proof of that claim.

## Reconstructable local timeline

| Event | Artifact | Local creation time (UTC) | Local mtime (UTC) | SHA-256 prefix |
|---|---|---:|---:|---|
| Model identity snapshot written before the preregistration file. | `Experiments/kimi_k3_api_show_2026-08-25.json` | 2026-08-26T00:13:39.865330+00:00 | 2026-08-26T00:13:39.866851+00:00 | `90da6c7b0a0a5ae5…` |
| Preregistration file created before analytic launch; later appended with execution results. | `Experiments/PREREGISTRATION_KIMI_K3_EXTENSION.md` | 2026-08-26T00:16:43.846458+00:00 | 2026-08-26T03:36:13.173975+00:00 | `24391757874299b9…` |
| Analytic runner log created at launch; final mtime includes post-run scorer output. | `Experiments/kimi_k3_extension_run.log` | 2026-08-26T00:26:16.738586+00:00 | 2026-08-26T03:28:12.554121+00:00 | `7a09a90e523c040b…` |
| Scorer last modified during code collection and before package-phase artifacts. | `score_kimi_k3_extension.py` | 2026-08-26T00:17:00.647118+00:00 | 2026-08-26T00:58:00.317081+00:00 | `957ab2e346109dd8…` |
| First code phase finalized. | `Tests/trackD_ollama_kimi-k3-cloud_Python/LLM_Recent_code.json` | 2026-08-26T01:52:32.141400+00:00 | 2026-08-26T01:52:32.146401+00:00 | `38eb8bf507096287…` |
| First package phase finalized. | `Tests/trackD_ollama_kimi-k3-cloud_Python/LLM_Recent_packages_1.json` | 2026-08-26T02:59:55.932169+00:00 | 2026-08-26T02:59:55.933168+00:00 | `d2cf92ddf0bb5ad7…` |
| Last package phase finalized. | `Tests/trackD_ollama_kimi-k3-cloud_Python/Stack_Overflow_All_Time_packages_2.json` | 2026-08-26T03:27:53.517095+00:00 | 2026-08-26T03:27:53.518606+00:00 | `caa5907b784c4540…` |
| Run manifest finalized after collection. | `Tests/trackD_ollama_kimi-k3-cloud_Python/run_manifest.json` | 2026-08-26T03:28:04.255131+00:00 | 2026-08-26T03:28:04.256130+00:00 | `633c45b40734d674…` |
| Scored result written after the run manifest. | `Experiments/kimi_k3_extension_results.json` | 2026-08-26T03:28:12.304767+00:00 | 2026-08-26T03:28:36.434268+00:00 | `29c6cce5c7095c24…` |

The chronology is consistent with pre-outcome specification: the preregistration file was
created before launch; the scorer predates package-phase finalization; the run manifest predates
the scored result. These are local filesystem timestamps and therefore corroborating evidence,
not a trusted timestamp authority. This stamp was generated on Windows, where the recorded
creation column comes from `st_ctime`; it should not be interpreted the same way on Unix.

## Content-addressed snapshot

- Parent commit before this snapshot: `eac1434964427ad114b548e5327e54301e619ada`
- Tracked pre-commit patch SHA-256: `bcdef6df71bfd8482ac3c30b523a90232c16580977f6d6ac2b1c66d3e18dd884`
- Commit-candidate files hashed (excluding the stamp outputs): 53
- Git-ignored raw artifacts covered by the separate index: 93
- Raw-artifact index SHA-256: `ff53dd0080f1db11311855bc2a9ada614edadbed124fa66835b6bf0284bb1dad`

The machine-readable companion contains the full SHA-256, byte size, and local mtime for every
commit-candidate file. Raw response content remains outside Git under the repository's release
policy; `Experiments/ollama_cloud_artifact_index.json` binds those 93 files by hash.

## Limitations and future gate

- This commit makes the current state tamper-evident only from the commit forward.
- A Git commit is content-addressed but its author timestamp is not an independent timestamp.
  Publishing the commit to the canonical remote supplies external history; a signed commit or
  trusted timestamp would add identity/time assurance.
- Future paid or analytic experiments must begin from a clean repository with the preregistration,
  scorer, runner, parser/version, registry digests, and baseline commit already committed. The
  run manifest should record that baseline commit and abort if the scientific inputs are dirty.
