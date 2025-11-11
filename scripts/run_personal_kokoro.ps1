Param(
    [Parameter(Mandatory = $true)][string]$InputFile,
    [string]$PipelineJson = "..\pipeline.json"
)

$ErrorActionPreference = "Stop"

# Determine repo root relative to script location
$repoRoot = Split-Path $PSScriptRoot -Parent
Write-Host "Repo root:" $repoRoot
Set-Location $repoRoot

$cleanupTargets = @(
    "phase2-extraction\extracted_text",
    "phase3-chunking\chunks",
    "phase4_tts\audio_chunks",
    "phase4_tts_styletts\audio_chunks",
    "phase5_enhancement\processed",
    "phase5_enhancement\subtitles"
)

Write-Host "Cleaning generated artifacts..."
foreach ($target in $cleanupTargets) {
    if (Test-Path $target) {
        Get-ChildItem $target -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
}
Remove-Item pipeline.json -Force -ErrorAction SilentlyContinue
Remove-Item .pipeline -Recurse -Force -ErrorAction SilentlyContinue

if (-not (Test-Path "phase4_tts")) {
    throw "Phase 4 directory (phase4_tts) is missing. Please restore it before running."
}

$resolvedInput = (Resolve-Path $InputFile).Path
if ([System.IO.Path]::IsPathRooted($PipelineJson)) {
    $resolvedJson = $PipelineJson
} elseif (Test-Path $PipelineJson) {
    $resolvedJson = (Resolve-Path $PipelineJson).Path
} else {
    $resolvedJson = Join-Path $repoRoot $PipelineJson
}
Write-Host "Input file:" $resolvedInput
Write-Host "Pipeline JSON:" $resolvedJson

Set-Location "$repoRoot\phase6_orchestrator"
Write-Host "Starting orchestrator run..."
poetry run python orchestrator.py $resolvedInput --pipeline-json $resolvedJson
