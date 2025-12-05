# Legacy Directories Analysis

**Date**: 2025-11-29
**Purpose**: Determine which directories are actively used vs. legacy/unused

---

## Summary

Out of 14 legacy directories analyzed:
- **3 are actively used** (agents, autonomy, introspection/long_horizon)
- **7 are NOT used** and can be safely removed
- **4 are configuration/assets** (need review)

---

## Actively Used Directories ✅

### 1. `agents/` (224 KB)
**Status**: ACTIVELY USED
**Used by**:
- [phase4_tts/src/main_multi_engine.py](phase4_tts/src/main_multi_engine.py): `from agents.llama_rewriter import LlamaRewriter`
- [phase6_orchestrator/orchestrator.py](phase6_orchestrator/orchestrator.py):
  - `from agents.llama_diagnostics import LlamaDiagnostics`
  - `from agents.llama_self_review import LlamaSelfReview`

**Contents**:
- `llama_base.py` - Base LLM agent class
- `llama_chunker.py` - Text chunking agent
- `llama_diagnostics.py` - **USED** in orchestrator
- `llama_metadata.py` - Metadata extraction
- `llama_reasoner.py` - Reasoning agent
- `llama_rewrite_policy.py` - Rewrite policies
- `llama_rewriter.py` - **USED** in Phase 4
- `llama_self_review.py` - **USED** in orchestrator

**Recommendation**: ✅ **KEEP** - Actively used for LLM-based text processing

---

### 2. `autonomy/` (260 KB)
**Status**: ACTIVELY USED
**Used by**:
- [phase6_orchestrator/orchestrator.py](phase6_orchestrator/orchestrator.py):
  - `from autonomy.profiles import export_profiles, reset_profiles`
  - `from autonomy.trace_recorder import begin_run_trace, finalize_trace, record_event`
  - `from autonomy.feature_attribution import explain_recommendations`
  - `from autonomy import introspection as auto_introspection`
  - `from autonomy import long_horizon as auto_long_horizon`

**Purpose**: Provides advanced orchestration features:
- Profile management
- Execution tracing
- Feature attribution
- Introspection
- Long-horizon planning

**Recommendation**: ✅ **KEEP** - Core orchestration functionality

---

### 3. `introspection/` (40 KB) & `long_horizon/` (40 KB)
**Status**: ACTIVELY USED (via autonomy module)
**Used by**:
- Orchestrator imports these through `autonomy` module

**Recommendation**: ✅ **KEEP** - Part of autonomy system

---

## Unused Directories (Safe to Remove) ❌

### 1. `audiobook_agent/` (9 KB)
**Status**: NOT USED
**Contents**:
- `agent_core.py`
- `storage_interface.py`

**Analysis**: No imports found in any active pipeline phase

**Recommendation**: ❌ **REMOVE** - Legacy code, no longer referenced

---

### 2. `genre_classifier/` (4 KB)
**Status**: NOT USED

**Analysis**: Genre classification is now handled by Phase 3's built-in profile system

**Recommendation**: ❌ **REMOVE** - Replaced by modern implementation

---

### 3. `orchestration/` (38 KB)
**Status**: NOT USED

**Analysis**: Orchestration logic is now in `phase6_orchestrator/orchestrator.py`

**Recommendation**: ❌ **REMOVE** - Superseded by Phase 6 orchestrator

---

### 4. `metadata/` (4 KB)
**Status**: NOT USED (false positives from .venv files)

**Analysis**: All matches were in virtual environment packages, not actual imports

**Recommendation**: ❌ **REMOVE** - No active usage

---

### 5. `g6_test_books/` (7 KB)
**Status**: NOT USED
**Contents**: Test text files (book_simple.txt, book_medium.txt, book_complex.txt)

**Analysis**: Old test data, not referenced by current tests

**Recommendation**: ❌ **REMOVE** - Legacy test data

---

### 6. `g6_verify_diffs/` (16 KB)
**Status**: NOT USED
**Contents**: Diff comparison files (diff_run1.txt, diff_run2.txt, diff_run3.txt)

**Analysis**: Old verification artifacts, no longer needed

**Recommendation**: ❌ **REMOVE** - Legacy verification data

---

### 7. `core/` (matched in .venv only)
**Status**: NOT USED in actual code

**Analysis**: All 189 matches were in virtual environment files, not pipeline code

**Recommendation**: ⚠️ **CHECK** - Verify `core/` directory doesn't exist or is empty

---

## Configuration Directories (Need Review) ⚠️

### 1. `config/` (matched in .venv only)
**Status**: UNCLEAR - 1278 matches in .venv files

**Analysis**: Need to verify if there's a separate `config/` directory vs. `configs/`

**Current structure**:
- `configs/` - Active configuration directory (voices.json, voice_references.json, etc.)
- `config/` - May be legacy or duplicate

**Recommendation**: ⚠️ **REVIEW** - Check if distinct from `configs/`, remove if duplicate

---

### 2. `assets/`
**Status**: Not analyzed (may contain static resources)

**Recommendation**: ⚠️ **REVIEW** - Check if contains required audio/image assets

---

## Cleanup Script

Here's a safe cleanup script to remove unused directories:

```bash
# Backup first (optional but recommended)
tar -czf legacy_dirs_backup_$(date +%Y%m%d).tar.gz \
    audiobook_agent genre_classifier orchestration metadata \
    g6_test_books g6_verify_diffs

# Remove unused directories
rm -rf audiobook_agent
rm -rf genre_classifier
rm -rf orchestration
rm -rf metadata
rm -rf g6_test_books
rm -rf g6_verify_diffs

# If core/ exists and is empty/legacy
# rm -rf core

echo "Cleanup complete! Removed 6 legacy directories"
```

**Disk Space Savings**:
- `audiobook_agent/`: 9 KB
- `genre_classifier/`: 4 KB
- `orchestration/`: 38 KB
- `metadata/`: 4 KB
- `g6_test_books/`: 7 KB
- `g6_verify_diffs/`: 16 KB
- **Total**: ~78 KB (minimal but good for code hygiene)

---

## Active Pipeline Structure

The current active pipeline uses:

```
pipeline/
├── phase1_ocr/              # OCR & text extraction
├── phase2-extraction/       # Text cleaning & formatting
├── phase3-chunking/         # Text chunking & profiling
├── phase4_tts/              # TTS synthesis (uses agents/)
├── phase5_enhancement/      # Audio enhancement
├── phase6_orchestrator/     # Main orchestrator (uses agents/, autonomy/)
├── ui/                      # Gradio web interface
├── pipeline_common/         # Shared utilities
├── configs/                 # Configuration files
├── agents/                  # ✅ LLM-based text processing (KEEP)
├── autonomy/                # ✅ Advanced orchestration (KEEP)
├── introspection/           # ✅ Part of autonomy (KEEP)
└── long_horizon/            # ✅ Part of autonomy (KEEP)
```

---

## Verification Steps

Before removing directories:

1. **Search for any remaining references**:
   ```bash
   grep -r "audiobook_agent\|genre_classifier\|orchestration" . \
       --include="*.py" --include="*.md" --include="*.yaml" \
       --exclude-dir=".venv" --exclude-dir="__pycache__"
   ```

2. **Check git history** (if these are experimental branches):
   ```bash
   git log --oneline --all --graph -- audiobook_agent/ genre_classifier/
   ```

3. **Run tests** after cleanup:
   ```bash
   cd tests
   pytest
   ```

---

## Summary Table

| Directory | Size | Status | Used By | Action |
|-----------|------|--------|---------|--------|
| `agents/` | 224 KB | ✅ Active | Phase 4, Phase 6 | **KEEP** |
| `autonomy/` | 260 KB | ✅ Active | Phase 6 | **KEEP** |
| `introspection/` | 40 KB | ✅ Active | Autonomy | **KEEP** |
| `long_horizon/` | 40 KB | ✅ Active | Autonomy | **KEEP** |
| `audiobook_agent/` | 9 KB | ❌ Unused | None | **REMOVE** |
| `genre_classifier/` | 4 KB | ❌ Unused | None | **REMOVE** |
| `orchestration/` | 38 KB | ❌ Unused | None | **REMOVE** |
| `metadata/` | 4 KB | ❌ Unused | None | **REMOVE** |
| `g6_test_books/` | 7 KB | ❌ Unused | None | **REMOVE** |
| `g6_verify_diffs/` | 16 KB | ❌ Unused | None | **REMOVE** |
| `config/` | ? | ⚠️ Unclear | Check vs `configs/` | **REVIEW** |
| `core/` | ? | ⚠️ Unclear | .venv only | **REVIEW** |
| `assets/` | ? | ⚠️ Unknown | Unknown | **REVIEW** |

**Total removable space**: ~78 KB (6 directories)
**Confidence**: High (based on code analysis of all active phases)

---

## Conclusion

**Recommendation**: Safe to remove 6 legacy directories (audiobook_agent, genre_classifier, orchestration, metadata, g6_test_books, g6_verify_diffs) after verification.

**Active directories to keep**: agents, autonomy, introspection, long_horizon

**Directories needing review**: config, core, assets
