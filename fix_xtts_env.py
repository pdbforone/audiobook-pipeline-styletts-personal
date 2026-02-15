import subprocess
import sys
import os

venv_path = os.path.join("phase4_tts", ".engine_envs", "xtts")
if sys.platform == "win32":
    python_executable = os.path.join(venv_path, "Scripts", "python.exe")
else:
    python_executable = os.path.join(venv_path, "bin", "python")

if not os.path.exists(python_executable):
    print(f"Python executable not found at {python_executable}")
else:
    print(f"Installing kokoro-onnx using {python_executable}...")
    try:
        subprocess.check_call([python_executable, "-m", "pip", "install", "kokoro-onnx"])
        print("Installation of kokoro-onnx successful.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing kokoro-onnx: {e}")
