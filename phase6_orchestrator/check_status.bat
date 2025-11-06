@echo off
echo ==========================================
echo Pipeline Status Check
echo ==========================================
echo.
poetry run python diagnose_json_state.py
echo.
pause
