# Verify All Phases - Check Dependencies and Python Versions
# Run this to diagnose installation issues

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Audiobook Pipeline - Verify Setup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$phases = @(
    @{Name="phase1-validation"; Key="ftfy"},
    @{Name="phase2-extraction"; Key="pdfplumber"},
    @{Name="phase3-chunking"; Key="spacy"},
    @{Name="phase5_enhancement"; Key="librosa"},
    @{Name="phase6_orchestrator"; Key="rich"},
    @{Name="phase7_batch"; Key="typer"}
)

$allGood = $true

foreach ($phase in $phases) {
    $phaseName = $phase.Name
    $keyPackage = $phase.Key

    Write-Host "`n=== $phaseName ===" -ForegroundColor Yellow

    if (-Not (Test-Path $phaseName)) {
        Write-Host "  [SKIP] Directory not found" -ForegroundColor Gray
        continue
    }

    Push-Location $phaseName

    try {
        # Check virtualenv exists
        $envInfo = poetry env info 2>&1 | Out-String

        if ($envInfo -match "Python:\s+(.+)") {
            $pythonVersion = $matches[1].Trim()
            Write-Host "  Python: $pythonVersion" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] No virtualenv found" -ForegroundColor Red
            $allGood = $false
            Pop-Location
            continue
        }

        # Verify key package is installed
        $importTest = poetry run python -c "import $keyPackage; print('OK')" 2>&1

        if ($importTest -match "OK") {
            Write-Host "  Package '$keyPackage': Installed ✓" -ForegroundColor Green
        } else {
            Write-Host "  Package '$keyPackage': MISSING ✗" -ForegroundColor Red
            Write-Host "  Error: $importTest" -ForegroundColor Red
            $allGood = $false
        }

        # Show installed packages count
        $packageCount = (poetry show 2>&1 | Measure-Object -Line).Lines
        Write-Host "  Installed packages: $packageCount" -ForegroundColor Gray

    } catch {
        Write-Host "  [ERROR] $_" -ForegroundColor Red
        $allGood = $false
    } finally {
        Pop-Location
    }
}

# Phase 4 (Conda) - Special handling
Write-Host "`n=== phase4_tts (Conda) ===" -ForegroundColor Yellow
Push-Location phase4_tts

try {
    $condaCheck = conda env list 2>&1 | Select-String "phase4_tts"

    if ($condaCheck) {
        Write-Host "  Conda env 'phase4_tts': Found ✓" -ForegroundColor Green

        # Test import
        $torchTest = conda run -n phase4_tts python -c "import torch; print('OK')" 2>&1

        if ($torchTest -match "OK") {
            Write-Host "  Package 'torch': Installed ✓" -ForegroundColor Green
        } else {
            Write-Host "  Package 'torch': MISSING ✗" -ForegroundColor Red
            $allGood = $false
        }
    } else {
        Write-Host "  Conda env 'phase4_tts': NOT FOUND ✗" -ForegroundColor Red
        Write-Host "  Run: cd phase4_tts && conda env create -f environment.yml" -ForegroundColor Yellow
        $allGood = $false
    }
} catch {
    Write-Host "  [ERROR] Conda not available or env not created" -ForegroundColor Red
    $allGood = $false
} finally {
    Pop-Location
}

# Final summary
Write-Host "`n========================================" -ForegroundColor Cyan

if ($allGood) {
    Write-Host "✅ All phases verified successfully!" -ForegroundColor Green
    Write-Host "`nYou're ready to run the pipeline." -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "❌ Some phases have issues" -ForegroundColor Red
    Write-Host "`nRun './setup_all_phases.ps1' to reinstall dependencies" -ForegroundColor Yellow
    exit 1
}
