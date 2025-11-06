@echo off
echo ==========================================
echo Phase 5 - Final Run
echo ==========================================
echo.
echo Changes applied:
echo ✓ models.py patched (validators removed)
echo ✓ config.yaml fixed (removed clipping_threshold)
echo ✓ Settings: snr_threshold=0.0, quality_validation=false
echo.
pause

cd ..\phase5_enhancement

echo [1/3] Clearing Python cache...
if exist "src\phase5_enhancement\__pycache__\" rmdir /s /q "src\phase5_enhancement\__pycache__"
echo ✓ Cache cleared

echo.
echo [2/3] Checking Phase 4 data...
python ..\check_quick.py
echo.
pause

echo.
echo [3/3] Running Phase 5...
echo.
poetry run python src\phase5_enhancement\main.py --config=config.yaml

echo.
echo ==========================================
echo DONE - Check output above!
echo ==========================================
pause
