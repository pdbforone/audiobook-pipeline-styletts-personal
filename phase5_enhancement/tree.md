Folder PATH listing
Volume serial number is B8DC-BD4D
C:.
│   main.py
│   models.py
│   __init__.py
│
├───processed
├───temp
└───__pycache__
        models.cpython-312.pyc

(phase5-enhancement-py3.12) PS C:\Users\myson\Pipeline\audiobook-pipeline\phase5_enhancement\src\phase5_enhancement> cd..
(phase5-enhancement-py3.12) PS C:\Users\myson\Pipeline\audiobook-pipeline\phase5_enhancement\src> tree /F
Folder PATH listing
Volume serial number is B8DC-BD4D
C:.
│   config.yaml
│
├───phase4_tts
│   └───audio_chunks
└───phase5_enhancement
    │   main.py
    │   models.py
    │   __init__.py
    │
    ├───processed
    ├───temp
    └───__pycache__
            models.cpython-312.pyc

(phase5-enhancement-py3.12) PS C:\Users\myson\Pipeline\audiobook-pipeline\phase5_enhancement\src> cd..
(phase5-enhancement-py3.12) PS C:\Users\myson\Pipeline\audiobook-pipeline\phase5_enhancement> tree /F
Folder PATH listing
Volume serial number is B8DC-BD4D
C:.
│   audio_enhancement.log
│   config.yaml
│   poetry.lock
│   pyproject.toml
│   README.md
│   tts_progress.py
│   validation.db
│
├───processed
│       audiobook.mp3
│       enhanced_0001.wav
│
├───src
│   │   config.yaml
│   │
│   ├───phase4_tts
│   │   └───audio_chunks
│   └───phase5_enhancement
│       │   main.py
│       │   models.py
│       │   __init__.py
│       │
│       ├───processed
│       ├───temp
│       └───__pycache__
│               models.cpython-312.pyc
│
├───temp
└───tests
        test_main.py
        __init__.py

(phase5-enhancement-py3.12) PS C:\Users\myson\Pipeline\audiobook-pipeline\phase5_enhancement> cd..
(phase5-enhancement-py3.12) PS C:\Users\myson\Pipeline\audiobook-pipeline> tree /F
Folder PATH listing
Volume serial number is B8DC-BD4D
C:.
│   validation.db
│
├───phase1-validation
│   │   config.yaml
│   │   poetry.lock
│   │   pyproject.toml
│   │   README.md
│   │   setup_phase1.ps1
│   │   setup_phase1.sh
│   │   validation.db
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
├───phase2-extraction
│   │   config.yaml
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
│   │           __init__.py
│   │
│   └───tests
│           test_extraction.py
│
├───phase3-chunking
│   │   .coverage
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
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_1.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_10.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_11.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_12.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_13.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_14.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_15.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_16.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_17.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_18.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_19.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_2.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_20.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_21.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_22.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_23.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_24.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_25.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_26.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_27.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_28.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_29.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_3.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_30.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_31.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_32.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_33.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_34.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_35.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_36.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_37.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_38.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_39.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_4.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_40.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_41.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_42.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_43.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_44.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_45.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_46.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_47.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_48.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_49.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_5.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_50.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_51.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_52.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_53.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_54.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_55.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_56.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_57.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_58.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_59.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_6.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_60.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_61.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_62.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_63.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_64.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_65.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_66.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_67.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_68.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_69.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_7.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_70.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_71.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_72.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_73.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_74.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_8.txt
│   │       The_Analects_of_Confucius_20240228_converted_with_pdfplumber_chunk_9.txt
│   │
│   ├───src
│   │   └───phase3_chunking
│   │       │   init.py
│   │       │   main.py
│   │       │   models.py
│   │       │   utils.py
│   │       │
│   │       └───__pycache__
│   │               main.cpython-312.pyc
│   │               models.cpython-312.pyc
│   │               utils.cpython-312.pyc
│   │
│   └───tests
│       │   test_chunking.py
│       │
│       └───__pycache__
│               test_chunking.cpython-312-pytest-8.4.2.pyc
│
├───phase4_tts
│   │   config.yaml
│   │   environment.yml
│   │   greenman_ref.wav
│   │   main.py
│   │   models.py
│   │   README.md
│   │   setup_phase4.ps1
│   │   temp.mp3
│   │   validation.db
│   │   validation1.db
│   │   __init__.py
│   │
│   ├───audio_chunks
│   │       backup_chunk_1.wav
│   │       chunk_1.wav
│   │
│   ├───chatterbox
│   │   │   .gitignore
│   │   │   Chatterbox-Multilingual.png
│   │   │   example_for_mac.py
│   │   │   example_tts.py
│   │   │   example_vc.py
│   │   │   gradio_tts_app.py
│   │   │   gradio_vc_app.py
│   │   │   LICENSE
│   │   │   multilingual_app.py
│   │   │   pyproject.toml
│   │   │   README.md
│   │   │
│   │   └───src
│   │       ├───chatterbox
│   │       │   │   mtl_tts.py
│   │       │   │   tts.py
│   │       │   │   vc.py
│   │       │   │   __init__.py
│   │       │   │
│   │       │   ├───models
│   │       │   │   │   utils.py
│   │       │   │   │   __init__.py
│   │       │   │   │
│   │       │   │   ├───s3gen
│   │       │   │   │   │   configs.py
│   │       │   │   │   │   const.py
│   │       │   │   │   │   decoder.py
│   │       │   │   │   │   f0_predictor.py
│   │       │   │   │   │   flow.py
│   │       │   │   │   │   flow_matching.py
│   │       │   │   │   │   hifigan.py
│   │       │   │   │   │   s3gen.py
│   │       │   │   │   │   xvector.py
│   │       │   │   │   │   __init__.py
│   │       │   │   │   │
│   │       │   │   │   ├───matcha
│   │       │   │   │   │   │   decoder.py
│   │       │   │   │   │   │   flow_matching.py
│   │       │   │   │   │   │   text_encoder.py
│   │       │   │   │   │   │   transformer.py
│   │       │   │   │   │   │
│   │       │   │   │   │   └───__pycache__
│   │       │   │   │   │           decoder.cpython-311.pyc
│   │       │   │   │   │           flow_matching.cpython-311.pyc
│   │       │   │   │   │           transformer.cpython-311.pyc
│   │       │   │   │   │
│   │       │   │   │   ├───transformer
│   │       │   │   │   │   │   activation.py
│   │       │   │   │   │   │   attention.py
│   │       │   │   │   │   │   convolution.py
│   │       │   │   │   │   │   embedding.py
│   │       │   │   │   │   │   encoder_layer.py
│   │       │   │   │   │   │   positionwise_feed_forward.py
│   │       │   │   │   │   │   subsampling.py
│   │       │   │   │   │   │   upsample_encoder.py
│   │       │   │   │   │   │   __init__.py
│   │       │   │   │   │   │
│   │       │   │   │   │   └───__pycache__
│   │       │   │   │   │           activation.cpython-311.pyc
│   │       │   │   │   │           attention.cpython-311.pyc
│   │       │   │   │   │           convolution.cpython-311.pyc
│   │       │   │   │   │           embedding.cpython-311.pyc
│   │       │   │   │   │           encoder_layer.cpython-311.pyc
│   │       │   │   │   │           positionwise_feed_forward.cpython-311.pyc  
│   │       │   │   │   │           subsampling.cpython-311.pyc
│   │       │   │   │   │           upsample_encoder.cpython-311.pyc
│   │       │   │   │   │           __init__.cpython-311.pyc
│   │       │   │   │   │
│   │       │   │   │   ├───utils
│   │       │   │   │   │   │   class_utils.py
│   │       │   │   │   │   │   mask.py
│   │       │   │   │   │   │   mel.py
│   │       │   │   │   │   │
│   │       │   │   │   │   └───__pycache__
│   │       │   │   │   │           class_utils.cpython-311.pyc
│   │       │   │   │   │           mask.cpython-311.pyc
│   │       │   │   │   │           mel.cpython-311.pyc
│   │       │   │   │   │
│   │       │   │   │   └───__pycache__
│   │       │   │   │           configs.cpython-311.pyc
│   │       │   │   │           const.cpython-311.pyc
│   │       │   │   │           decoder.cpython-311.pyc
│   │       │   │   │           f0_predictor.cpython-311.pyc
│   │       │   │   │           flow.cpython-311.pyc
│   │       │   │   │           flow_matching.cpython-311.pyc
│   │       │   │   │           hifigan.cpython-311.pyc
│   │       │   │   │           s3gen.cpython-311.pyc
│   │       │   │   │           xvector.cpython-311.pyc
│   │       │   │   │           __init__.cpython-311.pyc
│   │       │   │   │
│   │       │   │   ├───s3tokenizer
│   │       │   │   │   │   s3tokenizer.py
│   │       │   │   │   │   __init__.py
│   │       │   │   │   │
│   │       │   │   │   └───__pycache__
│   │       │   │   │           s3tokenizer.cpython-311.pyc
│   │       │   │   │           __init__.cpython-311.pyc
│   │       │   │   │
│   │       │   │   ├───t3
│   │       │   │   │   │   llama_configs.py
│   │       │   │   │   │   t3.py
│   │       │   │   │   │   __init__.py
│   │       │   │   │   │
│   │       │   │   │   ├───inference
│   │       │   │   │   │   │   alignment_stream_analyzer.py
│   │       │   │   │   │   │   t3_hf_backend.py
│   │       │   │   │   │   │
│   │       │   │   │   │   └───__pycache__
│   │       │   │   │   │           alignment_stream_analyzer.cpython-311.pyc  
│   │       │   │   │   │           t3_hf_backend.cpython-311.pyc
│   │       │   │   │   │
│   │       │   │   │   ├───modules
│   │       │   │   │   │   │   cond_enc.py
│   │       │   │   │   │   │   learned_pos_emb.py
│   │       │   │   │   │   │   perceiver.py
│   │       │   │   │   │   │   t3_config.py
│   │       │   │   │   │   │
│   │       │   │   │   │   └───__pycache__
│   │       │   │   │   │           cond_enc.cpython-311.pyc
│   │       │   │   │   │           learned_pos_emb.cpython-311.pyc
│   │       │   │   │   │           perceiver.cpython-311.pyc
│   │       │   │   │   │           t3_config.cpython-311.pyc
│   │       │   │   │   │
│   │       │   │   │   └───__pycache__
│   │       │   │   │           llama_configs.cpython-311.pyc
│   │       │   │   │           t3.cpython-311.pyc
│   │       │   │   │           __init__.cpython-311.pyc
│   │       │   │   │
│   │       │   │   ├───tokenizers
│   │       │   │   │   │   tokenizer.py
│   │       │   │   │   │   __init__.py
│   │       │   │   │   │
│   │       │   │   │   └───__pycache__
│   │       │   │   │           tokenizer.cpython-311.pyc
│   │       │   │   │           __init__.cpython-311.pyc
│   │       │   │   │
│   │       │   │   ├───voice_encoder
│   │       │   │   │   │   config.py
│   │       │   │   │   │   melspec.py
│   │       │   │   │   │   voice_encoder.py
│   │       │   │   │   │   __init__.py
│   │       │   │   │   │
│   │       │   │   │   └───__pycache__
│   │       │   │   │           config.cpython-311.pyc
│   │       │   │   │           melspec.cpython-311.pyc
│   │       │   │   │           voice_encoder.cpython-311.pyc
│   │       │   │   │           __init__.cpython-311.pyc
│   │       │   │   │
│   │       │   │   └───__pycache__
│   │       │   │           utils.cpython-311.pyc
│   │       │   │           __init__.cpython-311.pyc
│   │       │   │
│   │       │   └───__pycache__
│   │       │           mtl_tts.cpython-311.pyc
│   │       │           tts.cpython-311.pyc
│   │       │           vc.cpython-311.pyc
│   │       │           __init__.cpython-311.pyc
│   │       │
│   │       └───chatterbox_tts.egg-info
│   │               dependency_links.txt
│   │               PKG-INFO
│   │               requires.txt
│   │               SOURCES.txt
│   │               top_level.txt
│   │
│   ├───tests
│   │       test_main.py
│   │
│   └───__pycache__
│           models.cpython-311.pyc
│
└───phase5_enhancement
    │   audio_enhancement.log
    │   config.yaml
    │   poetry.lock
    │   pyproject.toml
    │   README.md
    │   tts_progress.py
    │   validation.db
    │
    ├───processed
    │       audiobook.mp3
    │       enhanced_0001.wav
    │
    ├───src
    │   │   config.yaml
    │   │
    │   ├───phase4_tts
    │   │   └───audio_chunks
    │   └───phase5_enhancement
    │       │   main.py
    │       │   models.py
    │       │   __init__.py
    │       │
    │       ├───processed
    │       ├───temp
    │       └───__pycache__
    │               models.cpython-312.pyc
    │
    ├───temp
    └───tests
            test_main.py
            __init__.py

