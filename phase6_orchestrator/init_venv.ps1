$ErrorActionPreference = "Stop"

$pythonExe = "C:\Program Files\Python311\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Error "Python 3.11 not found at $pythonExe"
    exit 1
}

$venvPath = Join-Path $PSScriptRoot ".venv"
if (Test-Path $venvPath) {
    Remove-Item -Recurse -Force $venvPath
}

& $pythonExe -m venv $venvPath
$venvPython = Join-Path $venvPath "Scripts\python.exe"

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install poetry

$poetryExe = Join-Path $venvPath "Scripts\poetry.exe"
Push-Location $PSScriptRoot
try {
    & $poetryExe install
} finally {
    Pop-Location
}

Write-Host "phase6_orchestrator virtual environment ready." -ForegroundColor Green
