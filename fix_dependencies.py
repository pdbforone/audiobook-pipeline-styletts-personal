"""
Quick fix script to install missing dependencies in engine environments.

This script installs g2p-en in the XTTS engine environment to fix number expansion warnings.

Usage:
    python fix_dependencies.py
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
    try:
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "install", package],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            print(f"✅ Successfully installed {package}")
            return True
        else:
            print(f"❌ Failed to install {package}")
            print(f"   Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ Installation timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("=" * 80)
    print("Dependency Fix Script")
    print("=" * 80)

    # Check for engine environments
    engine_envs_dir = Path("phase4_tts/.engine_envs")
    if not engine_envs_dir.exists():
        print(f"❌ Engine environments directory not found: {engine_envs_dir}")
        print("   This script is meant for multi-engine TTS setup.")
        sys.exit(1)

    # Install g2p-en in XTTS environment
    xtts_env = engine_envs_dir / "xtts"
    if xtts_env.exists():
        print(f"\n🔧 Fixing XTTS environment...")
        success = install_in_venv(xtts_env, "g2p-en")
        if success:
            print(f"   ✅ XTTS environment updated")
        else:
            print(f"   ❌ Failed to update XTTS environment")
    else:
        print(f"⚠️  XTTS environment not found: {xtts_env}")

    # Optional: Install in Kokoro environment too
    kokoro_env = engine_envs_dir / "kokoro"
    if kokoro_env.exists():
        print(f"\n🔧 Fixing Kokoro environment (optional)...")
        install_in_venv(kokoro_env, "g2p-en")

    print("\n" + "=" * 80)
    print("✅ Dependency fix complete!")
    print("\nNext steps:")
    print("1. Re-run Phase 4 to verify g2p-en warnings are gone")
    print("2. Check logs for 'g2p_en not installed' - should not appear")
    print("=" * 80)


if __name__ == "__main__":
    main()
