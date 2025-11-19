@echo off
REM Phase 5 Direct Mode - Bypass Pipeline.json
REM This processes ALL audio chunks directly from phase4_tts/audio_chunks/

cd /d "%~dp0"

echo ==========================================
echo Phase 5 Direct Mode
echo ==========================================
echo.
echo This will bypass pipeline.json completely and:
echo 1. Scan phase4_tts/audio_chunks/ for ALL .wav files
echo 2. Process every single file found (no skipping!)
echo 3. Create complete audiobook.mp3
echo.
echo Use this if pipeline.json is causing issues.
echo.
echo Press Ctrl+C to cancel, or
pause

echo.
echo Running Phase 5 in Direct Mode...
echo.

poetry run python phase5_direct_simple.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================================
    echo SUCCESS!
    echo ==========================================
    echo.
    echo Check:
    echo - Enhanced chunks: ..\phase5_enhancement\processed\
    echo - Final audiobook: ..\phase5_enhancement\output\audiobook.mp3
    echo.
) else (
    echo.
    echo ==========================================
    echo FAILED! Check logs above
    echo ==========================================
    echo.
)

pause
