@echo off
echo ==========================================
echo Testing Phase 3 Directly (Fixed Version)
echo ==========================================
echo.

cd ..\phase3-chunking

echo Checking if venv exists...
if exist ".venv\Scripts\python.exe" (
    echo ✓ Venv found
) else (
    echo Creating venv with Poetry...
    poetry install --no-root
)

echo.
echo Running Phase 3...
poetry run python -m phase3_chunking.main --file_id=test_story --json_path=..\pipeline.json --config=config.yaml

echo.
echo Exit code: %ERRORLEVEL%
if %ERRORLEVEL%==0 (
    echo ✓ Phase 3 SUCCESS
) else (
    echo ✗ Phase 3 FAILED
)

pause
