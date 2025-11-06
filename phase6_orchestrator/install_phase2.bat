@echo off
echo Installing Phase 2 dependencies...
cd ..\phase2-extraction
poetry install --no-root
echo.
echo Done! Now run test_orchestrator.bat again
pause
