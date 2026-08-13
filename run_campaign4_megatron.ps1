# Campaign 4 GPU pipeline for megatron (PREREGISTRATION_v4.md phases 2-4, serialized).
# Everything here is resumable: re-running the script skips completed work.
#   pwsh -File run_campaign4_megatron.ps1
#
# REQUIRES PowerShell 7+ (pwsh). Windows PowerShell 5.1 mangles the embedded double
# quotes in --extra-body JSON arguments, which silently fails every run.
#Requires -Version 7

$ErrorActionPreference = "Continue"
$py = "$env:USERPROFILE\miniconda3\envs\imagegen\python.exe"
Set-Location "C:\MachineLearning\github\PackageHallucination"

function Step($name, $block) {
    Write-Output "`n########## $name  ($(Get-Date -Format s)) ##########"
    & $block
    if ($LASTEXITCODE -ne 0) { Write-Output "!! $name exited $LASTEXITCODE (continuing; runs are resumable)" }
}

# ---- Phase 2: controlled cap diagnostic (not internally resumable -- skip if complete) ----
$capSummary = "Experiments/cap_diagnostic_summary.json"
if ((Test-Path $capSummary) -and ((Get-Content $capSummary -Raw) -match "deepseek-coder-v2:16b")) {
    Write-Output "Phase 2 already complete (both cells in $capSummary) -- skipping."
} else {
    Step "Phase 2: cap diagnostic" { & $py cap_diagnostic.py }
}

# ---- Phase 3: Track A -- 2 historical models x 3 seeds, paper protocol ----
foreach ($m in @("codellama:7b-instruct", "deepseek-coder:6.7b-instruct")) {
    foreach ($s in @(101, 102, 103)) {
        $slug = ($m -replace "[:.]", "_")
        Step "Track A: $m seed $s" {
            & $py run_test_api.py "ollama:$m" --base-url http://megatron:11434 `
                --language Python --sample 200 --seed 0 `
                --max-code-tokens 2048 --max-package-tokens 64 --workers 1 `
                --extra-body ('{"options":{"seed":' + $s + ',"num_ctx":12288}}') `
                --name ("trackA_" + $slug + "_s" + $s)
        }
    }
}

# ---- Phase 4 (local GPU cell): DeepSeek Coder V2 Lite under the modern protocol ----
Step "Track B: deepseek-coder-v2:16b" {
    & $py run_test_api.py ollama:deepseek-coder-v2:16b --base-url http://megatron:11434 `
        --language Python --sample 200 --seed 0 `
        --max-code-tokens 4096 --max-package-tokens 2048 --workers 2 `
        --extra-body '{"options":{"num_ctx":12288}}' `
        --name trackB_deepseek-coder-v2_16b
}

Write-Output "`n########## megatron pipeline complete ($(Get-Date -Format s)) ##########"
