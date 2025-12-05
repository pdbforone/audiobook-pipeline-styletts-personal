# Auto Mode Feature

**Date**: 2025-11-30
**Status**: ✅ IMPLEMENTED
**Impact**: Enables fully AI-driven voice selection based on genre detection

---

## Overview

Auto Mode is a new UI feature that allows the AI to automatically select the most appropriate voice for an audiobook based on genre detection. When enabled, it bypasses manual voice selection and lets Phase 3's AI make intelligent decisions about which voice best matches the detected book genre.

---

## How It Works

### Manual Mode (Default)
```
User selects voice: "Baldur Sanjin"
    ↓
UI → pipeline_api → orchestrator
    ↓
orchestrator passes --voice="Baldur Sanjin" to Phase 3
    ↓
Phase 3 uses CLI override (Priority 1)
    ↓
All chunks use "Baldur Sanjin" voice
```

### Auto Mode (🤖 AI-Driven)
```
User enables "Auto Mode" checkbox
    ↓
UI sets voice_id=None, auto_mode=True
    ↓
UI → pipeline_api → orchestrator
    ↓
orchestrator does NOT pass --voice to Phase 3
    ↓
Phase 3 skips CLI override (Priority 1)
Phase 3 detects genre: "philosophy"
Phase 3 uses genre profile match (Priority 4) → AI selects voice
    ↓
Phase 3 selects "Baldur Sanjin" (philosophy-optimized voice)
    ↓
All chunks use AI-selected voice based on genre
```

---

## Voice Selection Priority (Phase 3)

From [voice_selection.py](phase3-chunking/src/phase3_chunking/voice_selection.py):

1. **CLI override (--voice flag)** - HIGHEST PRIORITY
   - Used in manual mode when orchestrator passes --voice
   - **Bypassed in auto mode** (no --voice flag passed)

2. **File-level override** (pipeline.json voice_overrides.{file_id})
   - Per-file voice customization
   - Still respected in auto mode

3. **Global override** (pipeline.json tts_voice)
   - Global voice customization
   - Still respected in auto mode

4. **Genre profile match** - **AUTO MODE USES THIS**
   - AI detects genre (philosophy, fiction, academic, memoir, technical)
   - Selects voice from genre's preferred_profiles
   - Example: philosophy → "Baldur Sanjin" (measured, contemplative)

5. **Default voice** (fallback) - LOWEST PRIORITY
   - Used only if no genre match found

---

## Implementation Details

### 1. UI (ui/app.py)

**Lines 1389-1393**: Auto mode checkbox added to Single Book tab
```python
auto_mode = gr.Checkbox(
    label="🤖 Auto Mode (AI selects voice based on genre)",
    value=False,
    info="Let AI automatically choose the best voice for detected genre. Overrides manual voice selection.",
)
```

**Lines 907-915**: Auto mode logic in handle_create_audiobook()
```python
# In auto mode, AI selects voice based on genre; otherwise use manual selection
if auto_mode:
    voice_id = None  # Let Phase 3 AI select voice based on genre
    logger.info("Auto mode enabled: AI will select voice based on detected genre")
else:
    voice_meta = self.voice_manager.get_voice(voice_selection)
    if not voice_meta:
        return None, "❌ Please select a voice.", ui_state
    voice_id = voice_meta.voice_id
```

**Lines 954, 962**: Pass voice_id (None in auto mode) and auto_mode parameter
```python
result = await ui_state.pipeline_api.run_pipeline_async(
    file_path=file_path,
    voice_id=voice_id,  # None in auto mode, specific voice otherwise
    # ...
    auto_mode=bool(auto_mode),
    # ...
)
```

**Lines 990-1004**: Success message shows "AI-selected (auto mode)" when enabled
```python
if auto_mode:
    options_list.append("🤖 Auto mode (AI-selected voice based on genre)")
# ...
voice_display = "AI-selected (auto mode)" if auto_mode else voice_id
```

### 2. Pipeline API (ui/services/pipeline_api.py)

**Lines 386-401**: Updated run_pipeline_async() signature
```python
async def run_pipeline_async(
    self,
    *,
    file_path: Path,
    voice_id: Optional[str],  # Now Optional[str] instead of str
    # ...
    auto_mode: bool,
    # ...
) -> Dict[str, Any]:
```

**Lines 425-439**: Updated _run_pipeline_sync() signature
```python
def _run_pipeline_sync(
    self,
    file_path: Path,
    voice_id: Optional[str],  # Now Optional[str]
    # ...
    auto_mode: bool,
    # ...
) -> Dict[str, Any]:
```

**Lines 456-469**: Pass auto_mode to orchestrator's run_pipeline()
```python
return run_pipeline(
    file_path=file_path,
    voice_id=voice_id,  # Can be None in auto mode
    # ...
    auto_mode=auto_mode,
)
```

### 3. Orchestrator (phase6_orchestrator/orchestrator.py)

**Lines 3684-3698**: Updated run_pipeline() signature
```python
def run_pipeline(
    file_path: Path,
    voice_id: Optional[str] = None,  # Already Optional
    # ...
    auto_mode: bool = False,
    # ...
) -> Dict:
```

**Lines 3704, 3714**: Updated docstring
```python
Args:
    voice_id: Voice ID to use for TTS (ignored if auto_mode=True)
    # ...
    auto_mode: Let AI select voice based on genre detection (overrides voice_id)
```

**Lines 3912-3917**: Auto mode logic (CRITICAL SECTION)
```python
# Auto mode: Let AI select voice based on genre detection (Phase 3)
if auto_mode:
    logger.info("🤖 Auto mode enabled: AI will select voice based on detected genre")
    voice_id = None  # Don't pass --voice to Phase 3; let genre detection choose
elif voice_id:
    logger.info(f"Using manual voice selection: {voice_id}")
```

**Lines 2012-2013**: Voice is NOT passed to Phase 3 when voice_id=None
```python
# BUGFIX: Pass voice selection to Phase 3 so chunk voice_overrides are set correctly
if voice_id:  # When auto_mode=True, voice_id=None, so this is skipped
    cmd.append(f"--voice={voice_id}")
```

---

## User Experience

### UI Flow

1. **Upload book** (e.g., "The Republic" by Plato)
2. **Enable Auto Mode checkbox** (🤖 Auto Mode)
3. **Voice dropdown becomes irrelevant** (AI will choose)
4. **Click "Generate Audiobook"**

### Behind the Scenes

1. UI sets `voice_id=None`, `auto_mode=True`
2. Orchestrator skips passing `--voice` to Phase 3
3. Phase 3 detects genre: "philosophy"
4. Phase 3 AI selects voice: "Baldur Sanjin" (philosophy-optimized)
5. Logs show: `🤖 Auto mode enabled: AI will select voice based on detected genre`
6. Logs show: `Voice selection: baldur_sanjin (Profile match (philosophy → baldur_sanjin))`

### Success Message

```
✅ Audiobook generated successfully!

**Configuration:**
- Voice: AI-selected (auto mode)
- Engine: XTTS v2 (Expressive)
- Mastering: audiobook_intimate

**Options:**
- 🤖 Auto mode (AI-selected voice based on genre)

**Output:**
- Path: `phase5_enhancement/processed/audiobook.mp3`
```

---

## Benefits

### For Users
1. **No voice expertise required** - Just upload the book and let AI choose
2. **Genre-optimized voices** - AI matches voice to book genre automatically
3. **Consistent results** - Same book type always gets appropriate voice
4. **Faster workflow** - Skip manual voice selection step

### For AI Decision-Making
1. **Enables Phase 3 AI** - Lets genre detection + voice matching work as designed
2. **No manual overrides** - CLI override (Priority 1) is bypassed
3. **Fully autonomous** - AI makes influential, smart decisions
4. **Transparent** - Logs show exactly which voice AI selected and why

---

## Genre → Voice Mappings

From [configs/voices.json](configs/voices.json):

| Genre | Preferred Voice(s) | Voice Characteristics |
|-------|-------------------|----------------------|
| **Philosophy** | Baldur Sanjin, Jim Locke | Measured, contemplative, thoughtful |
| **Fiction** | af_heart, Alison Dietlinde | Warm, engaging, expressive |
| **Academic** | Landon Elkind | Clear, authoritative, structured |
| **Memoir** | Tom Weiss | Personal, intimate, narrative |
| **Technical** | George McKayland | Precise, informative, steady |

**Example**:
- Book: "The World of Universals" (philosophy)
- Auto mode detects: "philosophy" genre
- AI selects: "Baldur Sanjin" (preferred for philosophy)
- Result: Perfect voice match for philosophical text

---

## Testing

### Test Case 1: Philosophy Book (Auto Mode)

**Setup**:
1. Upload "The Republic" by Plato
2. Enable "Auto Mode" checkbox
3. Select any engine (e.g., XTTS)
4. Click "Generate Audiobook"

**Expected Behavior**:
```
UI log: "Auto mode enabled: AI will select voice based on detected genre"
Phase 3 log: "Detected genre: philosophy"
Phase 3 log: "Voice selection: baldur_sanjin (Profile match (philosophy → baldur_sanjin))"
Success message: "Voice: AI-selected (auto mode)"
```

**Verify**:
- Voice used is "Baldur Sanjin" (or another philosophy-preferred voice)
- No --voice flag passed to Phase 3
- Genre detection worked correctly

### Test Case 2: Fiction Book (Auto Mode)

**Setup**:
1. Upload "The Great Gatsby" by F. Scott Fitzgerald
2. Enable "Auto Mode" checkbox
3. Click "Generate Audiobook"

**Expected Behavior**:
```
Phase 3 log: "Detected genre: fiction"
Phase 3 log: "Voice selection: af_heart (Profile match (fiction → af_heart))"
```

**Verify**:
- Voice used is "af_heart" or another fiction-preferred voice
- Voice characteristics match fiction genre (warm, engaging)

### Test Case 3: Manual Mode (Baseline)

**Setup**:
1. Upload any book
2. **Disable** "Auto Mode" checkbox
3. **Manually select** "George McKayland" voice
4. Click "Generate Audiobook"

**Expected Behavior**:
```
UI log: "Using manual voice selection"
orchestrator log: "Using manual voice selection: George McKayland"
Phase 3 log: "Voice selection: george_mckayland (CLI override (--voice George McKayland))"
Success message: "Voice: george_mckayland"
```

**Verify**:
- Voice used is exactly "George McKayland" (manual selection)
- --voice flag passed to Phase 3
- Genre detection result ignored

---

## Limitations

### 1. Genre Detection Accuracy
- **Current**: Rule-based heuristics (keyword matching)
- **Future**: Could use LLM for better genre classification (see AI_DECISION_POINTS.md)
- **Mitigation**: Voice profile fallback ensures reasonable default

### 2. Single Voice Per Book
- **Current**: Auto mode selects one voice for entire audiobook
- **Future**: Could support multi-voice (narrator vs dialogue characters)
- **Mitigation**: Users can still manually override specific chunks

### 3. Requires Voice Profiles
- **Current**: Only works if voices have `preferred_profiles` in voices.json
- **Future**: Auto-learn voice→genre mappings from user feedback
- **Mitigation**: Default voice fallback if no genre match

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     UI (app.py)                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Voice Dropdown   │  │ Auto Mode ☑      │                │
│  │ (ignored if auto)│  │ (enabled)        │                │
│  └──────────────────┘  └──────────────────┘                │
│               │                  │                           │
│               └──────┬───────────┘                           │
│                      ↓                                       │
│            voice_id = None                                   │
│            auto_mode = True                                  │
└─────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│             Pipeline API (pipeline_api.py)                   │
│                                                              │
│  run_pipeline_async(voice_id=None, auto_mode=True)         │
└─────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│           Orchestrator (orchestrator.py)                     │
│                                                              │
│  if auto_mode:                                               │
│      voice_id = None  # Don't pass --voice to Phase 3       │
│      logger.info("🤖 Auto mode enabled")                    │
└─────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│             Phase 3 (voice_selection.py)                     │
│                                                              │
│  # Priority 1: CLI override (--voice flag)                  │
│  if cli_override:  # SKIPPED (no --voice passed)            │
│      ...                                                     │
│                                                              │
│  # Priority 4: Genre profile match ← AUTO MODE USES THIS    │
│  if not selected_voice:                                      │
│      genre = detect_genre(text)  # "philosophy"             │
│      matching_voices = find_voices_for_profile(genre)       │
│      selected_voice = matching_voices[0]  # "baldur_sanjin" │
│      logger.info("Profile match (philosophy → baldur_sanjin)")│
└─────────────────────────────────────────────────────────────┘
                       ↓
             Voice: "Baldur Sanjin"
             (AI-selected based on genre)
```

---

## Related Documentation

- **[AI_DECISION_POINTS.md](AI_DECISION_POINTS.md)** - All AI features across pipeline
- **[phase3-chunking/src/phase3_chunking/voice_selection.py](phase3-chunking/src/phase3_chunking/voice_selection.py)** - Voice selection logic
- **[phase3-chunking/src/phase3_chunking/detect.py](phase3-chunking/src/phase3_chunking/detect.py)** - Genre detection logic
- **[configs/voices.json](configs/voices.json)** - Voice registry with genre preferences
- **[VOICE_OVERRIDE_BUG_FIX.md](VOICE_OVERRIDE_BUG_FIX.md)** - Related voice system fixes

---

## Summary

**Auto Mode** is a powerful new feature that enables fully AI-driven voice selection in the audiobook pipeline. When enabled:

1. ✅ **User skips manual voice selection** - Just upload book and go
2. ✅ **AI detects genre** - Uses Phase 3 genre detection (philosophy, fiction, etc.)
3. ✅ **AI selects best voice** - Matches voice to genre using preferred_profiles
4. ✅ **Transparent decision-making** - Logs show exactly which voice AI chose and why
5. ✅ **Zero manual overrides** - No CLI flags, no manual intervention

**The AI makes influential, high-impact decisions that optimize audiobook quality for the detected genre.**

**Impact**: Transforms the pipeline from **semi-manual** to **fully autonomous** for voice selection.
