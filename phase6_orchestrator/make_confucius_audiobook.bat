@echo off
echo ==========================================
echo Process Confucius Audiobook
echo ==========================================
echo.
echo This will:
echo 1. Clean pipeline_magi.json (remove Gift of Magi)
echo 2. Process all 637 Confucius audio chunks
echo 3. Create final audiobook.mp3
echo.
echo Estimated time: 15-30 minutes
echo.
pause

echo.
echo Step 1: Cleaning JSON...
poetry run python process_confucius.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: JSON cleanup failed!
    pause
    exit /b 1
)

echo.
echo Step 2: Processing audio chunks...
echo.
call run_phase5_direct.bat

echo.
echo ==========================================
echo COMPLETE!
echo ==========================================
echo.
echo Your Confucius audiobook should be at:
echo   ..\phase5_enhancement\processed\audiobook.mp3
echo.
echo Listen to it:
echo   start "" "..\phase5_enhancement\processed\audiobook.mp3"
echo.
pause
