@echo off
REM Batch process all audio chunks to find the problematic phrase
REM Run this from the phase_audio_cleanup directory

echo ============================================================
echo Batch Processing All Audio Chunks
echo ============================================================
echo This will scan all .wav files in phase4_tts\audio_chunks\
echo and identify which ones contain the target phrase.
echo.
echo Press Ctrl+C to cancel, or
pause

poetry run python -m audio_cleanup.main --input-dir "..\phase4_tts\audio_chunks" --output-dir "..\phase4_tts\audio_chunks_cleaned" --batch --pattern "*.wav" --dry-run --verbose

echo.
echo ============================================================
echo Batch scan complete. Check output above to see which files
echo contain the target phrase.
echo ============================================================
pause
