@echo off
REM Master diagnostic for missing chunks

echo ============================================================
echo Professional Quality Check: Missing Chunks Analysis
echo ============================================================
echo.

cd /d C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox

echo Step 1: Identifying missing files...
python investigate_missing_chunks.py
echo.

echo Step 2: Analyzing missing chunk patterns...
python analyze_missing_chunks.py
echo.

echo ============================================================
echo Analysis complete. Review the output above.
echo ============================================================
echo.
pause
