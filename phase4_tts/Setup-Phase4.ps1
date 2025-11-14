#Requires -Version 5.1
<#
.SYNOPSIS
    Phase 4 Multi-Engine TTS Setup with Auto-Elevation

.DESCRIPTION
    Sets up Phase 4 TTS with automatic admin rights prompt.
    Double-click this file to run.

.NOTES
    This will request admin rights via UAC dialog if needed.
#>

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host ""
    Write-Host "========================================================================" -ForegroundColor Yellow
    Write-Host "  Administrator Rights Required" -ForegroundColor Yellow
    Write-Host "========================================================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "This setup needs admin rights to install Python packages."
    Write-Host "A UAC prompt will appear - please click 'Yes'"
    Write-Host ""
    Write-Host "Press any key to continue..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

    # Re-launch this script with admin rights
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Now running with admin rights
$Host.UI.RawUI.WindowTitle = "Phase 4 Setup (Administrator)"

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  Phase 4 Multi-Engine TTS Setup" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Running with administrator privileges..." -ForegroundColor Green
Write-Host ""

# Get script directory
$ScriptDir = Split-Path -Parent $PSCommandPath
Set-Location $ScriptDir

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found in PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python 3.8+ and add it to PATH."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Remove old venv if exists
if (Test-Path ".venv") {
    Write-Host "[INFO] Removing old virtual environment..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force .venv
}

# Create venv
Write-Host "[INFO] Creating virtual environment..." -ForegroundColor Cyan
python -m venv .venv

if (-not (Test-Path ".venv\Scripts\activate.ps1")) {
    Write-Host "[ERROR] Failed to create virtual environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OK] Virtual environment created" -ForegroundColor Green
Write-Host ""

# Activate venv
& .venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "[INFO] Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip --quiet

# Install core dependencies
Write-Host "[INFO] Installing core dependencies (torch, numpy, soundfile, pyyaml)..." -ForegroundColor Cyan
Write-Host "[INFO] This may take a few minutes..." -ForegroundColor Yellow

$installResult = pip install torch numpy soundfile pyyaml 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to install core dependencies" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error details:" -ForegroundColor Yellow
    Write-Host $installResult
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OK] Core dependencies installed" -ForegroundColor Green
Write-Host ""

# Engine selection
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  TTS Engine Installation (Optional)" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Which engines would you like to install?"
Write-Host ""
Write-Host "1. XTTS v2 (Expressive, recommended)" -ForegroundColor Green
Write-Host "2. Kokoro-onnx (CPU-friendly backup)"
Write-Host "3. Both XTTS + Kokoro"
Write-Host "4. Skip (install later)"
Write-Host ""

$choice = Read-Host "Enter choice (1-4)"

switch ($choice) {
    "1" {
        Write-Host "[INFO] Installing XTTS v2..." -ForegroundColor Cyan
        pip install TTS
    }
    "2" {
        Write-Host "[INFO] Installing Kokoro..." -ForegroundColor Cyan
        pip install kokoro-onnx
    }
    "3" {
        Write-Host "[INFO] Installing XTTS v2 + Kokoro..." -ForegroundColor Cyan
        pip install TTS kokoro-onnx
    }
    "4" {
        Write-Host "[INFO] Skipping engine installation" -ForegroundColor Yellow
    }
    default {
        Write-Host "[WARN] Unknown choice. Skipping engine installation." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Virtual environment: phase4_tts\.venv" -ForegroundColor White
Write-Host ""
Write-Host "To test:" -ForegroundColor Yellow
Write-Host "  cd phase4_tts" -ForegroundColor White
Write-Host "  .venv\Scripts\activate" -ForegroundColor White
Write-Host "  python -c `"import yaml; print('Dependencies OK!')`"" -ForegroundColor White
Write-Host ""
Write-Host "You can now use the multi-engine TTS from the UI!" -ForegroundColor Green
Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""

Read-Host "Press Enter to exit"
