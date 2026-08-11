"""API/Ollama port of ``generate_package_names.py`` -- Phase 2 of the experiment.

Both of the paper's package queries are reproduced verbatim:

* **Mode 1** -- given the code the model just wrote, which packages does it need?
* **Mode 2** -- given the original prompt, which packages would help solve it?

System messages, user prefixes, ``.strip()`` placement, the 64-token cap and the
low temperature (0.01) are unchanged from ``generate_package_names.py``.
"""

from __future__ import annotations

import pandas as pd

import api_batch


def generate_packages(mode, infile, outfile, client, language="Python", temperature=.01,
                      top_k=20, top_p=0.9, max_tokens=64, workers=1, limit=None,
                      fail_on_error=False):
    with open(infile, "r", encoding="utf-8") as file:
        df = pd.read_json(file, lines=True)
        code = []
        if mode == 1:
            for _, row in df.iterrows():
                code.append(row["Answers"])       # the model's own generated code
        else:
            for _, row in df.iterrows():
                code.append(row.iloc[0])          # the original prompt / SO question

    if limit:
        code = code[:limit]

    # --- verbatim from generate_package_names.py ----------------------------------
    if mode == 1:
        system_message = (
            f"You are a coding assistant that determines {language} packages necessary to "
            f"execute code. Respond with only a list of {language} packages, separated by "
            f"commas and no additional text or formatting. Your response must begin with "
            f"the name of a {language} package."
        )
        prefix = f"Which {language} packages are required to run this code: "
    elif mode == 2:
        system_message = (
            f"You are a coding assistant that recommends {language} packages that would be "
            f"helpful to solve given problems. Respond with only a list of {language} "
            f"packages, separated by commas and no additional text or formatting. Your "
            f"response must begin with the name of a {language} package."
        )
        prefix = f"What {language} packages would be useful in solving the following coding problem: "
    else:
        raise ValueError(f"mode must be 1 or 2, got {mode!r}")

    def build_messages(sample):
        return [{"role": "system", "content": system_message},
                {"role": "user", "content": prefix + str(sample).strip()}]
    # ------------------------------------------------------------------------------

    return api_batch.run_batch(
        client, code, build_messages, outfile,
        max_tokens=max_tokens,
        temperature=temperature,
        top_k=top_k,
        top_p=top_p,
        workers=workers,
        desc=f"Querying packages (mode {mode})",
        fail_on_error=fail_on_error,
    )
