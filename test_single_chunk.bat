@echo off
REM Test processing a single failed file to see the actual error

echo ============================================================
echo Testing Single Failed File
echo ============================================================
echo.

if "%1"=="" (
    echo Usage: test_single_chunk.bat "filename.wav"
    echo.
    echo Example:
    echo   test_single_chunk.bat "the meditations, by Marcus Aurelius_chunk_042.wav"
    echo.
    pause
    exit /b 1
)

cd /d C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase_audio_cleanup

echo Testing file: %1
echo.
echo Running cleanup tool with verbose output...
echo.

poetry run python -m audio_cleanup.main --input "..\phase4_tts\audio_chunks\%~1" --output "..\phase4_tts\test_output.wav" --verbose

echo.
echo ============================================================
echo Test complete. Check output above for error details.
echo ============================================================
pause
