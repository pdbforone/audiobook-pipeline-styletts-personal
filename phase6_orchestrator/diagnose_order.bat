@echo off
echo ==========================================
echo Diagnose Chunk Order Issue
echo ==========================================
echo.
echo This will check chunk ordering at every stage:
echo 1. pipeline.json chunk_audio_paths order
echo 2. Phase 4 audio files on disk
echo 3. Phase 5 enhanced files
echo.
poetry run python diagnose_chunk_order.py
echo.
pause
