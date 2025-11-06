@echo off
echo ==========================================
echo Resume Gift of the Magi - Phase 5 Only
echo ==========================================
echo.
echo Phase 5 config fixed:
echo   - Removed clipping_threshold
echo   - Set pipeline_json to pipeline_magi.json
echo.
echo This will run Phase 5 only to complete the audiobook.
echo.
pause

cd ..

echo Running Phase 5...
python phase6_orchestrator\orchestrator.py "input\Gift of the Magi.pdf" --pipeline-json=pipeline_magi.json --phases 5

echo.
echo ==========================================
if %ERRORLEVEL%==0 (
    echo SUCCESS! Audiobook created.
    echo.
    echo Listen to: phase5_enhancement\output\audiobook.mp3
) else (
    echo Phase 5 failed again.
    echo Check the error messages above.
)
echo ==========================================
echo.
pause
