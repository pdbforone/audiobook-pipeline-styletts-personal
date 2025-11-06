@echo off
REM Check what files have the problematic phrase in transcript

echo ============================================================
echo Finding Files with "You need to add some text for me to talk"
echo ============================================================
echo.

cd /d C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase4_tts\audio_chunks

echo Searching .srt transcript files for the phrase...
echo (This will show which audio files contain the phrase)
echo.

findstr /i /m "you need to add" *.srt > found_phrases.txt

if %errorlevel%==0 (
    echo Found files with the phrase:
    type found_phrases.txt
    echo.
    echo Total files found:
    find /c ".srt" found_phrases.txt
) else (
    echo No .srt files found with the phrase
)

echo.
echo ============================================================
echo Check found_phrases.txt for full list
echo ============================================================
pause
