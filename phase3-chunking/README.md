# Phase 3 – Structure & Chunking

Structure-aware chunking for TTS. Uses structure detection (Phase 2 output) plus sentence splitting (spaCy primary, pySBD fallback) to create TTS-sized chunks.

## Key entrypoints
- Chunking: `src/phase3_chunking/structure_chunking.py`
- Structure detector: `src/phase2_extraction/structure_detector.py` (upstream context)
- Docs: `STRUCTURE_ENHANCEMENT_README.md`, `PHASE3_CHUNKING_FIXES.md`, `PHASE3_4_ANALYSIS.md`

## Defaults (from Nov/Dec 2025 tuning)
- Target chunk duration: ~12–18 s (min_chunk_words=30, max_chunk_words=75; char soft/hard caps ~780/950; emergency 1250).
- Sentence splitter: spaCy → pySBD fallback for abbreviation/bullet-heavy text.
- Emdash/semicolon split for long sentences; fallback splits if RT risk.

## Outputs
- Chunk text files under `phase3-chunking/chunks/` with normalized IDs.
- Chunk metadata recorded into `pipeline.json` for downstream Phase 4.
