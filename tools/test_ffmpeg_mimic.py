import os
from pathlib import Path
import datetime

REPO_ROOT = Path(__file__).resolve().parents[1]
logs_dir = REPO_ROOT / "phase5_enhancement" / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
pid = os.getpid()
log_name = f"ffmpeg_failure_test_{timestamp}_{pid}.log"
content = (
    "FFmpeg command: fake-ffmpeg -i in.wav out.wav\n"
    "Exit code: 2\n\n--- STDOUT (preview) ---\n"
    "(none)\n\n--- STDERR (preview) ---\n"
    "error: simulated failure\n"
)
log_path = logs_dir / log_name
with open(log_path, "w", encoding="utf-8") as fh:
    fh.write(content)
print("Wrote diagnostics to:", log_path)
print(log_path.read_text())
