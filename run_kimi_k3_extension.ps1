# Resumable Kimi K3 Ollama Cloud extension.
# Smoke: pwsh -File run_kimi_k3_extension.ps1 -Mode smoke
# Full:  pwsh -File run_kimi_k3_extension.ps1 -Mode full
#Requires -Version 7

[CmdletBinding()]
param(
    [ValidateSet("smoke", "full")]
    [string]$Mode = "smoke",
    [string]$BaseUrl = "http://localhost:11434",
    [string]$Python = "C:\Users\JacobAnderson\miniconda3\envs\trading\python.exe",
    [int]$Workers = 2,
    [double]$SmokeBudgetUsd = 0.50,
    [double]$FullBudgetUsd = 94.50
)

$ErrorActionPreference = "Stop"
$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $workspace
$model = "kimi-k3:cloud"

if ($Mode -eq "smoke") {
    $subsetArgs = @("--limit", "1")
    $name = "smoke_ollama_kimi-k3-cloud_v2"
    $budget = $SmokeBudgetUsd
} else {
    $subsetArgs = @("--sample", "200", "--seed", "0")
    $name = "trackD_ollama_kimi-k3-cloud"
    $budget = $FullBudgetUsd
}

$showBody = @{ model = $model } | ConvertTo-Json -Compress
$show = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/show" `
    -Body $showBody -ContentType "application/json" -TimeoutSec 30
$identity = [ordered]@{
    requested = $model
    modified_at = $show.modified_at
    details = $show.details
    model_info = $show.model_info
}
Write-Output ($identity | ConvertTo-Json -Depth 8)

$arguments = @(
    "run_test_api.py", "ollama:$model",
    "--base-url", $BaseUrl,
    "--language", "Python",
    "--max-code-tokens", "4096",
    "--max-package-tokens", "2048",
    "--workers", "$Workers",
    "--extra-body", '{"think":false}',
    "--input-cost-per-million", "3.0",
    "--output-cost-per-million", "15.0",
    "--budget-usd", "$budget",
    "--fail-on-error",
    "--name", $name
) + $subsetArgs

Write-Output "Kimi K3 extension: mode=$Mode budget=$budget -> Tests/${name}_Python"
& $Python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Kimi K3 exited with code $LASTEXITCODE; rerun the same command to resume."
}

if ($Mode -eq "full") {
    & $Python score_kimi_k3_extension.py
    if ($LASTEXITCODE -ne 0) {
        throw "Kimi K3 scoring exited with code $LASTEXITCODE."
    }
    & $Python build_ollama_artifact_index.py
    if ($LASTEXITCODE -ne 0) {
        throw "Ollama artifact indexing exited with code $LASTEXITCODE."
    }
    & $Python build_ollama_artifact_index.py --verify
    if ($LASTEXITCODE -ne 0) {
        throw "Ollama artifact verification exited with code $LASTEXITCODE."
    }
}

Write-Output "Kimi K3 extension complete: mode=$Mode"
