Folder PATH listing
Volume serial number is B8DC-BD4D
C:.
│   pipeline.json
│   validation.db  # Legacy; migrate to pipeline.json
│
├───phase1_validation
│   │   config.yaml
│   │   pipeline.json  # Phase copy or symlink to root
│   │   poetry.lock
│   │   pyproject.toml
│   │   README.md
│   │   setup_phase1.ps1
│   │   setup_phase1.sh
│   │   validation.db  # Phase-specific
│   │
│   ├───.pytest_cache
│   │   │   .gitignore
│   │   │   CACHEDIR.TAG
│   │   │   README.md
│   │   │
│   │   └───v
│   │       └───cache
│   │               lastfailed
│   │               nodeids
│   │               stepwise
│   │
│   ├───src
│   │   └───phase1_validation
│   │       │   validation.py
│   │       │   __init__.py
│   │       │
│   │       └───__pycache__
│   │               validation.cpython-313.pyc
│   │               __init__.cpython-313.pyc
│   │
│   └───tests
│       │   test_validation.py
│       │   __init__.py
│       │
│       └───__pycache__
│               test_validation.cpython-313-pytest-8.3.3.pyc
│               __init__.cpython-313.pyc
│
├───phase2_extraction
│   │   config.yaml
│   │   pipeline.json
│   │   poetry.lock
│   │   pyproject.toml
│   │   README.md
│   │   The_Analects_of_Confucius_20240228.pdf
│   │
│   ├───backup
│   │   │   big.model
│   │   │   custom_instructions.md
│   │   │   phases_steps.md
│   │   │   README.md
│   │   │
│   │   ├───extracted_text
│   │   │       The Analects of Confucius_20240228.txt
│   │   │       The Analects of Confucius_20240228_converted_with_easyocr.txt
│   │   │       The Analects of Confucius_20240228_converted_with_pdfplumber.txt
│   │   │       The Analects of Confucius_20240228_converted_with_tesseract.txt
│   │   │
│   │   ├───src
│   │   └───tests
│   │           test_extraction.py
│   │           __init__.py
│   │
│   ├───extracted_text
│   │       The_Analects_of_Confucius_20240228.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_easyocr.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_tesseract.txt
│   │
│   ├───src
│   │   └───phase2_extraction
│   │           extraction.py
│   │           extractionbu.py
│   │           __init__.py
│   │
│   └───tests
│           test_extraction.py
│
├───phase3_chunking
│   │   .coverage
│   │   config.yaml
│   │   pipeline.json
│   │   poetry.lock
│   │   pyproject.toml
│   │   setup_phase3.ps1
│   │
│   ├───.pytest_cache
│   │   │   .gitignore
│   │   │   CACHEDIR.TAG
│   │   │   README.md
│   │   │
│   │   └───v
│   │       └───cache
│   │               lastfailed
│   │               nodeids
│   │
│   ├───chunks
│   │       The_Analects_of_Confucius_20240228_chunk_1.txt
│   │       The_Analects_of_Confucius_20240228_chunk_2.txt
│   │       # ... up to _22.txt (full listing for completeness)
│   │       The_Analects_of_Confucius_20240228_chunk_3.txt
│   │       The_Analects_of_Confucius_20240228_chunk_4.txt
│   │       The_Analects_of_Confucius_20240228_chunk_5.txt
│   │       The_Analects_of_Confucius_20240228_chunk_6.txt
│   │       The_Analects_of_Confucius_20240228_chunk_7.txt
│   │       The_Analects_of_Confucius_20240228_chunk_8.txt
│   │       The_Analects_of_Confucius_20240228_chunk_9.txt
│   │       The_Analects_of_Confucius_20240228_chunk_10.txt
│   │       The_Analects_of_Confucius_20240228_chunk_11.txt
│   │       The_Analects_of_Confucius_20240228_chunk_12.txt
│   │       The_Analects_of_Confucius_20240228_chunk_13.txt
│   │       The_Analects_of_Confucius_20240228_chunk_14.txt
│   │       The_Analects_of_Confucius_20240228_chunk_15.txt
│   │       The_Analects_of_Confucius_20240228_chunk_16.txt
│   │       The_Analects_of_Confucius_20240228_chunk_17.txt
│   │       The_Analects_of_Confucius_20240228_chunk_18.txt
│   │       The_Analects_of_Confucius_20240228_chunk_19.txt
│   │       The_Analects_of_Confucius_20240228_chunk_20.txt
│   │       The_Analects_of_Confucius_20240228_chunk_21.txt
│   │       The_Analects_of_Confucius_20240228_chunk_22.txt
│   │
│   ├───src
│   │   └───phase3_chunking
│   │       │   chunking.py
│   │       │   __init__.py
│   │       │
│   │       └───__pycache__
│   │               chunking.cpython-312.pyc
│   │               __init__.cpython-312.pyc
│   │
│   └───tests
│           test_chunking.py
│
├───phase4_tts
│   │   .coverage
│   │   config.yaml
│   │   poetry.lock
│   │   pyproject.toml
│   │   README.md
│   │   tts_progress.py
│   │   validation.db  # Legacy
│   │
│   ├───.pytest_cache
│   │   │   .gitignore
│   │   │   CACHEDIR.TAG
│   │   │   README.md
│   │   │
│   │   └───v
│   │       └───cache
│   │               nodeids
│   │
│   ├───audio_chunks
│   │       chunk_1.wav
│   │       # ... additional chunks as generated
│   │
│   ├───chatterbox_tts.egg-info
│   │       dependency_links.txt
│   │       PKG-INFO
│   │       requires.txt
│   │       SOURCES.txt
│   │       top_level.txt
│   │
│   ├───src
│   │   └───phase4_tts
│   │       │   main.py
│   │       │   models.py
│   │       │   utils.py
│   │       │
│   │       └───__pycache__
│   │               models.cpython-311.pyc
│   │               utils.cpython-311.pyc
│   │
│   ├───tests
│   │       test_main.py
│   │
│   └───__pycache__
│           models.cpython-311.pyc
│
├───phase5_enhancement
│   │   audio_enhancement.log
│   │   config.yaml
│   │   poetry.lock
│   │   pyproject.toml
│   │   README.md
│   │   tree.md
│   │   tts_progress.py
│   │   validation.db  # Legacy
│   │
│   ├───processed
│   │       audiobook.m3u
│   │       audiobook.mp3
│   │       enhanced_0001.wav
│   │       # ... additional enhanced chunks
│   │
│   ├───src
│   │   └───phase5_enhancement
│   │       │   config.yaml
│   │       │   main.py
│   │       │   models.py
│   │       │   __init__.py
│   │       │
│   │       ├───processed  # Empty or symlinked
│   │       ├───temp  # Runtime-generated
│   │       └───__pycache__
│   │               models.cpython-312.pyc
│   │
│   ├───temp  # Empty; cleaned post-run
│   └───tests
│           test_main.py
│           __init__.py
│
└───phase6_batch
    │   .coverage
    │   batch.log
    │   config.yaml
    │   poetry.lock
    │   pyproject.toml
    │   README.md
    │   tree.md
    │
    ├───.pytest_cache
    │   │   .gitignore
    │   │   CACHEDIR.TAG
    │   │   README.md
    │   │
    │   └───v
    │       └───cache
    │               nodeids
    │
    ├───inputs  # Empty or with test PDFs
    ├───src
    │   └───phase6_batch
    │       │   main.py
    │       │   models.py
    │       │
    │       └───__pycache__
    │               models.cpython-312.pyc
    │
    └───tests
            test_main.py  # Renamed from tests_main.py for standard pytest discovery

# Tree generated on 2025-09-26; Scan duration: 0.45s
# Metrics: Phases complete: 6/7; Artifacts count: 150+; Coverage target: >85% (pytest)