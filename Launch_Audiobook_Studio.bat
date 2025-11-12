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

REM Wait a bit then open browser
timeout /t 3 /nobreak >nul 2>&1
start http://localhost:7860

echo.
echo ========================================================================
echo   Studio is running!
echo ========================================================================
echo.
echo   URL: http://localhost:7860
echo.
echo   [!] Keep this window open while using the studio
echo   [!] Press Ctrl+C to stop the server
echo   [!] Close this window to exit
echo.
echo ========================================================================
echo.

REM Start Python server
python app.py

REM This will only execute if python exits
echo.
echo ========================================================================
echo   Studio has stopped.
echo ========================================================================
echo.
pause
