"""API/Ollama port of ``generate_code.py`` -- Phase 1 of the experiment.

The prompt text, message structure, sampling parameters and output format are copied
verbatim from ``generate_code.py``. The only change is the transport: an HTTP chat call
instead of ``transformers.AutoModelForCausalLM.generate``.

Two details of the original are intentionally preserved even though they look like bugs:

* The "system" instruction is concatenated into the **user** turn with no separator and
  no ``system`` role -- ``system_message + prompt``. That is what every model in the
  paper saw during code generation, so it is what new models see here.
* ``language`` is the raw CLI value, so JavaScript runs say "Javascript" in the prompt.
"""

from __future__ import annotations

import pandas as pd

import api_batch


def generate_code(infile, outfile, client, language="Python", temperature=.7,
                  top_k=20, top_p=0.9, max_tokens=2048, workers=1, limit=None,
                  fail_on_error=False):
    with open(infile, "r", encoding="utf-8") as file:
        df = pd.read_json(file, lines=True)
        prompts = []
        for _, row in df.iterrows():
            prompts.append(row.iloc[0])

    if limit:
        prompts = prompts[:limit]

    # --- verbatim from generate_code.py -------------------------------------------
    system_message = (
        f"You are a coding assistant that generates {language} code. Provide only the "
        f"{language} code and add additional explanatory text only when absolutely "
        f"necessary. If no code is required to answer the question, simply reply 'None'"
    )

    def build_messages(prompt):
        return [{"role": "user", "content": system_message + prompt}]
    # ------------------------------------------------------------------------------

    return api_batch.run_batch(
        client, prompts, build_messages, outfile,
        max_tokens=max_tokens,
        temperature=temperature,
        top_k=top_k,
        top_p=top_p,
        workers=workers,
        desc="Generating code",
        fail_on_error=fail_on_error,
    )
