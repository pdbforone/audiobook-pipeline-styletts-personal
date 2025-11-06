@echo off
REM Test Phase 5 Fix
REM This script runs ONLY Phase 5 with the fixed orchestrator

cd /d "%~dp0"

echo ==========================================
echo Testing Phase 5 Fix
echo ==========================================
echo.
echo This will:
echo 1. Clear old Phase 5 data from pipeline.json
echo 2. Set resume_on_failure=false in config.yaml
echo 3. Clear processed/ directory
echo 4. Run Phase 5 to process ALL 637 chunks
echo.
echo Press Ctrl+C to cancel, or
pause

echo.
echo Running Phase 5...
echo.

REM Run only Phase 5 (--phases 5)
poetry run python orchestrator.py ^
  "..\input\The_Analects_of_Confucius_20240228.pdf" ^
  --pipeline-json="..\pipeline.json" ^
  --phases 5 ^
  --no-resume

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================================
    echo SUCCESS! Phase 5 completed
    echo ==========================================
    echo.
    echo Check the results:
    echo 1. Enhanced chunks: ..\phase5_enhancement\processed\
    echo 2. Final audiobook: ..\phase5_enhancement\output\audiobook.mp3
    echo.
    echo Expected: 637 enhanced_XXXX.wav files in processed/
    echo.
) else (
    echo.
    echo ==========================================
    echo FAILED! Check logs above
    echo ==========================================
    echo.
)

pause
