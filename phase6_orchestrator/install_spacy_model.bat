@echo off
echo ==========================================
echo Installing spaCy Language Model
echo ==========================================
echo.

cd ..\phase3-chunking

echo Step 1: Downloading spaCy en_core_web_sm model...
echo (This is a small 15MB model, faster than en_core_web_lg)
echo.

poetry run python -m spacy download en_core_web_sm

echo.
echo Step 2: Verifying installation...
poetry run python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('✓ spaCy model loaded successfully!')"

echo.
echo ==========================================
echo DONE!
echo ==========================================
echo.
echo NOTE: Using en_core_web_sm (small model) for speed.
echo If you want the large model for better accuracy:
echo   poetry run python -m spacy download en_core_web_lg
echo.
pause
