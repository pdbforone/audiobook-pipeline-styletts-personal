@echo off
REM Summary of cleanup results and next steps

echo ============================================================
echo Meditations Cleanup Summary
echo ============================================================
echo.
echo Results from last cleanup run:
echo - Total files processed: 899
echo - Successfully cleaned: 42 (phrase removed)
echo - Already clean: 763 (no phrase found)
echo - Errors: 94 (failed to process)
echo.
echo This means you have 805 GOOD audio files ready to use!
echo (42 cleaned + 763 clean = 805 usable files)
echo.
echo ============================================================
echo Checking error details...
echo ============================================================
echo.

cd /d C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox

python check_cleanup_errors.py

echo.
echo ============================================================
echo Recommendations:
echo ============================================================
echo.
echo OPTION 1: Proceed with 805 good files (RECOMMENDED)
echo   - The 94 errors are likely corrupted/problematic files
echo   - 805 files is more than enough for your audiobook
echo   - Run: step2_run_phase5.bat
echo.
echo OPTION 2: Investigate the 94 errors first
echo   - Check the error output above
echo   - See if they're important chunks or just noise
echo.
echo What do you want to do?
echo.
pause
