@echo off
echo ==========================================
echo Fix Gift of the Magi - Remove Spaced Headers
echo ==========================================
echo.
echo This will:
echo 1. Clean the extracted text (remove spaced headers)
echo 2. Delete old chunks
echo 3. Re-run Phase 3 to create clean chunks
echo.
echo After this, you can resume with Phase 4.
echo.
pause

cd ..

echo Step 1: Backing up original file...
copy "phase2-extraction\extracted_text\Gift of the Magi.txt" "phase2-extraction\extracted_text\Gift of the Magi.txt.backup"

echo.
echo Step 2: Cleaning text file...
echo Please wait while we remove the spaced headers...

:: Create a temp Python script to clean the file
echo import re > temp_clean.py
echo. >> temp_clean.py
echo with open('phase2-extraction/extracted_text/Gift of the Magi.txt', 'r', encoding='utf-8') as f: >> temp_clean.py
echo     text = f.read() >> temp_clean.py
echo. >> temp_clean.py
echo # Remove the spaced title lines >> temp_clean.py
echo text = re.sub(r'T h e G i f t o f t h e M a g i\s*\n', '', text) >> temp_clean.py
echo text = re.sub(r'O \. H e n r y\s*\n', '', text) >> temp_clean.py
echo # Remove standalone 'p' and 'O' >> temp_clean.py
echo text = re.sub(r'^\s*p\s*\n', '', text, flags=re.MULTILINE) >> temp_clean.py
echo text = re.sub(r'^\s*O\s*\n', '', text, flags=re.MULTILINE) >> temp_clean.py
echo. >> temp_clean.py
echo with open('phase2-extraction/extracted_text/Gift of the Magi.txt', 'w', encoding='utf-8') as f: >> temp_clean.py
echo     f.write(text) >> temp_clean.py
echo. >> temp_clean.py
echo print('✓ Text cleaned successfully') >> temp_clean.py

python temp_clean.py
del temp_clean.py

echo.
echo Step 3: Deleting old chunks...
del /q "phase3-chunking\chunks\Gift of the Magi_chunk_*.txt"

echo.
echo Step 4: Re-running Phase 3...
cd phase3-chunking
poetry run python -m phase3_chunking.main --file_id="Gift of the Magi" --json_path=..\pipeline_magi.json --config=config.yaml

echo.
echo ==========================================
echo Done!
echo ==========================================
echo.
echo Now you can resume the pipeline:
echo   cd phase6_orchestrator
echo   .\run_gift_of_magi.bat
echo.
echo The pipeline will skip Phase 1-3 (already done)
echo and continue with Phase 4 using the clean chunks.
echo.
pause
