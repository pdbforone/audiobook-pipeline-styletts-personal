@echo off
REM Analyze why Phase 5 chunks are failing

cd /d "%~dp0"

echo ==========================================
echo Phase 5 Failure Analysis
echo ==========================================
echo.
echo This will analyze pipeline.json and logs to
echo determine why 334 chunks failed.
echo.
pause

poetry run python analyze_phase5_failures.py

echo.
echo ==========================================
echo.
echo Next steps:
echo 1. If quality validation is too strict - run phase5_direct.bat
echo 2. If audio files are corrupted - check Phase 4 output
echo 3. If enhancement process has bugs - report issue
echo.
pause
