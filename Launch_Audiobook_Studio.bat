@echo off
REM ========================================================================
REM Personal Audiobook Studio Launcher
REM Double-click this file to launch the UI
REM ========================================================================

title Personal Audiobook Studio

echo.
echo ========================================================================
echo   🎙️  Personal Audiobook Studio
echo ========================================================================
echo.
echo Starting the studio... This may take a moment.
echo.

REM Navigate to UI directory
cd /d "%~dp0ui"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python not found in PATH
    echo.
    echo Please install Python or ensure it's in your PATH.
    pause
    exit /b 1
)

REM Launch the UI
echo ✓ Python found
echo ✓ Launching UI...
echo.
echo The UI will open at: http://localhost:7860
echo.
echo 🌐 Opening browser in 3 seconds...
echo.

REM Start the UI in background and capture the PID
start /b python app.py

REM Wait a bit for server to start, then open browser
timeout /t 3 /nobreak >nul 2>&1
start http://localhost:7860

echo.
echo ========================================================================
echo   ✅ Studio is running!
echo ========================================================================
echo.
echo   URL: http://localhost:7860
echo.
echo   📝 Keep this window open while using the studio
echo   📝 Press Ctrl+C to stop the server
echo   📝 Close this window to exit
echo.
echo ========================================================================
echo.

REM Keep the window open and wait for the Python process
python app.py

REM This will only execute if python exits
echo.
echo ========================================================================
echo   Studio has stopped.
echo ========================================================================
echo.
pause
