Phase 1 Prompt: Validation and Repair

"As Grok, implement Phase 1: Validation and Repair in the audiobook pipeline monorepo. Create a sub-project 'phase1\_validation' with pyproject.toml using Poetry. Dependencies: pikepdf==9.11.0, ebooklib==0.19, python-docx==1.2.0, ftfy==6.3.1, chardet==5.2.0, PyMuPDF==1.26.4, hachoir==3.3.0, pydantic.

Sub-phases:

1.1: Verify file path, readability, size <500MB using pathlib, os. Log errors, skip invalid. Metric: Time elapsed.

1.2: Compute SHA256 with hashlib; query SQLite for duplicates. Output hash entry. Error: IntegrityError warning.

1.3: Detect corruption, repair with format tools (e.g., pikepdf 9.11.0 for PDFs). Retries: 2. Output: Repaired or skip. Metric: 70-90% success.

1.4: Classify PDFs with PyMuPDF 1.26.4 (>5% text). Output: Classification.

1.5: Extract title/author with hachoir. Validate Pydantic. Output: FileMetadata.

1.6: Insert to SQLite; log duration/repaired. Deliverable: validation.db. Tests: Mocks for file access, >85% coverage.

Generate PEP 8 code, argparse CLI, error handling, benchmarks. Output Markdown with code blocks."



Phase 2 Prompt: Text Extraction

"As Grok, implement Phase 2: Text Extraction. Sub-project 'phase2\_extraction'. Dependencies: pdfplumber==0.11.4, PyMuPDF==1.26.4, unstructured==0.18.15, easyocr==1.7.2, nostril==1.2.2, nltk==3.9.1, langdetect==1.1.1.

Sub-phases:

2.1: Query DB for type with sqlite3; route paths. Input: File path, DB.

2.2: Extract text PDFs with pdfplumber 0.11.4 or PyMuPDF. Output: Raw text. Metric: >98% yield.

2.3: OCR scanned/mixed: Primary up to date unstructured (CPU hybrid); fallback EasyOCR 1.7.2. Output: TXT files. Error: Retry empty.

2.4: Evaluate gibberish (nostril 1.2.2 <0.5), perplexity (NLTK 3.9.1 >0.92), language (langdetect 1.1.1 >0.9). Select best. Metrics: Logged scores.

2.5: Verify English; compute yield (len(text)/file\_size\*100). Output: Best TXT in /extracted\_text/.

2.6: Time extraction; log performance. Deliverable: TXT with diagnostics. Tests: OCR mocks.

Code: PEP 8, CLI, handling, benchmarks."



Phase 3 Prompt: Chunking

"As Grok, implement Phase 3: Chunking. Sub-project 'phase3\_chunking'. Dependencies: spacy==3.8.7 (en\_core\_web\_lg), sentence-transformers==5.1.1, gensim==4.3.3, textstat==0.7.4, nltk==3.9.1.

Sub-phases:

3.1: Clean text with regex/ftfy 6.3.1. Input: Extracted TXT.

3.2: Detect boundaries with spaCy 3.8.7. Output: Sentences.

3.3: Semantic chunks (250-400 words) via sentence-transformers 5.1.1/Gensim 4.3.3 (>0.87 cosine). Fallback: NLTK 3.9.1. Metric: Coherence.

3.4: Assess readability with textstat 0.7.4 (>60 Flesch). Adjust if low.

3.5: Save to /chunks/; validate count. Error: Retry low coherence.

3.6: Log time per chunk. Deliverable: Chunked files. Tests: Model mocks.

Code: PEP 8, CLI, handling, benchmarks."



Phase 4 Prompt: Text-to-Speech Synthesis

"As Grok, implement Phase 4: TTS Synthesis with Zero-Shot Voice Cloning. Sub-project 'phase4\_tts'. Dependencies: chatterbox-tts (pip install from git+https://github.com/resemble-ai/chatterbox.git for 2025 multilingual updates), piper-tts==1.3.0, bark (stable GitHub), librosa==0.11.0, requests==2.32.3, torchaudio (latest).

Sub-phases:

4.0: Validate Chatterbox install (ChatterboxMultilingualTTS.from\_pretrained(device='cpu')). Download reference MP3 from 'https://www.archive.org/download/roughing\_it\_jg/rough\_09\_twain.mp3' using requests; trim to 7-20s clip with Librosa (e.g., first clear speech segment), normalize, resample to 22kHz mono, save as 'greenman\_ref.wav'. Use as default audio\_prompt\_path for cloning John Greenman's voice.

4.1: Load chunks from /chunks/ via DB query.

4.2: Synthesize each chunk non-batched with Chatterbox (multilingual CPU: generate(text, audio\_prompt\_path='greenman\_ref.wav', language\_id='en', exaggeration=0.5, cfg\_weight=0.5)). Output: WAV per chunk.

4.3: Fallback (2 retries):  Metric: MOS >4.5 (Librosa spectral analysis for artifacts/SNR).

4.4: Verify quality with Librosa (e.g., detect noise/artifacts); log scores to DB.

4.5: Track progress in SQLite; resume interrupts with checkpoints.

4.6: Benchmark time per chunk; log engine and metrics. Deliverable: Cloned audio chunks in /audio\_chunks/. Tests: Mocks for downloads, inference (>85% coverage).

Code: PEP 8, CLI with argparse (e.g., --ref\_url), error handling (try-except for downloads/model fails, Pydantic configs), benchmarks with time.perf\_counter()."



Phase 5 Prompt: Audio Enhancement

"As Grok, implement Phase 5: Audio Enhancement. Sub-project 'phase5\_enhancement'. Dependencies: noisereduce==3.0.3, pyloudnorm==0.1.1, pydub==0.25.1, mutagen==1.47.0, librosa==0.11.0.

Sub-phases:

5.1: Reduce noise with noisereduce 3.0.3. Input: Audio chunks.

5.2: Normalize to -23 dB LUFS with pyloudnorm.

5.3: Crossfades (0.5s) and concatenate with pydub 0.25.1; create M3U.

5.4: Embed metadata with mutagen 1.47.0 (title/author).

5.5: Validate quality with librosa. Error: Reprocess failure.

5.6: Save to /processed/; benchmark duration. Deliverable: Enhanced audiobook. Tests: Audio mocks.

Code: PEP 8, CLI, handling, benchmarks."



Phase 6 Prompt: Batch Processing

"As Grok, implement Phase 6: Batch Processing. Sub-project 'phase6\_batch'. Dependencies: joblib==1.5.2, trio==0.30.0, tqdm==4.67.1, psutil==7.1.0.

Sub-phases:

6.1: Setup batch; parallelism <80% CPU via psutil 7.1.0. Tools: joblib 1.5.2.

6.2: Execute phases async with Trio 0.30.0. Progress: tqdm 4.67.1.

6.3: Monitor/throttle >80% CPU.

6.4: Resume via SQLite checkpoints. Error: Handle partials.

6.5: Multi-file batches; log skips.

6.6: Benchmark time, CPU. Deliverable: Batch logs. Tests: Parallel mocks.

Code: PEP 8, CLI, handling, benchmarks."



Phase 7 Prompt: Orchestration

"As Grok, implement Phase 7: Orchestration. Top-level script 'orchestration.py'. Dependencies: rich==14.1.0.

Sub-phases:

7.1: CLI with argparse; reports via rich 14.1.0. Input: YAML configs (include ref\_url for Phase 4 cloning).

7.2: Sequence phases via subprocess to sub-projects.

7.3: Aggregate errors; retry failed.

7.4: Generate tables/metrics with rich.

7.5: Cleanup temps after 7 days.

7.6: End-to-end validation. Deliverable: Full run. Tests: End-to-end mocks.

Code: PEP 8, CLI, handling, benchmarks."

