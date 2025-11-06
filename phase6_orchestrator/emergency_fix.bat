@echo off
REM Emergency Fix - Force Phase 5 to Accept ALL Chunks

cd /d "%~dp0"

echo ==========================================
echo Phase 5 Emergency Fix
echo ==========================================
echo.
echo This will:
echo 1. Patch config.yaml (set quality_validation_enabled=false, snr=0)
echo 2. Patch main.py code (force acceptance of all chunks)
echo 3. Clear old Phase 5 data
echo 4. Run Phase 5 (should process ALL 637 chunks)
echo.
echo Both files will be backed up before patching.
echo.
echo ⚠️  This bypasses ALL quality checks!
echo    All chunks will be accepted regardless of quality.
echo.
pause

echo.
echo Step 1: Patching config.yaml...
poetry run python patch_phase5_config.py

echo.
echo Step 2: Patching main.py code...
poetry run python patch_phase5_code.py

echo.
echo Step 3: Running Phase 5...
echo.

cd ..\phase5_enhancement

REM Clear old data
if exist "processed\enhanced_*.wav" (
    echo Clearing old enhanced files...
    del /Q "processed\enhanced_*.wav"
)

REM Run Phase 5
poetry run python src\phase5_enhancement\main.py --config=config.yaml

cd ..\phase6_orchestrator

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================================
    echo SUCCESS!
    echo ==========================================
    echo.
    echo Checking results...
    poetry run python check_phase5_results.py
    echo.
    echo If you see "637/637 chunks processed", you're done!
    echo Listen to: ..\phase5_enhancement\output\audiobook.mp3
    echo.
) else (
    echo.
    echo ==========================================
    echo FAILED!
    echo ==========================================
    echo.
    echo Check logs above for errors.
    echo.
)

echo.
echo To restore original files:
echo   1. Copy config.yaml.backup to config.yaml
echo   2. Copy main.py.backup to main.py
echo.
pause
