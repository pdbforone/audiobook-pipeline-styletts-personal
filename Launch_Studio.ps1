#Requires -Version 5.1
<#
.SYNOPSIS
    Personal Audiobook Studio Launcher (PowerShell)

.DESCRIPTION
    Double-click launcher for the Audiobook Studio UI.
    Alternative to the .bat launcher with better error handling.
#>

# Set window title
$Host.UI.RawUI.WindowTitle = "🎙️ Personal Audiobook Studio"

# Set colors
$HeaderColor = "Cyan"
$SuccessColor = "Green"
$ErrorColor = "Red"
$InfoColor = "Yellow"

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "========================================================================" -ForegroundColor $HeaderColor
    Write-Host "  $Text" -ForegroundColor $HeaderColor
    Write-Host "========================================================================" -ForegroundColor $HeaderColor
    Write-Host ""
}

function Write-Success {
    param([string]$Text)
    Write-Host "✓ $Text" -ForegroundColor $SuccessColor
}

function Write-ErrorMsg {
    param([string]$Text)
    Write-Host "❌ $Text" -ForegroundColor $ErrorColor
}

function Write-Info {
    param([string]$Text)
    Write-Host "📝 $Text" -ForegroundColor $InfoColor
}

# Clear screen
Clear-Host

Write-Header "🎙️ Personal Audiobook Studio"

Write-Host "Starting the studio... This may take a moment."
Write-Host ""

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$UIDir = Join-Path $ScriptDir "ui"

# Check if UI directory exists
if (-not (Test-Path $UIDir)) {
    Write-ErrorMsg "UI directory not found: $UIDir"
    Write-Host ""
    Write-Host "Please ensure you're running this from the project root."
    Write-Host ""
    pause
    exit 1
}

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python found: $pythonVersion"
} catch {
    Write-ErrorMsg "Python not found in PATH"
    Write-Host ""
    Write-Host "Please install Python 3.8+ or ensure it's in your PATH."
    Write-Host ""
    pause
    exit 1
}

# Check if app.py exists
$AppPath = Join-Path $UIDir "app.py"
if (-not (Test-Path $AppPath)) {
    Write-ErrorMsg "app.py not found: $AppPath"
    Write-Host ""
    pause
    exit 1
}

Write-Success "Found UI application"
Write-Host ""

Write-Header "✅ Launching Studio"

Write-Info "The UI will open at: http://localhost:7860"
Write-Info "Opening browser in 3 seconds..."
Write-Host ""

# Start the UI server
Set-Location $UIDir

# Launch Python in background
$job = Start-Job -ScriptBlock {
    param($AppPath)
    python $AppPath
} -ArgumentList $AppPath

# Wait for server to start
Start-Sleep -Seconds 3

# Open browser
try {
    Start-Process "http://localhost:7860"
    Write-Success "Browser opened!"
} catch {
    Write-Info "Please manually open: http://localhost:7860"
}

Write-Host ""
Write-Header "✅ Studio is Running!"

Write-Host ""
Write-Host "  URL: http://localhost:7860" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host ""
Write-Info "Keep this window open while using the studio"
Write-Info "Press Ctrl+C to stop the server"
Write-Host ""
Write-Host "========================================================================" -ForegroundColor $HeaderColor
Write-Host ""

# Wait for job and show output
try {
    Receive-Job -Job $job -Wait -ErrorAction Stop
} catch {
    Write-ErrorMsg "Server stopped unexpectedly"
}

# Cleanup
Remove-Job -Job $job -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Header "Studio has stopped"
Write-Host ""
pause
