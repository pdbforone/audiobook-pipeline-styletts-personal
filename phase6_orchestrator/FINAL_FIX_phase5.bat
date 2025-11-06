@echo off
echo ==========================================
echo FINAL FIX - Phase 5 Chunk Order
echo ==========================================
echo.
echo REAL BUG FOUND AND FIXED:
echo   - ThreadPoolExecutor completes in random order
echo   - enhanced_chunks list was built in completion order
echo   - Now using dict + sort before concatenation
echo.
echo This will:
echo   1. Remove Phase 5 from JSON (force fresh run)
echo   2. Delete old outputs
echo   3. Run Phase 5 with CORRECT sorting
echo.
pause

cd ..

echo Removing phase5 from JSON...
python -c "import json; f=open('pipeline_magi.json','r+'); d=json.load(f); d.pop('phase5',None); f.seek(0); json.dump(d,f,indent=2); f.truncate(); f.close(); print('✓ Removed phase5')"

echo.
echo Deleting old outputs...
if exist "phase5_enhancement\processed\audiobook.mp3" del /q "phase5_enhancement\processed\audiobook.mp3"
if exist "phase5_enhancement\processed\enhanced_*.wav" del /q "phase5_enhancement\processed\enhanced_*.wav"

echo.
echo Running Phase 5 with FIXED code...
python phase6_orchestrator\orchestrator.py "input\Gift of the Magi.pdf" --pipeline-json=pipeline_magi.json --phases 5 --no-resume

echo.
echo ==========================================
if %ERRORLEVEL%==0 (
    echo SUCCESS! Audiobook created with CORRECT order!
    echo.
    echo The log should show:
    echo   "Creating final audiobook from 41 chunks in order: [1, 2, 3, 4, 5]...[37, 38, 39, 40, 41]"
    echo.
    echo Listen to: phase5_enhancement\processed\audiobook.mp3
) else (
    echo Failed - check logs
)
echo ==========================================
pause
