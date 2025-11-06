@echo off
REM Test script for audio cleanup tool
REM Run this from the phase_audio_cleanup directory

echo ============================================================
echo Testing Audio Cleanup Tool (Dry Run)
echo ============================================================
echo.

poetry run python -m audio_cleanup.main --input "..\phase4_tts\audio_chunks\the meditations, by Marcus Aurelius_chunk_004.wav" --dry-run --verbose

echo.
echo ============================================================
echo Test complete. Check output above for results.
echo ============================================================
pause
