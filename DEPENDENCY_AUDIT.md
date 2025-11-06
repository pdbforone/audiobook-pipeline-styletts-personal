# Dependency Audit

Legend:  
✅ = used/imported in code, ⚠️ = unused or questionable, ❌ = GPU-only / incompatible, 🧩 = version concern.

## phase_audio_cleanup/pyproject.toml
| Dependency | Status | Notes |
| --- | --- | --- |
| python (^3.10) | ✅ | Runtime baseline. |
| faster-whisper ^1.0.0 | ✅ | `src/audio_cleanup` uses Whisper for phrase detection; CPU builds exist, so no GPU-only constraint violation. Ensure `--device cpu` is configured to avoid CUDA expectations. |
| pydub ^0.25.1 | ✅ | Used for audio slicing/export. |
| pyyaml ^6.0 | ✅ | Config loader in cleanup scripts. |
| python-dateutil ^2.8.2 | ⚠️ | No direct imports spotted in `phase_audio_cleanup/src`; verify if timestamps or scheduling actually use it. |
| requests ^2.32.5 | ⚠️ | CLI references remote voice sample downloads? If unused, drop it. |
| Dev: pytest/pytest-cov | ✅ | Tests import them. |
| GPU-only? | None flagged. |
| Version issues | None; Python 3.10 aligns with dependencies. |

## phase1-validation/pyproject.toml (PEP 621)
| Dependency | Status | Notes |
| --- | --- | --- |
| pikepdf 9.11.0 | ✅ | Repair pipeline uses PikePDF. |
| pymupdf 1.26.4 | ✅ | Metadata extraction/classification. |
| ebooklib 0.19 | ✅ | EPUB support. |
| python-docx 1.2.0 | ✅ | DOCX validation. |
| ftfy 6.3.1 | ✅ | Metadata normalization. |
| chardet 5.2.0 | ✅ | Charset detection for TXT fallback. |
| pydantic 2.11.9 | ✅ | `FileMetadata` dataclass. |
| hachoir 3.3.0 | ✅ | Metadata extraction fallback. |
| charset-normalizer >=3.4.3 | ⚠️ | Not imported directly (chardet already handles detection). Consider removing unless future plans require it. |
| Dev: pytest | ✅ | Tests exist. |
| GPU-only? | None. |
| Version issues | Python >=3.12; `pymupdf` 1.26.x supports 3.12, so OK. |

## phase2-extraction/pyproject.toml
| Dependency | Status | Notes |
| --- | --- | --- |
| pdfplumber / pdfminer.six / pymupdf / pypdf / pdf2image | ✅ | Different extractor backends. |
| unstructured 0.18.15 | ⚠️ | No explicit import in `src/phase2_extraction`; confirm if `consensus_extractor` uses it; otherwise remove. |
| easyocr 1.7.2 | ⚠️ | OCR path unreferenced (no `import easyocr`), plus this pulls GPU deps; violates “no GPU-only” constraint unless CPU mode proven. |
| nostril | ✅ | `tts_normalizer` uses it. |
| nltk | ✅ | Sentence detection. |
| langdetect | ✅ | Language scoring. |
| numpy 2.3.3 | ✅ | Vectorized normalization. |
| pydantic | ✅ | Config models. |
| pyyaml | ✅ | Config load. |
| charset-normalizer | ⚠️ | Not imported; redundant with `chardet`? consider removal. |
| num2words/unidecode/clean-text | ✅ | Normalizer uses them. |
| python-docx / ebooklib / beautifulsoup4 / lxml / readability-lxml / python-magic / python-magic-bin | ✅ | Format inference + HTML parsing. |
| python-magic vs python-magic-bin | ⚠️ | Both declared; on Windows, only `python-magic-bin` needed. Duplicated functionality. |
| GPU-only? | easyocr likely expects CUDA; either ensure CPU wheels or replace. |
| Version issues | `numpy 2.3.3` + Python 3.11 OK. |

## phase3-chunking/pyproject.toml
| Dependency | Status | Notes |
| --- | --- | --- |
| spacy 3.8.4 | ✅ | Sentence parsing / embeddings. |
| sentence-transformers 5.1.0 | ✅ | `voice_selection` uses it. Note: default models pull torch; CPU builds exist but watch GPU defaults. |
| gensim | ⚠️ | No import found in `phase3_chunking`; if unused, remove. |
| textstat/nltk/ftfy | ✅ | Readability scoring, cleanup. |
| pyyaml | ✅ | Config loader. |
| filelock | ✅ | `merge_to_json` locking. |
| langdetect | ✅ | CLI fallback detection. |
| charset-normalizer | ⚠️ | Not imported anywhere; redundant. |
| Dev deps (pytest, pytest-cov) | ✅ | Tests use them. |
| GPU-only? | sentence-transformers depends on torch; default installs CPU wheels but ensure no CUDA-only packages. |
| Version issues | spacy 3.8.4 supports Python 3.12; confirm model downloads specify CPU. |

## phase5_enhancement/pyproject.toml
| Dependency | Status | Notes |
| --- | --- | --- |
| noisereduce, pyloudnorm, pydub, mutagen, librosa, soundfile, psutil | ✅ | All used in `main.py`. |
| pydantic | ✅ | Config models. |
| pyyaml | ✅ | Config. |
| charset-normalizer | ⚠️ | Not referenced; remove if unused. |
| faster-whisper | ✅ | Subtitle generation uses `WhisperModel`. CPU builds OK; GPU optional. |
| python-dateutil | ⚠️ | Not imported in `src/phase5_enhancement`; check subtitle timestamp code; remove if unused. |
| requests | ⚠️ | Not imported; probably vestigial from download scripts. |
| webvtt-py / jiwer / srt | ✅ | Subtitle validator uses them. |
| Dev deps | ✅ | Tests import pytest + mock. |
| Version issues | `librosa 0.11.0` requires numpy <=1.23; ensure environment pins numpy accordingly (currently inherited from system). |

## phase6_orchestrator/pyproject.toml
| Dependency | Status | Notes |
| --- | --- | --- |
| pydantic | ✅ | Config validations. |
| rich | ✅ | UI output. |
| pyyaml | ✅ | Config. |
| charset-normalizer | ⚠️ | Not imported anywhere; remove. |
| python-docx / ebooklib / beautifulsoup4 / lxml / readability-lxml / pdf2image / pypdf / python-magic-bin | ⚠️ | Orchestrator no longer manipulates documents directly; these belong to Phase 1/2. No `import` statements in `orchestrator.py`; drop to slim dependencies. |
| GPU-only? | None. |
| Version issues | `lxml 6.0.2` requires Python >=3.11 which matches, but again unused. |

## phase7_batch/pyproject.toml
| Dependency | Status | Notes |
| --- | --- | --- |
| trio, tqdm, psutil, pyyaml, pydantic, rich | ✅ | Used in `src/phase7_batch`. |
| Dev deps (pytest*, pytest-cov) | ✅ | Tests import them. |
| GPU-only? | None. |
| Version issues | Python ~3.12 requirement matches dependencies. |

## Cross-cutting observations
- **Repeated charset-normalizer**: nearly every project lists it but only Phase 1 actually imports `chardet`. Remove redundant entries to avoid unnecessary installs.
- **easyocr GPU risk**: For Phase 2, consider swapping to CPU-friendly OCR (e.g., pytesseract) or document CPU configuration to satisfy constraints.
- **Duplicate doc-processing deps in orchestrator**: `python-docx`, `ebooklib`, `pdf2image`, etc., are unused in Phase 6 since validation happens in Phase 1. Removing them cuts install size and avoids conflicting versions.
- **Optional dependencies not documented**: Projects that rely on `faster-whisper`/`sentence-transformers` should document CPU installation steps to prevent CUDA auto-downloads.
- **Version compatibility**: `librosa 0.11` requires numpy <=1.23, but Phase 5 doesn’t pin numpy—ensure environment inherits compatible version from global install or add explicit dependency.

## Action items
1. For each unused dependency above (charset-normalizer in phases 2/3/5/6, python-dateutil/requests in Phase 5, requests/python-dateutil in Phase audio cleanup, etc.) confirm actual usage and prune `pyproject.toml`.
2. Replace or document GPU-sensitive packages (`easyocr`, `sentence-transformers` default torch builds) with CPU-safe alternatives or explicit CPU instructions to honor “no GPU-only deps”.
3. Align `librosa` with a pinned numpy requirement to avoid runtime errors on fresh installs.
4. Update `phase6_orchestrator` dependencies to include only what the orchestrator truly imports; remaining format-specific libraries belong to earlier phases.***
