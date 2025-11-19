# Phase 2 – Extraction

Multi-pass text extraction with TTS-oriented normalization. Handles PDF/EPUB/DOCX/TXT using fallback strategies, reuses prior results via pipeline.json, and emits a ready-to-chunk TXT plus Phase 2 metadata.

## Core features
- Multi-pass PDF extraction (pypdf, pdfplumber, PyMuPDF) with quality scoring; picks the best result.
- Classification-aware path: uses Phase 1 `classification` (`text|mixed|scanned`) from `pipeline.json`.
- TTS normalization hook (`tts_normalizer`) to clean whitespace/formatting and validate TTS readiness (optional if module missing).
- Reuse check: skips extraction when Phase 2 already succeeded and source hash is unchanged (unless `--force`).
- Output merges into `pipeline.json` under `phase2.files[file_id]` (path, tool_used, yield_pct, quality_score, language, timestamps, status) and writes extracted text to `extracted_text/{file_id}.txt`.
- Cache: additionally stores extraction text/metadata keyed by source hash under `~/.cache/phase2_extract` to skip re-extraction on unchanged inputs (honors `--force` to bypass).

## CLI
```
python src/phase2_extraction/extraction.py \
  --file_id <id> \
  [--file <override path>] \
  [--json_path pipeline.json] \
  [--extracted_dir extracted_text] \
  [--no-multipass] \
  [--config config.yaml] \
  [--force]
```

### Config (optional YAML)
- `retry_limit` (default 1) – passed to config model; other toggles are via CLI flags.

## Dependencies and notes
- Heavy deps (PyMuPDF, pdfplumber, pypdf, nltk, langdetect, pydantic, yaml). Install Phase 2 extras before running.
- `tts_normalizer` is optional; if absent, normalization is skipped with a warning.
- PDF extraction can take seconds on large books; this step is single-threaded by design for thermal safety on Ryzen 5 5500U.

## Recent behavior details
- Reads Phase 1 info (path, classification) from `pipeline.json`; warns if Phase 1 wasn’t run.
- Hashes the source file to detect changes; records `source_hash` in Phase 2 metadata.
- Quality heuristics: replacement character count, alphabetic ratio, common-word presence; sets status to `success/partial_success/failed`.

## Outputs
- `extracted_text/{file_id}.txt` (UTF-8) – normalized text when extraction succeeds.
- `pipeline.json` updates under `phase2.files[file_id]` with tool, yield, quality, lang, duration, hash, status.
