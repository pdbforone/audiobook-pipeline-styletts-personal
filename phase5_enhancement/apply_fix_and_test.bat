@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo Phase 5: Unicode Fix and Smart Test
echo ============================================================

:: Step 1: Apply the fixed version
echo.
echo Step 1: Applying Unicode-fixed version...
copy /Y src\phase5_enhancement\main_fixed.py src\phase5_enhancement\main.py
if errorlevel 1 (
    echo [ERROR] Failed to copy fixed file
    pause
    exit /b 1
)
echo [OK] Fixed version applied

:: Step 2: Find an existing chunk from Phase 4
echo.
echo Step 2: Finding existing audio chunk for testing...

:: Check multiple possible locations
set "CHUNK_FOUND=0"
set "CHUNK_PATH="

:: Location 1: From pipeline.json phase4 output
if exist "..\phase4_tts\audio_chunks\" (
    for %%f in (..\phase4_tts\audio_chunks\*.wav) do (
        set "CHUNK_PATH=%%f"
        set "CHUNK_FOUND=1"
        goto :found
    )
)

:: Location 2: Check audio_chunks in current directory
if exist "audio_chunks\" (
    for %%f in (audio_chunks\*.wav) do (
        set "CHUNK_PATH=%%f"
        set "CHUNK_FOUND=1"
        goto :found
    )
)

:: Location 3: Check processed directory
if exist "processed\" (
    for %%f in (processed\*.wav) do (
        set "CHUNK_PATH=%%f"
        set "CHUNK_FOUND=1"
        goto :found
    )
)

:found
if "%CHUNK_FOUND%"=="0" (
    echo [ERROR] No audio chunks found in common locations
    echo.
    echo Searched:
    echo   - ..\phase4_tts\audio_chunks\
    echo   - audio_chunks\
    echo   - processed\
    echo.
    echo Please ensure Phase 4 has completed successfully
    pause
    exit /b 1
)

echo [OK] Found test chunk: %CHUNK_PATH%

:: Step 3: Extract chunk number from filename
for %%f in ("%CHUNK_PATH%") do set "CHUNK_FILE=%%~nxf"
echo [INFO] Testing with file: %CHUNK_FILE%

:: Try to extract number from filename
set "CHUNK_NUM="
for /f "tokens=2 delims=_" %%a in ("%CHUNK_FILE%") do set "CHUNK_NUM=%%a"
if "%CHUNK_NUM%"=="" (
    :: Try different pattern
    for /f "tokens=1 delims=." %%a in ("%CHUNK_FILE%") do (
        set "TEMP=%%a"
        for /f "tokens=* delims=0123456789" %%b in ("!TEMP!") do set "CHUNK_NUM=!TEMP:%%b=!"
    )
)

if "%CHUNK_NUM%"=="" (
    echo [WARNING] Could not extract chunk number, using 0
    set "CHUNK_NUM=0"
)

:: Remove leading zeros for Python
set /a CHUNK_NUM_INT=%CHUNK_NUM% 2>nul
if errorlevel 1 set CHUNK_NUM_INT=0

echo [INFO] Extracted chunk number: %CHUNK_NUM_INT%

:: Step 4: Run test
echo.
echo Step 3: Running integrated test...
echo ============================================================

poetry run python -m phase5_enhancement.main --chunk_id %CHUNK_NUM_INT% --skip_concatenation

if errorlevel 1 (
    echo.
    echo ============================================================
    echo [ERROR] Test failed! Check the logs above.
    echo ============================================================
    echo.
    echo Troubleshooting:
    echo   1. Check audio_enhancement.log for details
    echo   2. Verify config.yaml has correct input_dir path
    echo   3. Ensure Phase 4 chunks are accessible
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo [SUCCESS] Unicode fix applied and test passed!
echo ============================================================
echo.
echo Next steps:
echo   1. Review audio_enhancement.log for details
echo   2. Check processed/ directory for enhanced output
echo   3. Run full processing: step2_run_phase5.bat
echo.
pause
