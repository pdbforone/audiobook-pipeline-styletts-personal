@echo off
REM ========================================================================
REM Personal Audiobook Studio Launcher
REM Double-click this file to launch the UI
REM ========================================================================

title Personal Audiobook Studio

echo.
echo ========================================================================
echo   Personal Audiobook Studio
echo ========================================================================
echo.
echo Starting the studio... This may take a moment.
echo.

REM Navigate to UI directory
cd /d "%~dp0ui"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    echo.
    echo Please install Python or ensure it's in your PATH.
    pause
    exit /b 1
)

REM Check if port 7860 is already in use
netstat -ano | findstr :7860 >nul 2>&1
if not errorlevel 1 (
    echo.
    echo ========================================================================
    echo   WARNING: Port 7860 is already in use!
    echo ========================================================================
    echo.
    echo The studio might already be running in another window.
    echo.
    echo Options:
    echo   1. Check for other terminal windows running the studio
    echo   2. Close them and try again
    echo   3. Or open http://localhost:7860 in your browser
    echo   4. Or run Stop_Studio.bat to force close
    echo.
    pause
    exit /b 1
)

REM Launch the UI
echo [OK] Python found
echo [OK] Launching UI...
echo.
echo The UI will open at: http://localhost:7860
echo.
echo Opening browser in 3 seconds...
echo.

REM Wait a bit then open browser in background
start /B timeout /t 3 /nobreak >nul 2>&1 ^&^& start http://localhost:7860

echo.
echo ========================================================================
echo   Studio is running!
echo ========================================================================
echo.
echo   URL: http://localhost:7860
echo.
echo   [!] Press Ctrl+C (NOT X) to stop the server properly
echo   [!] Closing window may leave port occupied
echo   [!] Use Stop_Studio.bat if port gets stuck
echo.
echo ========================================================================
echo.

REM Enable Ctrl+C handling
setlocal EnableDelayedExpansion

REM Start Python server with proper signal handling
python app.py

REM This executes when Python exits
set exitcode=%ERRORLEVEL%

echo.
echo ========================================================================
echo   Studio has stopped (exit code: %exitcode%)
echo ========================================================================
echo.

REM Clean up any remaining Python processes on this port
netstat -ano | findstr :7860 >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Cleaning up lingering processes on port 7860...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7860') do (
        taskkill /PID %%a /F >nul 2>&1
        echo [OK] Killed process %%a
    )
)

pause
