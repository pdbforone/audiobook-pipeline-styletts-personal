@echo off
REM Check what book is configured in pipeline.json

echo ============================================================
echo Pipeline.json Current Configuration
echo ============================================================
echo.

cd /d C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox

echo Looking for audiobook title and Phase 4 status...
echo.

findstr /i "audiobook_title tts_profile" pipeline.json
echo.

echo Phase 4 status:
findstr /i "\"phase4\"" pipeline.json
echo.

echo Phase 5 status:
findstr /i "\"phase5\"" pipeline.json
echo.

echo ============================================================
echo.
pause
