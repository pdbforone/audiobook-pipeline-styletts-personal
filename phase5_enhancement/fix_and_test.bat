@echo off
echo ============================================================
echo Fixing Import Issue and Retrying Installation
echo ============================================================
echo.

cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement

echo Step 1: Copying fixed main_integrated.py to main.py...
copy /Y src\phase5_enhancement\main_integrated.py src\phase5_enhancement\main.py

echo.
echo Step 2: Testing with a single chunk...
echo.
call poetry run python -m phase5_enhancement.main --chunk_id 0 --skip_concatenation

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Test failed! Check the logs above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS! Fixed and tested.
echo ============================================================
echo.
echo You can now proceed with full processing:
echo   C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\step2_run_phase5.bat
echo.
pause
