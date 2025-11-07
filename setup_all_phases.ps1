# Setup All Phases - Install Dependencies Across All Poetry Environments
# Run this from the project root directory

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Audiobook Pipeline - Setup All Phases" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$phases = @(
    "phase1-validation",
    "phase2-extraction",
    "phase3-chunking",
    "phase5_enhancement",
    "phase6_orchestrator",
    "phase7_batch",
    "phase_audio_cleanup"
)

$success = 0
$failed = 0
$errors = @()

foreach ($phase in $phases) {
    Write-Host "`n=== Setting up $phase ===" -ForegroundColor Yellow

    if (-Not (Test-Path $phase)) {
        Write-Host "  [SKIP] Directory not found" -ForegroundColor Gray
        continue
    }

    Push-Location $phase

    try {
        # Show current virtualenv info
        Write-Host "  Checking virtualenv..." -ForegroundColor Gray
        poetry env info 2>&1 | Out-Null

        # Force sync installation
        Write-Host "  Installing dependencies..." -ForegroundColor Gray
        $result = poetry install --sync 2>&1

        if ($LASTEXITCODE -eq 0) {
            # Verify Python version
            $pythonVersion = poetry run python --version 2>&1
            Write-Host "  [OK] $pythonVersion" -ForegroundColor Green
            $success++
        } else {
            Write-Host "  [FAIL] Installation failed" -ForegroundColor Red
            Write-Host "  Error: $result" -ForegroundColor Red
            $failed++
            $errors += "$phase - Installation failed: $result"
        }

    } catch {
        Write-Host "  [ERROR] $_" -ForegroundColor Red
        $failed++
        $errors += "$phase - $_"
    } finally {
        Pop-Location
    }
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Setup Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Successful: $success" -ForegroundColor Green
Write-Host "  Failed:     $failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })

if ($errors.Count -gt 0) {
    Write-Host "`nErrors:" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "  - $error" -ForegroundColor Red
    }
    exit 1
}

Write-Host "`n✅ All phases ready!" -ForegroundColor Green
Write-Host "`nNext step: Run the orchestrator" -ForegroundColor Cyan
Write-Host "  cd phase6_orchestrator" -ForegroundColor Gray
Write-Host "  poetry run python orchestrator.py --pipeline ../pipeline.json <input_file>" -ForegroundColor Gray
Write-Host ""

exit 0
