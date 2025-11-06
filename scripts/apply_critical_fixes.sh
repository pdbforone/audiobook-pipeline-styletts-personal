#!/bin/bash
set -euo pipefail

echo "🔧 Applying critical fixes to audiobook pipeline..."

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQ_FILE="$REPO_ROOT/phase4_tts/Chatterbox-TTS-Extended/requirements.txt"
PHASE4_ENV="phase4_tts"

echo ""
echo "📦 Ensuring charset-normalizer is listed for Phase 4..."

if [[ ! -f "$REQ_FILE" ]]; then
  echo "❌ Requirements file not found at $REQ_FILE"
  exit 1
fi

update_result="$(python - "$REQ_FILE" <<'PY'
import sys
from pathlib import Path

req_path = Path(sys.argv[1])
lines = req_path.read_text(encoding="utf-8").splitlines()
target = "charset-normalizer==3.4.3"

if any(line.strip().startswith("charset-normalizer") for line in lines):
    print("skip")
else:
    try:
        idx = next(i for i, line in enumerate(lines) if line.strip().lower() == "gradio")
        lines.insert(idx + 1, target)
    except StopIteration:
        lines.append(target)
    req_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("added")
PY
)"

if [[ "$update_result" == "added" ]]; then
  echo "✅ Added charset-normalizer==3.4.3 to requirements.txt"
else
  echo "ℹ️ charset-normalizer already present in requirements.txt"
fi

echo ""
echo "📦 Installing charset-normalizer inside Conda env ($PHASE4_ENV)..."
if conda env list | grep -q "^$PHASE4_ENV\\s"; then
  conda run -n "$PHASE4_ENV" pip install "charset-normalizer==3.4.3" >/dev/null
  echo "✅ Conda environment now has charset-normalizer==3.4.3"
else
  echo "⚠️ Conda environment '$PHASE4_ENV' not found. Skipping pip install."
fi

echo ""
echo "🧪 Running Phase 4 tests..."
set +e
conda run -n "$PHASE4_ENV" python -m pytest phase4_tts/tests -v
test_status=$?
set -e

if [[ $test_status -eq 0 ]]; then
  echo "✅ Phase 4 tests passed."
else
  echo "⚠️ Phase 4 tests returned exit code $test_status (see output above)."
fi

echo ""
echo "✅ Critical fixes applied!"
echo ""
echo "📋 Summary:"
if [[ "$update_result" == "added" ]]; then
  echo "  ✅ Inserted charset-normalizer==3.4.3 into Phase 4 requirements"
else
  echo "  ℹ️ charset-normalizer requirement already present"
fi
if conda env list | grep -q "^$PHASE4_ENV\\s"; then
  echo "  ✅ Ensured Conda env '$PHASE4_ENV' has charset-normalizer installed"
else
  echo "  ⚠️ Skipped pip install (env '$PHASE4_ENV' missing)"
fi
if [[ $test_status -eq 0 ]]; then
  echo "  ✅ Phase 4 pytest suite completed successfully"
else
  echo "  ⚠️ Phase 4 pytest suite reported failures"
fi

echo ""
echo "Next steps:"
echo "  1. Review test output above (especially if warnings appeared)."
echo "  2. Rerun: conda run -n $PHASE4_ENV python -m pytest phase4_tts/tests -v (after any fixes)."
echo "  3. Proceed with orchestration: poetry run python -m phase6_orchestrator.orchestrator --enable-subtitles"
echo ""
