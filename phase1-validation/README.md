# Phase 1 – Validation & Repair

Early gate for audiobook inputs. Validates and, when possible, repairs PDFs/EPUB/DOCX/TXT before downstream extraction/chunking. Optimized for CPU-only on Ryzen 5 5500U; single-threaded and low memory, but PDF inspection can take seconds on large files.

## What it does
- Size and access checks (errors on empty files; caps size via `--max_size_mb`).
- Hash reuse check against `pipeline.json` to skip rework (unless `--force`).
- Metadata extraction (PyMuPDF + hachoir, ftfy cleanup).
- File repair: pikepdf (PDF), ebooklib (EPUB), python-docx (DOCX), chardet/ftfy rewrite (TXT).
- PDF classification (text / scanned / mixed) via extractable text heuristic.
- Optional fast mode: metadata only, minimal checks.

## Key flags
- `--file` (required): input path.
- `--max_size_mb` (default 500): fail fast on huge inputs.
- `--retries` (default 2): repair attempts.
- `--json_path` (default pipeline.json): merge metadata + hashes.
- `--artifacts_dir` (default artifacts/phase1): store repaired copies.
- `--force`: ignore prior hash match; revalidate.
- `--mode [thorough|fast]`: fast skips repairs/classification.

## Recent reliability fixes
- Empty-file guard; explicit UTF-8+replace when reading `.txt`.
- Removed duplicate PDF classification pass (less I/O).
- Deduplicates stored hashes in `pipeline.json` to avoid unbounded growth.

## Outputs
- Updates `pipeline.json` under `phase1.files[file_id]` with metadata, hash, classification, repair status, and elapsed time.
- Stores repaired artifact when applicable.

## Notes and cautions
- Heavy dependencies (PyMuPDF, pikepdf, hachoir, ebooklib) stay in Phase 1 only; they are not needed later.
- Large PDFs still require full traversal for classification; expect seconds, not ms, on long books.
- If `psutil`/temp guards are desired, integrate at the orchestrator level (Phase 6/7), not here.
