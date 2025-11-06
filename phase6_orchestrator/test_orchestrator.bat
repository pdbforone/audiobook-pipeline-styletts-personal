@echo off
echo ==========================================
echo Phase 6 Orchestrator - Test Run
echo ==========================================
echo.
echo Input: test_story.txt
echo Pipeline: C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\pipeline_test.json
echo.
echo NOTE: Skipping Phase 1 (validation only needed for PDFs)
echo Starting from Phase 2 (text extraction)
echo.
pause

cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase6_orchestrator

echo.
echo Running orchestrator...
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
echo Check pipeline_test.json for results
echo Check phase5_enhancement\processed\ for audiobook.mp3
echo.
pause
