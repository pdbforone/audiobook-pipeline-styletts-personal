@echo off
echo ==========================================
echo Manual Phase 3 Bypass - Create Test Chunks
echo ==========================================
echo.
echo Creating simple test chunks for Phase 4...
echo.

cd ..

REM Create chunks directory
mkdir phase3-chunking\chunks 2>nul

REM Create 3 simple test chunks
echo The Quick Brown Fox > phase3-chunking\chunks\test_story_chunk_0.txt
echo Once upon a time, in a forest far away, there lived a quick brown fox. > phase3-chunking\chunks\test_story_chunk_1.txt
echo As the day drew to a close, the fox returned home. > phase3-chunking\chunks\test_story_chunk_2.txt

echo ✓ Created 3 test chunks

REM Update pipeline.json with chunk paths
python -c "import json; p=json.load(open('pipeline.json')); p.setdefault('phase3',{}).setdefault('files',{})['test_story']={'status':'success','chunk_paths':['phase3-chunking/chunks/test_story_chunk_0.txt','phase3-chunking/chunks/test_story_chunk_1.txt','phase3-chunking/chunks/test_story_chunk_2.txt']}; json.dump(p,open('pipeline.json','w'),indent=4)"

echo ✓ Updated pipeline.json

echo.
echo Now you can run orchestrator with: --phases 4 5
echo.
pause
