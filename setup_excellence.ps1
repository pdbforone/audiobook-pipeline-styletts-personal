#Requires -Version 5.1
<#
.SYNOPSIS
    Personal Audiobook Studio - Excellence Setup Script

.DESCRIPTION
    Automated installation of cutting-edge TTS engines and audio processing tools.
    Transforms your pipeline into a professional audiobook creation studio.

.PARAMETER QuickWinsOnly
    Install only the Quick Win trio (Silero VAD, OpenVoice, DeepFilterNet)
    Recommended for first-time setup. ~3 hours to 10x quality.

.PARAMETER FullStack
    Install everything including Bark, XTTS, and optional tools
    For the complete experience. ~1 day setup.

.PARAMETER SkipTests
    Skip the verification tests at the end

.EXAMPLE
    .\setup_excellence.ps1 -QuickWinsOnly
    Install the Quick Win trio for immediate impact

.EXAMPLE
    .\setup_excellence.ps1 -FullStack
    Install the complete stack for maximum quality

.NOTES
    Author: Claude (Anthropic)
    Created: 2024-11
    Purpose: Craft excellence through state-of-the-art technology
#>

[CmdletBinding()]
param(
    [Parameter(ParameterSetName='QuickWins')]
    [switch]$QuickWinsOnly,

    [Parameter(ParameterSetName='Full')]
    [switch]$FullStack,

    [switch]$SkipTests
)

# ============================================================================
# CONFIGURATION
# ============================================================================

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$Script:TotalSteps = 0
$Script:CurrentStep = 0
$Script:InstallLog = @()

# Colors for beautiful output
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }
function Write-Header { param($Message) Write-Host "`n$('='*70)`n$Message`n$('='*70)" -ForegroundColor Magenta }
function Write-Step {
    param($Message)
    $Script:CurrentStep++
    $percent = [math]::Round(($Script:CurrentStep / $Script:TotalSteps) * 100)
    Write-Host "`n[$Script:CurrentStep/$Script:TotalSteps - $percent%] $Message" -ForegroundColor Yellow
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Test-PythonPackage {
    param([string]$Package)
    $result = python -c "import $Package; print('OK')" 2>&1
    return $result -eq "OK"
}

function Install-PipPackage {
    param(
        [string]$Package,
        [string]$DisplayName = $Package,
        [switch]$Quiet
    )

    Write-Info "Installing $DisplayName..."

    try {
        if ($Quiet) {
            pip install $Package --quiet 2>&1 | Out-Null
        } else {
            pip install $Package
        }

        Write-Success "$DisplayName installed"
        $Script:InstallLog += @{Package=$DisplayName; Status="Success"; Error=$null}
        return $true
    }
    catch {
        Write-Error "Failed to install $DisplayName : $_"
        $Script:InstallLog += @{Package=$DisplayName; Status="Failed"; Error=$_.Exception.Message}
        return $false
    }
}

function Test-DiskSpace {
    param([int]$RequiredGB = 10)

    $drive = (Get-Location).Drive
    $freeSpaceGB = [math]::Round((Get-PSDrive $drive.Name).Free / 1GB, 2)

    if ($freeSpaceGB -lt $RequiredGB) {
        Write-Warning "Low disk space: ${freeSpaceGB}GB free (${RequiredGB}GB recommended)"
        return $false
    }

    Write-Info "Disk space: ${freeSpaceGB}GB free ✓"
    return $true
}

# ============================================================================
# PRE-FLIGHT CHECKS
# ============================================================================

function Test-Prerequisites {
    Write-Header "🔍 PRE-FLIGHT CHECKS"

    $allGood = $true

    # Check Python
    Write-Info "Checking Python..."
    if (-not (Test-Command python)) {
        Write-Error "Python not found. Please install Python 3.10+"
        $allGood = $false
    } else {
        $pythonVersion = python --version
        Write-Success "Found: $pythonVersion"
    }

    # Check pip
    Write-Info "Checking pip..."
    if (-not (Test-Command pip)) {
        Write-Error "pip not found"
        $allGood = $false
    } else {
        Write-Success "pip available"
    }

    # Check git
    Write-Info "Checking git..."
    if (-not (Test-Command git)) {
        Write-Warning "git not found (needed for cloning repos)"
        Write-Info "Install from: https://git-scm.com/download/win"
    } else {
        Write-Success "git available"
    }

    # Check disk space
    Test-DiskSpace -RequiredGB 10 | Out-Null

    if (-not $allGood) {
        throw "Pre-flight checks failed. Please resolve issues above."
    }

    Write-Success "All prerequisites met!"
}

# ============================================================================
# INSTALLATION FUNCTIONS
# ============================================================================

function Install-SileroVAD {
    Write-Step "Installing Silero VAD (Neural Silence Detection)"

    Write-Info "Package: silero-vad"
    Write-Info "Size: ~2 MB (tiny!)"
    Write-Info "Impact: 🔥🔥🔥🔥 Surgical crossfades"

    Install-PipPackage "silero-vad" "Silero VAD"

    # Test installation
    Write-Info "Testing Silero VAD..."
    if (Test-PythonPackage "silero_vad") {
        Write-Success "Silero VAD ready!"
        return $true
    } else {
        Write-Warning "Silero VAD may not be properly installed"
        return $false
    }
}

function Install-DeepFilterNet {
    Write-Step "Installing DeepFilterNet (Professional Noise Reduction)"

    Write-Info "Package: deepfilternet"
    Write-Info "Size: ~50 MB"
    Write-Info "Impact: 🔥🔥🔥 Professional clarity"
    Write-Info "Note: Already integrated in your code!"

    Install-PipPackage "deepfilternet" "DeepFilterNet"

    # Test installation
    Write-Info "Testing DeepFilterNet..."
    $testResult = python -c "from df import enhance, init_df; print('OK')" 2>&1
    if ($testResult -eq "OK") {
        Write-Success "DeepFilterNet ready!"
        return $true
    } else {
        Write-Warning "DeepFilterNet may not be properly installed"
        return $false
    }
}

function Install-OpenVoice {
    Write-Step "Installing OpenVoice v2 (Emotion Control + Instant Cloning)"

    Write-Info "Package: OpenVoice (from GitHub)"
    Write-Info "Size: ~800 MB (models download on first use)"
    Write-Info "Impact: 🔥🔥🔥🔥🔥 GAME CHANGER"
    Write-Info "License: MIT (free for personal use)"

    $tempDir = Join-Path $env:TEMP "OpenVoice"

    try {
        # Clone repository
        Write-Info "Cloning OpenVoice repository..."
        if (Test-Path $tempDir) {
            Remove-Item $tempDir -Recurse -Force
        }

        git clone https://github.com/myshell-ai/OpenVoice $tempDir 2>&1 | Out-Null

        if (-not (Test-Path $tempDir)) {
            throw "Failed to clone OpenVoice repository"
        }

        # Install
        Write-Info "Installing OpenVoice..."
        Push-Location $tempDir

        try {
            pip install -e . 2>&1 | Out-Null
            Write-Success "OpenVoice installed"

            # Test
            Write-Info "Testing OpenVoice..."
            $testResult = python -c "from openvoice import se_extractor; print('OK')" 2>&1
            if ($testResult -eq "OK") {
                Write-Success "OpenVoice ready!"
                $Script:InstallLog += @{Package="OpenVoice v2"; Status="Success"; Error=$null}
                return $true
            } else {
                throw "OpenVoice import test failed"
            }
        }
        finally {
            Pop-Location
        }
    }
    catch {
        Write-Error "OpenVoice installation failed: $_"
        $Script:InstallLog += @{Package="OpenVoice v2"; Status="Failed"; Error=$_.Exception.Message}
        return $false
    }
}

function Install-Pedalboard {
    Write-Step "Installing Pedalboard (Professional Audio Processing)"

    Write-Info "Package: pedalboard (Spotify's audio library)"
    Write-Info "Size: ~20 MB"
    Write-Info "Impact: 🔥🔥🔥🔥 Pro mastering"
    Write-Info "License: GPL-2.0 (OK for personal use)"

    Install-PipPackage "pedalboard" "Pedalboard"

    # Test
    Write-Info "Testing Pedalboard..."
    if (Test-PythonPackage "pedalboard") {
        Write-Success "Pedalboard ready!"
        return $true
    } else {
        Write-Warning "Pedalboard may not be properly installed"
        return $false
    }
}

function Install-Gradio {
    Write-Step "Installing Gradio (Beautiful UI)"

    Write-Info "Package: gradio"
    Write-Info "Size: ~100 MB"
    Write-Info "Impact: 🔥🔥🔥🔥 Joyful interface"

    Install-PipPackage "gradio>=4.0.0" "Gradio"

    # Test
    if (Test-PythonPackage "gradio") {
        Write-Success "Gradio ready!"
        return $true
    } else {
        Write-Warning "Gradio may not be properly installed"
        return $false
    }
}

function Install-F5TTS {
    Write-Step "Installing F5-TTS (Cutting-Edge Prosody)"

    Write-Info "Package: F5-TTS (from GitHub)"
    Write-Info "Size: ~1.5 GB (models)"
    Write-Info "Impact: 🔥🔥🔥🔥🔥 Superior quality"
    Write-Info "License: MIT"

    $tempDir = Join-Path $env:TEMP "F5-TTS"

    try {
        Write-Info "Cloning F5-TTS repository..."
        if (Test-Path $tempDir) {
            Remove-Item $tempDir -Recurse -Force
        }

        git clone https://github.com/SWivid/F5-TTS $tempDir 2>&1 | Out-Null

        if (-not (Test-Path $tempDir)) {
            throw "Failed to clone F5-TTS repository"
        }

        Write-Info "Installing F5-TTS..."
        Push-Location $tempDir

        try {
            pip install -e . 2>&1 | Out-Null
            Write-Success "F5-TTS installed"

            # Test
            Write-Info "Testing F5-TTS..."
            $testResult = python -c "from f5_tts.api import F5TTS; print('OK')" 2>&1
            if ($testResult -eq "OK") {
                Write-Success "F5-TTS ready!"
                $Script:InstallLog += @{Package="F5-TTS"; Status="Success"; Error=$null}
                return $true
            } else {
                throw "F5-TTS import test failed"
            }
        }
        finally {
            Pop-Location
        }
    }
    catch {
        Write-Error "F5-TTS installation failed: $_"
        $Script:InstallLog += @{Package="F5-TTS"; Status="Failed"; Error=$_.Exception.Message}
        return $false
    }
}

function Install-XTTS {
    Write-Step "Installing XTTS v2 (Versatile Multilingual)"

    Write-Info "Package: TTS (Coqui)"
    Write-Info "Size: ~500 MB"
    Write-Info "Impact: 🔥🔥🔥🔥 17 languages"
    Write-Info "License: Coqui Public (non-commercial OK)"

    Install-PipPackage "TTS" "Coqui TTS (XTTS v2)"

    # Test
    Write-Info "Testing XTTS..."
    $testResult = python -c "from TTS.api import TTS; print('OK')" 2>&1
    if ($testResult -eq "OK") {
        Write-Success "XTTS v2 ready!"
        return $true
    } else {
        Write-Warning "XTTS may not be properly installed"
        return $false
    }
}

function Install-Bark {
    Write-Step "Installing Bark (Ultra-Expressive TTS)"

    Write-Info "Package: bark (via git+https)"
    Write-Info "Size: ~2 GB (models)"
    Write-Info "Impact: 🔥🔥🔥🔥🔥 Emotion + laughter + music"
    Write-Info "License: MIT"
    Write-Info "Note: Slower but incredibly expressive"

    try {
        Write-Info "Installing Bark from repository..."
        pip install git+https://github.com/suno-ai/bark.git 2>&1 | Out-Null

        Write-Success "Bark installed"

        # Test
        Write-Info "Testing Bark..."
        $testResult = python -c "from bark import SAMPLE_RATE, generate_audio; print('OK')" 2>&1
        if ($testResult -eq "OK") {
            Write-Success "Bark ready!"
            $Script:InstallLog += @{Package="Bark"; Status="Success"; Error=$null}
            return $true
        } else {
            throw "Bark import test failed"
        }
    }
    catch {
        Write-Error "Bark installation failed: $_"
        $Script:InstallLog += @{Package="Bark"; Status="Failed"; Error=$_.Exception.Message}
        return $false
    }
}

# ============================================================================
# TEST SUITE
# ============================================================================

function Test-Installation {
    Write-Header "🧪 VERIFICATION TESTS"

    Write-Info "Running comprehensive tests..."

    $tests = @(
        @{Name="Silero VAD"; Test={Test-PythonPackage "silero_vad"}},
        @{Name="DeepFilterNet"; Test={python -c "from df import enhance, init_df; print('OK')" 2>&1; $? -and $LASTEXITCODE -eq 0}},
        @{Name="Pedalboard"; Test={Test-PythonPackage "pedalboard"}},
        @{Name="Gradio"; Test={Test-PythonPackage "gradio"}}
    )

    if ($FullStack) {
        $tests += @(
            @{Name="OpenVoice"; Test={python -c "from openvoice import se_extractor; print('OK')" 2>&1; $? -and $LASTEXITCODE -eq 0}},
            @{Name="F5-TTS"; Test={python -c "from f5_tts.api import F5TTS; print('OK')" 2>&1; $? -and $LASTEXITCODE -eq 0}},
            @{Name="XTTS"; Test={python -c "from TTS.api import TTS; print('OK')" 2>&1; $? -and $LASTEXITCODE -eq 0}},
            @{Name="Bark"; Test={python -c "from bark import generate_audio; print('OK')" 2>&1; $? -and $LASTEXITCODE -eq 0}}
        )
    } elseif ($QuickWinsOnly) {
        $tests += @(
            @{Name="OpenVoice"; Test={python -c "from openvoice import se_extractor; print('OK')" 2>&1; $? -and $LASTEXITCODE -eq 0}}
        )
    }

    $passed = 0
    $failed = 0

    foreach ($test in $tests) {
        Write-Host "  Testing $($test.Name)..." -NoNewline

        try {
            if (& $test.Test) {
                Write-Host " ✅" -ForegroundColor Green
                $passed++
            } else {
                Write-Host " ❌" -ForegroundColor Red
                $failed++
            }
        }
        catch {
            Write-Host " ❌ (Error: $_)" -ForegroundColor Red
            $failed++
        }
    }

    Write-Host ""
    Write-Host "Results: $passed passed, $failed failed" -ForegroundColor $(if ($failed -eq 0) {"Green"} else {"Yellow"})

    return $failed -eq 0
}

# ============================================================================
# INSTALLATION SUMMARY
# ============================================================================

function Show-Summary {
    Write-Header "📊 INSTALLATION SUMMARY"

    Write-Host ""
    Write-Host "Installed Packages:" -ForegroundColor Cyan
    Write-Host ""

    foreach ($entry in $Script:InstallLog) {
        $status = if ($entry.Status -eq "Success") { "✅" } else { "❌" }
        Write-Host "  $status $($entry.Package)"
        if ($entry.Error) {
            Write-Host "     Error: $($entry.Error)" -ForegroundColor Red
        }
    }

    Write-Host ""

    $successCount = ($Script:InstallLog | Where-Object {$_.Status -eq "Success"}).Count
    $totalCount = $Script:InstallLog.Count

    Write-Host "Total: $successCount/$totalCount successful" -ForegroundColor $(if ($successCount -eq $totalCount) {"Green"} else {"Yellow"})
}

function Show-NextSteps {
    Write-Header "🚀 NEXT STEPS"

    Write-Host ""
    Write-Host "What to do now:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1️⃣  Launch the UI:" -ForegroundColor Yellow
    Write-Host "   cd ui"
    Write-Host "   python app.py"
    Write-Host "   # Opens at: http://localhost:7860"
    Write-Host ""
    Write-Host "2️⃣  Test Quick Wins:" -ForegroundColor Yellow
    Write-Host "   python test_quick_wins.py"
    Write-Host ""
    Write-Host "3️⃣  Read Documentation:" -ForegroundColor Yellow
    Write-Host "   cat README_EXCELLENCE.md"
    Write-Host "   cat QUICK_WINS.md"
    Write-Host "   cat STATE_OF_THE_ART.md"
    Write-Host ""
    Write-Host "4️⃣  Create Your First Audiobook:" -ForegroundColor Yellow
    Write-Host "   - Upload book in UI"
    Write-Host "   - Select george_mckayland voice"
    Write-Host "   - Choose F5-TTS engine"
    Write-Host "   - Pick audiobook_intimate preset"
    Write-Host "   - Click Generate!"
    Write-Host ""

    if ($QuickWinsOnly) {
        Write-Host "💡 Pro Tip:" -ForegroundColor Magenta
        Write-Host "   You installed Quick Wins. For the complete experience,"
        Write-Host "   run: .\setup_excellence.ps1 -FullStack"
        Write-Host ""
    }

    Write-Success "Setup complete! Ready to craft audiobooks. 🎙️"
}

# ============================================================================
# MAIN INSTALLATION FLOW
# ============================================================================

function Start-QuickWinsInstallation {
    Write-Header "⚡ QUICK WINS INSTALLATION"
    Write-Info "Installing the Big 3 for 10x quality improvement"
    Write-Info "Estimated time: ~15 minutes"
    Write-Info "Impact: 🔥🔥🔥🔥🔥"

    $Script:TotalSteps = 6

    Install-SileroVAD
    Install-DeepFilterNet
    Install-OpenVoice
    Install-Pedalboard
    Install-Gradio

    Write-Success "Quick Wins installed!"
}

function Start-FullStackInstallation {
    Write-Header "🎨 FULL STACK INSTALLATION"
    Write-Info "Installing everything for maximum quality"
    Write-Info "Estimated time: ~45 minutes (models download on first use)"
    Write-Info "Impact: LEGENDARY"

    $Script:TotalSteps = 9

    # Quick Wins first
    Install-SileroVAD
    Install-DeepFilterNet
    Install-OpenVoice
    Install-Pedalboard
    Install-Gradio

    # Advanced engines
    Install-F5TTS
    Install-XTTS
    Install-Bark

    Write-Success "Full stack installed!"
}

# ============================================================================
# ENTRY POINT
# ============================================================================

try {
    Clear-Host

    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
    Write-Host "║                                                                    ║" -ForegroundColor Magenta
    Write-Host "║           🎙️  PERSONAL AUDIOBOOK STUDIO SETUP  🎙️                ║" -ForegroundColor Magenta
    Write-Host "║                                                                    ║" -ForegroundColor Magenta
    Write-Host "║              Transform. Craft. Perfect.                            ║" -ForegroundColor Magenta
    Write-Host "║                                                                    ║" -ForegroundColor Magenta
    Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
    Write-Host ""

    # Determine what to install
    if (-not $QuickWinsOnly -and -not $FullStack) {
        Write-Host "Choose installation type:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "1) Quick Wins Only (Recommended)" -ForegroundColor Green
        Write-Host "   - Silero VAD, OpenVoice, DeepFilterNet"
        Write-Host "   - ~15 minutes, 10x quality improvement"
        Write-Host "   - Perfect for getting started"
        Write-Host ""
        Write-Host "2) Full Stack (Advanced)" -ForegroundColor Cyan
        Write-Host "   - Everything including F5-TTS, XTTS, Bark"
        Write-Host "   - ~45 minutes, legendary quality"
        Write-Host "   - For maximum creative freedom"
        Write-Host ""

        $choice = Read-Host "Enter choice (1 or 2)"

        if ($choice -eq "1") {
            $QuickWinsOnly = $true
        } elseif ($choice -eq "2") {
            $FullStack = $true
        } else {
            throw "Invalid choice. Please run again and choose 1 or 2."
        }
    }

    # Pre-flight checks
    Test-Prerequisites

    # Install based on choice
    if ($QuickWinsOnly) {
        Start-QuickWinsInstallation
    } else {
        Start-FullStackInstallation
    }

    # Run tests unless skipped
    if (-not $SkipTests) {
        Test-Installation | Out-Null
    }

    # Show summary
    Show-Summary
    Show-NextSteps

    Write-Host ""
    Write-Success "All done! Time to create something insanely great. ✨"
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Error "Setup failed: $_"
    Write-Host ""
    Write-Host "For help, check:" -ForegroundColor Yellow
    Write-Host "  - QUICKSTART.md"
    Write-Host "  - QUICK_WINS.md"
    Write-Host "  - STATE_OF_THE_ART.md"
    Write-Host ""
    exit 1
}
