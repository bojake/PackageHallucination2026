# Rebuild the manuscript from the committed artifacts.
#   pwsh -File paper/build.ps1
# Tables and figures are regenerated from Experiments/*.json; Figure 5 additionally needs the
# git-ignored raw responses under Tests/ and silently keeps the committed PDF when they are absent.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = "C:\Users\JacobAnderson\miniconda3\envs\trading\python.exe"
if (-not (Test-Path $python)) { $python = "python" }
Push-Location $root
try {
    & $python paper/build_tables.py
    & $python paper/make_figures.py
    Push-Location (Join-Path $root "paper")
    try {
        latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
    } finally {
        Pop-Location
    }
} finally {
    Pop-Location
}
