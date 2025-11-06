@echo off
echo ==========================================
echo Cleaning ALL Phase venvs
echo ==========================================
echo.
echo This will delete all .venv directories
echo so the orchestrator can recreate them
echo with proper dependencies.
echo.
pause

cd ..

echo Cleaning Phase 2...
cd phase2-extraction
if exist .venv rmdir /s /q .venv
cd ..

echo Cleaning Phase 3...
cd phase3-chunking
if exist .venv rmdir /s /q .venv
cd ..

echo Cleaning Phase 5...
cd phase5_enhancement
if exist .venv rmdir /s /q .venv
cd ..

echo.
echo ==========================================
echo Done! All venvs cleaned.
echo ==========================================
echo.
echo Now run test_orchestrator_v2.bat
echo The orchestrator will install dependencies automatically.
echo.
pause
