@echo off
echo ==========================================
echo Testing Full Pipeline with Gift of the Magi
echo ==========================================
echo.
echo This will run the complete pipeline:
echo   Phase 1: Validation
echo   Phase 2: Text Extraction
echo   Phase 3: Chunking
echo   Phase 4: TTS Synthesis
echo   Phase 5: Audio Enhancement
echo.
echo Input: Gift of the Magi.pdf (86KB)
echo.
pause

cd ..

echo Starting orchestrator...
python phase6_orchestrator\orchestrator.py "input\Gift of the Magi.pdf" --pipeline-json=pipeline_magi.json --no-resume

echo.
echo ==========================================
echo Pipeline Complete!
echo ==========================================
echo.
echo Check outputs:
echo   - Chunks: phase3-chunking\chunks\
echo   - Audio: phase4_tts\audio_chunks\
echo   - Final: phase5_enhancement\output\audiobook.mp3
echo.
echo Pipeline state: pipeline_magi.json
echo.
pause
