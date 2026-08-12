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


def _load_partial(outfile):
    """Read completed (index, text) pairs from a previous interrupted run."""
    path = _partial_path(outfile)
    done = {}
    if not os.path.exists(path):
        return done
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                done[int(record["i"])] = record["text"]
            except (ValueError, KeyError, TypeError):
                continue  # truncated final line from a hard kill -- just redo that item
    return done


def run_batch(client, items, build_messages, outfile, max_tokens,
              temperature=None, top_k=None, top_p=None,
              workers=1, desc="Generating", fail_on_error=False):
    """Call ``client`` once per item and write the responses to ``outfile`` in order.

    ``build_messages(item)`` returns the message list for that item; it is the *only*
    place prompt text is constructed, and it is kept identical to the original scripts.

    Returns a stats dict for the run manifest.
    """
    done = _load_partial(outfile)
    todo = [i for i in range(len(items)) if i not in done]
    errors = []
    truncated_before = client.truncated

    if done:
        print(f"  resuming: {len(done)}/{len(items)} responses already collected")

    if todo:
        partial = open(_partial_path(outfile), "a", encoding="utf-8", newline="")
        try:
            def call(index):
                text, _ = client.chat(
                    build_messages(items[index]),
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_k=top_k,
                    top_p=top_p,
                )
                return index, text

            with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
                futures = {pool.submit(call, i): i for i in todo}
                for future in tqdm(as_completed(futures), total=len(futures),
                                   desc=desc, unit="prompt"):
                    index = futures[future]
                    try:
                        index, text = future.result()
                    except llm_api.ProviderError as exc:
                        # Keep row alignment: an empty response occupies the slot so every
                        # downstream join still lines up, and the failure is recorded
                        # loudly instead of silently deflating the hallucination counts.
                        # Failures are deliberately NOT written to the .partial file, so
                        # re-running the experiment retries exactly those rows.
                        errors.append({"index": index, "error": str(exc)})
                        done[index] = ""
                        continue
                    done[index] = text
                    partial.write(json.dumps({"i": index, "text": text}) + "\n")
                    partial.flush()
        finally:
            partial.close()

    with open(outfile, "w", newline="", encoding="utf-8") as output:
        for index in range(len(items)):
            json.dump(done.get(index, ""), output)
            output.write("\n")

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

    # Truncations among the requests THIS invocation made. Rows recovered from a prior
    # partial file are not re-measured, so a resumed phase undercounts relative to a fresh
    # one -- callers wanting exact per-phase cap-hit denominators should run without resume.
    return {"items": len(items), "requested": len(todo), "resumed": len(items) - len(todo),
            "errors": len(errors), "truncated_new_requests": client.truncated - truncated_before}
