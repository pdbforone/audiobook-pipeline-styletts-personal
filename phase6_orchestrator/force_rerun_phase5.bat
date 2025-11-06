@echo off
echo ==========================================
echo Force Re-run Phase 5 - Correct Chunk Order
echo ==========================================
echo.
echo This will FORCE Phase 5 to re-run by:
echo   1. Removing Phase 5 status from pipeline_magi.json
echo   2. Deleting old audiobook.mp3
echo   3. Running Phase 5 fresh with correct sorting
echo.
pause

cd ..

echo Step 1: Removing Phase 5 from pipeline_magi.json...
python -c "import json; f=open('pipeline_magi.json','r+'); d=json.load(f); d.pop('phase5',None); f.seek(0); json.dump(d,f,indent=2); f.truncate(); f.close(); print('✓ Removed phase5 from JSON')"

echo.
echo Step 2: Cleaning old outputs...
if exist "phase5_enhancement\processed\audiobook.mp3" (
    del /q "phase5_enhancement\processed\audiobook.mp3"
    echo ✓ Deleted old audiobook.mp3
)

if exist "phase5_enhancement\processed\enhanced_*.wav" (
    del /q "phase5_enhancement\processed\enhanced_*.wav"
    echo ✓ Deleted old enhanced chunks
)

echo.
echo Step 3: Running Phase 5 with FORCED execution...
python phase6_orchestrator\orchestrator.py "input\Gift of the Magi.pdf" --pipeline-json=pipeline_magi.json --phases 5 --no-resume

echo.
echo ==========================================
if %ERRORLEVEL%==0 (
    echo SUCCESS! Audiobook re-created with CORRECT order!
    echo.
    echo Listen to: phase5_enhancement\processed\audiobook.mp3
    echo.
    echo Verify the story plays in correct sequence.
) else (
    echo Phase 5 failed.
    echo Check the error messages above.
)
echo ==========================================
echo.
pause
