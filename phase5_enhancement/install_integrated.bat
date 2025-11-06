@echo off
echo ============================================================
echo Phase 5: Integrated Audio Enhancement with Phrase Cleanup
echo ============================================================
echo.

echo Step 1: Installing dependencies...
echo.
cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement
call poetry install
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Poetry install failed!
    pause
    exit /b 1
)

echo.
echo Step 2: Backing up current files...
echo.
copy src\phase5_enhancement\main.py src\phase5_enhancement\main.py.backup_before_integration 2>nul
copy src\phase5_enhancement\config.yaml src\phase5_enhancement\config.yaml.backup_before_integration 2>nul

echo.
echo Step 3: Activating integrated version...
echo.
copy /Y src\phase5_enhancement\main_integrated.py src\phase5_enhancement\main.py
copy /Y src\phase5_enhancement\config_integrated.yaml src\phase5_enhancement\config.yaml

echo.
echo Step 4: Testing with a single chunk...
echo.
echo Testing chunk 0 to verify integration...
call poetry run python -m phase5_enhancement.main --chunk_id 0 --skip_concatenation

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Test failed! Check the logs above.
    echo.
    echo To rollback:
    echo   copy src\phase5_enhancement\main.py.backup_before_integration src\phase5_enhancement\main.py
    echo   copy src\phase5_enhancement\config.yaml.backup_before_integration src\phase5_enhancement\config.yaml
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS! Integration complete and tested.
echo ============================================================
echo.
echo Next steps:
echo   1. Review the test output above
echo   2. Check processed\enhanced_0000.wav was created
echo   3. If good, run full processing:
echo      C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\step2_run_phase5.bat
echo.
echo Backups saved as:
echo   - main.py.backup_before_integration
echo   - config.yaml.backup_before_integration
echo.
pause
