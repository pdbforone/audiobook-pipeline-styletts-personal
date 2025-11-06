@echo off
REM Quick test script for Phase 6 Orchestrator

echo ============================================================
echo PHASE 6 ORCHESTRATOR - QUICK TEST
echo ============================================================
echo.

echo Step 1: Testing Conda environment...
python test_conda.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo FAILED: Conda environment not ready
    echo Create it with:
    echo   cd ..\phase4_tts
    echo   conda env create -f environment.yml
    pause
    exit /b 1
)

echo.
echo Step 2: Checking if test file exists...
set TEST_FILE=..\The_Analects_of_Confucius_20240228.pdf
if exist "%TEST_FILE%" (
    echo Found test file: %TEST_FILE%
) else (
    echo Test file not found: %TEST_FILE%
    echo Please provide a PDF file to test with
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Ready to run orchestrator!
echo ============================================================
echo.
echo To test phases 1-3 only (skip TTS):
echo   python orchestrator.py "%TEST_FILE%" --phases 1 2 3
echo.
echo To test full pipeline:
echo   python orchestrator.py "%TEST_FILE%"
echo.
pause
