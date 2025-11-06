@echo off
REM Step 2: Run Phase 5 on cleaned chunks

echo ============================================================
echo Running Phase 5 on CLEANED Chunks
echo ============================================================
echo.

cd /d C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement

echo Checking config...
findstr "input_dir:" src\phase5_enhancement\config.yaml
echo.

echo Running Phase 5...
echo.

REM FIXED: Run as module instead of direct file to fix relative imports
poetry run python -m phase5_enhancement.main --config config.yaml

if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: Phase 5 failed!
    echo ============================================================
    echo Check the error output above
    echo Check log file: audio_enhancement.log
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS! Final audiobook created at:
echo C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement\processed\audiobook.mp3
echo ============================================================
echo.
echo Phrase cleanup has been applied automatically!
echo Check audio_enhancement.log for details on phrases removed.
echo.
pause
