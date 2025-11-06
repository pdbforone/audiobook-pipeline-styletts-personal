@echo off
echo ==========================================
echo Complete Phase 3 Setup
echo ==========================================
echo.
echo This will:
echo 1. Install all Python dependencies
echo 2. Download spaCy language model
echo 3. Verify everything works
echo.

cd ..\phase3-chunking

echo Step 1: Installing Poetry dependencies...
poetry install --no-root

echo.
echo Step 2: Downloading spaCy language model (en_core_web_sm - 15MB)...
poetry run python -m spacy download en_core_web_sm

echo.
echo Step 3: Verifying installation...
poetry run python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('✓ spaCy model loaded successfully')" 2>nul

if %ERRORLEVEL%==0 (
    echo ✓ Phase 3 is ready!
) else (
    echo ✗ Verification failed - check errors above
)

echo.
echo Step 4: Testing Phase 3 with test file...
cd ..\phase6_orchestrator
call test_phase3_quick.bat

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
pause
