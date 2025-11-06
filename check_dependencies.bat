@echo off
REM Check dependency compatibility

cd /d C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox

echo Running dependency analysis...
echo.

python analyze_dependencies.py

echo.
echo ============================================================
echo.
echo Would you like to proceed with integration?
echo.
echo PROS:
echo   - Single phase handles cleanup + enhancement
echo   - No separate orchestration needed
echo   - Simpler workflow
echo.
echo CONS:
echo   - Adds 150MB Whisper model to Phase 5
echo   - Adds 2-3 seconds per chunk (transcription time)
echo   - Phase 5 becomes heavier
echo.
pause
