"""
Install Whisper (openai-whisper) in Phase 4 engine environments.

This enables Tier 2 ASR validation for better audio quality checks.

Usage:
    python install_whisper.py
"""

import subprocess
import sys
from pathlib import Path


def install_in_venv(venv_path: Path, package: str) -> bool:
    """Install a package in a specific virtual environment."""
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"

    if not python_exe.exists():
        print(f"❌ Python executable not found: {python_exe}")
        return False

    print(f"📦 Installing {package} in {venv_path.name}...")
    print(f"   This may take several minutes (installing PyTorch dependencies)...")
    try:
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "install", package, "-q"],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes for large packages
        )
        if result.returncode == 0:
            print(f"✅ Successfully installed {package}")
            return True
        else:
            print(f"❌ Failed to install {package}")
            if result.stderr:
                print(f"   Error: {result.stderr[:500]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ Installation timed out (may need manual install)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("=" * 80)
    print("Whisper Installation Script for Phase 4")
    print("=" * 80)
    print("\nThis will install openai-whisper for ASR-based validation.")
    print("Note: Whisper is OPTIONAL - skip if you don't need Tier 2 validation.")
    print()

    # Check for engine environments
    engine_envs_dir = Path("phase4_tts/.engine_envs")
    if not engine_envs_dir.exists():
        print(f"❌ Engine environments directory not found: {engine_envs_dir}")
        sys.exit(1)

    # Install in XTTS environment
    xtts_env = engine_envs_dir / "xtts"
    if xtts_env.exists():
        print(f"🔧 Installing Whisper in XTTS environment...")
        success = install_in_venv(xtts_env, "openai-whisper")
        if success:
            print(f"   ✅ XTTS environment updated")
        else:
            print(f"   ❌ Failed - you may need to install manually:")
            print(f"      {xtts_env / 'Scripts' / 'python.exe'} -m pip install openai-whisper")
    else:
        print(f"⚠️  XTTS environment not found: {xtts_env}")

    # Optional: Install in Kokoro environment too
    kokoro_env = engine_envs_dir / "kokoro"
    if kokoro_env.exists():
        print(f"\n🔧 Installing Whisper in Kokoro environment...")
        install_in_venv(kokoro_env, "openai-whisper")

    print("\n" + "=" * 80)
    print("✅ Whisper installation complete!")
    print("\nNext steps:")
    print("1. Re-run Phase 4 to enable Tier 2 validation")
    print("2. Check logs - 'Whisper not installed' warning should be gone")
    print("3. You'll see 'Tier2 validation' entries in logs")
    print("=" * 80)


if __name__ == "__main__":
    main()
