@echo off
REM Clean only Meditations chunks

echo ============================================================
echo Cleaning ONLY Meditations Audio Chunks
echo ============================================================
echo.

cd /d C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase_audio_cleanup

echo Cleaning chunks matching "meditations" in filename...
echo.

poetry run python -m audio_cleanup.main --input-dir "..\phase4_tts\audio_chunks" --output-dir "..\phase4_tts\meditations_cleaned" --batch --pattern "*meditations*.wav"

if errorlevel 1 (
    echo ERROR: Cleanup failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS! Meditations chunks cleaned
echo ============================================================
echo.
pause
