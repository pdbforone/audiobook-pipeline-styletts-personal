# Gaps and Issues

> **Last Updated:** 2025-11-10
> **Status Legend:** ✅ Fixed | ⚠️ Partial | ❌ Open

---

## ✅ FIXED ISSUES

### 1. ~~`pipeline.json` schema mismatches between phases~~ **FIXED**
**Problem:** Phase 5.5 subtitle generation expected Phase 5 to write `phase5["output_file"]`, but Phase 5 only wrote status/metrics/artifacts without the final MP3 path. Phase 5.5 relied on hardcoded fallback paths, defeating the purpose of pipeline.json as source of truth.

**Solution (2025-11-10):**
- Phase 5 now writes `"output_file"` key to pipeline.json with path to audiobook.mp3 (`phase5_enhancement/src/phase5_enhancement/main.py:752`)
- Orchestrator updated to read from `phase5["output_file"]` first, with graceful fallbacks (`phase6_orchestrator/orchestrator.py:871-894`)
- Maintains backward compatibility with legacy structures

**Impact:** Phase 5.5 now correctly reads artifact paths from pipeline.json instead of guessing.

---

### 2. ~~Implemented CLI features remain undocumented~~ **FIXED**
**Problem:** Orchestrator exposed `--voice`, `--max-retries`, `--no-resume`, and `--enable-subtitles` flags, but README only documented legacy options. Additionally, README used incorrect flag name `--pipeline` instead of actual `--pipeline-json`.

**Solution (2025-11-10):**
- Fixed all Quick Start examples to use correct `--pipeline-json` flag
- Added comprehensive "Orchestrator CLI Options" section documenting all flags with examples (`phase6_orchestrator/README.md:43-78`)
- Documented default values and use cases for each option

**Impact:** Users can now discover and use all available CLI features.

---

### 3. ~~Missing runtime dependencies for `requests`~~ **FIXED**
**Problem:** Phase 4 utilities import `requests` but it wasn't in requirements.txt, causing potential network failures when downloading reference voices.

**Solution (2025-11-10):**
- Added `requests>=2.31.0` to Phase 4 requirements.txt (`phase4_tts/Chatterbox-TTS-Extended/requirements.txt:3`)
- Leverages existing `charset-normalizer==3.4.3` dependency (already present)

**Impact:** Phase 4 conda environment will now include requests library, eliminating import errors.

---

## ❌ OPEN ISSUES

### 4. Docs reference functions/modules that do not exist
- `PHASE_6.5_PUBLISHING_PLAN.md` prescribes running `poetry run python -m phase6_orchestrator.publisher` and describes a publishing stage that should run after Phase 5.5 (`PHASE_6.5_PUBLISHING_PLAN.md:1-55`), but there is no `publisher.py` anywhere in `phase6_orchestrator/`, nor does `orchestrator.py` have any hook beyond optional Phase 5.5 subtitles (`phase6_orchestrator/orchestrator.py:1120-1187`). The planned Phase 6.5 is therefore unimplemented despite being documented as ready.

**Status:** Open - Phase 6.5 automation is planned but not implemented
**Workaround:** Manual YouTube/podcast uploads as documented in publishing checklist
**Priority:** Medium - automation would save time but manual process works

---

### 5. ~~Tests reference scripts that are no longer in the repo~~ **VERIFIED - NOT AN ISSUE**
**Investigation Result:** The file `test_simple_text.py` DOES exist at `/phase4_tts/test_simple_text.py` (confirmed). Earlier reports of missing file were due to search limitations.

**Status:** Closed - No action needed

---

## 📊 Summary

| Issue | Status | Priority | Effort to Fix |
|-------|--------|----------|---------------|
| pipeline.json schema mismatches | ✅ Fixed | High | Complete |
| Undocumented CLI features | ✅ Fixed | High | Complete |
| Missing requests dependency | ✅ Fixed | Medium | Complete |
| Phase 6.5 not implemented | ❌ Open | Medium | 8-12 hours |
| Phantom test references | ✅ Verified OK | N/A | N/A |

**Next Recommended Action:** Implement Phase 6.5 automated publishing when bandwidth permits.
