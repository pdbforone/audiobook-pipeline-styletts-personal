# Subtitle & Publishing Status

## Phase 5.5 – Subtitle Generation
- **Implementation file present**: `phase5_enhancement/src/phase5_enhancement/subtitles.py` implements the Whisper-based `SubtitleGenerator` CLI described in the plan (`phase5_enhancement/src/phase5_enhancement/subtitles.py:1-40`).
- **Orchestrator integration**: `phase6_orchestrator/orchestrator.py` exposes `--enable-subtitles` and runs `run_phase5_5_subtitles` immediately after Phase 5 when the flag is set, invoking the Poetry CLI in Phase 5’s venv (`phase6_orchestrator/orchestrator.py:1062-1180`).
- **Tests**: `phase5_enhancement/tests/test_subtitles.py` plus helpers in `subtitle_aligner.py`/`subtitle_validator.py` provide pytest coverage for drift detection, alignment, and formatting (`phase5_enhancement/tests/test_subtitles.py:1-19`).
- **Plan accuracy**: `PHASE_5.5_SUBTITLES_PLAN.md` largely matches reality: the file layout exists, dependencies such as `webvtt-py` are listed in `phase5_enhancement/pyproject.toml`, and orchestrator-triggered generation aligns with the plan’s “Called by orchestrator after Phase 5” requirement (`PHASE_5.5_SUBTITLES_PLAN.md:6-34`). Minor deltas: the plan cites `--enable-subtitles` on the phase6 CLI, which now exists, and faster-whisper/webvtt versions may differ slightly (plan pins `^0.4.6`, repo uses `^0.5.1`), but functionally the plan is accurate.

## Phase 6.5 – Publishing Package
- **Implementation file present**: **No** `phase6_orchestrator/publisher.py` (or equivalent under `src/`) exists—`Test-Path` returns false, and `rg 'publisher' phase6_orchestrator` finds only the plan reference (`PHASE_6.5_PUBLISHING_PLAN.md:43`).
- **Orchestrator integration**: there are no references to “Phase 6.5”, “publisher”, or publishing-related CLI switches in `phase6_orchestrator/orchestrator.py`; the run loop stops after optional Phase 5.5 subtitles (`phase6_orchestrator/orchestrator.py:1120-1187`).
- **Tests**: No test module names or fixtures mention publishing; `phase6_orchestrator/tests` only covers phase coverage checks, so Phase 6.5 currently has zero automated coverage.
- **Plan accuracy**: The publishing plan describes release artifacts, cover generation, FFmpeg video output, and a `phase6_orchestrator.publisher` entry point (`PHASE_6.5_PUBLISHING_PLAN.md:1-45`), but none of these components exist. The plan is aspirational and outdated relative to the repo’s actual implementation (which stops at subtitles). Until code is added, this plan does not reflect reality.

## Summary Table
| Question | Phase 5.5 (Subtitles) | Phase 6.5 (Publishing) |
| --- | --- | --- |
| 1. Module file exists? | Yes – `src/phase5_enhancement/subtitles.py` | No publisher module present |
| 2. Orchestrator calls it? | Yes, gated by `--enable-subtitles` | No references or hooks |
| 3. Tests exist? | Yes – `phase5_enhancement/tests/test_subtitles.py` | No |
| 4. Plan file accurate? | Mostly (minor version drift only) | No – plan unimplemented |

**Action items**
1. Decide whether to enable `--enable-subtitles` by default or keep it opt-in; ensure pipeline.json captures subtitle artifacts (currently only logged).
2. For Phase 6.5, either implement `phase6_orchestrator.publisher` per the plan (release folder, cover art, FFmpeg video, metadata) and add tests, or update `PHASE_6.5_PUBLISHING_PLAN.md` to mark it as deferred so automation scripts don’t assume it exists.
