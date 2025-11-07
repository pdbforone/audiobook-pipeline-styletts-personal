# Setup Phase 3 Only - Install Dependencies + Download spaCy Model
# Run this if Phase 3 specifically is having issues

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Phase 3 Setup - Chunking with spaCy" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$phase = "phase3-chunking"

if (-Not (Test-Path $phase)) {
    Write-Host "[ERROR] $phase directory not found!" -ForegroundColor Red
    exit 1
}

Push-Location $phase

try {
    # Step 1: Install dependencies
    Write-Host "Step 1: Installing Python dependencies..." -ForegroundColor Yellow
    $result = poetry install --sync 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Poetry install failed" -ForegroundColor Red
        Write-Host "Error: $result" -ForegroundColor Red
        exit 1
    }

    $pythonVersion = poetry run python --version 2>&1
    Write-Host "[OK] Python dependencies installed ($pythonVersion)" -ForegroundColor Green

    # Step 2: Download spaCy language model
    Write-Host "`nStep 2: Downloading spaCy language model (en_core_web_sm)..." -ForegroundColor Yellow
    Write-Host "  This is a ~40MB download and may take a minute..." -ForegroundColor Gray

    $spacyResult = poetry run python -m spacy download en_core_web_sm 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] spaCy model download failed" -ForegroundColor Red
        Write-Host "Error: $spacyResult" -ForegroundColor Red
        Write-Host "`nPlease check your internet connection and try again." -ForegroundColor Yellow
        exit 1
    }

    Write-Host "[OK] spaCy model downloaded" -ForegroundColor Green

    # Step 3: Verify everything works
    Write-Host "`nStep 3: Verifying installation..." -ForegroundColor Yellow

    # Test spaCy import
    $importTest = poetry run python -c "import spacy; print('OK')" 2>&1
    if ($importTest -notmatch "OK") {
        Write-Host "[FAIL] spaCy import failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "  [OK] spaCy package" -ForegroundColor Green

    # Test spaCy model load
    $modelTest = poetry run python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('OK')" 2>&1
    if ($modelTest -notmatch "OK") {
        Write-Host "[FAIL] spaCy model load failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "  [OK] en_core_web_sm model" -ForegroundColor Green

    # Success!
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "✅ Phase 3 is ready!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "`nYou can now run Phase 3 through the orchestrator." -ForegroundColor Gray

} catch {
    Write-Host "[ERROR] $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

exit 0
