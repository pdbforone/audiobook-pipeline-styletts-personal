@echo off
echo ==========================================
echo Phase 6 Orchestrator - Skip Phase 3
echo ==========================================
echo.
echo Phase 3 requires Python 3.12 (you have 3.11)
echo Testing with Phases 2, 4, 5 only
echo.
pause

cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase6_orchestrator

poetry run python orchestrator.py ^
    ..\test_story.txt ^
    --phases 2 4 5

echo.
echo ==========================================
echo DONE!
echo ==========================================
pause
