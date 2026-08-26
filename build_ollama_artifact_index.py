"""Build a content-addressed index for git-ignored Ollama experiment artifacts.

The repository deliberately ignores Tests/.  This index retains enough provenance to detect
silent local changes and to verify a separately archived raw-artifact bundle without copying
response content or candidate package names into Experiments/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone


RUNS = [
    ("qwen3.5:cloud", "trackC_ollama_qwen3-5-cloud_Python"),
    ("kimi-k2.7-code:cloud", "trackC_ollama_kimi-k2-7-code-cloud_Python"),
    ("kimi-k3:cloud", "trackD_ollama_kimi-k3-cloud_Python"),
]
DATASETS = ["LLM_Recent", "LLM_All_Time", "Stack_Overflow_Recent",
            "Stack_Overflow_All_Time"]
PHASES = [f"{dataset}_{suffix}" for dataset in DATASETS
          for suffix in ("code", "packages_1", "packages_2")]
OUT = os.path.join("Experiments", "ollama_cloud_artifact_index.json")


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def nonempty_lines(path: str) -> int | None:
    extension = os.path.splitext(path)[1].lower()
    if extension not in {".json", ".jsonl", ".csv"}:
        return None
    with open(path, "rb") as handle:
        return sum(bool(line.strip()) for line in handle)


def file_record(path: str) -> dict:
    return {
        "path": path.replace("\\", "/"),
        "bytes": os.path.getsize(path),
        "nonempty_lines": nonempty_lines(path),
        "sha256": sha256(path),
    }


def index_run(model: str, run: str) -> dict:
    directory = os.path.join("Tests", run)
    manifest_path = os.path.join(directory, "run_manifest.json")
    required_outputs = [os.path.join(directory, f"{phase}.json") for phase in PHASES]
    required_sidecars = [f"{path}.request_metadata.jsonl" for path in required_outputs]
    item = {
        "model": model,
        "run": run,
        "tests_directory_git_ignored": True,
        "required_phase_outputs": len(required_outputs),
        "required_response_sidecars": len(required_sidecars) if model == "kimi-k3:cloud" else 0,
    }
    if not os.path.exists(manifest_path):
        item.update({"status": "collecting", "files": []})
        return item

    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    missing_outputs = [path for path in required_outputs if not os.path.exists(path)]
    missing_sidecars = ([path for path in required_sidecars if not os.path.exists(path)]
                        if model == "kimi-k3:cloud" else [])
    phase_items = sum(int(value.get("items") or 0)
                      for value in (manifest.get("phases") or {}).values())
    phase_errors = sum(int(value.get("errors") or 0)
                       for value in (manifest.get("phases") or {}).values())
    complete = not missing_outputs and not missing_sidecars and phase_items == 2400 \
        and phase_errors == 0 and manifest.get("token_usage_cumulative", {}).get("calls") == 2400
    item.update({
        "status": "complete" if complete else "incomplete",
        "manifest_summary": {
            "model_spec": manifest.get("model_spec"),
            "calls": manifest.get("token_usage_cumulative", {}).get("calls"),
            "phase_items": phase_items,
            "phase_errors": phase_errors,
            "served_model_ids": (manifest.get("client") or {}).get("served_model_ids"),
            "request_adjustments": (manifest.get("client") or {}).get(
                "request_adjustments"
            ),
        },
        "missing_phase_outputs": [path.replace("\\", "/") for path in missing_outputs],
        "missing_response_sidecars": [path.replace("\\", "/") for path in missing_sidecars],
    })
    if complete:
        # Index every retained file, not only the minimum scoring inputs, so a separately
        # archived directory can be checked byte-for-byte.
        files = [os.path.join(directory, name) for name in sorted(os.listdir(directory))
                 if os.path.isfile(os.path.join(directory, name))]
        item["files"] = [file_record(path) for path in files]
    else:
        # Never hash a live partial: doing so would create a misleading moving provenance mark.
        item["files"] = []
    return item


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify", action="store_true",
        help="verify the current local files against the existing index instead of rebuilding",
    )
    args = parser.parse_args()
    if args.verify:
        with open(OUT, encoding="utf-8") as handle:
            existing = json.load(handle)
        failures = []
        checked = 0
        for run in existing.get("runs", []):
            if run.get("status") != "complete":
                continue
            for expected in run.get("files", []):
                path = expected["path"]
                checked += 1
                if not os.path.exists(path):
                    failures.append(f"missing: {path}")
                    continue
                observed = file_record(path)
                for field in ("bytes", "nonempty_lines", "sha256"):
                    if observed[field] != expected[field]:
                        failures.append(
                            f"{path}: {field}={observed[field]!r}, "
                            f"expected={expected[field]!r}"
                        )
        if failures:
            raise SystemExit(
                f"artifact verification failed ({len(failures)} discrepancies):\n"
                + "\n".join(failures)
            )
        print(f"verified {checked} files against {OUT}")
        return

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "purpose": (
            "SHA-256, size, and row-count index for separately archived raw experiment "
            "artifacts under the git-ignored Tests directory."
        ),
        "contains_raw_response_content": False,
        "runs": [index_run(model, run) for model, run in RUNS],
    }
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
