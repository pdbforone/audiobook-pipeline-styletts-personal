@echo off
REM ========================================================================
REM Phase 4 Setup for Windows with Auto-Elevation
REM This script will automatically request admin rights if needed
REM ========================================================================

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :run_setup
) else (
    echo.
    echo ========================================================================
    echo   Administrator Rights Required
    echo ========================================================================
    echo.
    echo This setup needs admin rights to install Python packages.
    echo A UAC prompt will appear - please click "Yes"
    echo.
    pause

    REM Re-launch this script with admin rights
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:run_setup
REM Now running with admin rights

title Phase 4 Setup (Administrator)

echo.
echo ========================================================================
echo   Phase 4 Multi-Engine TTS Setup
echo ========================================================================
echo.
echo Running with administrator privileges...
echo.

REM Navigate to script directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    echo.
    echo Please install Python and ensure it's in your PATH.
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Remove old Poetry venv if exists
if exist ".venv" (
    echo [INFO] Removing old venv...
    rmdir /s /q .venv
)

REM Create new venv with standard Python
echo [INFO] Creating virtual environment...
python -m venv .venv

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Failed to create venv
    pause
    exit /b 1
)

echo [OK] Virtual environment created
echo.

REM Activate venv
call .venv\Scripts\activate.bat

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install core dependencies
echo [INFO] Installing core dependencies (torch, numpy, soundfile, pyyaml)...
echo [INFO] This may take a few minutes...
pip install torch numpy soundfile pyyaml

if errorlevel 1 (
    echo [ERROR] Failed to install core dependencies
    echo.
    echo Check your internet connection and try again.
    pause
    exit /b 1
)

echo [OK] Core dependencies installed
echo.

REM Offer to install TTS engines
echo ========================================================================
echo   TTS Engine Installation (Optional)
echo ========================================================================
echo.
echo Which engines would you like to install?
echo.
echo 1. XTTS v2 (Expressive, recommended)
echo 2. Kokoro-onnx (CPU-friendly backup)
echo 3. Install both XTTS + Kokoro
echo 4. Skip (install later)
echo.

set /p choice="Enter choice (1-4): "

if "%choice%"=="1" (
    echo [INFO] Installing XTTS v2 (this may take a while)...
    pip install TTS
)

if "%choice%"=="2" (
    echo [INFO] Installing Kokoro...
    pip install kokoro-onnx
)

if "%choice%"=="3" (
    echo [INFO] Installing XTTS v2 + Kokoro...
    pip install TTS kokoro-onnx
)

if "%choice%"=="4" (
    echo [INFO] Skipping engine installation
    goto done
)

:done

echo.
echo ========================================================================
echo   Setup Complete!
echo ========================================================================
echo.
echo Virtual environment: phase4_tts\.venv
echo.
echo To test:
echo   cd phase4_tts
echo   .venv\Scripts\activate
echo   python -c "import yaml; print('Dependencies OK!')"
echo.
echo You can now use the multi-engine TTS from the UI!
echo.
echo ========================================================================
echo.
pause
