@echo off
REM Install Phase 5 with Audio Cleanup Integration

echo ============================================================
echo Installing Phase 5 Enhancement with Phrase Cleanup
echo ============================================================
echo.

cd /d C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement

echo Step 1: Installing dependencies...
echo This will add faster-whisper (~150MB model download on first run)
echo.

poetry install

if errorlevel 1 (
    echo.
    echo ERROR: Dependency installation failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS! Phase 5 updated with phrase cleanup capability
echo ============================================================
echo.
echo New features:
echo   - Automatic phrase detection and removal
echo   - Configurable via config.yaml
echo   - Can be disabled with: enable_phrase_cleanup: false
echo.
echo Configuration:
echo   - Edit config.yaml to customize target phrases
echo   - Default: Removes "You need to add [some] text for me to talk"
echo   - Whisper model: base (change to 'small' for better accuracy)
echo.
echo IMPORTANT: First run will download Whisper model (~150MB, 1-2 min)
echo.
pause
