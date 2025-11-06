@echo off
REM Complete workflow: Clean chunks then run Phase 5

echo ============================================================
echo Step 1: Cleaning Audio Chunks
echo ============================================================
echo Removing "You need to add some text for me to talk" from all chunks
echo.

cd /d C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase_audio_cleanup

poetry run python -m audio_cleanup.main --input-dir "..\phase4_tts\audio_chunks" --output-dir "..\phase4_tts\audio_chunks_cleaned" --batch --pattern "*.wav"

if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: Cleanup failed! Check output above.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Step 2: Running Phase 5 Enhancement
echo ============================================================
echo Processing cleaned chunks into final audiobook
echo.

cd /d C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement

poetry run python -m phase5_enhancement.main

if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: Phase 5 failed! Check output above.
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS! Audiobook complete.
echo ============================================================
echo Check: C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement\processed\meditations\audiobook.mp3
echo.
pause
