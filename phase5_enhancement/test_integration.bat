@echo off
echo ============================================================
echo Phase 5 Integration Test: With vs Without Cleanup
echo ============================================================
echo.
echo This script will process the SAME chunk twice:
echo   1. With phrase cleanup enabled
echo   2. Without phrase cleanup (disabled)
echo.
echo You can then compare the outputs to verify cleanup works!
echo.

set TEST_CHUNK=0
set OUTPUT_DIR=C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement\processed

echo Using test chunk: %TEST_CHUNK%
echo.

REM Clean up previous test outputs
if exist "%OUTPUT_DIR%\test_with_cleanup" rmdir /S /Q "%OUTPUT_DIR%\test_with_cleanup"
if exist "%OUTPUT_DIR%\test_without_cleanup" rmdir /S /Q "%OUTPUT_DIR%\test_without_cleanup"

mkdir "%OUTPUT_DIR%\test_with_cleanup"
mkdir "%OUTPUT_DIR%\test_without_cleanup"

echo ============================================================
echo Test 1: WITH Phrase Cleanup
echo ============================================================
echo.

cd C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase5_enhancement

REM Create temp config with cleanup enabled
(
echo audiobook_author: Marcus Aurelius
echo audiobook_title: The Meditations
echo backup_original: false
echo chunk_size_seconds: 30
echo cleanup_temp_files: true
echo crossfade_duration: 0.2
echo enable_volume_normalization: true
echo input_dir: ../phase4_tts/audio_chunks
echo log_file: audio_enhancement_test_with.log
echo log_level: INFO
echo lufs_target: -18.0
echo max_workers: 1
echo memory_limit_mb: 1024
echo mp3_bitrate: 192k
echo noise_reduction_factor: 0.02
echo output_dir: processed\test_with_cleanup
echo pipeline_json: C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\pipeline_magi.json
echo processing_timeout: 60
echo quality_validation_enabled: false
echo resume_on_failure: false
echo retries: 0
echo sample_rate: 24000
echo snr_threshold: 0.0
echo temp_dir: temp
echo volume_norm_headroom: 0.3
echo enable_phrase_cleanup: true
echo cleanup_target_phrases:
echo   - "You need to add some text for me to talk"
echo   - "You need to add some text for me to talk."
echo   - "You need to add text for me to talk"
echo   - "You need to add text for me to talk."
echo cleanup_whisper_model: "base"
echo cleanup_save_transcripts: true
) > src\phase5_enhancement\config_test_with.yaml

call poetry run python -m phase5_enhancement.main --config config_test_with.yaml --chunk_id %TEST_CHUNK% --skip_concatenation

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Test with cleanup failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Test 2: WITHOUT Phrase Cleanup
echo ============================================================
echo.

REM Create temp config with cleanup disabled
(
echo audiobook_author: Marcus Aurelius
echo audiobook_title: The Meditations
echo backup_original: false
echo chunk_size_seconds: 30
echo cleanup_temp_files: true
echo crossfade_duration: 0.2
echo enable_volume_normalization: true
echo input_dir: ../phase4_tts/audio_chunks
echo log_file: audio_enhancement_test_without.log
echo log_level: INFO
echo lufs_target: -18.0
echo max_workers: 1
echo memory_limit_mb: 1024
echo mp3_bitrate: 192k
echo noise_reduction_factor: 0.02
echo output_dir: processed\test_without_cleanup
echo pipeline_json: C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\pipeline_magi.json
echo processing_timeout: 60
echo quality_validation_enabled: false
echo resume_on_failure: false
echo retries: 0
echo sample_rate: 24000
echo snr_threshold: 0.0
echo temp_dir: temp
echo volume_norm_headroom: 0.3
echo enable_phrase_cleanup: false
) > src\phase5_enhancement\config_test_without.yaml

call poetry run python -m phase5_enhancement.main --config config_test_without.yaml --chunk_id %TEST_CHUNK% --skip_concatenation

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Test without cleanup failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Comparison Results
echo ============================================================
echo.

REM Get file sizes
for %%F in ("%OUTPUT_DIR%\test_with_cleanup\enhanced_0000.wav") do set SIZE_WITH=%%~zF
for %%F in ("%OUTPUT_DIR%\test_without_cleanup\enhanced_0000.wav") do set SIZE_WITHOUT=%%~zF

echo Files created:
echo   WITH cleanup:    %OUTPUT_DIR%\test_with_cleanup\enhanced_0000.wav
echo                    Size: %SIZE_WITH% bytes
echo.
echo   WITHOUT cleanup: %OUTPUT_DIR%\test_without_cleanup\enhanced_0000.wav
echo                    Size: %SIZE_WITHOUT% bytes
echo.

REM Check if transcript was created
if exist "%OUTPUT_DIR%\test_with_cleanup\chunk_%TEST_CHUNK%_transcript.srt" (
    echo ✓ Transcript created: test_with_cleanup\chunk_%TEST_CHUNK%_transcript.srt
) else (
    echo ⚠️  No transcript found - check if chunk has the target phrase
)

echo.
echo ============================================================
echo What to Check:
echo ============================================================
echo.
echo 1. File sizes should be DIFFERENT:
echo    - WITH cleanup should be SMALLER (phrase removed)
echo    - WITHOUT cleanup should be LARGER (phrase still present)
echo.
echo 2. Listen to both files and compare:
echo    - WITH cleanup: Should NOT have the unwanted phrase
echo    - WITHOUT cleanup: Should STILL have the unwanted phrase
echo.
echo 3. Check the transcript (if created):
echo    - Open: test_with_cleanup\chunk_%TEST_CHUNK%_transcript.srt
echo    - Search for the target phrase to confirm detection
echo.
echo 4. Compare logs:
echo    - WITH cleanup:    audio_enhancement_test_with.log
echo    - WITHOUT cleanup: audio_enhancement_test_without.log
echo.
echo    Look for lines like:
echo      "🧹 Running phrase cleanup on chunk %TEST_CHUNK%..."
echo      "✓ Removed 1 phrase(s) from chunk %TEST_CHUNK%"
echo.
echo ============================================================
echo Test Complete!
echo ============================================================
echo.
pause
