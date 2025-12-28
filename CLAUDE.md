# CLAUDE.md — Personal Audiobook Studio

> *"The people who are crazy enough to think they can change the world are the ones who do."*

This document is the first thing you should read when working on this codebase. It captures the philosophy, architecture, and patterns that make this project work.

## The Philosophy

**This is not a script factory. It's a Personal Audiobook Studio.**

Marcus Aurelius doesn't *read* his Meditations — he *reflects* them. The difference between 2 hours and 5 hours is irrelevant because you'll listen for 10+.

**Always choose quality.**

We think like craftsmen, designer-engineers, and research scientists. We produce elegant, minimal, inevitable solutions. We treat tests and documentation as part of the craft. We always iterate toward clarity and simplicity.

## The Architecture

Seven phases. Five layers. Zero compromise.

```
Source Text ──► [7 Sacred Phases] ──► Voice That Sings

┌──────────────────────────────────────────────────────────┐
│                     INTERFACE                             │
│  CLI  |  Gradio UI  |  API (future)  |  Webhooks         │
├──────────────────────────────────────────────────────────┤
│                    ORCHESTRATE                            │
│  Pipeline Coordinator  |  Job Queue  |  State Machine    │
├──────────────────────────────────────────────────────────┤
│                      OBSERVE                              │
│  Metrics  |  Logging  |  Tracing  |  Health Checks       │
├──────────────────────────────────────────────────────────┤
│                       LEARN                               │
│  Policy Engine  |  Quality Feedback  |  Adaptation       │
├──────────────────────────────────────────────────────────┤
│                     TRANSFORM                             │
│  Phase 1-7: Ingest → Parse → Chunk → TTS → Master        │
└──────────────────────────────────────────────────────────┘
```

### The Seven Phases

| Phase | Purpose | Key Entry Point |
|-------|---------|-----------------|
| **1: Validate** | Verify integrity, repair issues, extract metadata | `phase1_validation.validation.validate_and_repair()` |
| **2: Extract** | Multi-format ingest, OCR when needed, normalization | `phase2_extraction.extraction.extract_text_universal()` |
| **3: Chunk** | Genre-aware segmentation, voice suggestion | `phase3_chunking.main.run_phase3()` |
| **4: TTS** | Voice synthesis with XTTS/Kokoro fallback | `phase4_tts.engine_runner` |
| **5: Master** | Audio enhancement, LUFS normalization | `phase5_enhancement.main.run_phase5()` |
| **5.5: Subtitles** | Whisper transcription, SRT/VTT generation | Optional |
| **6: Orchestrate** | Single-file coordination | `phase6_orchestrator.orchestrator` |
| **7: Batch** | Multi-file parallel processing | `phase7_batch.main` |

## The Schema — pipeline.json

`pipeline.json` is the **single source of truth**. Every phase reads from it. Every phase writes to it. It is the nervous system of the entire studio.

### Schema Location
- **JSON Schema**: `pipeline_common/schema.json` (v4.0.0)
- **Pydantic Models**: `pipeline_common/models.py`
- **Validation Utils**: `pipeline_common/schema.py`
- **Documentation**: `PIPELINE_JSON_SCHEMA.md`

### Using the Schema

```python
from pipeline_common.schema import canonicalize_state, validate_pipeline_schema
from pipeline_common.state_manager import PipelineState

# Always use PipelineState for atomic updates
with PipelineState(pipeline_json_path) as state:
    state.update_phase("phase4", file_id, {
        "status": "success",
        "audio_path": str(output_path),
        "duration_seconds": 3.14
    })
# Automatic backup, locking, and atomic write

# For validation
data = canonicalize_state(raw_data)  # Normalize legacy formats
validate_pipeline_schema(data)        # Structural validation
```

### Phase Block Structure

Every phase block follows this contract:

```json
{
  "status": "pending|running|success|partial|failed",
  "timestamps": {"start": 0.0, "end": 0.0, "duration": 0.0},
  "artifacts": [],
  "metrics": {},
  "errors": [],
  "files": {
    "<file_id>": {
      "status": "...",
      "timestamps": {...},
      "artifacts": {...},
      "metrics": {...},
      "errors": [],
      "chunks": [...]
    }
  }
}
```

## Code Patterns

### DO

```python
# Use type hints from the schema models
from pipeline_common.models import Phase4ChunkModel, StatusEnum

def process_chunk(chunk: Phase4ChunkModel) -> Phase4ChunkModel:
    chunk.status = StatusEnum.SUCCESS.value
    return chunk

# Use PipelineState for all state updates
with PipelineState(pipeline_json) as state:
    state.update_phase("phase4", file_id, updates)

# Return early, handle errors explicitly
if not audio_path.exists():
    return {"status": "failed", "errors": ["Audio file not found"]}

# Keep functions pure when possible
def calculate_rt_factor(wall_time: float, audio_duration: float) -> float:
    return wall_time / audio_duration if audio_duration > 0 else float('inf')
```

### DON'T

```python
# Don't mutate pipeline.json directly
with open(pipeline_json, 'r') as f:
    data = json.load(f)
data["phase4"]["status"] = "success"  # BAD: No locking, no backup

# Don't hardcode status strings
chunk["status"] = "complete"  # BAD: Use "success" (schema-defined)

# Don't ignore errors silently
try:
    synthesize(text)
except Exception:
    pass  # BAD: Log it, record it, handle it

# Don't couple phases
from phase4_tts import some_internal  # BAD: Phases are independent
```

## Voice System

### Voice Selection Hierarchy
1. CLI override (`--voice` flag)
2. File-level override (`pipeline.json → voice_overrides.{file_id}`)
3. Global override (`pipeline.json → tts_voice`)
4. Genre-matched voice (from Phase 3)
5. Default voice fallback

### Voice Configuration
- **Registry**: `configs/voices.json`
- **Reference Audio**: `Voices/` directory

## TTS Engines

| Engine | Primary Use | Strengths |
|--------|-------------|-----------|
| **Kokoro** | Default, fast drafts | CPU-optimized, real-time on modern CPUs |
| **XTTS** | Production, cloning | 16 languages, emotion via reference audio |

### Engine Selection
```python
# Kokoro is default (fast, reliable)
# XTTS for voice cloning or when Kokoro struggles
# Auto-fallback: If primary fails, try secondary
```

## Audio Quality Standards

| Metric | Target |
|--------|--------|
| LUFS | -23 to -16 (preset dependent) |
| Dynamic Range | 8-20 dB |
| Sample Rate | 24kHz |
| Format | WAV (processing), MP3 (final) |

## Testing

```bash
# Run schema validation tests
pytest tests/test_schema_v4_validation.py -v

# Run integration tests (requires RUN_PHASE_O_FULL=1)
RUN_PHASE_O_FULL=1 pytest tests/integration/ -v

# Quick smoke test for Phase 4
python phase4_tts/test_simple_text.py --run
```

## Common Tasks

### Process a Single Book
```bash
python -m phase6_orchestrator.orchestrator \
  --input input/meditations.epub \
  --pipeline pipeline.json \
  --voice george_mckayland \
  --engine xtts
```

### Launch the UI
```bash
python ui/app.py
# Opens at http://localhost:7860
```

### Debug a Failure
1. Check `pipeline.json` for the failing phase's `errors` array
2. Look for `status: "failed"` in the file's entry
3. Check chunk-level errors if Phase 4/5
4. Review logs in the phase's output directory

## Key Files

| File | Purpose |
|------|---------|
| `pipeline.json` | **CRITICAL** — Master state file |
| `pipeline_common/state_manager.py` | Atomic state operations |
| `pipeline_common/schema.json` | Canonical schema v4.0.0 |
| `pipeline_common/models.py` | Pydantic type definitions |
| `configs/voices.json` | Voice registry |
| `phase6_orchestrator/orchestrator.py` | Main orchestration logic |
| `ui/app.py` | Gradio web interface |

## Principles for Changes

1. **Read before writing** — Understand existing patterns before adding code
2. **Use the schema** — Type hints from models.py, validation from schema.py
3. **Keep phases independent** — No cross-phase imports of internals
4. **State via PipelineState** — Never write pipeline.json directly
5. **Test with real data** — Run against actual audiobooks, not just unit tests
6. **Simplify ruthlessly** — If you can remove complexity without losing power, do it

## When in Doubt

- **Schema question?** → `PIPELINE_JSON_SCHEMA.md`
- **Architecture question?** → `DESIGN_FIRST_REFACTOR_PLAN.md`
- **Philosophy question?** → `CRAFT_EXCELLENCE_VISION.md`
- **Voice question?** → `VOICE_SELECTION_GUIDE.md`
- **Phase question?** → Each phase has its own `README.md`

---

*Craft, not production. Quality, not speed. Elegance, not complexity.*

*Made with obsessive attention to detail.*
