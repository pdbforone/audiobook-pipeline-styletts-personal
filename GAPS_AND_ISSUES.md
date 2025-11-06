# Gaps and Issues

## 1. Docs reference functions/modules that do not exist
- `PHASE_6.5_PUBLISHING_PLAN.md` prescribes running `poetry run python -m phase6_orchestrator.publisher` and describes a publishing stage that should run after Phase 5.5 (`PHASE_6.5_PUBLISHING_PLAN.md:1-55`), but there is no `publisher.py` anywhere in `phase6_orchestrator/`, nor does `orchestrator.py` have any hook beyond optional Phase 5.5 subtitles (`phase6_orchestrator/orchestrator.py:1120-1187`). The planned Phase 6.5 is therefore unimplemented despite being documented as ready.

## 2. Implemented CLI features remain undocumented
- The orchestrator exposes `--voice`, `--max-retries`, `--no-resume`, and `--enable-subtitles` switches (`phase6_orchestrator/orchestrator.py:1062-1088`), yet the README’s “With Options” section still lists only the legacy flags for pipeline path, selected phases, and skipping Phase 4 (`phase6_orchestrator/README.md:34-52`). Users reading the docs have no way to discover the newer capabilities (voice override, retry tuning, resume disabling, subtitle generation).

## 3. Missing runtime dependencies for `requests`
- Every command currently emits `RequestsDependencyWarning: Unable to find acceptable character detection dependency (chardet or charset_normalizer)` from the global install (`C:\Users\myson\miniconda3\Lib\site-packages\requests\__init__.py:86`). Phase 4 utilities import `requests` directly (`phase4_tts/src/utils.py:6-20`), so this missing dependency will degrade network calls (e.g., downloading reference voices) until `charset-normalizer`/`chardet` is added to the environment running Phase 4.

## 4. Tests reference scripts that are no longer in the repo
- `phase6_orchestrator/test_language_fix.py` compares command lines against `phase4_tts/test_simple_text.py` and prints instructions derived from that file (`phase6_orchestrator/test_language_fix.py:37-67`), but there is no `test_simple_text.py` anywhere under `phase4_tts/` (ripgrep of `phase4_tts` returns zero matches). The same missing script is referenced in `phase6_orchestrator/trace_execution.py:32-41`, so these diagnostics/tests cannot actually be run.

## 5. `pipeline.json` schema mismatches between phases
- Phase 5.5 subtitle generation expects Phase 5 to have written `phase5["output_file"]` and Phase 2 to expose a top-level `phase2["output_file"]` for reference text (`phase6_orchestrator/orchestrator.py:815-848`). In reality Phase 5 only stores status/metrics/artifacts and chunk metadata (no output-file path) (`phase5_enhancement/src/phase5_enhancement/main.py:748-774`), and Phase 2 nests its data under `phase2["files"][file_id]` (the extracted text path lives in that record, not at the phase root) (`phase2-extraction/src/phase2_extraction/extraction.py:335-348`). As a result, Phase 5.5 silently misses both the enhanced audiobook path and the source text unless the user manually places files in the fallback locations.
