@echo off
echo ==========================================
echo Fixing Phase 2 Venv Issue
echo ==========================================
echo.

cd ..\phase2-extraction

echo Step 1: Removing corrupted .venv directory...
if exist ".venv" (
    rmdir /s /q .venv
    echo ✓ Removed old .venv
) else (
    echo Already clean - no .venv found
)

echo.
echo Step 2: Configuring Poetry to use local venv...
poetry config virtualenvs.in-project true --local

echo.
echo Step 3: Creating fresh venv with Poetry...
poetry install --no-root

echo.
echo Step 4: Verifying Python executable...
if exist ".venv\Scripts\python.exe" (
    echo ✓ SUCCESS: Python found at .venv\Scripts\python.exe
    .\.venv\Scripts\python.exe --version
) else (
    echo ✗ FAILED: Python not found in .venv\Scripts\python.exe
    echo.
    echo Troubleshooting steps:
    echo 1. Check if Poetry is using the correct Python version
    echo 2. Try: poetry env info
    echo 3. Try: poetry env remove python
    echo 4. Then re-run this script
)

echo.
echo ==========================================
echo DONE!
echo ==========================================
pause
