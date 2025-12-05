# Auto Mode Implementation Summary

**Date**: 2025-11-30
**Status**: ✅ COMPLETE
**Impact**: Fully autonomous AI-driven voice selection based on genre detection

---

## What Was Implemented

A new **Auto Mode** feature that enables fully AI-driven voice selection throughout the audiobook pipeline. When enabled via a UI checkbox, the AI automatically selects the best voice for the detected book genre without any manual intervention.

---

## Files Modified

### 1. UI Layer ([ui/app.py](ui/app.py))

**Lines 1389-1393**: Added Auto Mode checkbox to Single Book tab
```python
auto_mode = gr.Checkbox(
    label="🤖 Auto Mode (AI selects voice based on genre)",
    value=False,
    info="Let AI automatically choose the best voice for detected genre. Overrides manual voice selection.",
)
```

**Lines 886-900**: Updated `handle_create_audiobook()` signature to accept `auto_mode` parameter

**Lines 907-915**: Auto mode logic - sets `voice_id=None` when enabled
```python
if auto_mode:
    voice_id = None  # Let Phase 3 AI select voice based on genre
    logger.info("Auto mode enabled: AI will select voice based on detected genre")
else:
    voice_meta = self.voice_manager.get_voice(voice_selection)
    if not voice_meta:
        return None, "❌ Please select a voice.", ui_state
    voice_id = voice_meta.voice_id
```

**Lines 962**: Pass `auto_mode` parameter to pipeline API

**Lines 990-1004**: Success message shows "AI-selected (auto mode)" when enabled

**Lines 1474-1490**: Updated button click handler to include `auto_mode` in inputs

### 2. Pipeline API Layer ([ui/services/pipeline_api.py](ui/services/pipeline_api.py))

**Lines 386-401**: Updated `run_pipeline_async()` signature
- Changed `voice_id: str` to `voice_id: Optional[str]`
- Added `auto_mode: bool` parameter

**Lines 425-439**: Updated `_run_pipeline_sync()` signature with same changes

**Lines 456-469**: Pass `auto_mode` to orchestrator's `run_pipeline()` function

### 3. Orchestrator Layer ([phase6_orchestrator/orchestrator.py](phase6_orchestrator/orchestrator.py))

**Lines 3684-3698**: Updated `run_pipeline()` signature
- Added `auto_mode: bool = False` parameter
- Updated docstring to explain auto mode behavior

**Lines 3704, 3714**: Updated documentation
```python
Args:
    voice_id: Voice ID to use for TTS (ignored if auto_mode=True)
    # ...
    auto_mode: Let AI select voice based on genre detection (overrides voice_id)
```

**Lines 3912-3917**: **CRITICAL LOGIC** - Auto mode sets `voice_id=None`
```python
# Auto mode: Let AI select voice based on genre detection (Phase 3)
if auto_mode:
    logger.info("🤖 Auto mode enabled: AI will select voice based on detected genre")
    voice_id = None  # Don't pass --voice to Phase 3; let genre detection choose
elif voice_id:
    logger.info(f"Using manual voice selection: {voice_id}")
```

**Lines 2012-2013**: When `voice_id=None`, no `--voice` flag is passed to Phase 3
```python
# BUGFIX: Pass voice selection to Phase 3 so chunk voice_overrides are set correctly
if voice_id:  # In auto mode, this is None, so --voice is NOT passed
    cmd.append(f"--voice={voice_id}")
```

### 4. Documentation

**Created**: [AUTO_MODE_FEATURE.md](AUTO_MODE_FEATURE.md) (comprehensive feature documentation)
**Updated**: [AI_DECISION_POINTS.md](AI_DECISION_POINTS.md) (added auto mode to AI features table)

---

## How It Works

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     UI (app.py)                              │
│                                                              │
│  User enables: ☑ Auto Mode (AI selects voice)              │
│                                                              │
│  Result:                                                     │
│    voice_id = None                                          │
│    auto_mode = True                                         │
└─────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│             Pipeline API (pipeline_api.py)                   │
│                                                              │
│  run_pipeline_async(voice_id=None, auto_mode=True)         │
│  → _run_pipeline_sync(voice_id=None, auto_mode=True)       │
└─────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│           Orchestrator (orchestrator.py)                     │
│                                                              │
│  if auto_mode:                                               │
│      logger.info("🤖 Auto mode enabled")                    │
│      voice_id = None  # Ensure no --voice flag             │
│                                                              │
│  Phase 3 execution:                                          │
│    if voice_id:  # False (voice_id is None)                │
│        cmd.append(f"--voice={voice_id}")  # SKIPPED        │
└─────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│             Phase 3 (voice_selection.py)                     │
│                                                              │
│  Priority 1: CLI override (--voice flag)                    │
│    if cli_override:  # No --voice passed, SKIPPED           │
│                                                              │
│  Priority 4: Genre profile match ← AUTO MODE USES THIS      │
│    genre = detect_genre(text)  # "philosophy"               │
│    selected_voice = "baldur_sanjin"                         │
│    logger.info("Profile match (philosophy → baldur_sanjin)")│
└─────────────────────────────────────────────────────────────┘
```

### Voice Selection Priority (Phase 3)

1. **CLI override (--voice flag)** - HIGHEST PRIORITY
   - **Manual mode**: Orchestrator passes `--voice="UserSelection"`
   - **Auto mode**: No `--voice` flag passed (SKIPPED) ✅

2. **File-level override** (pipeline.json)
   - Still respected in both modes

3. **Global override** (pipeline.json)
   - Still respected in both modes

4. **Genre profile match** - **AUTO MODE ACTIVATES HERE** ✅
   - AI detects genre: philosophy, fiction, academic, memoir, technical
   - Selects voice from genre's preferred_profiles
   - Example: philosophy → "Baldur Sanjin"

5. **Default voice** (fallback) - LOWEST PRIORITY
   - Used only if no genre match

---

## User Experience

### Before (Manual Mode)

1. User uploads book
2. **User must select voice from dropdown** (requires voice knowledge)
3. User clicks "Generate Audiobook"
4. Voice used: User's manual selection

### After (Auto Mode Enabled)

1. User uploads book
2. **User enables "Auto Mode" checkbox**
3. User clicks "Generate Audiobook"
4. Voice used: **AI-selected based on detected genre** ✅

### UI Feedback

**Success message in auto mode**:
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

## Technical Benefits

### 1. Fully Autonomous Voice Selection
- **Before**: User must know which voice suits which genre
- **After**: AI automatically matches voice to genre

### 2. Enables AI Decision-Making
- **Before**: CLI override (Priority 1) always blocked genre-based selection
- **After**: Auto mode bypasses CLI override, letting genre detection work

### 3. Genre-Optimized Results
- Philosophy books → Measured, contemplative voices
- Fiction books → Warm, engaging voices
- Academic books → Clear, authoritative voices
- Technical books → Precise, informative voices

### 4. Consistent Quality
- Same genre always gets appropriate voice characteristics
- No user error from voice mismatches

### 5. Transparent AI Decisions
- Logs show exactly which genre was detected
- Logs show exactly which voice AI selected and why
- Example: `"Voice selection: baldur_sanjin (Profile match (philosophy → baldur_sanjin))"`

---

## Testing Recommendations

### Test Case 1: Philosophy Book
**Book**: "The Republic" by Plato
**Steps**:
1. Enable Auto Mode checkbox
2. Generate audiobook
**Expected**: Voice = "Baldur Sanjin" (or other philosophy-optimized voice)
**Verify**: Logs show `"Detected genre: philosophy"`

### Test Case 2: Fiction Book
**Book**: "The Great Gatsby"
**Steps**:
1. Enable Auto Mode checkbox
2. Generate audiobook
**Expected**: Voice = "af_heart" (or other fiction-optimized voice)
**Verify**: Logs show `"Detected genre: fiction"`

### Test Case 3: Manual Mode (Baseline)
**Book**: Any book
**Steps**:
1. **Disable** Auto Mode checkbox
2. Manually select "George McKayland" voice
3. Generate audiobook
**Expected**: Voice = "George McKayland" (manual selection)
**Verify**: Logs show `"CLI override (--voice George McKayland)"`

---

## Related Documentation

- **[AUTO_MODE_FEATURE.md](AUTO_MODE_FEATURE.md)** - Comprehensive feature documentation with diagrams
- **[AI_DECISION_POINTS.md](AI_DECISION_POINTS.md)** - All AI features across the pipeline
- **[phase3-chunking/src/phase3_chunking/voice_selection.py](phase3-chunking/src/phase3_chunking/voice_selection.py)** - Voice selection priority logic
- **[phase3-chunking/src/phase3_chunking/detect.py](phase3-chunking/src/phase3_chunking/detect.py)** - Genre detection implementation
- **[configs/voices.json](configs/voices.json)** - Voice registry with genre preferences

---

## Summary

**Auto Mode** transforms the audiobook pipeline from **semi-manual** to **fully autonomous** for voice selection:

### What Changed
✅ **UI**: Added Auto Mode checkbox to Single Book tab
✅ **Pipeline API**: Added `auto_mode` parameter throughout call chain
✅ **Orchestrator**: Auto mode sets `voice_id=None` to bypass CLI override
✅ **Phase 3**: Genre detection + voice matching now works without manual override
✅ **Documentation**: Comprehensive docs created (AUTO_MODE_FEATURE.md, updated AI_DECISION_POINTS.md)

### Impact
- **Before**: User manually selects voice (requires expertise)
- **After**: AI automatically selects best voice for detected genre (zero expertise required)

### AI Decision-Making
- **Before**: CLI override always blocked genre-based voice selection
- **After**: Auto mode enables AI to make influential, high-impact decisions

**The AI now makes smart, autonomous decisions about voice selection based on genre, eliminating the need for manual voice expertise.**

---

## Files Modified Summary

1. **ui/app.py** - Added auto mode UI checkbox and logic (6 sections modified)
2. **ui/services/pipeline_api.py** - Added auto_mode parameter (4 sections modified)
3. **phase6_orchestrator/orchestrator.py** - Added auto mode logic (3 sections modified)
4. **AI_DECISION_POINTS.md** - Updated to document auto mode (3 sections modified)
5. **AUTO_MODE_FEATURE.md** - Created comprehensive feature documentation (NEW)

**Total lines modified**: ~50 lines across 5 files
**Status**: ✅ COMPLETE AND READY FOR TESTING
