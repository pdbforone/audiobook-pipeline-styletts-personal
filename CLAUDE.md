# CLAUDE.md — Personal Audiobook Studio

> *"The people who are crazy enough to think they can change the world are the ones who do."*

## READ FIRST: The Canon

**[AUTONOMOUS_PIPELINE_ROADMAP.md](AUTONOMOUS_PIPELINE_ROADMAP.md)** is the project canon — 1500+ lines defining the vision, implementation status, and technical decisions. Read it before making significant changes.

**Key sections in the roadmap:**
- Latest Updates (Post-Coqui XTTS hardening, Kokoro as default)
- 12 LLM Agents and their integration points
- Self-healing architecture
- Implementation status matrix
- Phase A-F + G-H + L-M + AA-AB breakdown

---

## The Philosophy

**This is not a script factory. It's a Personal Audiobook Studio.**

Marcus Aurelius doesn't *read* his Meditations — he *reflects* them. The difference between 2 hours and 5 hours is irrelevant because you'll listen for 10+.

**Always choose quality.** We think like craftsmen, designer-engineers, and research scientists. Elegant, minimal, inevitable solutions.

---

## Quick Reference

### TTS Engines (Current Status)

| Engine | Role | Notes |
|--------|------|-------|
| **Kokoro** | **DEFAULT** | CPU-optimized, Apache 2.0, best for most use cases |
| **XTTS** | Voice cloning | Use only when zero-shot cloning required; Post-Coqui hardening applied |
| Piper | **DISABLED** | Intentionally disabled — project standardizes on Kokoro/XTTS only |

### Best Kokoro Voices for Audiobooks

| Voice | Gender | Accent | Best For |
|-------|--------|--------|----------|
| `af_bella` | Female | American | Fiction, memoir (DEFAULT) |
| `af_sarah` | Female | American | Academic, philosophy |
| `bf_emma` | Female | British | Classic literature |
| `am_adam` | Male | American | Philosophy, theology |
| `bm_george` | Male | British | Academic content |

### The 12 LLM Agents

| Agent | Location | Purpose |
|-------|----------|---------|
| **LlamaChunker** | `agents/llama_chunker.py` | Semantic chunk boundary detection |
| **LlamaReasoner** | `agents/llama_reasoner.py` | Pipeline failure analysis |
| **LlamaRewriter** | `agents/llama_rewriter.py` | TTS-friendly text rewriting |
| **LlamaMetadataGenerator** | `agents/llama_metadata.py` | Audiobook metadata generation |
| **LlamaPreValidator** | `agents/llama_pre_validator.py` | Pre-synthesis text analysis |
| **LlamaVoiceMatcher** | `agents/llama_voice_matcher.py` | Intelligent voice selection |
| **LlamaChunkReviewer** | `agents/llama_chunk_reviewer.py` | Post-batch quality analysis |
| **LlamaSemanticRepetition** | `agents/llama_semantic_repetition.py` | Deep repetition detection |
| **LlamaSelfReview** | `agents/llama_self_review.py` | Post-run reflection |
| **LlamaDiagnostics** | `agents/llama_diagnostics.py` | Run diagnostics |

All agents have graceful fallback when Ollama unavailable.

---

## Architecture

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

| Phase | Purpose | Entry Point |
|-------|---------|-------------|
| **1: Validate** | Integrity, repair, metadata | `phase1_validation.validation` |
| **2: Extract** | Multi-format ingest, OCR | `phase2_extraction.extraction` |
| **3: Chunk** | Genre-aware segmentation | `phase3_chunking.main` |
| **4: TTS** | Kokoro/XTTS synthesis | `phase4_tts.engine_runner` |
| **5: Master** | Audio enhancement, LUFS | `phase5_enhancement.main` |
| **5.5: Subtitles** | Whisper transcription | Optional |
| **6: Orchestrate** | Single-file coordination | `phase6_orchestrator.orchestrator` |
| **7: Batch** | Multi-file parallel | `phase7_batch.main` |

---

## The Schema — pipeline.json

`pipeline.json` is the **single source of truth**. Schema v4.0.0.

### Key Files
- **JSON Schema**: `pipeline_common/schema.json`
- **Pydantic Models**: `pipeline_common/models.py`
- **Validation**: `pipeline_common/schema.py`
- **Documentation**: `PIPELINE_JSON_SCHEMA.md`

### Usage Pattern
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

---

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

# Handle errors explicitly
if not audio_path.exists():
    return {"status": "failed", "errors": ["Audio file not found"]}
```

### DON'T
```python
# Don't mutate pipeline.json directly
data["phase4"]["status"] = "success"  # BAD: No locking

# Don't hardcode status strings
chunk["status"] = "complete"  # BAD: Use "success"

# Don't couple phases
from phase4_tts import some_internal  # BAD: Phases are independent
```

---

## Latest Critical Fixes (2025-12)

### XTTS Post-Coqui Hardening
- **Underscore Trick**: Append `_` to text → fixes EOS prediction
- **Optimized Penalties**: `repetition_penalty=3.5`, `length_penalty=1.2`
- **Seed Management**: Deterministic synthesis via `XTTS_SYNTHESIS_SEED=42`
- **Segment-Level Synthesis**: Pre-split text <220 chars to avoid internal XTTS splitting

### Phase 3 Chunk Duplication Fix
Fixed critical bug where sentences appeared in multiple consecutive chunks.

### Process Recycling
For 500+ chunk books: `RecyclingProcessPool` restarts workers every N tasks.

---

## Audio Quality Standards

| Metric | Target |
|--------|--------|
| LUFS | -23 to -16 (preset dependent) |
| Dynamic Range | 8-20 dB |
| Sample Rate | 24kHz |
| Format | WAV (processing), MP3 (final) |

---

## Common Commands

```bash
# Launch the UI
python ui/app.py

# Process a single book
python -m phase6_orchestrator.orchestrator \
  --input input/meditations.epub \
  --pipeline pipeline.json \
  --voice af_bella \
  --engine kokoro

# Run schema tests
pytest tests/test_schema_v4_validation.py -v

# Run integration tests
RUN_PHASE_O_FULL=1 pytest tests/integration/ -v
```

---

## Key Files

| File | Purpose |
|------|---------|
| `AUTONOMOUS_PIPELINE_ROADMAP.md` | **THE CANON** — Read this first |
| `pipeline.json` | Master state file |
| `pipeline_common/schema.json` | Schema v4.0.0 |
| `pipeline_common/state_manager.py` | Atomic state operations |
| `phase6_orchestrator/orchestrator.py` | Main orchestration |
| `agents/` | 12 LLM agents |
| `ui/app.py` | Gradio interface |

---

## When in Doubt

| Question | Document |
|----------|----------|
| **Roadmap/Status?** | `AUTONOMOUS_PIPELINE_ROADMAP.md` |
| **Schema?** | `PIPELINE_JSON_SCHEMA.md` |
| **Architecture?** | `DESIGN_FIRST_REFACTOR_PLAN.md` |
| **Philosophy?** | `CRAFT_EXCELLENCE_VISION.md` |
| **Voices?** | `VOICE_SELECTION_GUIDE.md` |

---

*Craft, not production. Quality, not speed. Local-first, CPU-friendly, no external API dependencies.*
