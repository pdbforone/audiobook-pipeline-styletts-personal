@echo off
echo ==========================================
echo Gift of the Magi - Full Pipeline (Resume Enabled)
echo ==========================================
echo.
echo This runs ALL phases with resume capability:
echo   - If interrupted, re-run to continue
echo   - Skips completed phases automatically
echo.

cd ..

python phase6_orchestrator\orchestrator.py "input\Gift of the Magi.pdf" --pipeline-json=pipeline_magi.json

echo.
echo ==========================================
if %ERRORLEVEL%==0 (
    echo SUCCESS! Audiobook created.
    echo.
    echo Listen to: phase5_enhancement\output\audiobook.mp3
) else (
    echo FAILED at some phase.
    echo Check logs above for details.
    echo Re-run this script to resume from checkpoint.
)
echo ==========================================
echo.
pause
