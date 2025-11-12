#Requires -Version 5.1
<#
.SYNOPSIS
    Personal Audiobook Studio Launcher (PowerShell)

.DESCRIPTION
    Double-click launcher for the Audiobook Studio UI.
    Checks for port conflicts and provides better error handling.
#>

# Set error action
$ErrorActionPreference = "Stop"

# Set window title
$Host.UI.RawUI.WindowTitle = "Personal Audiobook Studio"

# Set colors
$HeaderColor = "Cyan"
$SuccessColor = "Green"
$ErrorColor = "Red"
$InfoColor = "Yellow"

Clear-Host

Write-Host ""
Write-Host "========================================================================" -ForegroundColor $HeaderColor
Write-Host "  Personal Audiobook Studio" -ForegroundColor $HeaderColor
Write-Host "========================================================================" -ForegroundColor $HeaderColor
Write-Host ""
Write-Host "Starting the studio... This may take a moment."
Write-Host ""

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$UIDir = Join-Path $ScriptDir "ui"

# Check if UI directory exists
if (-not (Test-Path $UIDir)) {
    Write-Host "[ERROR] UI directory not found: $UIDir" -ForegroundColor $ErrorColor
    Write-Host ""
    Write-Host "Please ensure you're running this from the project root."
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python found: $pythonVersion" -ForegroundColor $SuccessColor
} catch {
    Write-Host "[ERROR] Python not found in PATH" -ForegroundColor $ErrorColor
    Write-Host ""
    Write-Host "Please install Python 3.8+ or ensure it's in your PATH."
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if port 7860 is in use
$portInUse = Get-NetTCPConnection -LocalPort 7860 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host ""
    Write-Host "========================================================================" -ForegroundColor $InfoColor
    Write-Host "  WARNING: Port 7860 is already in use!" -ForegroundColor $InfoColor
    Write-Host "========================================================================" -ForegroundColor $InfoColor
    Write-Host ""
    Write-Host "The studio might already be running in another window."
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  1. Check for other terminal windows running the studio"
    Write-Host "  2. Close them and try again"
    Write-Host "  3. Or open http://localhost:7860 in your browser"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if app.py exists
$AppPath = Join-Path $UIDir "app.py"
if (-not (Test-Path $AppPath)) {
    Write-Host "[ERROR] app.py not found: $AppPath" -ForegroundColor $ErrorColor
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OK] Found UI application" -ForegroundColor $SuccessColor
Write-Host ""

Write-Host ""
Write-Host "========================================================================" -ForegroundColor $HeaderColor
Write-Host "  Launching Studio" -ForegroundColor $HeaderColor
Write-Host "========================================================================" -ForegroundColor $HeaderColor
Write-Host ""

Write-Host "[INFO] The UI will open at: http://localhost:7860" -ForegroundColor $InfoColor
Write-Host "[INFO] Opening browser in 3 seconds..." -ForegroundColor $InfoColor
Write-Host ""

# Change to UI directory
Set-Location $UIDir

# Wait and open browser
Start-Sleep -Seconds 3
try {
    Start-Process "http://localhost:7860"
    Write-Host "[OK] Browser opened!" -ForegroundColor $SuccessColor
} catch {
    Write-Host "[INFO] Please manually open: http://localhost:7860" -ForegroundColor $InfoColor
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor $HeaderColor
Write-Host "  Studio is Running!" -ForegroundColor $HeaderColor
Write-Host "========================================================================" -ForegroundColor $HeaderColor
Write-Host ""
Write-Host "  URL: http://localhost:7860" -ForegroundColor White
Write-Host ""
Write-Host "[!] Keep this window open while using the studio" -ForegroundColor $InfoColor
Write-Host "[!] Press Ctrl+C to stop the server" -ForegroundColor $InfoColor
Write-Host ""
Write-Host "========================================================================" -ForegroundColor $HeaderColor
Write-Host ""

# Start Python server (this will block until server stops)
try {
    python app.py
} catch {
    Write-Host ""
    Write-Host "[ERROR] Server stopped unexpectedly" -ForegroundColor $ErrorColor
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor $HeaderColor
Write-Host "  Studio has stopped" -ForegroundColor $HeaderColor
Write-Host "========================================================================" -ForegroundColor $HeaderColor
Write-Host ""
Read-Host "Press Enter to exit"
