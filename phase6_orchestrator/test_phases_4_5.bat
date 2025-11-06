@echo off
echo ==========================================
echo Test Orchestrator - Phases 4-5 Only
echo ==========================================
echo.
echo Using existing Confucius file with completed Phases 1-3
echo Running Phases 4-5 only
echo.
pause

cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase6_orchestrator

poetry run python orchestrator.py ^
    "..\input\The_Analects_of_Confucius_20240228.pdf" ^
    --phases 4 5

echo.
pause
