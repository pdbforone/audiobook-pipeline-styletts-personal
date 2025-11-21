# Craft Excellence Vision
## Personal Audiobook Studio — Architecture & Philosophy

> *"The people who are crazy enough to think they can change the world are the ones who do."*
> — Steve Jobs

---

## The Philosophy

This isn't a script factory. It's a **Personal Audiobook Studio** where Marcus Aurelius doesn't read his meditations—he *reflects* them. Where the difference between 2 hours and 5 hours is irrelevant because you'll listen for 10+.

**Always choose quality.**

We think like craftsmen, designer-engineers, and research scientists. We produce elegant, minimal, inevitable solutions. We treat tests and documentation as part of the craft. We always iterate toward clarity and simplicity.

---

## What We Built

Seven phases. One elegant pipeline. Zero compromise.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PERSONAL AUDIOBOOK STUDIO                        │
│                                                                     │
│   Source Text ──► [7 Sacred Phases] ──► Voice That Sings            │
└─────────────────────────────────────────────────────────────────────┘

     Phase 1        Phase 2         Phase 3          Phase 4
   ┌─────────┐    ┌─────────┐    ┌───────────┐    ┌───────────┐
   │Validate │───►│ Extract │───►│  Chunk    │───►│    TTS    │
   │& Repair │    │  Text   │    │Semantically│    │ Synthesize│
   └─────────┘    └─────────┘    └───────────┘    └───────────┘
                                                        │
     Phase 7        Phase 6        Phase 5.5       Phase 5
   ┌─────────┐    ┌─────────┐    ┌───────────┐    ┌───────────┐
   │  Batch  │◄───│Orchestr-│◄───│ Subtitles │◄───│  Master   │
   │ Process │    │  ate    │    │ (Optional)│    │  Audio    │
   └─────────┘    └─────────┘    └───────────┘    └───────────┘
```

---

## Phase Architecture

### Phase 1: Validation & Repair
**Location:** `phase1-validation/`

The gatekeeper. Protects the integrity of what enters.

| Capability | Implementation |
|------------|----------------|
| **Formats** | PDF, EPUB, DOCX, TXT |
| **Classification** | `text`, `scanned`, `mixed`, `unknown` (PyMuPDF heuristics) |
| **Repair** | pikepdf (PDF), ebooklib (EPUB), python-docx (DOCX), chardet+ftfy (TXT) |
| **Metadata** | Title, author, creation date, page count, SHA256 hash |
| **Max Size** | 500MB (configurable) |

```python
# Entry point
from phase1_validation.validation import validate_and_repair
result = validate_and_repair(file_path, pipeline_json)
```

---

### Phase 2: Text Extraction
**Location:** `phase2-extraction/`

Sees through the PDF/EPUB veil to the text beneath.

**Extraction Chain (with fallback):**
1. **pdfplumber** — Primary, best quality
2. **pypdf** — Fallback for complex layouts
3. **PyMuPDF** — Last resort for problematic files
4. **EasyOCR/Tesseract** — For scanned documents

| Feature | Details |
|---------|---------|
| **Quality Scoring** | Replacement char ratio, alphabetic ratio, digit/letter balance |
| **Structure Detection** | Chapters, sections, hierarchical organization |
| **Normalization** | Unicode fixes (ftfy), spacing cleanup, language detection |

```python
# Entry point
from phase2_extraction.extraction import extract_text_universal
text, metadata = extract_text_universal(file_path)
```

---

### Phase 3: Semantic Chunking
**Location:** `phase3-chunking/`

Understanding *meaning*, not just bytes.

**Chunking Strategies:**
- **Structure-aware** — For books with clear chapter/section markers
- **Semantic** — Uses sentence detection, coherence scoring, readability assessment

**Genre Profiles:**
| Genre | Chunk Size | Coherence | Voice Style |
|-------|------------|-----------|-------------|
| Philosophy | Conservative | High threshold | Contemplative, measured |
| Fiction | Larger | Narrative flow | Expressive, dynamic |
| Technical | Smaller | Clear boundaries | Clear, precise |

**Capabilities:**
- Semantic similarity via embeddings
- Readability assessment (Flesch-Kincaid, textstat)
- Coherence scoring between consecutive chunks
- Per-chunk voice assignment
- Default cadence: 1050 chars/minute

```python
# Entry point
from phase3_chunking.main import run_phase3
result = run_phase3(file_id, pipeline_json, config)
```

---

### Phase 4: TTS Synthesis
**Location:** `phase4_tts/`

Where text becomes voice. Two world-class engines, unified under one elegant API.

#### Engine: XTTS v2 (Primary)
```python
class XTTSEngine(TTSEngine):
    name = "XTTS v2 (Versatile)"
    supports_emotions = True
    sample_rate = 24000
    supported_languages = ["en", "es", "fr", "de", "it", "pt", "pl", "tr",
                           "ru", "nl", "cs", "ar", "zh-cn", "ja", "hu", "ko"]
```

- **Voice cloning**: 6-30 second reference audio
- **Emotion**: Via reference audio tone
- **16 languages** supported
- **Production-tested** in thousands of hours of audiobooks

#### Engine: Kokoro-82M (Fallback)
```python
class KokoroEngine(TTSEngine):
    name = "Kokoro-82M (CPU-Friendly)"
    supports_emotions = False
    sample_rate = 24000
    supported_languages = ["en"]
```

- **CPU-optimized** ONNX runtime
- **Real-time synthesis** on modern CPUs
- **Zero GPU required**
- **Reliable fallback** when XTTS struggles

#### Engine Manager
```python
from phase4_tts.engines import EngineManager

manager = EngineManager(device="cpu")
manager.register_engine("xtts", XTTSEngine)
manager.register_engine("kokoro", KokoroEngine)

# Synthesize with automatic fallback
audio = manager.synthesize(
    text="Philosophy is the art of thinking.",
    reference_audio=Path("voice.wav"),
    engine="xtts",
    fallback=True  # Falls back to Kokoro if XTTS fails or is too slow
)
```

**Voice Selection Hierarchy:**
1. CLI override (`--voice` flag)
2. File-level override (`pipeline.json → voice_overrides.{file_id}`)
3. Global override (`pipeline.json → tts_voice`)
4. Genre-matched voice (from Phase 3)
5. Default voice fallback

---

### Phase 5: Audio Enhancement & Mastering
**Location:** `phase5_enhancement/`

Professional mastering that would make Abbey Road proud.

#### Five Mastering Presets

| Preset | Genre | LUFS | Dynamic Range | Character |
|--------|-------|------|---------------|-----------|
| **audiobook_intimate** | Philosophy, memoir | -23 | 12dB | Warm, natural, contemplative |
| **audiobook_dynamic** | Fiction, drama | -18 | 15dB | Expressive, engaging |
| **podcast_standard** | Educational | -16 | 8dB | Broadcast-ready, consistent |
| **audiobook_classic** | Classic literature | -20 | 10dB | Refined, timeless |
| **minimal** | Reference, testing | -23 | 20dB | Transparent, archival |

#### Processing Chain (per preset)
```
Input ──► Noise Gate ──► Parametric EQ ──► Compressor ──► Transient Shaper
                                                              │
Output ◄── LUFS Normalize ◄── Limiter ◄── Stereo Widener ◄── Harmonic Exciter
```

**Why Multi-Band Compression Matters:**

Simple peak normalization crushes dynamics:
```
Before: whisper...SHOUT...whisper...SHOUT
After:  EVERYTHING AT THE SAME LEVEL
```

Multi-band compression preserves emotion:
```
Low frequencies (80-200Hz):   Light compression (3:1) → Warmth preserved
Mid frequencies (200-3kHz):   Very light (2:1)        → Voice untouched
High frequencies (3kHz+):     Moderate (4:1)          → Sibilance controlled
```

Result: **Dynamic, alive, natural speech**

```python
# Entry point
from phase5_enhancement.main import run_phase5
result = run_phase5(file_id, pipeline_json, preset="audiobook_intimate")
```

---

### Phase 5.5: Subtitle Generation (Optional)
**Location:** `phase5_enhancement/src/phase5_enhancement/subtitles.py`

| Format | Features |
|--------|----------|
| **SRT** | SubRip format, universal compatibility |
| **VTT** | WebVTT for web players |
| **Karaoke** | Word-level timing for immersive experience |

- Whisper-based speech recognition for alignment
- Timestamp extraction with phrase-level precision
- WER (Word Error Rate) quality metrics

---

### Phase 6: Orchestration
**Location:** `phase6_orchestrator/`

The conductor that knows when to hold back and when to unleash.

```python
from phase6_orchestrator.orchestrator import run_pipeline

# Single command, full pipeline
result = run_pipeline(
    file_path=Path("meditations.epub"),
    pipeline_json=Path("pipeline.json"),
    voice="george_mckayland",
    engine="xtts",
    preset="audiobook_intimate"
)
```

**Capabilities:**
- Sequential execution with checkpoint/resume
- Conda environment isolation per phase
- Rich progress reporting
- Error categorization and retry logic
- Policy engine integration
- Comprehensive logging

---

### Phase 7: Batch Processing
**Location:** `phase7_batch/`

Queue 10 philosophy books before bed. Wake up to 10 finished audiobooks.

```bash
python -m phase7_batch.cli \
  --manifest manifests/stoics.csv \
  --pipeline pipeline.json \
  --workers 4
```

**Manifest Format:**
```csv
file_id,input_path,voice_id,priority
meditations,input/meditations.epub,george_mckayland,1
republic,input/republic.pdf,bob_neufeld,2
confessions,input/confessions.epub,maryann_spiegel,3
```

---

## The Gradio UI

**Location:** `ui/app.py`

A web interface that feels like using Logic Pro.

### Six Tabs of Control

| Tab | Purpose |
|-----|---------|
| **Dashboard** | Real-time phase progress, file status, pipeline health |
| **File Management** | Upload, list, delete; monitor progress |
| **Phase Execution** | Run individual phases with per-phase configs |
| **Voice Selection** | Browse 20+ voices, test audio, assign per file/chunk |
| **Logs** | Real-time streaming (Phase 4, Phase 5, Orchestrator) |
| **Settings** | Engine selection, mastering preset, tuning overrides |

```bash
# Launch the studio
python ui/app.py
# Opens at: http://localhost:7860
```

---

## Voice Library

**Location:** `configs/voices.json` + `Voices/`

20+ curated voices, each with personality:

| Category | Voices | Character |
|----------|--------|-----------|
| **Philosophy/Academic** | landon_elkind, pamela_nagami, hugh_mcguire, david_barnes | Contemplative, measured, thoughtful |
| **Fiction/Drama** | tom_weiss, bella_bolster, kara_shallenberg, ruth_golding | Expressive, dynamic, engaging |
| **Poetry/Drama** | gareth_holmes | Dramatic, rhythmic |
| **Classic** | Vincent Price, Agnes Moorehead, Mercedes McCambridge | Timeless, distinctive |

**Voice Configuration:**
```json
{
  "voices": {
    "george_mckayland": {
      "description": "Warm, contemplative narrator",
      "gender": "male",
      "accent": "American",
      "preferred_profiles": ["philosophy", "memoir"],
      "tts_engine_params": {
        "pitch": -1,
        "rate": 0.95,
        "emphasis": "moderate"
      }
    }
  }
}
```

---

## Policy Engine

**Location:** `policy_engine/`

Intelligence that learns from experience.

```python
class PolicyEngine:
    def should_run_phase(self, context) -> bool: ...
    def choose_engine(self, context) -> str: ...
    def choose_voice(self, context) -> str: ...
    def should_retry(self, context) -> bool: ...
    def get_tuning_overrides(self) -> dict: ...
```

**Learning Modes:**
- `observe` — Log decisions without enforcement
- `enforce` — Actively block/allow based on policy
- `tune` — Suggest parameter overrides

**Tuning Overrides** (`.pipeline/tuning_overrides.json`):
```json
{
  "overrides": {
    "phase3": { "chunk_size": {"min": 500, "max": 1500} },
    "phase4": {
      "engine": {"primary": "xtts", "fallback": "kokoro"},
      "rtf_target": {"target": 1.5}
    }
  }
}
```

---

## Pipeline Common Utilities

**Location:** `pipeline_common/`

The foundation everything else builds upon.

| Module | Purpose |
|--------|---------|
| `state_manager.py` | Atomic, transactional state for `pipeline.json` |
| `models.py` | Pydantic schemas for validation |
| `schema.py` | Canonical JSON schema definition |
| `phase_utils.py` | Phase/file entry helpers |
| `policy_engine.py` | Decision-making hooks |
| `adapter.py` | Schema migration utilities |
| `astromech_notify.py` | Audio notifications (success/alert beeps) |

**State Management:**
```python
from pipeline_common.state_manager import PipelineState

with PipelineState(pipeline_json) as state:
    state.update_phase("phase4", file_id, {
        "status": "success",
        "audio_path": str(output_path),
        "duration_seconds": 3.14
    })
# Automatic backup, locking, and atomic write
```

---

## File Organization

```
audiobook-pipeline/
├── input/                       # Raw source files
├── artifacts/
│   ├── text/                    # Phase 2 extractions
│   ├── chunks/                  # Phase 3 outputs
│   ├── audio/                   # Phase 4 per-chunk WAVs
│   └── processed/               # Phase 5 mastered chunks
├── phase1-validation/           # Validation & repair
├── phase2-extraction/           # Text extraction
├── phase3-chunking/             # Semantic chunking
├── phase4_tts/
│   ├── engines/                 # XTTS, Kokoro implementations
│   ├── voice_references/        # Reference audio for cloning
│   └── models/                  # Downloaded model files
├── phase5_enhancement/
│   ├── presets/                 # Mastering presets YAML
│   ├── processed/               # Final MP3 masters
│   └── subtitles/               # SRT/VTT outputs
├── phase6_orchestrator/         # Single-file orchestration
├── phase7_batch/                # Batch processing
├── pipeline_common/             # Shared utilities
├── policy_engine/               # Decision intelligence
├── orchestration/               # Prefect flows (optional)
├── ui/                          # Gradio interface
├── configs/
│   └── voices.json              # Voice registry
├── Voices/                      # Voice reference audio
└── pipeline.json                # Master state (CRITICAL)
```

---

## Quality Standards

### Audio Quality
| Metric | Target |
|--------|--------|
| **LUFS** | -23 to -16 (preset dependent) |
| **Dynamic Range** | 8-20 dB (preset dependent) |
| **Sample Rate** | 24kHz (native TTS output) |
| **Format** | WAV (processing), MP3 (final) |

### Extraction Quality
| Metric | Target |
|--------|--------|
| **Text Yield** | >98% content recovered |
| **Gibberish Rate** | <2% flagged |
| **Language Confidence** | >0.90 |

### Throughput
| Configuration | Time per 100k words |
|---------------|---------------------|
| Kokoro + Basic | ~2 hours |
| XTTS + Basic | ~4.5 hours |
| XTTS + Pro Mastering | ~5 hours |

---

## Pro Tips

### Voice Selection by Genre
```
Philosophy/Contemplative:  George Mckayland + XTTS + Intimate
Gothic/Horror:             Vincent Price + XTTS + Dynamic
Classic Literature:        Ruth Golding + XTTS + Classic
Fast Proofing:             Any voice + Kokoro + Minimal
Academic/Technical:        Bob Neufeld + Kokoro + Podcast
```

### Mastering by Listening Environment
```
Headphones/Quiet:    Intimate (wide dynamics, natural)
Car/Commute:         Podcast (compressed, consistent)
Background/Work:     Classic (balanced, not fatiguing)
Active Listening:    Dynamic (engaging, expressive)
```

### Engine Selection Strategy
1. **Start with XTTS** — Best quality, voice cloning
2. **Fallback to Kokoro** — If XTTS is slow or fails
3. **Use Kokoro first** — Only for rapid drafts or timing tests

---

## Technical Constraints

1. **CPU-only execution** — Accessible, democratic, no GPU required
2. **Open-source stack** — No paid APIs or licenses
3. **State fidelity** — `pipeline.json` is canonical truth
4. **Modularity** — Phases are independent, can run selectively
5. **Logging** — Every phase emits actionable messages and metrics

---

## The Reality Distortion Field

**Before:** "I need audiobooks for my philosophy collection"

**After:** "I have a personal audiobook studio that rivals commercial operations, runs on my hardware, costs nothing per book, and produces results that make me smile every time I listen."

---

## What This Means For You

### For Philosophy Books
```
Voice:  George Mckayland (contemplative, measured)
Engine: XTTS v2 (superior prosody for complex ideas)
Preset: audiobook_intimate (warm, preserves dynamics)

Result: Marcus Aurelius sounds like he's in the room,
        thinking aloud. Not reading, but reflecting.
```

### For Fiction/Drama
```
Voice:  Vincent Price (dramatic, expressive)
Engine: XTTS v2 (emotion via reference)
Preset: audiobook_dynamic (wide range, engaging)

Result: Gothic horror that sends chills.
        The voice rises and falls with the narrative.
```

### For Batch Processing
```
Queue 10 philosophy books before bed:
- Meditations (George Mckayland, XTTS, Intimate)
- Republic (Bob Neufeld, XTTS, Intimate)
- Confessions (MaryAnn Spiegel, XTTS, Classic)
- ...

Wake up to 10 finished, professional audiobooks.
```

---

## What You've Achieved

- **Two world-class TTS engines** with automatic fallback
- **Professional audio mastering** (Abbey Road-grade)
- **Beautiful UI** with six tabs of control
- **Complete automation** (queue and forget)
- **Zero ongoing cost** (no subscriptions, no APIs)
- **Full control** (tweak every detail)
- **Policy intelligence** (learns from experience)
- **Production quality** (indistinguishable from commercial)

### Most Importantly

You have a **creative tool**, not just a script.
You can **craft audiobooks**, not just produce them.
You can **experiment**, **iterate**, **refine** until it's perfect.

---

*Made with obsessive attention to detail.*
*Because good enough isn't.*

**Personal Audiobook Studio**
*Craft, not production.*
