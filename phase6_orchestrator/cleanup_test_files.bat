@echo off
echo ==========================================
echo Clean Up Old Test Files
echo ==========================================
echo.
echo This will DELETE:
echo   - All chunk files in phase3-chunking/chunks/
echo   - Old pipeline_magi.json
echo   - Phase 4 error logs
echo.
echo This gives you a fresh start for testing.
echo.
pause

cd ..

echo Cleaning Phase 3 chunks...
if exist "phase3-chunking\chunks\*.txt" (
    del /q "phase3-chunking\chunks\*.txt"
    echo ✓ Removed all chunk files
) else (
    echo No chunk files found
)

echo.
echo Cleaning pipeline_magi.json...
if exist "pipeline_magi.json" (
    del /q "pipeline_magi.json"
    echo ✓ Removed pipeline_magi.json
) else (
    echo No pipeline_magi.json found
)

echo.
echo Cleaning Phase 4 error logs...
if exist "phase4_tts\chunk_*_error.log" (
    del /q "phase4_tts\chunk_*_error.log"
    echo ✓ Removed error logs
) else (
    echo No error logs found
)

echo.
echo ==========================================
echo Cleanup Complete!
echo ==========================================
echo.
echo Ready for fresh run.
echo.
pause
