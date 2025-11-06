@echo off
REM Step 1: Clean the Meditations chunks

echo ============================================================
echo Cleaning Meditations Audio Chunks
echo ============================================================
echo This will remove "You need to add some text for me to talk"
echo from all audio chunks.
echo.

cd /d C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase_audio_cleanup

echo Running cleanup tool...
echo.

poetry run python -m audio_cleanup.main --input-dir "..\phase4_tts\audio_chunks" --output-dir "..\phase4_tts\audio_chunks_cleaned" --batch --pattern "*.wav"

if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: Cleanup failed!
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS! Cleaned chunks saved to:
echo C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase4_tts\audio_chunks_cleaned\
echo ============================================================
echo.
echo Next step: Run the orchestrator again, or manually run Phase 5
echo.
pause
