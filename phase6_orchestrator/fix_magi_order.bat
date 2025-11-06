@echo off
echo ==========================================
echo Fix Gift of Magi Chunk Order
echo ==========================================
echo.
echo This script will:
echo 1. Check which book(s) are in pipeline.json
echo 2. Ensure ONLY Gift of Magi is selected
echo 3. Clear old Phase 5 output
echo 4. Re-run Phase 5 with CORRECT chunk ordering
echo 5. Verify the result
echo.
echo Time: ~2 minutes
echo.
pause

echo.
echo ========================================
echo Step 1: Check current JSON state...
echo ========================================
poetry run python check_what_will_process.py
echo.
pause

echo.
echo ========================================
echo Step 2: Ensure only Gift of Magi...
echo ========================================
poetry run python switch_to_magi.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Could not set up JSON for Gift of Magi
    pause
    exit /b 1
)

echo.
echo ========================================
echo Step 3: Clearing old Phase 5 files...
echo ========================================

cd ..\phase5_enhancement\processed

if exist "audiobook.mp3" (
    echo Deleting old audiobook.mp3...
    del /Q "audiobook.mp3"
)

if exist "enhanced_*.wav" (
    echo Deleting old enhanced chunks...
    del /Q "enhanced_*.wav"
)

if exist "audiobook.m3u" (
    del /Q "audiobook.m3u"
)

echo ✓ Old files cleared
cd ..\..\phase6_orchestrator

echo.
echo ========================================
echo Step 4: Re-running Phase 5...
echo ========================================
echo.
echo Processing Gift of Magi (41 chunks) with CORRECT ordering...
echo.

cd ..\phase5_enhancement

REM Run Phase 5 with the fixed code
poetry run python src\phase5_enhancement\main.py --config=config.yaml

cd ..\phase6_orchestrator

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================================
    echo SUCCESS! Gift of Magi audiobook created
    echo ==========================================
    echo.
    echo ========================================
    echo Step 5: Verification
    echo ========================================
    echo.
    
    poetry run python verify_chunk_order.py
    
    echo.
    if exist "..\phase5_enhancement\processed\audiobook.mp3" (
        echo.
        echo 🎧 Listen to verify correct order:
        echo.
        echo The story should start with:
        echo   "ONE DOLLAR AND EIGHTY-SEVEN CENTS. That was all..."
        echo.
        echo And flow naturally through the complete story.
        echo.
        echo Play it now? (Y/N)
        choice /C YN /N
        if errorlevel 2 goto skip_play
        if errorlevel 1 goto do_play
        
        :do_play
        start "" "..\phase5_enhancement\processed\audiobook.mp3"
        
        :skip_play
    )
) else (
    echo.
    echo ==========================================
    echo FAILED!
    echo ==========================================
    echo.
    echo Phase 5 encountered an error.
    echo Check the log:
    echo   ..\phase5_enhancement\audio_enhancement.log
)

echo.
pause
