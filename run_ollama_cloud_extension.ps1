# Resumable Qwen/Kimi Ollama Cloud extension.
#
# Smoke gate (separate, non-analytic outputs):
#   pwsh -File run_ollama_cloud_extension.ps1 -Mode smoke
# Full frozen sample:
#   pwsh -File run_ollama_cloud_extension.ps1 -Mode full
# Remote daemon used for Campaign 4:
#   pwsh -File run_ollama_cloud_extension.ps1 -Mode full -BaseUrl http://megatron:11434
#Requires -Version 7

[CmdletBinding()]
param(
    [ValidateSet("smoke", "full")]
    [string]$Mode = "smoke",
    [string]$BaseUrl = "http://localhost:11434",
    [string]$Python = "python",
    [int]$Workers = 2,
    [string[]]$Models = @("qwen3.5:cloud", "kimi-k3:cloud")
)

$ErrorActionPreference = "Stop"
$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $workspace

if ($Mode -eq "smoke") {
    $subsetArgs = @("--limit", "1")
    $namePrefix = "smoke_ollama_"
} else {
    $subsetArgs = @("--sample", "200", "--seed", "0")
    $namePrefix = "trackC_ollama_"
}

Write-Output "Ollama Cloud extension: mode=$Mode base=$BaseUrl workers=$Workers"

foreach ($model in $Models) {
    $showBody = @{ model = $model } | ConvertTo-Json -Compress
    try {
        $show = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/show" `
            -Body $showBody -ContentType "application/json" -TimeoutSec 30
        $identity = [ordered]@{
            requested = $model
            modified_at = $show.modified_at
            details = $show.details
            model_info = $show.model_info
        }
        Write-Output ($identity | ConvertTo-Json -Depth 8)
    } catch {
        Write-Output "Identity probe failed for ${model}: $($_.Exception.Message)"
        throw
    }

    $slug = $model -replace "[:.]", "-"
    $name = "$namePrefix$slug"
    $arguments = @(
        "run_test_api.py", "ollama:$model",
        "--base-url", $BaseUrl,
        "--language", "Python",
        "--max-code-tokens", "4096",
        "--max-package-tokens", "2048",
        "--workers", "$Workers",
        "--extra-body", '{"think":false}',
        "--fail-on-error",
        "--name", $name
    ) + $subsetArgs

    Write-Output "Starting $model -> Tests/${name}_Python"
    & $Python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$model exited with code $LASTEXITCODE; rerun the same command to resume."
    }
}

if ($Mode -eq "full") {
    & $Python score_ollama_cloud_extension.py
    if ($LASTEXITCODE -ne 0) {
        throw "Extension scoring exited with code $LASTEXITCODE."
    }
    & $Python churilov_bridge_analysis.py
    if ($LASTEXITCODE -ne 0) {
        throw "Churilov bridge refresh exited with code $LASTEXITCODE."
    }
}

Write-Output "Ollama Cloud extension complete: mode=$Mode"
