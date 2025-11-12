#Requires -Version 5.1
<#
.SYNOPSIS
    Fix remaining Quick Wins issues (DeepFilterNet + OpenVoice)

.DESCRIPTION
    Fixes the two remaining issues from setup_excellence.ps1:
    1. DeepFilterNet import error (torchaudio backend)
    2. OpenVoice installation/import error

.EXAMPLE
    .\fix_remaining_issues.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# Colors for beautiful output
function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan -NoNewline
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Success {
    param([string]$Text)
    Write-Host "✅ $Text" -ForegroundColor Green
}

function Write-Info {
    param([string]$Text)
    Write-Host "ℹ️  $Text" -ForegroundColor Cyan
}

function Write-Warning {
    param([string]$Text)
    Write-Host "⚠️  $Text" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Text)
    Write-Host "❌ $Text" -ForegroundColor Red
}

Write-Header "🔧 Fixing Remaining Quick Wins Issues"

Write-Info "This will fix DeepFilterNet and OpenVoice"
Write-Info "Estimated time: 5 minutes"
Write-Host ""

# ============================================================================
# Fix 1: DeepFilterNet (torchaudio backend issue)
# ============================================================================

Write-Header "1️⃣ Fixing DeepFilterNet"

Write-Info "Upgrading torchaudio to fix backend compatibility..."

try {
    $output = pip install --upgrade torchaudio 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "torchaudio upgraded successfully"
    } else {
        Write-Warning "torchaudio upgrade returned non-zero exit code"
    }
} catch {
    Write-Error-Custom "Failed to upgrade torchaudio: $_"
}

Write-Info "Testing DeepFilterNet import..."

$testCode = @"
try:
    from df import enhance, init_df
    print('DeepFilterNet OK!')
    exit(0)
except Exception as e:
    print(f'Failed: {e}')
    exit(1)
"@

$result = python -c $testCode 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Success "DeepFilterNet working! $result"
} else {
    Write-Warning "DeepFilterNet still has issues: $result"
    Write-Info "You can still create audiobooks without DeepFilterNet"
    Write-Info "The noise reduction is optional"
}

# ============================================================================
# Fix 2: OpenVoice v2 (proper installation)
# ============================================================================

Write-Header "2️⃣ Fixing OpenVoice v2"

Write-Info "Reinstalling OpenVoice with proper editable install..."

$tempDir = $env:TEMP
$openVoicePath = Join-Path $tempDir "OpenVoice"

# Remove old installation
if (Test-Path $openVoicePath) {
    Write-Info "Removing old OpenVoice installation..."
    Remove-Item $openVoicePath -Recurse -Force -ErrorAction SilentlyContinue
}

# Clone fresh
Write-Info "Cloning OpenVoice repository..."
try {
    Push-Location $tempDir
    $output = git clone https://github.com/myshell-ai/OpenVoice 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "OpenVoice cloned successfully"
    } else {
        Write-Warning "Git clone returned non-zero exit code"
    }
} catch {
    Write-Error-Custom "Failed to clone OpenVoice: $_"
    Pop-Location
    exit 1
}

# Install in editable mode
Write-Info "Installing OpenVoice in editable mode..."
try {
    Push-Location $openVoicePath
    $output = pip install -e . 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "OpenVoice installed successfully"
    } else {
        Write-Warning "pip install returned non-zero exit code"
    }
    Pop-Location
} catch {
    Write-Error-Custom "Failed to install OpenVoice: $_"
    Pop-Location
    Pop-Location
    exit 1
}

Pop-Location

# Test import
Write-Info "Testing OpenVoice import..."

$testCode = @"
try:
    from openvoice import se_extractor
    from openvoice.api import ToneColorConverter
    print('OpenVoice v2 OK!')
    exit(0)
except Exception as e:
    print(f'Failed: {e}')
    exit(1)
"@

$result = python -c $testCode 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Success "OpenVoice working! $result"
} else {
    Write-Warning "OpenVoice still has issues: $result"
    Write-Info "You can still create audiobooks with F5-TTS"
    Write-Info "OpenVoice adds emotion control (optional)"
}

# ============================================================================
# Final Test: Run complete test suite
# ============================================================================

Write-Header "🧪 Running Complete Test Suite"

Write-Info "Testing all Quick Wins components..."

if (Test-Path "test_quick_wins.py") {
    python test_quick_wins.py
} else {
    Write-Warning "test_quick_wins.py not found, skipping comprehensive test"
}

# ============================================================================
# Summary
# ============================================================================

Write-Header "✨ Setup Complete!"

Write-Success "Core system ready:"
Write-Info "  • F5-TTS (superior quality)"
Write-Info "  • Pedalboard (pro mastering)"
Write-Info "  • Gradio UI (beautiful interface)"
Write-Info "  • Silero VAD (surgical crossfades)"
Write-Host ""

Write-Info "To launch the UI:"
Write-Host "  cd ui" -ForegroundColor Yellow
Write-Host "  python app.py" -ForegroundColor Yellow
Write-Host ""

Write-Info "Then open: http://localhost:7860"
Write-Host ""

Write-Success "You're ready to create insanely great audiobooks! 🎉"
Write-Host ""
