@echo off
REM ========================================================================
REM Stop Audiobook Studio
REM Use this if the studio is stuck running and won't close
REM ========================================================================

title Stop Audiobook Studio

echo.
echo ========================================================================
echo   Stop Audiobook Studio
echo ========================================================================
echo.
echo Checking for running studio processes...
echo.

REM Find process using port 7860
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :7860') do (
    set PID=%%a
)

if not defined PID (
    echo [INFO] No studio process found running on port 7860
    echo.
    echo The studio is not currently running.
    pause
    exit /b 0
)

echo [FOUND] Process ID: %PID%
echo.
echo Stopping studio...

REM Kill the process
taskkill /PID %PID% /F >nul 2>&1

if errorlevel 1 (
    echo [ERROR] Failed to stop process
    echo.
    echo You may need to close it manually or run this as Administrator.
    pause
    exit /b 1
)

echo [OK] Studio stopped successfully!
echo.
echo You can now launch the studio again.
echo.
pause
