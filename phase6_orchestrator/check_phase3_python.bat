@echo off
echo Checking Phase 3 venv Python version...
cd ..\phase3-chunking
echo.
echo Checking if .venv exists:
if exist .venv (
    echo ✓ .venv exists
    echo.
    echo Python version in venv:
    .venv\Scripts\python.exe --version
    echo.
    echo Poetry environment info:
    poetry env info
) else (
    echo ✗ .venv does NOT exist
)
echo.
pause
