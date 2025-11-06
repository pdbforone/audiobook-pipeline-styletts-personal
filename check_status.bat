@echo off
REM Diagnostic script to check audio chunk cleanup status

echo ============================================================
echo Audio Cleanup Diagnostic
echo ============================================================
echo.

echo Checking directories...
echo.

echo [1] Original chunks directory:
if exist "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase4_tts\audio_chunks\" (
    echo    EXISTS: C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase4_tts\audio_chunks\
    dir /b "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase4_tts\audio_chunks\*.wav" | find /c ".wav"
    echo    files found
) else (
    echo    NOT FOUND: C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase4_tts\audio_chunks\
)
echo.

echo [2] Cleaned chunks directory:
if exist "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase4_tts\audio_chunks_cleaned\" (
    echo    EXISTS: C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase4_tts\audio_chunks_cleaned\
    dir /b "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase4_tts\audio_chunks_cleaned\*.wav" | find /c ".wav"
    echo    files found
) else (
    echo    NOT FOUND: C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase4_tts\audio_chunks_cleaned\
    echo    This means cleanup has NOT been run yet!
)
echo.

echo [3] Phase 5 config check:
echo    Current input_dir in phase5_enhancement\config.yaml:
findstr "input_dir:" "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement\config.yaml"
echo.

echo [4] Phase 5 output:
if exist "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement\processed\meditations\audiobook.mp3" (
    echo    EXISTS: Final audiobook found
    dir "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement\processed\meditations\audiobook.mp3"
) else (
    echo    NOT FOUND: No final audiobook
)
echo.

echo ============================================================
echo Summary:
echo ============================================================
echo - If cleaned directory does NOT exist, you need to run cleanup first
echo - If Phase 5 config points to 'audio_chunks' instead of 'audio_chunks_cleaned', 
echo   it will use the ORIGINAL (unclean) chunks
echo.
pause
