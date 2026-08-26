"""Ordered, resumable batch execution for API-backed generation.

The downstream pipeline (``aggregate_results.combine_code_and_prompt`` /
``merge_prompts_and_packages``) joins prompts to responses **by row position** with
``pd.concat(axis=1)``. Output ordering is therefore load-bearing: response *n* must be on
line *n*. This module guarantees that even with concurrent workers, and can resume a
half-finished file after a rate-limit wall or a dropped connection.

Output format is byte-for-byte what the original scripts wrote: one ``json.dump``'d
string per line, readable by ``pd.read_json(..., lines=True)``.
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

import llm_api


def _partial_path(outfile):
    return f"{outfile}.partial"


def _metadata_path(outfile):
    return f"{outfile}.request_metadata.jsonl"


def _load_partial(outfile):
    """Read completed responses and metadata from a previous interrupted run."""
    path = _partial_path(outfile)
    done = {}
    metadata = {}
    if not os.path.exists(path):
        return done, metadata
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                index = int(record["i"])
                done[index] = record["text"]
                if isinstance(record.get("meta"), dict):
                    metadata[index] = record["meta"]
            except (ValueError, KeyError, TypeError):
                continue  # truncated final line from a hard kill -- just redo that item
    return done, metadata


def run_batch(client, items, build_messages, outfile, max_tokens,
              temperature=None, top_k=None, top_p=None,
              workers=1, desc="Generating", fail_on_error=False):
    """Call ``client`` once per item and write the responses to ``outfile`` in order.

    ``build_messages(item)`` returns the message list for that item; it is the *only*
    place prompt text is constructed, and it is kept identical to the original scripts.

    Returns a stats dict for the run manifest.
    """
    done, response_metadata = _load_partial(outfile)
    todo = [i for i in range(len(items)) if i not in done]
    errors = []
    truncated_before = client.truncated

    if done:
        print(f"  resuming: {len(done)}/{len(items)} responses already collected")

    if todo:
        partial = open(_partial_path(outfile), "a", encoding="utf-8", newline="")
        try:
            def call(index):
                text, _, metadata = client.chat(
                    build_messages(items[index]),
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_k=top_k,
                    top_p=top_p,
                    include_metadata=True,
                )
                return index, text, metadata

            with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
                futures = {pool.submit(call, i): i for i in todo}
                for future in tqdm(as_completed(futures), total=len(futures),
                                   desc=desc, unit="prompt"):
                    index = futures[future]
                    try:
                        index, text, metadata = future.result()
                    except Exception as exc:  # noqa: BLE001 -- any per-row failure must
                        # be recorded and retried on resume, never crash a multi-hour run
                        # Keep row alignment: an empty response occupies the slot so every
                        # downstream join still lines up, and the failure is recorded
                        # loudly instead of silently deflating the hallucination counts.
                        # Failures are deliberately NOT written to the .partial file, so
                        # re-running the experiment retries exactly those rows.
                        errors.append({"index": index, "error": str(exc)})
                        done[index] = ""
                        continue
                    done[index] = text
                    response_metadata[index] = metadata
                    partial.write(json.dumps({"i": index, "text": text,
                                              "meta": metadata}) + "\n")
                    partial.flush()
        finally:
            partial.close()

    with open(outfile, "w", newline="", encoding="utf-8") as output:
        for index in range(len(items)):
            json.dump(done.get(index, ""), output)
            output.write("\n")

    # A sidecar preserves the paper-compatible raw response file while making finish reason
    # and token use auditable per row. Legacy partial files may lack metadata; mark those rows
    # explicitly instead of inventing values.
    with open(_metadata_path(outfile), "w", newline="", encoding="utf-8") as output:
        for index in range(len(items)):
            record = {"index": index}
            if index in response_metadata:
                record.update(response_metadata[index])
            else:
                record["metadata_missing"] = True
            output.write(json.dumps(record) + "\n")

    error_file = f"{outfile}.errors.json"
    if errors:
        with open(error_file, "w", encoding="utf-8") as handle:
            json.dump(errors, handle, indent=2)
        message = (f"{len(errors)}/{len(items)} requests failed after retries; blank "
                   f"responses written for those rows. Details: {error_file}. Re-run the "
                   f"same command to retry only the failed rows.")
        if fail_on_error:
            raise llm_api.ProviderError(message)
        print(f"  WARNING: {message}")
    else:
        for path in (_partial_path(outfile), error_file):
            if os.path.exists(path):
                os.remove(path)

    # Preserve both invocation-specific and complete-phase truncation counts. The latter is
    # reconstructed from the ordered sidecar metadata and therefore remains exact after a
    # legitimate resume; scorers must not compare a complete sidecar with the new-request-only
    # counter.
    truncated_total_rows = sum(
        bool(record.get("truncated"))
        for record in response_metadata.values()
        if isinstance(record, dict) and not record.get("metadata_missing")
    )
    return {"items": len(items), "requested": len(todo), "resumed": len(items) - len(todo),
            "errors": len(errors), "truncated_new_requests": client.truncated - truncated_before,
            "truncated_total_rows": truncated_total_rows,
            "response_metadata_rows": len(response_metadata),
            "response_metadata_path": _metadata_path(outfile).replace("\\", "/")}
