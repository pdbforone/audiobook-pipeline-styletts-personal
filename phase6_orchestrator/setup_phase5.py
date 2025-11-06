"""
Setup script for Phase 5 - Creates Python 3.12 environment
Run this before using the orchestrator if Phase 5 fails with Python version error
"""
import subprocess
import sys
from pathlib import Path

def main():
    phase5_dir = Path(__file__).parent.parent / "phase5_enhancement"
    
    print("="*60)
    print("Phase 5 Environment Setup")
    print("="*60)
    print(f"Phase 5 directory: {phase5_dir}")
    print()
    
    # Check if .venv already exists
    venv_dir = phase5_dir / ".venv"
    if venv_dir.exists():
        print("✓ Virtual environment already exists")
        print("  To recreate, delete .venv folder first:")
        print(f"    Remove-Item {venv_dir} -Recurse -Force")
        return 0
    
    print("Setting up Python 3.12 environment...")
    
    # Set Python 3.12
    try:
        result = subprocess.run(
            ["poetry", "env", "use", "python3.12"],
            cwd=str(phase5_dir),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print("⚠ python3.12 not found, trying 'python'...")
            result = subprocess.run(
                ["poetry", "env", "use", "python"],
                cwd=str(phase5_dir),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print("✗ ERROR: Failed to set Python environment")
                print(result.stderr)
                print()
                print("Manual fix:")
                print(f"  cd {phase5_dir}")
                print("  poetry env use python3.12")
                print("  poetry install")
                return 1
        
        print("✓ Python 3.12 environment created")
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return 1
    
    # Install dependencies
    print("Installing dependencies...")
    try:
        result = subprocess.run(
            ["poetry", "install", "--no-root"],
            cwd=str(phase5_dir),
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            print("✗ ERROR: Poetry install failed")
            print(result.stderr)
            return 1
        
        print("✓ Dependencies installed")
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return 1
    
    print()
    print("="*60)
    print("SUCCESS: Phase 5 is ready!")
    print("="*60)
    print("You can now run the orchestrator:")
    print("  python orchestrator.py ../input/The_Analects_of_Confucius_20240228.pdf --phases 5")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
