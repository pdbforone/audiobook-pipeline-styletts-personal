@echo off
REM ========================================================================
REM Phase 4 Setup for Windows (No Poetry Required)
REM Simple pip-based installation that works without admin rights
REM ========================================================================

title Phase 4 Setup

echo.
echo ========================================================================
echo   Phase 4 Multi-Engine TTS Setup
echo ========================================================================
echo.
echo This will set up Phase 4 using pip (no Poetry needed)
echo.

REM Navigate to phase4_tts directory
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Remove old Poetry venv if exists
if exist ".venv" (
    echo [INFO] Removing old Poetry venv...
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
pip install torch numpy soundfile pyyaml --quiet

if errorlevel 1 (
    echo [ERROR] Failed to install core dependencies
    echo.
    echo Try running this script as Administrator, or check your network connection.
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
echo 1. None (just core dependencies - use StyleTTS2 separately)
echo 2. F5-TTS (Expressive, best quality)
echo 3. XTTS v2 (Versatile, multi-language)
echo 4. Kokoro (CPU-friendly, fast)
echo 5. All engines
echo.

set /p choice="Enter choice (1-5): "

if "%choice%"=="1" (
    echo [INFO] Skipping engine installation
    goto done
)

if "%choice%"=="2" (
    echo [INFO] Installing F5-TTS...
    pip install f5-tts
)

if "%choice%"=="3" (
    echo [INFO] Installing XTTS v2...
    pip install TTS
)

if "%choice%"=="4" (
    echo [INFO] Installing Kokoro...
    pip install kokoro-onnx
)

if "%choice%"=="5" (
    echo [INFO] Installing all engines...
    pip install f5-tts TTS kokoro-onnx
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
echo   python -c "import yaml; print('OK!')"
echo.
echo You can now use the multi-engine system from the UI!
echo.
pause
