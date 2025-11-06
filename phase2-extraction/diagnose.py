"""Diagnostic script to check Poetry/Python setup."""
import sys
from pathlib import Path

print("=== Python Environment Diagnostics ===\n")
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"\n=== Python Path ===")
for p in sys.path:
    print(f"  {p}")

print(f"\n=== Current Working Directory ===")
print(f"  {Path.cwd()}")

print(f"\n=== Package Installation Check ===")
try:
    import phase2_extraction
    print(f"✓ phase2_extraction found at: {phase2_extraction.__file__}")
except ModuleNotFoundError as e:
    print(f"✗ phase2_extraction NOT FOUND: {e}")

print(f"\n=== Dependency Check ===")
deps = ['num2words', 'unidecode', 'pdfplumber']
for dep in deps:
    try:
        __import__(dep)
        print(f"✓ {dep} installed")
    except ModuleNotFoundError:
        print(f"✗ {dep} NOT installed")
