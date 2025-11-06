@echo off
REM Complete fix: Clear Phase 5, update pipeline.json, and re-run Phase 5

echo ========================================
echo Phase 5 Complete Fix
echo ========================================
echo.
echo This will:
echo 1. Clear Phase 5 entry from pipeline.json (resume was skipping chunks!)
echo 2. Clear incomplete Phase 5 output files
echo 3. Re-run Phase 5 with ALL 637 chunks
echo.
echo Estimated time: ~5-10 minutes
echo.
pause

echo.
echo [1/3] Clearing Phase 5 from pipeline.json...
cd /d "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase6_orchestrator"
poetry run python clear_phase5.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to clear Phase 5 from pipeline.json!
    pause
    exit /b 1
)

echo.
echo [2/3] Clearing incomplete Phase 5 output files...
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
echo [3/3] Running Phase 5 with ALL 637 chunks...
cd /d "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase6_orchestrator"
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
echo.
echo Check results:
echo   Enhanced chunks: C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement\processed\
echo   Final audiobook: C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement\output\audiobook.mp3
echo.
pause
