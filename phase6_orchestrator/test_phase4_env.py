#!/usr/bin/env python3
"""
Quick test to verify Phase 4 Conda environment is set up correctly
"""

import subprocess
import sys

def test_conda_installed():
    """Check if Conda is installed"""
    print("\n1. Checking if Conda is installed...")
    try:
        result = subprocess.run(
            ["conda", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"   ✓ Conda found: {result.stdout.strip()}")
            return True
        else:
            print("   ✗ Conda command failed")
            return False
    except FileNotFoundError:
        print("   ✗ Conda not found in PATH")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_conda_env_exists():
    """Check if phase4_tts environment exists"""
    print("\n2. Checking if 'phase4_tts' Conda environment exists...")
    try:
        result = subprocess.run(
            ["conda", "env", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "phase4_tts" in result.stdout:
            print("   ✓ Environment 'phase4_tts' exists")
            # Show the path
            for line in result.stdout.split('\n'):
                if 'phase4_tts' in line:
                    print(f"   Location: {line.strip()}")
            return True
        else:
            print("   ✗ Environment 'phase4_tts' not found")
            print("\n   Available environments:")
            print(result.stdout)
            print("\n   To create it, run:")
            print("   cd phase4_tts")
            print("   conda env create -f environment.yml")
            return False
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_conda_run():
    """Test if we can run Python in the Conda environment"""
    print("\n3. Testing 'conda run' with phase4_tts environment...")
    try:
        result = subprocess.run(
            ["conda", "run", "-n", "phase4_tts", "python", "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"   ✓ Successfully ran Python: {result.stdout.strip()}")
            return True
        else:
            print(f"   ✗ Failed to run Python")
            print(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def test_imports():
    """Test if key packages are installed in the environment"""
    print("\n4. Testing key package imports...")
    
    packages = [
        ("torch", "PyTorch"),
        ("torchaudio", "TorchAudio"),
        ("librosa", "Librosa"),
        ("chatterbox", "Chatterbox TTS")
    ]
    
    all_ok = True
    
    for module, name in packages:
        try:
            result = subprocess.run(
                ["conda", "run", "-n", "phase4_tts", "python", "-c", f"import {module}; print('{name} OK')"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"   ✓ {name}")
            else:
                print(f"   ✗ {name} - Import failed")
                print(f"      {result.stderr.strip()}")
                all_ok = False
                
        except Exception as e:
            print(f"   ✗ {name} - Error: {e}")
            all_ok = False
    
    return all_ok


def main():
    print("="*60)
    print("PHASE 4 CONDA ENVIRONMENT TEST")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Conda installed", test_conda_installed()))
    
    if results[-1][1]:  # Only continue if Conda is installed
        results.append(("Environment exists", test_conda_env_exists()))
        
        if results[-1][1]:  # Only continue if env exists
            results.append(("Conda run works", test_conda_run()))
            results.append(("Packages installed", test_imports()))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL TESTS PASSED - Phase 4 is ready!")
    else:
        print("✗ SOME TESTS FAILED - See above for details")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
