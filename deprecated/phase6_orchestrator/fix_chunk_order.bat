@echo off
echo ==========================================
echo Fix Gift of Magi Chunk Order
echo ==========================================
echo.
echo This will:
echo 1. Diagnose current chunk order
echo 2. Clear old Phase 5 output
echo 3. Re-run Phase 5 with CORRECT ordering
echo 4. Verify the audiobook plays in order
echo.
echo Time: ~2 minutes
echo.
pause

echo.
echo ========================================
echo Step 1: Diagnosing current order...
echo ========================================
poetry run python diagnose_chunk_order.py
echo.
echo Press any key to continue with the fix...
pause > nul

echo.
echo ========================================
echo Step 2: Clearing old Phase 5 files...
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
echo Step 3: Clearing Phase 5 from JSON...
echo ========================================

poetry run python clear_phase5.py

echo.
echo ========================================
echo Step 4: Re-running Phase 5...
echo ========================================
echo.
echo Processing 41 chunks with CORRECT ordering...
echo.

cd ..\phase5_enhancement

REM Run Phase 5 with the fixed code
poetry run python src\phase5_enhancement\main.py --config=config.yaml

cd ..\phase6_orchestrator

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================================
    echo SUCCESS! Audiobook created with correct order
    echo ==========================================
    echo.
    echo ========================================
    echo Step 5: Verification
    echo ========================================
    echo.
    echo Checking if audiobook exists...
    
    if exist "..\phase5_enhancement\processed\audiobook.mp3" (
        echo ✅ audiobook.mp3 created successfully!
        echo.
        echo 📊 File info:
        dir "..\phase5_enhancement\processed\audiobook.mp3" | findstr "audiobook"
        echo.
        echo 🎧 Listen to verify correct order:
        echo    The story should start with:
        echo    "ONE DOLLAR AND EIGHTY-SEVEN CENTS. That was all..."
        echo.
        echo    And flow naturally through the story in sequence.
        echo.
        echo To play it now:
        start "" "..\phase5_enhancement\processed\audiobook.mp3"
    ) else (
        echo ❌ ERROR: audiobook.mp3 was not created
        echo Check the logs above for errors
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
