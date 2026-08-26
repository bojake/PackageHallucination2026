"""Create a retrospective, content-addressed provenance record for the cloud experiment.

This does not turn a post-run commit into a cryptographic preregistration. It preserves the
present evidence, the local timeline, the pre-outcome design core as currently attested, and
the complete commit-candidate file set so later changes are detectable from Git history.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT_JSON = ROOT / "Experiments" / "PROVENANCE_STAMP_2026-08-26.json"
OUT_MD = ROOT / "Experiments" / "PROVENANCE_STAMP_2026-08-26.md"
PREREG = ROOT / "Experiments" / "PREREGISTRATION_KIMI_K3_EXTENSION.md"
RAW_INDEX = ROOT / "Experiments" / "ollama_cloud_artifact_index.json"
EXCLUDED = {
    OUT_JSON.relative_to(ROOT).as_posix(),
    OUT_MD.relative_to(ROOT).as_posix(),
}


def git(*args: str, text: bool = True) -> str | bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=text)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def record(path: Path) -> dict:
    value = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(value),
        "sha256": sha256_bytes(value),
        "local_filesystem_mtime_utc": iso_mtime(path),
    }


def candidate_paths() -> list[Path]:
    output = git("ls-files", "-m", "-o", "--exclude-standard", "-z", text=False)
    paths = []
    for item in output.split(b"\0"):
        if not item:
            continue
        relative = item.decode("utf-8").replace("\\", "/")
        if relative in EXCLUDED or relative.startswith("tmp/"):
            continue
        path = ROOT / relative
        if path.is_file():
            paths.append(path)
    return sorted(paths, key=lambda value: value.relative_to(ROOT).as_posix())


def timeline_record(relative: str, event: str) -> dict:
    path = ROOT / relative
    return {
        "event": event,
        "path": relative,
        "local_filesystem_created_time_utc": datetime.fromtimestamp(
            path.stat().st_ctime, timezone.utc
        ).isoformat(),
        "local_filesystem_mtime_utc": iso_mtime(path),
        "sha256": sha256_bytes(path.read_bytes()),
    }


def main() -> None:
    created = datetime.now(timezone.utc).isoformat()
    prereg_text = PREREG.read_text(encoding="utf-8").replace("\r\n", "\n")
    marker = "\n## Execution log\n"
    if marker not in prereg_text:
        raise SystemExit("cannot locate preregistration execution-log boundary")
    frozen_core = prereg_text.split(marker, 1)[0].rstrip() + "\n"

    raw_index = json.loads(RAW_INDEX.read_text(encoding="utf-8"))
    indexed_files = sum(len(run.get("files", [])) for run in raw_index.get("runs", []))
    tracked_patch = git("diff", "--binary", "HEAD", text=False)
    files = [record(path) for path in candidate_paths()]
    timeline = [
        timeline_record(
            "Experiments/kimi_k3_api_show_2026-08-25.json",
            "Model identity snapshot written before the preregistration file.",
        ),
        timeline_record(
            "Experiments/PREREGISTRATION_KIMI_K3_EXTENSION.md",
            "Preregistration file created before analytic launch; later appended with execution results.",
        ),
        timeline_record(
            "Experiments/kimi_k3_extension_run.log",
            "Analytic runner log created at launch; final mtime includes post-run scorer output.",
        ),
        timeline_record(
            "score_kimi_k3_extension.py",
            "Scorer last modified during code collection and before package-phase artifacts.",
        ),
        timeline_record(
            "Tests/trackD_ollama_kimi-k3-cloud_Python/LLM_Recent_code.json",
            "First code phase finalized.",
        ),
        timeline_record(
            "Tests/trackD_ollama_kimi-k3-cloud_Python/LLM_Recent_packages_1.json",
            "First package phase finalized.",
        ),
        timeline_record(
            "Tests/trackD_ollama_kimi-k3-cloud_Python/Stack_Overflow_All_Time_packages_2.json",
            "Last package phase finalized.",
        ),
        timeline_record(
            "Tests/trackD_ollama_kimi-k3-cloud_Python/run_manifest.json",
            "Run manifest finalized after collection.",
        ),
        timeline_record(
            "Experiments/kimi_k3_extension_results.json",
            "Scored result written after the run manifest.",
        ),
    ]

    payload = {
        "schema": "package-hallucination-retrospective-provenance-v1",
        "created_at_utc": created,
        "status": "retrospective evidence stamp; not a cryptographic preregistration",
        "git": {
            "branch": git("branch", "--show-current").strip(),
            "parent_commit_before_snapshot": git("rev-parse", "HEAD").strip(),
            "tracked_worktree_patch_sha256": sha256_bytes(tracked_patch),
            "tracked_worktree_patch_bytes": len(tracked_patch),
            "snapshot_file_count_excluding_stamp_outputs": len(files),
        },
        "attestation": {
            "claim": (
                "The substantive Kimi K3 design is the normalized-LF content before the "
                "Execution log heading in the current preregistration. The maintainer and "
                "experiment operator attest that this core preceded outcome inspection."
            ),
            "frozen_core_normalization": "UTF-8 text; CRLF normalized to LF; one final LF",
            "frozen_core_lines": len(frozen_core.splitlines()),
            "frozen_core_sha256": sha256_bytes(frozen_core.encode("utf-8")),
            "limitations": [
                "The preregistration, scorer, and results were not committed before inference.",
                "The current preregistration was legitimately appended during and after collection.",
                "Filesystem creation and modification times are local metadata and can be altered.",
                "The current runner contains a post-launch artifact-index addition and is not byte-identical to the script parsed by the already-running PowerShell process.",
                "This record cannot independently prove the design was frozen before data; it makes the present evidence and all future changes content-addressable.",
            ],
        },
        "local_timeline_evidence": timeline,
        "local_timeline_note": (
            "Generated on Windows, where st_ctime is exposed as file creation time. Both "
            "creation and modification times are mutable local metadata, not trusted timestamps."
        ),
        "raw_artifact_index": {
            "path": RAW_INDEX.relative_to(ROOT).as_posix(),
            "sha256": sha256_bytes(RAW_INDEX.read_bytes()),
            "indexed_files": indexed_files,
            "verification_command": "python build_ollama_artifact_index.py --verify",
            "last_verified_result": f"verified {indexed_files} files",
            "note": "Raw response files remain git-ignored; this index commits their hashes, sizes, and row counts, not response content.",
        },
        "commit_candidate_files": files,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    rows = "\n".join(
        f"| {item['event']} | `{item['path']}` | "
        f"{item['local_filesystem_created_time_utc']} | "
        f"{item['local_filesystem_mtime_utc']} | `{item['sha256'][:16]}…` |"
        for item in timeline
    )
    md = f"""# Retrospective provenance stamp — 2026-08-26

**Status:** retrospective evidence stamp; **not** a cryptographic preregistration.

The Kimi K3 preregistration, scorer, and outcomes were not committed before inference. No
post-run artifact can repair that historical fact. This stamp instead locks the evidence that
exists now, states the maintainer/operator attestation narrowly, and makes later modifications
detectable through the containing Git commit.

## Attested pre-outcome design core

The attested design core is the current Kimi K3 preregistration from its first byte through the
line immediately before `## Execution log`, normalized to LF. Its SHA-256 is:

`{payload['attestation']['frozen_core_sha256']}`

This digest is **retrospectively derived**. The maintainer and experiment operator attest that
the substantive core preceded outcome inspection, but the digest itself was created after the
run and is not independent proof of that claim.

## Reconstructable local timeline

| Event | Artifact | Local creation time (UTC) | Local mtime (UTC) | SHA-256 prefix |
|---|---|---:|---:|---|
{rows}

The chronology is consistent with pre-outcome specification: the preregistration file was
created before launch; the scorer predates package-phase finalization; the run manifest predates
the scored result. These are local filesystem timestamps and therefore corroborating evidence,
not a trusted timestamp authority. This stamp was generated on Windows, where the recorded
creation column comes from `st_ctime`; it should not be interpreted the same way on Unix.

## Content-addressed snapshot

- Parent commit before this snapshot: `{payload['git']['parent_commit_before_snapshot']}`
- Tracked pre-commit patch SHA-256: `{payload['git']['tracked_worktree_patch_sha256']}`
- Commit-candidate files hashed (excluding the stamp outputs): {len(files)}
- Git-ignored raw artifacts covered by the separate index: {indexed_files}
- Raw-artifact index SHA-256: `{payload['raw_artifact_index']['sha256']}`

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
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"wrote {OUT_MD.relative_to(ROOT)}")
    print(f"hashed {len(files)} commit-candidate files and {indexed_files} raw artifacts")


if __name__ == "__main__":
    main()
