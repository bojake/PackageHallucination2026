# We Have a Package for You!  
_A Comprehensive Analysis of Package Hallucinations by Code-Generating LLMs_

[![Conference](https://img.shields.io/badge/Conference-USENIX%20Security%20'25-blue)](https://www.usenix.org/conference/usenixsecurity25)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Data](https://img.shields.io/badge/Data-Zenodo-4c7e9b.svg)](https://zenodo.org/records/14676377)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.14676377.svg)](https://doi.org/10.5281/zenodo.14676377)

This repository contains the **code, data, and instructions** for reproducing the experiments and results from our paper:

> **We Have a Package for You! A Comprehensive Analysis of Package Hallucinations by Code Generating LLMs**  
> Joseph Spracklen, Raveen Wijewickrama, A H M Nazmus Sakib, Anindya Maiti, Bimal Viswanath, Murtuza Jadliwala  
> In *Proceedings of the USENIX Security Symposium*, 2025.  
> [📄 Paper PDF](https://www.usenix.org/system/files/conference/usenixsecurity25/sec25cycle1-prepub-742-spracklen.pdf)

---

## 🔦 Highlights (TL;DR)
- Large-scale study across **16** LLMs (commercial + open-source), **Python** and **JavaScript**  
- **576,000** code samples analyzed; **19.7%** of recommended packages were hallucinations  
- **205,474** unique hallucinated package names discovered  
- Effective mitigations evaluated: **RAG**, **self-detection**, **fine-tuning** (largest reduction from fine-tuning)

---

## 📌 Table of Contents
- [Overview](#-overview)
- [Repository Structure](#-repository-structure)
- [Setup](#-setup)
- [Usage](#-usage)
- [Testing Modern Models (Ollama + OpenAI / Grok / Claude)](#-testing-modern-models-ollama--openai--grok--claude)
- [Comparing Against the Paper](#-comparing-against-the-paper)
- [Data](#-data)
- [Reproducing Results](#-reproducing-results)
- [Mitigation Experiments](#-mitigation-experiments)
- [Hardware & Runtime Notes](#-hardware--runtime-notes)
- [Security & Ethics](#-security--ethics)
- [Troubleshooting](#-troubleshooting)
- [Citation](#-citation)
- [License](#-license)
- [Contact](#-contact)

---

## 🔍 Overview
Package hallucinations occur when an LLM generates code that references a **non-existent package** (e.g., via `pip install xyz` or `npm install xyz` where `xyz` does not exist).  
This creates a **software supply-chain risk**: adversaries can upload a malicious package using that hallucinated name.

This repo provides:
- End-to-end pipeline to **generate code**, **extract package names**, and **measure hallucinations**
- Prompt datasets (Stack Overflow–derived and LLM-generated)
- Code to reproduce **figures/tables** and **mitigation experiments**

---

## 📂 Repository Structure
```bash
.
├── run_test.py                 # Runs a full hallucination detection experiment (local weights)
├── run_test_api.py             # Same experiment against Ollama / OpenAI / Grok / Claude
├── compare_to_paper.py         # Scores a run on the paper's scale (Tables 7 & 8)
├── Baselines/                  # Published per-model results, transcribed from the paper
├── llm_api.py                  # Provider shim (plain HTTP, no SDKs)
├── api_batch.py                # Ordered + resumable batch execution
├── generate_code_api.py        # API port of generate_code.py (prompts unchanged)
├── generate_package_names_api.py  # API port of generate_package_names.py (prompts unchanged)
├── Models/                     # Place tested models here (one default model included)
├── Data/                       # Prompt datasets & per-language resources
│   ├── Python/
│   │   ├── LLM_AT.json
│   │   ├── LLM_LY.json
│   │   ├── SO_AT.json
│   │   └── SO_LY.json
│   └── JavaScript/
│       ├── LLM_AT.json
│       ├── LLM_LY.json
│       ├── SO_AT.json
│       └── SO_LY.json
├── Tests/                      # Output directory for experiment results (starts empty)
├── Mitigation/                 # Mitigation experiments
│   ├── run_model_RAG.py
│   ├── run_model_SD.py
│   ├── run_model_combined.py
│   ├── Data/                   # RAG DB + build data
│   ├── Fine_tuned/             # Fine-tuned & quantized models used in mitigation testing
│   └── RAG_setup.py            # Builds the vector DB from Mitigation/Data
├── Plots/                      # Code and data to reproduce paper figures
├── environment.yml             # Conda environment (local-weights path)
├── requirements.txt            # (Optional) pip dependencies
├── requirements-api.txt        # Dependencies for the API path (pandas, requests, tqdm)
├── .env.example                # Template for API keys
├── EXTENSION_NOTES.md          # How the API path was built, and what deviates from the paper
└── README.md
```

---

## ⚙️ Setup

### 1) Clone
```bash
git clone https://github.com/Spracks/PackageHallucination.git
cd PackageHallucination
```

### 2) Create environment
Using Conda (recommended):
```bash
conda env create -f environment.yml
conda activate pkg-hallucination
```

Or using pip:
```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The environment listed is bloated, really just need PyTorch + transformers and the associated dependencies.

> Only testing API / Ollama models? Skip all of the above — `pip install -r requirements-api.txt`
> is enough. See [Testing Modern Models](#-testing-modern-models-ollama--openai--grok--claude).

### 3) Unpack the npm master list (JavaScript runs only)
`Data/Javascript/npm_package_names.csv` ships zipped (53 MB unpacked). Detection expects the
`.csv`:
```bash
unzip Data/Javascript/npm_package_names.zip -d Data/Javascript/
```

---

## 🚀 Usage

Run a **full hallucination detection** experiment for one model:
```bash
python run_test.py DeepSeek_1B --language Python
# or
python run_test.py DeepSeek_1B --language JavaScript
```

**What it does**
- Generates code for prompts in `Data/<LANG>/`
- Extracts package names via the paper’s three heuristics
- Compares against master lists to mark hallucinations
- Writes results/artifacts under `Tests/`

**Notes**
- Ensure your chosen model is available under `Models/`
- End-to-end runs can take **24–72 hours** depending on model size and hardware

---

## 🌐 Testing Modern Models (Ollama + OpenAI / Grok / Claude)

`run_test.py` loads model weights locally with `transformers`, which limits the study to
models you can fit on your own GPU. `run_test_api.py` runs the **same experiment over HTTP**
instead, so the 2024-era model list can be extended to whatever is current — local models
served by [Ollama](https://ollama.com), or hosted models from OpenAI, xAI (Grok) and
Anthropic (Claude).

Nothing about the technique changes. Same prompts, same two-query protocol, same sampling
parameters, same extraction heuristics, same master lists, same detection code. The only
difference is the transport: a `requests` call to a chat endpoint instead of
`model.generate()`.

> [EXTENSION_NOTES.md](EXTENSION_NOTES.md) records how this path was built, every design
> decision behind it, what deviates from the paper and why, and exactly what was verified.

### 1) Install

```bash
pip install -r requirements-api.txt
```

That's `pandas`, `requests` and `tqdm` — no torch, no CUDA, no `text-generation-webui`.

### 2) Provide credentials

```bash
cp .env.example .env    # then fill in the keys you need
```

`.env` is gitignored and real environment variables take precedence. Ollama needs no key.

### 3) Run

```bash
python run_test_api.py ollama:qwen3-coder:30b --language Python
```

```bash
python run_test_api.py openai:gpt-4.1 --language Python
```

```bash
python run_test_api.py anthropic:claude-sonnet-4-5-20250929 --language Javascript
```

```bash
python run_test_api.py xai:grok-4 --language Python --workers 8
```

The model spec is always `provider:model_id`. Providers: `ollama`, `openai`, `xai` (alias
`grok`), `anthropic` (alias `claude`), plus `openai_compatible` with `--base-url` for
anything else that speaks the OpenAI chat schema (vLLM, llama.cpp, LM Studio, OpenRouter,
Together, Groq).

Model ids churn faster than papers do, so ask the provider rather than trusting a list:

```bash
python run_test_api.py --list-models ollama
```

**Always smoke-test first.** A full run is ~59,000 requests per model per language
(4 datasets × ~4,900 prompts, one code generation plus two package queries each):

```bash
python run_test_api.py openai:gpt-4.1 --limit 25
```

### What is preserved verbatim

| Stage | Preserved from the paper |
|---|---|
| Code generation | Prompt text, and the original quirk of folding the "system" instruction into the **user** turn with no separator; `temperature=0.7`, `top_k=20`, `top_p=0.9` |
| Package query 1 | *"Which \<lang\> packages are required to run this code: …"* over the model's own generated code; `temperature=0.01` |
| Package query 2 | *"What \<lang\> packages would be useful in solving the following coding problem: …"* over the original prompt; `temperature=0.01` |
| Detection | Unchanged — `package_detection.py`, `custom_parse_*.py`, `aggregate_results.py` and the PyPI/npm master lists are called as-is |
| Output layout | Identical file names under `Tests/<model>_<language>/`, so `Plots/` and every downstream script work without modification |

### The one deliberate deviation: response caps

The paper capped responses at **2048 tokens** for code generation and **64 tokens** for the
package queries. Both defaults are raised to **30,000** here, because a reasoning model
spends those budgets on hidden thinking tokens and returns an empty answer — which reads
downstream as "recommended no packages" and produces a hallucination rate near zero that is
a measurement artifact, not a result.

30,000 is chosen to stay inside what a plain non-streaming HTTP request can do: it is far
below every current model's output ceiling (128k, or 64k on Haiku 4.5), so no provider needs
streaming support to answer. The runner's request timeout is 600 s to match.

The cap only binds when a model would otherwise have been cut off, so for models that answer
in a few dozen tokens the raised cap changes nothing. Where it does bind, the model now
finishes its list instead of being truncated mid-name. Every run records this in
`run_manifest.json` under `deviations_from_paper`. To reproduce the paper's exact setup:

```bash
python run_test_api.py openai:gpt-4.1 --max-code-tokens 2048 --max-package-tokens 64
```

### Sampling fidelity (read this before comparing to the paper)

The original used HuggingFace sampling with `temperature` + `top_k` + `top_p`. Not every
hosted API accepts all three:

| Provider | temperature | top_k | top_p |
|---|:--:|:--:|:--:|
| Ollama (native `/api/chat`) | ✅ | ✅ | ✅ |
| Anthropic (`/v1/messages`) | ✅ | ✅ | ✅ |
| OpenAI (`/v1/chat/completions`) | ✅ | ❌ | ✅ |
| xAI (`/v1/chat/completions`) | ✅ | ❌ | ✅ |

Anything that cannot be sent is **recorded, not hidden** — every run writes
`Tests/<model>_<language>/run_manifest.json` listing the exact endpoint, the parameters
that were sent, the parameters that were adjusted and why, and total token usage. Use
`--strict-sampling` to abort instead of dropping.

Individual models also reject parameters at request time. The runner reacts to the API's
400, fixes the request, retries, and records the change under `request_adjustments`:

| The model says | The runner does |
|---|---|
| `temperature` / `top_p` not supported (common on reasoning models) | Drops that parameter |
| Use `max_completion_tokens` instead of `max_tokens` (OpenAI) | Renames the field |
| `max_tokens` exceeds this model's output ceiling | Clamps to the ceiling named in the error |

> **Reasoning models** are the reason the response caps are raised (see above). If a run
> still reports a high `responses_hitting_token_cap`, pass
> `--extra-body '{"reasoning_effort": "low"}'` so the model spends less of the budget on
> hidden thinking — and say which settings you used when reporting results.

### Response parsing

The paper hand-wrote a response parser per model family (`custom_parse_python.py`,
`custom_parse_javascript.py`). `--parser-style auto` (the default) selects the parser the
paper used for its **commercial API models**, which is the right fit for modern
instruction-tuned models that honour "respond with only a comma-separated list". Override
with `--parser-style {gpt,deepseek,mistral,wizardcoder,mixtral,magicoder,openchat,codellama}`
if a model's output format needs one of the others. **Spot-check `PACKAGE_NAMES.csv` on a
`--limit` run** — a parser mismatch shows up as junk tokens counted as hallucinated packages.

### Reliability

- **Resumable.** Responses stream to a `.partial` file; re-running the same command picks up
  where it stopped instead of paying for the whole dataset again.
- **Ordered.** Responses are always written at their prompt's row index, even with
  `--workers > 1`, because the merge step joins prompts to answers by position.
- **Failures are visible.** A request that exhausts its retries leaves a blank row (keeping
  alignment) plus a `*.errors.json` file, and the next run retries exactly those rows. Use
  `--fail-on-error` to abort instead.
- **Not deterministic.** `temperature=0.7` sampling plus provider-side model updates mean
  repeat runs differ. This is equally true of the original setup; report the date and the
  exact model id (the manifest does both).

### Useful flags

| Flag | Purpose |
|---|---|
| `--limit N` | Only use the first N prompts per dataset (smoke tests) |
| `--stage {all,code,packages,detect}` | Run one phase at a time |
| `--workers N` | Concurrent requests. Wall-clock only — prompts and sampling are unchanged. Default 1 for Ollama, 4 otherwise |
| `--base-url URL` | Point at a remote Ollama host or any OpenAI-compatible server |
| `--extra-body JSON` | Merge extra fields into every request body. An `"options"` object is merged into Ollama's options block, so `'{"options": {"num_ctx": 32768}}'` works |
| `--max-code-tokens`, `--max-package-tokens` | Response caps (default 30,000 each; paper values 2048 / 64) |
| `--name NAME` | Override the `Tests/` output directory name |
| `--max-retries`, `--timeout` | Backoff behaviour on rate limits and 5xx |
| `--sample N --seed S` | Randomly sample N prompts per dataset. Use this, not `--limit`, for anything you intend to measure |

---

## 📐 Comparing Against the Paper

```bash
python compare_to_paper.py
```

Reads every `Tests/*/FINAL_RESULTS.csv`, computes the hallucination rate the way the paper
defines it, and places the run on the scale of the 16 models from Tables 7 and 8.

### The metric

§5.1: *"a simple ratio of the number of hallucinated packages to the total number of
recommended packages"*, pooling all three detection heuristics:

```
rate = (hallucinated_1 + hallucinated_2 + install_hallucinated)
     / (all valid + hallucinated packages from both queries and pip/npm install)
```

The paper's own tables confirm this — for every one of the 30 model×language rows, the
LLM-prompt, Stack-Overflow-prompt and `pip install` components sum exactly to the published
total. `Baselines/paper_appendix_e.csv` holds those counts and
`python compare_to_paper.py --verify-baseline` re-checks the transcription. Summed, it
reproduces the paper's headline figures: **440,445 hallucinated of 2,235,642 packages
(19.7%)**, Python averaging 15.87% and JavaScript 21.38% against the stated 15.8% / 21.3%.

### Sampling

A full run is ~19,200 code samples per model per language. `--sample N --seed S` draws a
random subset instead — the unit of analysis is *packages*, not prompts, so a few hundred
prompts per dataset still yields thousands of packages and a usable confidence interval.
Use `--sample`, not `--limit`: the Stack Overflow datasets are ordered by popularity, so a
prefix is a biased subset. The manifest records the sample size and seed.

### Replicating one of the paper's own models

Comparing a 2026 model to the paper's 2024 list tells you models changed. To check that
*this pipeline measures what the paper measured*, re-run one of their models — several are
on Ollama (CodeLlama, DeepSeek Coder, Mistral, Mixtral, WizardCoder, Magicoder, OpenChat) —
with the paper's exact caps:

```bash
python run_test_api.py ollama:codellama:7b-instruct --language Python --sample 100 --seed 0 --max-code-tokens 2048 --max-package-tokens 64
```

`compare_to_paper.py` detects that the model spec names a model in the baseline and reports
the delta as a **REPLICATION** line rather than a cross-model comparison. See
[EXTENSION_NOTES.md](EXTENSION_NOTES.md) for the result and its caveats — quantization,
chat template and sampling nondeterminism all differ from the original setup, so this is a
sanity check on the pipeline, not a bit-exact reproduction.

---

## 📊 Data

**Included prompt datasets (per language):**
- `LLM_AT.json` – LLM-generated prompts based on **all-time** most popular packages  
- `LLM_LY.json` – LLM-generated prompts based on **last-year** most popular packages  
- `SO_AT.json` – Top Stack Overflow questions (all-time)  
- `SO_LY.json` – Top Stack Overflow questions (last-year)

Each language directory also contains the **master list of valid package names** used for detection.

> We **do not** publish the master list of hallucinated package names or per-prompt detailed results (see [Security & Ethics](#-security--ethics)). Verified researchers can request access.

---

## 📈 Reproducing Results

Reproduce main tables/figures by re-running experiments and then building plots:

```bash
# 1) Run experiments (example)
python run_test.py DeepSeek_1B --language Python
python run_test.py CodeLlama_7B --language Python
# ... (repeat for desired model/language combinations)

# 2) Build figures
cd Plots
python reproduce_figures.py
```

Where applicable, figure scripts read from `Tests/` to regenerate the paper plots.

---

## 🛠 Mitigation Experiments

We provide three mitigation strategies:

1. **RAG (Retrieval-Augmented Generation)**  
   Augments prompts with retrieved package-context from a vector DB built from package descriptions.

   ```bash
   # Build RAG DB (once)
   python Mitigation/RAG_setup.py
   # Run RAG experiment
   python Mitigation/run_model_RAG.py DeepSeek_1B --language Python
   ```

2. **Self-Detection / Self-Refinement**  
   The model checks its own suggested package list; if invalid, regenerate with constraints.

   ```bash
   python Mitigation/run_model_SD.py CodeLlama_7B --language Python
   ```

3. **Fine-Tuning**  
   Fine-tune on valid (non-hallucinated) package recommendations derived from the pipeline.

   ```bash
   # Use the fine-tuned checkpoints under Mitigation/Fine_tuned/
   python Mitigation/run_model_combined.py DeepSeek_1B --language Python
   ```

> See paper for comparative results; fine-tuning produced the **largest** hallucination reduction.

---

## 🧰 Hardware & Runtime Notes
- Open-source models were evaluated in **quantized** form to mimic realistic hardware constraints.
- A single full run can take **24–72 hours** depending on model size/GPU availability.
- For reproducibility, stick to the provided `environment.yml` and keep decoding parameters consistent unless you are explicitly testing RQ2-style variations.

---

## 🔒 Security & Ethics
- We **do not** publicly release:
  - The master list of hallucinated package names
  - Per-prompt detailed results
- Rationale: releasing these could enable **package confusion attacks** at scale.
- **Access policy:** verified researchers may request full results for academic use.  
- See the paper’s **Ethics Considerations** for additional detail.

---

## 🧪 Troubleshooting
- **Environment fails to resolve:** ensure you’re using the listed CUDA/PyTorch versions in `environment.yml`.
- **Model not found:** confirm the checkpoint is placed under `Models/` and the name matches your CLI arg.
- **Very slow runs:** you’re likely on CPU; use a CUDA GPU where possible.
- **Different hallucination rates than reported:** minor variation is expected across hardware/versions; ensure decoding params and temperatures match defaults in the code.

**API / Ollama path**
- **`FileNotFoundError: npm_package_names.csv`:** unzip it (see [Setup](#-setup) step 3).
- **`Environment variable OPENAI_API_KEY is not set`:** copy `.env.example` to `.env` and fill it in.
- **Connection refused on `ollama:`:** start the server (`ollama serve`) and pull the model
  (`ollama pull <model>`); confirm with `python run_test_api.py --list-models ollama`.
- **Hallucination rate suspiciously near zero:** check `run_manifest.json` for
  `responses_hitting_token_cap`. Empty answers read downstream as "recommended no packages".
  Raise the caps, or pass `--extra-body '{"reasoning_effort": "low"}'`.
- **Requests timing out:** a 30,000-token response can take minutes. Raise `--timeout`
  (default 600 s), or lower `--max-package-tokens`.
- **`PACKAGE_NAMES.csv` full of prose fragments:** the response parser doesn't match the
  model's output format — try a different `--parser-style`.
- **Rate limits:** lower `--workers`; the runner already backs off and honours `Retry-After`,
  and re-running resumes rather than restarting.

---

## 📜 Citation
If you use this repository, please cite:
```bibtex
@inproceedings{spracklen2025packagehallucination,
  title     = {We Have a Package for You! A Comprehensive Analysis of Package Hallucinations by Code Generating LLMs},
  author    = {Joseph Spracklen and Raveen Wijewickrama and A H M Nazmus Sakib and Anindya Maiti and Bimal Viswanath and Murtuza Jadliwala},
  booktitle = {USENIX Security Symposium},
  year      = {2025}
}
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).

---

## 📬 Contact
Questions or collaboration:
- **Joseph Spracklen** — joseph.spracklen@utsa.edu  
- Or open an issue on the repository
