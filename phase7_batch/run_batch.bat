@echo off
REM Quick batch processing launcher for Windows
REM Usage: run_batch.bat

echo ============================================
echo  Phase 7: Batch Audiobook Processing
echo ============================================
echo.

REM Check if poetry is available
where poetry >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Poetry not found in PATH
    echo Install Poetry from: https://python-poetry.org/docs/#installation
    pause
    exit /b 1
)

REM Check if venv exists
if not exist ".venv" (
    echo Installing dependencies...
    poetry install
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Poetry install failed
        pause
        exit /b 1
    )
)

REM Run verification
echo.
echo Running installation check...
poetry run python verify_install.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: Installation check failed
    echo Fix issues above before running batch processing
    pause
    exit /b 1
)

REM Run batch processing
echo.
echo ============================================
echo  Starting Batch Processing
echo ============================================
echo.
echo Press Ctrl+C to cancel...
timeout /t 3 >nul

poetry run batch-audiobook

REM Check exit code
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo  SUCCESS: All files processed
    echo ============================================
) else if %ERRORLEVEL% EQU 2 (
    echo.
    echo ============================================
    echo  PARTIAL: Some files had issues
    echo ============================================
    echo Check batch.log for details
) else (
    echo.
    echo ============================================
    echo  FAILED: Batch processing failed
    echo ============================================
    echo Check batch.log for details
)

echo.
echo Results saved to:
echo   - pipeline.json (processing details)
echo   - batch.log (execution log)
echo   - phase5_enhancement/output/ (final audiobooks)
echo.
pause
