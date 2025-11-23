"""
Direct test of Phase 4 with one chunk to see full error messages
"""

import subprocess
import sys
from pathlib import Path

# Settings
phase4_dir = Path("../phase4_tts")
conda_env = "phase4_tts"
file_id = "The Analects of Confucius"
chunk_id = 0
pipeline_json = "../pipeline.json"

# Build command
cmd = [
    "conda",
    "run",
    "-n",
    conda_env,
    "--no-capture-output",
    "python",
    str(phase4_dir / "src" / "phase4_tts" / "main.py"),
    f"--chunk_id={chunk_id}",
    f"--file_id={file_id}",
    f"--json_path={pipeline_json}",
    f"--ref_file={phase4_dir / 'greenman_ref.wav'}",
]

print("Running Phase 4 directly for one chunk...")
print(f"Command: {' '.join(cmd)}\n")
print("=" * 60)

result = subprocess.run(
    cmd,
    cwd=str(phase4_dir),
    text=True,
    capture_output=False,  # Show output in real-time
)

print("=" * 60)
print(f"\nExit code: {result.returncode}")

if result.returncode == 0:
    print("✓ SUCCESS!")
else:
    print("✗ FAILED")

sys.exit(result.returncode)
