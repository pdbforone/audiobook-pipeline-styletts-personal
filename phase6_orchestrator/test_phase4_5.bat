@echo off
echo ==========================================
echo Test Phase 4 and 5 Only
echo ==========================================
echo.
echo Running with manually created chunks
echo (bypassing Phase 3 Python version issue)
echo.

cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase6_orchestrator

poetry run python orchestrator.py ^
    ..\test_story.txt ^
    --phases 4 5

echo.
pause
