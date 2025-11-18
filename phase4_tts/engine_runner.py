"""Engine-specific runner that manages per-engine virtual environments.

This wrapper keeps heavyweight dependencies isolated (XTTS vs Kokoro)
and allows the orchestrator to invoke each engine in its own process.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List

ROOT = Path(__file__).resolve().parent
ENGINE_ENV_ROOT = ROOT / ".engine_envs"
ENGINE_REQUIREMENTS = {
    "xtts": ROOT / "envs" / "requirements_xtts.txt",
    "kokoro": ROOT / "envs" / "requirements_kokoro.txt",
}
PYTHON_CANDIDATES = {
    # Include generic 'python' fallback for Windows where python3.x may not be on PATH
    "xtts": ("python3.11", "python3.10", "python3.9", "python3", "python"),
    "kokoro": ("python3.11", "python3", "python"),
}


def determine_default_workers() -> int:
    """Pick a sensible default worker count with env override support."""
    env_value = os.environ.get("PHASE4_WORKERS")
    if env_value:
        try:
            return max(1, int(env_value))
        except ValueError:
            pass

    cpu_total = os.cpu_count() or 2
    if cpu_total <= 2:
        return 1
    # Keep two cores free for I/O / OS, cap to a reasonable upper bound
    return max(1, min(cpu_total - 2, 6))


def get_env_python(engine: str) -> Path:
    """Ensure the engine-specific virtual environment exists and return python."""
    ENGINE_ENV_ROOT.mkdir(exist_ok=True)
    env_dir = ENGINE_ENV_ROOT / engine
    if os.name == "nt":
        python_path = env_dir / "Scripts" / "python.exe"
    else:
        python_path = env_dir / "bin" / "python"

    if python_path.exists():
        return python_path

    python_cmd = (
        os.environ.get(f"PHASE4_{engine.upper()}_PY")
        or os.environ.get("PHASE4_PYTHON_BIN")
        or find_python(PYTHON_CANDIDATES.get(engine, ("python3", "python")))
    )
    if python_cmd is None:
        raise RuntimeError(
            f"Unable to find a Python interpreter for engine '{engine}'. "
            f"Tried {PYTHON_CANDIDATES.get(engine)}."
        )

    env_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([python_cmd, "-m", "venv", str(env_dir)], check=True)

    req_file = ENGINE_REQUIREMENTS.get(engine)
    pip_cmd = [str(python_path), "-m", "pip"]
    subprocess.run([*pip_cmd, "install", "--upgrade", "pip", "wheel", "setuptools"], check=True)
    if req_file and req_file.exists():
        subprocess.run([*pip_cmd, "install", "-r", str(req_file)], check=True)

    return python_path


def find_python(candidates: Iterable[str]) -> str | None:
    for cmd in candidates:
        resolved = shutil.which(cmd)
        if resolved:
            return resolved
    return None


def build_phase4_command(args: argparse.Namespace, engine_py: Path, engine: str) -> List[str]:
    cmd = [
        str(engine_py),
        str(ROOT / "src" / "main_multi_engine.py"),
        f"--file_id={args.file_id}",
        f"--engine={engine}",
        f"--json_path={args.json_path}",
        "--config=config.yaml",
        f"--device={args.device}",
        f"--workers={args.workers}",
    ]

    if args.voice:
        cmd.append(f"--voice={args.voice}")
    if args.language:
        cmd.append(f"--language={args.language}")
    if args.chunk_id is not None:
        cmd.append(f"--chunk_id={args.chunk_id}")
    if args.disable_fallback:
        cmd.append("--disable_fallback")
    if args.resume:
        cmd.append("--resume")

    return cmd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 4 engine runner")
    parser.add_argument("--engine", required=True, choices=["xtts", "kokoro"])
    parser.add_argument("--file_id", required=True)
    parser.add_argument("--json_path", required=True)
    parser.add_argument("--voice")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--workers", type=int, default=determine_default_workers())
    parser.add_argument("--language")
    parser.add_argument("--chunk_id", type=int)
    parser.add_argument("--disable_fallback", action="store_true")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--resume", action="store_true", help="Skip existing chunk outputs (resume)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine_python = get_env_python(args.engine)
    cmd = build_phase4_command(args, engine_python, args.engine)

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    process = subprocess.run(cmd, cwd=str(ROOT), env=env)
    return process.returncode


if __name__ == "__main__":
    sys.exit(main())
