@echo off
echo ==========================================
echo Phase 6 Orchestrator - Test Run (v2)
echo ==========================================
echo.
echo This version will auto-install dependencies
echo for each phase if needed.
echo.
pause

cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase6_orchestrator

echo.
echo Running orchestrator with improved error handling...
echo.

poetry run python orchestrator.py ^
    ..\test_story.txt ^
    --pipeline-json=..\pipeline_test.json ^
    --phases 2 3 4 5

echo.
echo ==========================================
echo DONE!
echo ==========================================
echo.
pause
