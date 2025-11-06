@echo off
echo ==========================================
echo Fix and Re-run Phase 5 - Correct Chunk Order
echo ==========================================
echo.
echo ISSUE FIXED:
echo   - Phase 5 was using array index instead of filename chunk number
echo   - This caused chunks to concatenate in wrong order
echo.
echo FIX APPLIED:
echo   - Extract chunk number from filename (e.g., "_chunk_001")
echo   - Sort by actual chunk number, not array position
echo.
echo This will:
echo   1. Delete old audiobook.mp3 (wrong order)
echo   2. Delete old enhanced WAV files
echo   3. Re-run Phase 5 with correct sorting
echo.
pause

cd ..

echo Cleaning old Phase 5 outputs...
if exist "phase5_enhancement\processed\audiobook.mp3" (
    del /q "phase5_enhancement\processed\audiobook.mp3"
    echo ✓ Deleted old audiobook.mp3
)

if exist "phase5_enhancement\processed\enhanced_*.wav" (
    del /q "phase5_enhancement\processed\enhanced_*.wav"
    echo ✓ Deleted old enhanced chunks
)

echo.
echo Running Phase 5 with corrected sorting...
python phase6_orchestrator\orchestrator.py "input\Gift of the Magi.pdf" --pipeline-json=pipeline_magi.json --phases 5

echo.
echo ==========================================
if %ERRORLEVEL%==0 (
    echo SUCCESS! Audiobook re-created with CORRECT order!
    echo.
    echo Listen to: phase5_enhancement\processed\audiobook.mp3
    echo.
    echo The chunks should now be in the correct sequence:
    echo   001, 002, 003, ... 040, 041
) else (
    echo Phase 5 failed.
    echo Check the error messages above.
)
echo ==========================================
echo.
pause
