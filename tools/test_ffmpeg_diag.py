import sys
from pathlib import Path

# Ensure repo root importable
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from phase5_enhancement.src.phase5_enhancement.ffmpeg_utils import run_ffmpeg  # noqa: E402

print("Running ffmpeg diagnostic test...")
try:
    # Command that exits non-zero
    run_ffmpeg([sys.executable, "-c", "import sys; sys.exit(2)"], "ffmpeg-test")
except Exception as e:
    print("Raised:", repr(e))
    # Search for logs in phase5_enhancement/logs
    logs_dir = REPO_ROOT / "phase5_enhancement" / "logs"
    print("Logs dir exists:", logs_dir.exists())
    if logs_dir.exists():
        print("Recent logs:")
        for p in sorted(logs_dir.glob("ffmpeg_failure_*"), reverse=True)[:5]:
            print("-", p)
print("Done")
