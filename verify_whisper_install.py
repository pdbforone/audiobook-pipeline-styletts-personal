
import sys
try:
    import whisper
    print("SUCCESS: The 'openai-whisper' package is installed and accessible in the current environment.")
    print(f"Python executable: {sys.executable}")
except ImportError:
    print("FAILURE: The 'openai-whisper' package could not be imported.")
    print("Please ensure you have run the following command:")
    print(r".\.venv\Scripts\python.exe -m pip install openai-whisper")
    print(f"Python executable being used: {sys.executable}")
    sys.exit(1)
