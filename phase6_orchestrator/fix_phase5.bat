@echo off
REM Fix Phase 5 by clearing incomplete output and re-running with absolute paths

echo ========================================
echo Phase 5 Fix Script
echo ========================================
echo.
echo This will:
echo 1. Clear incomplete Phase 5 output
echo 2. Re-run Phase 4 finalization (updates pipeline.json with absolute paths)
echo 3. Re-run Phase 5 with corrected paths
echo.
pause

echo.
echo [1/3] Clearing incomplete Phase 5 output...
cd /d "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement"
if exist "processed" (
    rmdir /s /q "processed"
    echo   - Deleted processed directory
)
mkdir "processed"
echo   - Created fresh processed directory

if exist "output" (
    del /q "output\enhanced_*.wav" 2>nul
    del /q "output\audiobook.mp3" 2>nul
    echo   - Cleared output directory
)

echo.
echo [2/3] Re-running Phase 4 finalization...
echo   (This updates pipeline.json with absolute paths)
cd /d "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase6_orchestrator"
poetry run python orchestrator.py "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\input\The_Analects_of_Confucius_20240228.pdf" --phases 4 --no-resume

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Phase 4 finalization failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Re-running Phase 5 with corrected paths...
poetry run python orchestrator.py "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\input\The_Analects_of_Confucius_20240228.pdf" --phases 5 --no-resume

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Phase 5 failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS!
echo ========================================
echo.
echo All 637 chunks should now be processed.
echo Check: C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement\processed
echo.
echo Final audiobook:
echo C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement\output\audiobook.mp3
echo.
pause
