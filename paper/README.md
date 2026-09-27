# Manuscript

`main.tex` is the paper draft written from [`PAPER_OUTLINE.md`](../PAPER_OUTLINE.md) and the
committed result artifacts under [`Experiments/`](../Experiments).
`PackageHallucinationRevisitedPaper.pdf` is the compiled output (a copy of the untracked build
product `main.pdf`, made by `build.ps1`).

## Provenance of every number

- `build_tables.py` writes every table in `tables/` directly from `Experiments/*.json`
  (`campaign4_results.json`, `campaign4_post_analysis.json`, `churilov_bridge_analysis.json`,
  `ollama_cloud_extension_results.json`, `ollama_cloud_extension_post_analysis.json`,
  `kimi_k3_extension_results.json`, `kimi_k2_7_vs_k3_post_analysis.json`,
  `parser_v2_validation.json`). The only hand-transcribed table is the cell-identity table
  (Table 1), whose rows come from the run manifests under the git-ignored `Tests/` tree and the
  preregistration execution logs.
- `data/churilov_bridge_analysis_six_cell_eac1434.json` is the six-cell bridge artifact as
  committed at `eac1434`, kept here because the current artifact holds the nine-cell version and
  the paper reports both.
- `make_figures.py` draws Figures 2--4 and 6--9 from the same JSON files. Figure 5 (ranked-prompt
  concentration curves) re-scores the raw responses under `Tests/` through the frozen
  `post_campaign_analysis.py` path and prints each cell's totals so they can be checked against
  the committed artifacts; when `Tests/` is absent the committed PDF is kept.
- Figure 1 is drawn in TikZ inside `main.tex`.

## Build

```powershell
pwsh -File paper/build.ps1
```

This regenerates tables and figures with the pinned analysis interpreter and runs `latexmk`
(TeX Live). Prose numbers in `main.tex` were checked against the artifacts when the draft was
written; if an artifact changes, rerun the scripts and re-read the prose around the affected
section.

## Release policy

No candidate unregistered package name appears in the manuscript, the tables, the figures, or
the generator scripts.
