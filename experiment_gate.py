"""Human freeze gate: no analytic collection from an uncommitted repository.

The Kimi K3 review found that preregistration freezes were self-attested -- the protocol,
scorer, and results lived only in the working tree, so nothing could prove the frozen
sections predated the data. This gate makes the freeze tamper-evident and makes a human
commit the only way to launch:

1. ``python experiment_gate.py stamp --prereg <file> --run-name <Tests dir name>``
   refuses to run unless ``git status`` is completely clean, then writes a stamp under
   ``Experiments/freeze_stamps/`` recording the preregistration's committed blob hash,
   its SHA-256, and the HEAD commit it was frozen at.
2. The maintainer commits the stamp. That commit is the freeze event.
3. The runner launches with ``--freeze-stamp <stamp>``. ``check`` aborts the launch unless
   the tree is still clean, the stamp itself is committed at HEAD, the stamp names this
   run, and the preregistration blob at HEAD equals the stamped hash. The verified stamp
   is embedded in the run manifest.

There is deliberately no ``--allow-dirty`` escape: the gate exists to stop the maintainer,
not strangers. Editing this file to get around it is itself a recorded, diffable act.
``Tests/`` raw artifacts are intentionally git-ignored and never block a launch; they are
content-addressed separately by ``build_ollama_artifact_index.py``. Because a resumed
launch re-runs ``check``, editing any tracked file mid-campaign also blocks the resume --
mid-run pipeline edits now require either finishing dirty-launch-free or amending in git
first.

Blob hashes (not raw bytes) are compared so Windows CRLF checkout normalization cannot
produce false mismatches. ``git_provenance()`` is the one non-fatal helper: it records
repository state into manifests and must never break a run, so it reports errors as data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
STAMP_DIR = os.path.join("Experiments", "freeze_stamps")
GATE_RULE = ("analytic launches require a clean working tree, this stamp committed at "
             "HEAD, a matching run name, and an unchanged preregistration blob")


class GateError(SystemExit):
    """Launch-blocking failure. SystemExit so CLI and runner abort identically."""


def _git(*args: str) -> str:
    result = subprocess.run(["git", "-C", REPO_ROOT, *args],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise GateError(
            f"git {' '.join(args)} failed in {REPO_ROOT}: "
            f"{result.stderr.strip() or result.stdout.strip() or 'unknown error'}"
        )
    return result.stdout


def repo_dirt() -> list[str]:
    """Non-empty lines from ``git status --porcelain``; ignored paths never appear."""
    return [line for line in _git("status", "--porcelain").splitlines() if line.strip()]


def head_commit() -> str:
    return _git("rev-parse", "HEAD").strip()


def _repo_relative(path: str) -> str:
    """Normalize to a forward-slash path relative to REPO_ROOT.

    Relative inputs are resolved against the repository root, not the process CWD, and
    realpath collapses Windows 8.3 short-name aliases so containment checks cannot lie.
    """
    root = os.path.realpath(REPO_ROOT)
    absolute = path if os.path.isabs(path) else os.path.join(root, path)
    relative = os.path.relpath(os.path.realpath(absolute), root)
    if relative.startswith(".."):
        raise GateError(f"{path} is outside the repository at {REPO_ROOT}")
    return relative.replace(os.sep, "/")


def committed_blob(path: str) -> str:
    """Blob hash of ``path`` as committed at HEAD; GateError if not committed."""
    relative = _repo_relative(path)
    try:
        return _git("rev-parse", f"HEAD:{relative}").strip()
    except GateError:
        raise GateError(
            f"{relative} is not committed at HEAD. Commit it first; the freeze is the commit."
        )


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_provenance() -> dict:
    """Repository state for run manifests. Non-fatal by design: errors become data."""
    try:
        dirt = repo_dirt()
        return {
            "head_commit": head_commit(),
            "working_tree_clean": not dirt,
            "dirty_paths": len(dirt),
            "dirty_preview": dirt[:15],
        }
    except (GateError, OSError) as exc:
        return {"error": str(exc)}


def _dirt_message(dirt: list[str]) -> str:
    preview = "\n".join(f"  {line}" for line in dirt[:15])
    more = f"\n  ... and {len(dirt) - 15} more" if len(dirt) > 15 else ""
    return (f"the working tree has {len(dirt)} uncommitted path(s):\n{preview}{more}\n"
            "Commit (or revert) everything, then retry. There is no override flag.")


def stamp_path_for(run_name: str) -> str:
    return os.path.join(STAMP_DIR, f"{run_name}.json").replace(os.sep, "/")


def stamp(prereg: str, run_name: str) -> str:
    """Freeze ``prereg`` for ``run_name``. Requires a fully clean, committed tree."""
    dirt = repo_dirt()
    if dirt:
        raise GateError("Cannot stamp: " + _dirt_message(dirt))
    relative = _repo_relative(prereg)
    absolute = os.path.join(REPO_ROOT, relative)
    if not os.path.exists(absolute):
        raise GateError(f"Preregistration file not found: {relative}")
    record = {
        "run_name": run_name,
        "preregistration": relative,
        "prereg_git_blob": committed_blob(relative),
        "prereg_sha256": sha256_file(absolute),
        "stamped_at_head": head_commit(),
        "stamped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gate": GATE_RULE,
    }
    destination = stamp_path_for(run_name)
    os.makedirs(os.path.join(REPO_ROOT, STAMP_DIR), exist_ok=True)
    with open(os.path.join(REPO_ROOT, destination), "w", encoding="utf-8",
              newline="\n") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    print(f"stamped {record['preregistration']} (blob {record['prereg_git_blob'][:12]}) "
          f"-> {destination}")
    print(f"Next: git add {destination} && git commit  # the commit is the freeze; "
          "then launch with --freeze-stamp")
    return destination


def check(stamp_file: str, expected_run_name: str | None = None) -> dict:
    """Verify a committed freeze stamp; return it with verification fields, or abort."""
    relative = _repo_relative(stamp_file)
    absolute = os.path.join(REPO_ROOT, relative)
    if not os.path.exists(absolute):
        raise GateError(f"Freeze stamp not found: {relative}")
    try:
        with open(absolute, encoding="utf-8") as handle:
            record = json.load(handle)
    except ValueError as exc:
        raise GateError(f"Freeze stamp {relative} is not valid JSON: {exc}")

    problems = []
    if expected_run_name and record.get("run_name") != expected_run_name:
        problems.append(
            f"stamp names run {record.get('run_name')!r}, but this launch is "
            f"{expected_run_name!r}; stamps are single-use per run"
        )
    dirt = repo_dirt()
    if dirt:
        problems.append(_dirt_message(dirt))
    else:
        # A clean tree plus presence at HEAD proves both files match their commits
        # (porcelain is line-ending aware, so CRLF checkouts do not false-positive).
        try:
            committed_blob(absolute)
        except GateError as exc:
            problems.append(f"the stamp itself is not frozen: {exc}")
        prereg = record.get("preregistration") or ""
        try:
            blob_now = committed_blob(os.path.join(REPO_ROOT, prereg))
            if blob_now != record.get("prereg_git_blob"):
                problems.append(
                    f"{prereg} was re-committed after stamping "
                    f"(blob {blob_now[:12]} != stamped {str(record.get('prereg_git_blob'))[:12]}); "
                    "re-stamp to freeze the new protocol"
                )
        except GateError as exc:
            problems.append(str(exc))
    if problems:
        raise GateError("Freeze gate BLOCKED the launch:\n- " + "\n- ".join(problems))

    record["verified_at_head"] = head_commit()
    record["verified_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record["working_tree_clean"] = True
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    stamper = commands.add_parser("stamp", help="freeze a preregistration for one run")
    stamper.add_argument("--prereg", required=True,
                         help="preregistration markdown file to freeze")
    stamper.add_argument("--run-name", required=True,
                         help="full Tests/ directory name, e.g. trackE_model_Python")
    checker = commands.add_parser("check", help="verify a committed stamp (launch gate)")
    checker.add_argument("--stamp", required=True, help="stamp file written by 'stamp'")
    checker.add_argument("--run-name", default=None,
                         help="expected Tests/ directory name; mismatch blocks")
    args = parser.parse_args()
    if args.command == "stamp":
        stamp(args.prereg, args.run_name)
    else:
        record = check(args.stamp, args.run_name)
        print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
