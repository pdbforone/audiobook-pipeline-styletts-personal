@echo off
echo ============================================================
echo STEP 1: Checking pipeline.json structure
echo ============================================================
python check_pipeline_structure.py
echo.
echo.

echo ============================================================
echo STEP 2: Running coverage tests
echo ============================================================
python tests\test_coverage.py --show-diff
echo.

pause
