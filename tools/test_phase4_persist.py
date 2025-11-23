import json
import shutil
from pathlib import Path
import tempfile
from pipeline_common import PipelineState

# Create a test copy of pipeline.json
REPO_ROOT = Path(__file__).resolve().parents[1]
orig = REPO_ROOT / "pipeline.json"
if not orig.exists():
    print("No pipeline.json found in repo root; aborting test.")
    raise SystemExit(1)

test_path = REPO_ROOT / "pipeline.test.json"
shutil.copyfile(orig, test_path)
print("Created test pipeline copy:", test_path)

# Choose a file_id to test: pick first phase4 file or create one
state = PipelineState(test_path, validate_on_read=False)
data = state.read(validate=False)
phase4 = data.get("phase4", {}) or {}
files = phase4.get("files", {}) or {}

if files:
    file_id = next(iter(files.keys()))
    print("Using existing phase4 file_id:", file_id)
else:
    file_id = "TEST_FILE"
    print("No existing phase4 files; creating test entry for:", file_id)

# Ensure the entry exists and remove chunk_audio_paths if present
with state.transaction() as txn:
    phase4 = txn.data.get("phase4", {}) or {}
    files = phase4.get("files", {}) or {}
    files.setdefault(file_id, {})
    files[file_id].pop("chunk_audio_paths", None)
    files[file_id]["total_chunks"] = files[file_id].get("total_chunks", 3)
    phase4["files"] = files
    txn.data["phase4"] = phase4

print("Removed (or ensured absent) chunk_audio_paths; writing transaction done.")

# Now run the same persistence logic used in orchestrator.collect_failed_chunks
try:
    state = PipelineState(test_path, validate_on_read=False)
    with state.transaction() as txn:
        phase4 = txn.data.get("phase4", {}) or {}
        files = phase4.get("files", {}) or {}
        files.setdefault(file_id, {})
        files[file_id].setdefault("chunk_audio_paths", [])
        phase4["files"] = files
        txn.data["phase4"] = phase4
    print("Persisted fallback chunk_audio_paths=[] for", file_id)
except Exception as e:
    print("Failed to persist fallback:", e)
    raise

# Verify
state = PipelineState(test_path, validate_on_read=False)
data = state.read(validate=False)
entry = data.get("phase4", {}).get("files", {}).get(file_id, {})
print("Final entry chunk_audio_paths:", entry.get("chunk_audio_paths"))
print("Test pipeline saved at:", test_path)
