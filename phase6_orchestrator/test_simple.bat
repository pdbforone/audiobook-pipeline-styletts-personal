@echo off
echo ==========================================
echo Phase 6 Orchestrator - Simple Test
echo ==========================================
echo.
echo Using existing pipeline.json
echo Input: test_story.txt
echo.
pause

cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase6_orchestrator

poetry run python orchestrator.py ^
    ..\test_story.txt ^
    --phases 2 3 4 5

echo.
echo ==========================================
echo DONE!
echo ==========================================
pause
