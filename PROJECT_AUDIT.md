# Project Audit
_Generated 2025-11-04T04:34:25 UTC_

## 1. Phase Python Coverage
### phase1-validation (5 Python files)
- `phase1-validation/src/phase1_validation/__init__.py`
- `phase1-validation/src/phase1_validation/validation.py`
- `phase1-validation/test_classification_fix.py`
- `phase1-validation/tests/__init__.py`
- `phase1-validation/tests/test_validation.py`

### phase2-extraction (66 Python files)
- `phase2-extraction/TTS_QUALITY_STANDARDS.py`
- `phase2-extraction/backup/tests/__init__.py`
- `phase2-extraction/backup/tests/test_extraction.py`
- `phase2-extraction/check_new_extraction.py`
- `phase2-extraction/check_phase1.py`
- `phase2-extraction/check_systematic_theology_status.py`
- `phase2-extraction/compare_and_normalize.py`
- `phase2-extraction/compare_orchestrator_vs_test.py`
- `phase2-extraction/compare_pdf_to_extracted.py`
- `phase2-extraction/complete_fix.py`
- `phase2-extraction/complete_fix_CORRECTED.py`
- `phase2-extraction/consensus_extractor.py`
- `phase2-extraction/debug_read_sample.py`
- `phase2-extraction/debug_spacing.py`
- `phase2-extraction/deep_compare.py`
- `phase2-extraction/diagnose.py`
- `phase2-extraction/diagnose_quality_difference.py`
- `phase2-extraction/diagnose_systematic_theology.py`
- `phase2-extraction/direct_compare.py`
- `phase2-extraction/extraction_PATCHED.py`
- `phase2-extraction/investigate_orphaned_files.py`
- `phase2-extraction/investigate_slowness.py`
- `phase2-extraction/multi_pass_extractor.py`
- `phase2-extraction/normalize_now.py`
- `phase2-extraction/phase2_status_report.py`
- `phase2-extraction/process_systematic_theology.py`
- `phase2-extraction/process_systematic_theology_FIXED.py`
- `phase2-extraction/quick_check.py`
- `phase2-extraction/quick_test.py`
- `phase2-extraction/src/phase2_extraction/__init__.py`
- `phase2-extraction/src/phase2_extraction/cleaner.py`
- `phase2-extraction/src/phase2_extraction/extraction.py`
- `phase2-extraction/src/phase2_extraction/extraction_OLD.py`
- `phase2-extraction/src/phase2_extraction/extraction_TTS_READY.py`
- `phase2-extraction/src/phase2_extraction/extraction_v2.py`
- `phase2-extraction/src/phase2_extraction/extractionbu.py`
- `phase2-extraction/src/phase2_extraction/extractors/__init__.py`
- `phase2-extraction/src/phase2_extraction/extractors/docx.py`
- `phase2-extraction/src/phase2_extraction/extractors/epub.py`
- `phase2-extraction/src/phase2_extraction/extractors/html.py`
- `phase2-extraction/src/phase2_extraction/extractors/ocr.py`
- `phase2-extraction/src/phase2_extraction/extractors/pdf.py`
- `phase2-extraction/src/phase2_extraction/extractors/txt.py`
- `phase2-extraction/src/phase2_extraction/ingest.py`
- `phase2-extraction/src/phase2_extraction/normalize.py`
- `phase2-extraction/src/phase2_extraction/structure_detector.py`
- `phase2-extraction/src/phase2_extraction/tts_normalizer.py`
- `phase2-extraction/src/phase2_extraction/utils.py`
- `phase2-extraction/test_all_extraction_methods.py`
- `phase2-extraction/test_cleaner.py`
- `phase2-extraction/test_cleaner_fixed.py`
- `phase2-extraction/test_extraction_accuracy.py`
- `phase2-extraction/test_extraction_methods.py`
- `phase2-extraction/test_full_gift.py`
- `phase2-extraction/test_nemo_cleaner.py`
- `phase2-extraction/test_normalize_enhancements.py`
- `phase2-extraction/test_pypdf_raw.py`
- `phase2-extraction/test_tts_normalization.py`
- `phase2-extraction/tests/test_extraction.py`
- `phase2-extraction/tests/test_extractors_basic.py`
- `phase2-extraction/trace_good_file.py`
- `phase2-extraction/tts_quality_check.py`
- `phase2-extraction/universal_extractor.py`
- `phase2-extraction/verify_extraction_quality.py`
- `phase2-extraction/verify_extractors.py`
- `phase2-extraction/verify_systematic_theology_quality.py`

### phase3-chunking (20 Python files)
- `phase3-chunking/src/phase3_chunking/__init__.py`
- `phase3-chunking/src/phase3_chunking/chunker.py`
- `phase3-chunking/src/phase3_chunking/detect.py`
- `phase3-chunking/src/phase3_chunking/main.py`
- `phase3-chunking/src/phase3_chunking/main_backup_chunkopt.py`
- `phase3-chunking/src/phase3_chunking/mainbu.py`
- `phase3-chunking/src/phase3_chunking/mainbu1.py`
- `phase3-chunking/src/phase3_chunking/models.py`
- `phase3-chunking/src/phase3_chunking/modelsbu.py`
- `phase3-chunking/src/phase3_chunking/profiles.py`
- `phase3-chunking/src/phase3_chunking/structure_chunking.py`
- `phase3-chunking/src/phase3_chunking/utils copy.py`
- `phase3-chunking/src/phase3_chunking/utils.py`
- `phase3-chunking/src/phase3_chunking/utils_v2.py`
- `phase3-chunking/src/phase3_chunking/voice_selection.py`
- `phase3-chunking/test_chapter_detection.py`
- `phase3-chunking/test_genre_aware.py`
- `phase3-chunking/tests/test_chunk_optimization.py`
- `phase3-chunking/tests/test_chunking.py`
- `phase3-chunking/validate_chunks.py`

### phase4_tts (53 Python files)
- `phase4_tts/Chatterbox-TTS-Extended/Chatter.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/__init__.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/__init__.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/const.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/decoder.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/f0_predictor.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/flow.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/flow_matching.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/hifigan.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/matcha/decoder.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/matcha/flow_matching.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/matcha/text_encoder.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/matcha/transformer.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/s3gen.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/transformer/__init__.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/transformer/activation.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/transformer/attention.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/transformer/convolution.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/transformer/embedding.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/transformer/encoder_layer.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/transformer/positionwise_feed_forward.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/transformer/subsampling.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/transformer/upsample_encoder.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/utils/class_utils.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/utils/mask.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/utils/mel.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3gen/xvector.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3tokenizer/__init__.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/s3tokenizer/s3tokenizer.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/t3/__init__.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/t3/inference/alignment_stream_analyzer.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/t3/inference/t3_hf_backend.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/t3/llama_configs.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/t3/modules/cond_enc.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/t3/modules/learned_pos_emb.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/t3/modules/perceiver.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/t3/modules/t3_config.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/t3/t3.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/tokenizers/__init__.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/tokenizers/tokenizer.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/voice_encoder/__init__.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/voice_encoder/config.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/voice_encoder/melspec.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/models/voice_encoder/voice_encoder.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/tts.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/utils.py`
- `phase4_tts/Chatterbox-TTS-Extended/chatterbox/src/chatterbox/vc.py`
- `phase4_tts/Chatterbox-TTS-Extended/test_tts.py`
- `phase4_tts/src/main.py`
- `phase4_tts/src/models.py`
- `phase4_tts/src/utils copy.py`
- `phase4_tts/src/utils.py`
- `phase4_tts/src/validation.py`

### phase5_enhancement (31 Python files)
- `phase5_enhancement/INTEGRATION_INSTRUCTIONS.py`
- `phase5_enhancement/clean_audiobook_v2.py`
- `phase5_enhancement/create_youtube_video.py`
- `phase5_enhancement/diagnose_clipping.py`
- `phase5_enhancement/diagnose_whisper.py`
- `phase5_enhancement/extract_phrase_timestamps.py`
- `phase5_enhancement/fix_config.py`
- `phase5_enhancement/generate_subtitles.py`
- `phase5_enhancement/process_meditations.py`
- `phase5_enhancement/rerun_with_cleaning.py`
- `phase5_enhancement/src/phase5_enhancement/__init__.py`
- `phase5_enhancement/src/phase5_enhancement/fix_main.py`
- `phase5_enhancement/src/phase5_enhancement/main.py`
- `phase5_enhancement/src/phase5_enhancement/main_fixed.py`
- `phase5_enhancement/src/phase5_enhancement/main_integrated.py`
- `phase5_enhancement/src/phase5_enhancement/main_integrated_fixed.py`
- `phase5_enhancement/src/phase5_enhancement/models.py`
- `phase5_enhancement/src/phase5_enhancement/phrase_cleaner.py`
- `phase5_enhancement/src/phase5_enhancement/subtitle_aligner.py`
- `phase5_enhancement/src/phase5_enhancement/subtitle_validator.py`
- `phase5_enhancement/src/phase5_enhancement/subtitles.py`
- `phase5_enhancement/strip_chunk_starts.py`
- `phase5_enhancement/strip_phrases_final.py`
- `phase5_enhancement/surgical_phrase_remover.py`
- `phase5_enhancement/tests/__init__.py`
- `phase5_enhancement/tests/test_main.py`
- `phase5_enhancement/tests/test_subtitles.py`
- `phase5_enhancement/tts_progress.py`
- `phase5_enhancement/validate_subtitles.py`
- `phase5_enhancement/verify_fix.py`
- `phase5_enhancement/youtube_workflow.py`

### phase6_orchestrator (54 Python files)
- `phase6_orchestrator/analyze_audio_quality.py`
- `phase6_orchestrator/analyze_failures.py`
- `phase6_orchestrator/analyze_phase5_failures.py`
- `phase6_orchestrator/analyze_pipeline_state.py`
- `phase6_orchestrator/check_and_fix_json.py`
- `phase6_orchestrator/check_chunk_paths.py`
- `phase6_orchestrator/check_paths.py`
- `phase6_orchestrator/check_phase3_output.py`
- `phase6_orchestrator/check_phase4.py`
- `phase6_orchestrator/check_phase4_output.py`
- `phase6_orchestrator/check_phase5.py`
- `phase6_orchestrator/check_phase5_detail.py`
- `phase6_orchestrator/check_phase5_python.py`
- `phase6_orchestrator/check_phase5_results.py`
- `phase6_orchestrator/check_pipeline.py`
- `phase6_orchestrator/check_pipeline_structure.py`
- `phase6_orchestrator/check_what_will_process.py`
- `phase6_orchestrator/check_working_dir.py`
- `phase6_orchestrator/clean_text_FIXED.py`
- `phase6_orchestrator/clear_phase5.py`
- `phase6_orchestrator/debug_phase5_paths.py`
- `phase6_orchestrator/detailed_diff.py`
- `phase6_orchestrator/diagnose_chunk_mismatch.py`
- `phase6_orchestrator/diagnose_chunk_order.py`
- `phase6_orchestrator/diagnose_json_state.py`
- `phase6_orchestrator/diagnose_paths.py`
- `phase6_orchestrator/diagnose_text_quality.py`
- `phase6_orchestrator/direct_comparison.py`
- `phase6_orchestrator/final_comparison.py`
- `phase6_orchestrator/finalize_phase4_only.py`
- `phase6_orchestrator/fix_pipeline_path.py`
- `phase6_orchestrator/orchestrator.py`
- `phase6_orchestrator/orchestrator_backup_stable.py`
- `phase6_orchestrator/orchestratorv1.py`
- `phase6_orchestrator/orchestratorv2.py`
- `phase6_orchestrator/patch_phase5_code.py`
- `phase6_orchestrator/patch_phase5_config.py`
- `phase6_orchestrator/patch_phase5_models.py`
- `phase6_orchestrator/phase5_direct_mode.py`
- `phase6_orchestrator/phase5_direct_simple.py`
- `phase6_orchestrator/process_confucius.py`
- `phase6_orchestrator/quick_status.py`
- `phase6_orchestrator/setup_phase5.py`
- `phase6_orchestrator/src/phase6_orchestrator/main.py`
- `phase6_orchestrator/switch_to_magi.py`
- `phase6_orchestrator/test_conda.py`
- `phase6_orchestrator/test_coverage_manual.py`
- `phase6_orchestrator/test_language_fix.py`
- `phase6_orchestrator/test_minimal.py`
- `phase6_orchestrator/test_phase4_direct.py`
- `phase6_orchestrator/test_phase4_env.py`
- `phase6_orchestrator/tests/test_coverage.py`
- `phase6_orchestrator/trace_execution.py`
- `phase6_orchestrator/verify_chunk_order.py`

### phase7_batch (9 Python files)
- `phase7_batch/src/phase7_batch/__init__.py`
- `phase7_batch/src/phase7_batch/cli.py`
- `phase7_batch/src/phase7_batch/main.py`
- `phase7_batch/src/phase7_batch/mainbu.py`
- `phase7_batch/src/phase7_batch/mainbu1.py`
- `phase7_batch/src/phase7_batch/models.py`
- `phase7_batch/tests/test_cli.py`
- `phase7_batch/tests/test_main.py`
- `phase7_batch/verify_install.py`

### phase_audio_cleanup (4 Python files)
- `phase_audio_cleanup/src/audio_cleanup/__init__.py`
- `phase_audio_cleanup/src/audio_cleanup/cleaner.py`
- `phase_audio_cleanup/src/audio_cleanup/main.py`
- `phase_audio_cleanup/tests/test_cleaner.py`

## 2. Test Assets
| File | Focus |
| --- | --- |
| `create_test_pdf.py` | Create a simple PDF with a few paragraphs |
| `diagnose_voice_test.ps1` | Diagnostic Script for Voice Testing Failures |
| `phase1-validation/test_classification_fix.py` | Test Phase 1 with improved classification. |
| `phase1-validation/tests/test_validation.py` | Expand for EPUB/D |
| `phase2-extraction/backup/tests/test_extraction.py` | Inferred from filename: tests test extraction |
| `phase2-extraction/compare_orchestrator_vs_test.py` | Read a sample from file. |
| `phase2-extraction/extracted_text/analects_test.txt` | The Analects of |
| `phase2-extraction/extracted_text/analects_test_meta.json` | { |
| `phase2-extraction/extracted_text/analects_test_v2.txt` | The Analects of |
| `phase2-extraction/extracted_text/analects_test_v2_meta.json` | { |
| `phase2-extraction/extracted_text/test_story.txt` | The Quick Brown Fox |
| `phase2-extraction/quick_test.py` | Run a test script and capture output. |
| `phase2-extraction/READY_TO_TEST.md` | # 🎯 READY TO TEST - Extraction Accuracy Tools |
| `phase2-extraction/test_all_extraction_methods.py` | Test 1: Multi-Pass Extraction |
| `phase2-extraction/test_cleaner.py` | Your sample text |
| `phase2-extraction/test_cleaner_fixed.py` | Working test script - adds src to path for import. |
| `phase2-extraction/test_extraction_accuracy.py` | Extract with pypdf. |
| `phase2-extraction/test_extraction_methods.py` | Try importing all extraction libraries |
| `phase2-extraction/test_full_gift.py` | Full test using the actual Gift of the Magi text file. |
| `phase2-extraction/test_nemo_cleaner.py` | Add src to path |
| `phase2-extraction/test_normalize_enhancements.py` | Add src to path |
| `phase2-extraction/test_output.txt` | TheGiftoftheMagi |
| `phase2-extraction/test_output_file_api.txt` | TheGiftoftheMagi |
| `phase2-extraction/test_output_nemo.txt` | TheGiftoftheMagi |
| `phase2-extraction/test_pypdf_raw.py` | Extract with pypdf |
| `phase2-extraction/TEST_SCRIPTS_README.md` | # Test Scripts for Phase 2 Text Cleaner |
| `phase2-extraction/test_tts_normalization.py` | Test that extraction.py properly normalizes text. |
| `phase2-extraction/TESTING_GUIDE.md` | # 🧪 Phase 2 Extraction Testing Guide |
| `phase2-extraction/TESTING_SUMMARY.md` | # Phase 2 Testing Summary - Systematic Theology |
| `phase2-extraction/tests/test_extraction.py` | Inferred from filename: tests test extraction |
| `phase2-extraction/tests/test_extractors_basic.py` | Add src to path |
| `phase3-chunking/chunks/analects_test_v2_chunk_001.txt` | The Analects of Confucius Confucius Wale р. кв. The Analects of Confucius Confucius Translated by Arthur Waley. . Contents I. Is it not pleasant to learn. .. II. He who exercises government. .. III. If he can bear to do this. .. IV. It is virtuous manners. .. V. The Master said of Kung-ye Ch'ang. .. VI. He |
| `phase3-chunking/chunks/analects_test_v2_chunk_002.txt` | " VII. Believing in and loving the ancients. .. VIII. The highest point of virtuous action. .. IX. The subjects of which the Master seldom spoke. .. X. Confucius, in his village, looked simple and sincere. .. XI. The men of former times. .. XII. Yen Yuan asked about perfect virtue. .. . XIII. Tsze-lu asked |
| `phase3-chunking/chunks/analects_test_v2_chunk_003.txt` | XIV. Hsien asked what was shameful. XV. The Duke Ling of Wei asked Confucius about tactics. .. . XVI. The head of the Chi family. .. XVII. Yang Ho wished to see Confucius. .. XVIII. The Viscount of Wei withdrew from the court. XIX. The scholar, trained for public duty. .. XX. The Heaven-determined order of |
| `phase3-chunking/chunks/analects_test_v2_chunk_004.txt` | The Master said, "Is it not pleasant to learn with a constant perseverance and application? "Is it not delightful to have friends coming from distant quarters? "Is he not a man of complete virtue, who feels no discomposure though men may take no note of him? " The philosopher Yu said, "They are few who, being |
| `phase3-chunking/chunks/analects_test_v2_chunk_005.txt` | filial and fraternal, are fond of offending against their superiors. |
| `phase3-chunking/chunks/analects_test_v2_chunk_006.txt` | There have been none, who, not liking to offend against their superiors, have been fond of stirring up confusion. "The superior man bends his attention to what is radical. That being established, all practical courses naturally grow up. Filial piety and fraternal submission, are they not the root of all |
| `phase3-chunking/chunks/analects_test_v2_chunk_007.txt` | " The Master said, "Fine words and an insinuating appearance are seldom associated with true virtue. " The philosopher Tsang said, "I daily examine myself on three points: -whether, in transacting business for others, I may have been not faithful; -whether, in intercourse with friends, I may have been not |
| `phase3-chunking/chunks/analects_test_v2_chunk_008.txt` | sincere; -whether I may have not mastered and practiced the instructions of my teacher. |
| `phase3-chunking/chunks/analects_test_v2_chunk_009.txt` | " The Master said, "To rule a country of a thousand chariots, there must be reverent attention to business, and sincerity; economy in expenditure, and love for men; and the employment of the people at the proper seasons. " The Master said, "A youth, when at home, should be filial, and, abroad, respectful to his |
| `phase3-chunking/chunks/analects_test_v2_chunk_010.txt` | Tsze-hsia said, "If a man withdraws his mind from the love of beauty, and applies it as sincerely to the love of the virtuous; if, in serving his parents, he can exert his utmost strength; if, in serving his prince, he can devote his life; if, in his intercourse with his friends, his words are sincere: |
| `phase3-chunking/chunks/analects_test_v2_chunk_011.txt` | -although men say that he has not learned, I will certainly say that he has. |
| `phase3-chunking/chunks/analects_test_v2_chunk_012.txt` | He should be earnest and truthful. He should overflow in love to all, and cultivate the friendship of the good. When he has time and opportunity, after the performance of these things, he should employ them in polite studies. " 7. The Master said, "If the scholar be not grave, he will not call forth any |
| `phase3-chunking/chunks/analects_test_v2_chunk_013.txt` | "Hold faithfulness and sincerity as first principles. 1. "Have no friends not equal to yourself. "When you have faults, do not fear to abandon them. " The philosopher Tsang said, "Let there be a careful attention to perform the funeral rites to parents, and let them be followed when long gone with the |
| `phase3-chunking/chunks/analects_test_v2_chunk_014.txt` | ceremonies of sacrifice: -then the virtue of the people will resume its proper excellence. |
| `phase3-chunking/chunks/analects_test_v2_chunk_015.txt` | " Tsze-ch'in asked Tsze-kung saying, "When our master comes to any country, he does not fail to learn all about its government. Does he ask his information? or is it given to him? " Tsze-kung said, "Our master is benign, upright, courteous, temperate, and complaisant and thus he gets his information. The |
| `phase3-chunking/chunks/analects_test_v2_chunk_016.txt` | master's mode of asking information, -is it not different from that of other men? |
| `phase3-chunking/chunks/analects_test_v2_chunk_017.txt` | " The Master said, "While a man's father is alive, look at the bent of his will; when his father is dead, look at his conduct. If for three years he does not alter from the way of his father, he may be called filial. " The philosopher Yu said, "In practicing the rules of propriety, a natural ease is to be |
| `phase3-chunking/chunks/analects_test_v2_chunk_018.txt` | In the ways prescribed by the ancient kings, this is the excellent quality, and in things small and great we follow them. "Yet it is not to be observed in all cases. If one, knowing how such ease should be prized, manifests it, without regulating it by the rules of propriety, this likewise is not to be done. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_019.txt` | The philosopher Yu said, "When agreements are made according to what is right, what is spoken can be made good. When respect is shown according to what is proper, one keeps far from shame and disgrace. When the parties upon whom a man leans are proper persons to be intimate with, he can make them his guides and |
| `phase3-chunking/chunks/analects_test_v2_chunk_020.txt` | The Master said, "He who aims to be a man of complete virtue in his food does not seek to gratify his appetite, nor in his dwelling place does he seek the appliances of ease; he is earnest in what he is doing, and careful in his speech; he frequents the company of men of principle that he may be rectified: |
| `phase3-chunking/chunks/analects_test_v2_chunk_021.txt` | -such a person may be said indeed to love to learn. |
| `phase3-chunking/chunks/analects_test_v2_chunk_022.txt` | " 14. " 15. Tsze-kung said, "What do you pronounce concerning the poor man who yet does not flatter, and the rich man who is not proud? " The Master replied, "They will do; but they are not equal to him, who, though poor, is yet cheerful, and to him, who, though rich, loves the rules of propriety. " Tsze-kung |
| `phase3-chunking/chunks/analects_test_v2_chunk_023.txt` | replied, "It is said in the Book of Poetry, 'As you cut and then file, as you carve and then polish. ' |
| `phase3-chunking/chunks/analects_test_v2_chunk_024.txt` | -The meaning is the same, I apprehend, as that which you have just expressed. " The Master said, "With one like Ts'ze, I can begin to talk about the odes. I told him one point, and he knew its proper sequence. " 16. The Master said, "I will not be afflicted at men's not knowing me; I will be afflicted that I do |
| `phase3-chunking/chunks/analects_test_v2_chunk_025.txt` | " II. The Master said, "He who exercises government by means of his virtue may be compared to the north polar star, which keeps its place and all the stars turn towards it. " I. 2. The Master said, "In the Book of Poetry are three hundred pieces, but the design of them all may be embraced in one sentence |
| `phase3-chunking/chunks/analects_test_v2_chunk_026.txt` | " 3. The Master said, "If the people be led by laws, and uniformity sought to be given them by punishments, they will try to avoid the punishment, but have no sense of shame. "If they be led by virtue, and uniformity sought to be given them by the rules of propriety, they will have the sense of shame, and |
| `phase3-chunking/chunks/analects_test_v2_chunk_027.txt` | " 4. The Master said, "At fifteen, I had my mind bent on learning. "At thirty, I stood firm. "At forty, I had no doubts. "At fifty, I knew the decrees of Heaven. "At sixty, my ear was an obedient organ for the reception of truth. "At seventy, I could follow what myheart desired, without transgressing what was |
| `phase3-chunking/chunks/analects_test_v2_chunk_028.txt` | " 5. Mang I asked what filial piety was. The Master said, "It is not being disobedient. " Soon after, as Fan Ch'ih was driving him, the Master told him, saying, "Mang-sun asked me what filial piety was, and I answered him, -'not being disobedient. "" Fan Ch'ih said, "What did you mean? " The Master replied, |
| `phase3-chunking/chunks/analects_test_v2_chunk_029.txt` | "That parents, when alive, beserved according to propriety; that, when dead, they should be buried according to propriety; and that they should be sacrificed to according to propriety. |
| `phase3-chunking/chunks/analects_test_v2_chunk_030.txt` | " 6. Mang Wu asked what filial piety was. The Master said, "Parents are anxious lesttheir children should be sick. " 7. Tsze-yu asked what filial piety was. The Master said, "The filial piety nowadays means the support of one's parents. But dogs and horses likewise are able to do something in the way of |
| `phase3-chunking/chunks/analects_test_v2_chunk_031.txt` | support; -without reverence, what is there to distinguish the one support given from the other? |
| `phase3-chunking/chunks/analects_test_v2_chunk_032.txt` | " Tsze-hsia asked what filial piety was. The Master said, "The difficulty is with the 8. countenance. If, when their elders have any troublesome affairs, the young take the toil of them, and if, when the young have wine and food, they set them before their elders, is THIS to be considered filial piety? " The |
| `phase3-chunking/chunks/analects_test_v2_chunk_033.txt` | Master said, "I have talked with Hui for a whole day, and he has not made any objection to anything I said; |
| `phase3-chunking/chunks/analects_test_v2_chunk_034.txt` | -as if he were stupid. He has retired, and I have examined his conduct when away from me, and found him able to illustrate my teachings. Hui! He is not stupid. " The Master said. "See what a man does. "Mark his motives. "Examine in what things he rests. "How can a man conceal his character? How can a man |
| `phase3-chunking/chunks/analects_test_v2_chunk_035.txt` | " The Master said, "If a man keeps cherishing his old knowledge, so as continually to be acquiring new, he may be a teacher of others. " The Master said. "The accomplished scholar is not a utensil. " Tsze-kung asked what constituted the superior man. The Master said, "He acts before he speaks, and afterwards |
| `phase3-chunking/chunks/analects_test_v2_chunk_036.txt` | " The Master said, "The superior man is catholic and not partisan. The mean man is partisan and not catholic. " The Master said, "Learning without thought is labor lost; thought without learning is perilous. " The Master said, "The study of strange doctrines is injurious indeed! " The Master said, "Yu, shall I |
| `phase3-chunking/chunks/analects_test_v2_chunk_037.txt` | When you know a thing, to hold that you know it; and when you do not know a thing, to allow that you do not know it; -this is knowledge. " 18. Tsze-chang was learning with a view to official emolument. The Master said, "Hear much and put aside the points of which you stand in doubt, while you speak cautiously |
| `phase3-chunking/chunks/analects_test_v2_chunk_038.txt` | at the same time of the others: -then you will afford few occasions for blame. |
| `phase3-chunking/chunks/analects_test_v2_chunk_039.txt` | See much and put aside the things which seem perilous, while you are cautious at the same time in carrying the others into practice: then you will have few occasions for repentance. When one gives few occasions for blame in his words, and few occasions for repentance in his conduct, he is in the way to get |
| `phase3-chunking/chunks/analects_test_v2_chunk_040.txt` | " The Duke Ai asked, saying, "What should be done in order to secure the submission of the people? " Confucius replied, "Advance the upright and set aside the crooked, then the people will submit. Advance the crooked and set aside the upright, then the people will not submit. " Cu Chi K'ang asked how to cause |
| `phase3-chunking/chunks/analects_test_v2_chunk_041.txt` | the people to reverence their ruler, to be faithful to him, and to go on to nerve themselves to virtue. |
| `phase3-chunking/chunks/analects_test_v2_chunk_042.txt` | The Master said, "Let him preside over -them with gravity; then they will reverence him. Let him be final and kind to all; - then they will be faithful to him. Let him advance the good and teach the incompetent; -then they will eagerly seek to be virtuous. " Some one addressed Confucius, saying, "Sir, why are |
| `phase3-chunking/chunks/analects_test_v2_chunk_043.txt` | " The Master said, "What does the Shu-ching say of filial piety? -'You are final, you discharge your brotherly duties. These qualities are displayed in government. ' This then also constitutes the exercise of government. Why must there be THAT-making one be in the government? " 22. The Master said, "I do not |
| `phase3-chunking/chunks/analects_test_v2_chunk_044.txt` | How can a large carriage be made to go without the crossbar for yoking the oxen to, or a small carriage without the arrangement for yoking the horses? " 23. Tsze-chang asked whether the affairs of ten ages after could be known. Confucius said, "The Yin dynasty followed the regulations of the Hsia: wherein it |
| `phase3-chunking/chunks/analects_test_v2_chunk_045.txt` | The Chau dynasty has followed the regulations of Yin: wherein it took from or added to them may be known. Some other may follow the Chau, but though it should be at the distance of a hundred ages, its affairs may beknown. " The Master said, "For a man to sacrifice to a spirit which does not belong to him |
| `phase3-chunking/chunks/analects_test_v2_chunk_046.txt` | "To see what is right and not to do it is want of courage. " Confucius said of the head of the Chi family, who had eight rows of pantomimes in his area, "If he can bear to do this, what may he not bear to do? " The three families used the Yungode, while the vessels were being removed, at the conclusion of the |
| `phase3-chunking/chunks/analects_test_v2_chunk_047.txt` | The Master said, "Assisting are the princes; -the son of heaven looks profound and grave'; -what application can these words have in the hall of the three families? " The Master said, "If a man be without the virtues proper to humanity, what has he to do with the rites of propriety? If a man be without the |
| `phase3-chunking/chunks/analects_test_v2_chunk_048.txt` | virtues proper to humanity, what has he to do with music? |
| `phase3-chunking/chunks/analects_test_v2_chunk_049.txt` | " Lin Fang asked what was the first thing to be attended to in ceremonies. The Master said, "A great question indeed! "In festive ceremonies, it is better to be sparing than extravagant. In the ceremonies of mourning, it is better that there be deep sorrow than in minute attention to observances. " The Master |
| `phase3-chunking/chunks/analects_test_v2_chunk_050.txt` | said, "The rude tribes of the east and north have their princes, and are not like the States of our great land which are without them. |
| `phase3-chunking/chunks/analects_test_v2_chunk_051.txt` | " (1 The chief of the Chi family was about to sacrifice to the T'ai mountain. The Master said to Zan Yu, "Can you not save him from this? " He answered, "I cannot. " Confucius said, "Alas! will you say that the T'ai mountain is not so discerning as Lin Fang? " The Master said, "The student of virtue has no |
| `phase3-chunking/chunks/analects_test_v2_chunk_052.txt` | If it be said he cannot avoid them, shall this be in archery? But he bows complaisantly to his competitors; thus he ascends the hall, descends, and exacts the forfeit of drinking. In his contention, he is still the Chun-tsze. " Tsze-hsia asked, saying, "What is the meaning of the passage -'The pretty dimples of |
| `phase3-chunking/chunks/analects_test_v2_chunk_053.txt` | The well-defined black and white of her eye! The plain ground for the colors? "" The Master said, "The business of laying on the colors follows the preparation of the plain ground. " "Ceremonies then are a subsequent thing? " The Master said, "It is Shang who can bring out my meaning. Now I can begin to talk |
| `phase3-chunking/chunks/analects_test_v2_chunk_054.txt` | " The Master said, "I could describe the ceremonies of the Hsia dynasty, but Chi cannot sufficiently attest my words. I could describe the ceremonies of the Yin dynasty, but Sung cannot sufficiently attest my words. They cannot do so because of theinsufficiency of their records and wise men. If those were |
| `phase3-chunking/chunks/analects_test_v2_chunk_055.txt` | sufficient, I could adduce them in support of my words. |
| `phase3-chunking/chunks/analects_test_v2_chunk_056.txt` | " 10. The Master said, "At the great sacrifice, after the pouring out of the libation, I have no wish to look on. " 11. Some one asked the meaning of the great sacrifice. The Master said, "I do not know. He who knew its meaning would find it as easy to govern the kingdom as to look on this"-pointing to his |
| `phase3-chunking/chunks/analects_test_v2_chunk_057.txt` | 12. He sacrificed to the dead, as if they were present. He sacrificed to the spirits, as if the spirits were present. The Master said, "I consider my not being present at the sacrifice, as if I did not sacrifice. " 13. Wang-sun Chia asked, saying, "What is the meaning of the saying, 'It is better to pay court |
| `phase3-chunking/chunks/analects_test_v2_chunk_058.txt` | "" The Master said, "Not so. He who offends against Heaven has none to whom he can pray. " The Master said, "Chau had the advantage of viewing the two past dynasties. How complete and elegant are its regulations! I follow Chau. " 15. The Master, when he entered the grand temple, asked about everything. Some one |
| `phase3-chunking/chunks/analects_test_v2_chunk_059.txt` | said, "Who say that the son of the man of Tsau knows the rules of propriety! |
| `phase3-chunking/chunks/analects_test_v2_chunk_060.txt` | He has entered the grand temple and asks about everything. " The Master heard the remark, and said, "This is a rule of propriety. " 16. The Master said, "In archery it is not going through the leather which is the principal thing; -because people's strength is not equal. This was the old way. " 17. Tsze-kung |
| `phase3-chunking/chunks/analects_test_v2_chunk_061.txt` | wished to do away with the offering of a sheep connected with the inauguration of the first day of each month. |
| `phase3-chunking/chunks/analects_test_v2_chunk_062.txt` | The Master said, "Ts'ze, you love the sheep; I love the ceremony. " 18. The Master said, "The full observance of the rules of propriety in serving one's prince is accounted by people to be flattery. " 19. The Duke Ting asked how a prince should employ his ministers, and how ministers should serve their prince. |
| `phase3-chunking/chunks/analects_test_v2_chunk_063.txt` | Confucius replied, "A prince should employ his minister according to according to the rules of propriety; ministers should serve their prince withfaithfulness. |
| `phase3-chunking/chunks/analects_test_v2_chunk_064.txt` | " 20. The Master said, "The Kwan Tsu is expressive of enjoyment without being licentious, and of grief without being hurtfully excessive. " The Duke Ai asked Tsai Wo about the altars of the spirits of the land. Tsai Wo replied, "The Hsia sovereign planted the pine tree about them; the men of the Yin planted the |
| `phase3-chunking/chunks/analects_test_v2_chunk_065.txt` | cypress; and the men of the Chau planted the chestnut tree, meaning thereby to cause the people to be in awe. |
| `phase3-chunking/chunks/analects_test_v2_chunk_066.txt` | " When the Master heard it, he said, "Things that are done, it is needless to speak about; things that have had their course, it is needless to remonstrate about; things that are past, it is needless to blame. " The Master said, "Small indeed was the capacity of Kwan Chung! " Some one said, "Was Kwan Chung |
| `phase3-chunking/chunks/analects_test_v2_chunk_067.txt` | "Kwan, " was the reply, "had the San Kwei, and his officers performed no double duties; how can he be considered parsimonious? " "Then, did Kwan Chung know the rules of propriety? " The Master said, "The princes of States have a screen intercepting the view at their gates. Kwan had likewise a screen at his |
| `phase3-chunking/chunks/analects_test_v2_chunk_068.txt` | The princes of States on any friendly meeting between two of them, had a stand on which to place their inverted cups. Kwan had also such a stand. If Kwan knew the rules of propriety, who does not know them? " The Master instructing the grand music master of Lu said, "How to play music may be known. At the |
| `phase3-chunking/chunks/analects_test_v2_chunk_069.txt` | commencement of the piece, all the parts should sound together. |
| `phase3-chunking/chunks/analects_test_v2_chunk_070.txt` | As it proceeds, they should be in harmony while severally distinct and flowing without break, and thus on to the conclusion. " The border warden at Yi requested to be introduced to the Master, saying, "When men of superior virtue have come to this, I have never been denied the privilege of seeing them. " The |
| `phase3-chunking/chunks/analects_test_v2_chunk_071.txt` | followers of the sage introduced him, and when he came out from the interview, he said. |
| `phase3-chunking/chunks/analects_test_v2_chunk_072.txt` | "My friends, why are you distressed by your master's loss of office? The kingdom has long been without the principles of truth and right; Heaven is going to use your master as a bell with its wooden tongue. " The Master said of the Shao that it was perfectly beautiful and also perfectly good. He said of the Wu |
| `phase3-chunking/chunks/analects_test_v2_chunk_073.txt` | that it was perfectly beautiful but not perfectly good. |
| `phase3-chunking/chunks/analects_test_v2_chunk_074.txt` | The Master said. "High station filled without indulgent generosity; ceremonies performed without reverence: mourning conducted without sorrow; -wherewith should I contemplate such ways? " The Master said, "It is virtuous manners which constitute the excellence of a neighborhood. If a man in selecting a |
| `phase3-chunking/chunks/analects_test_v2_chunk_075.txt` | residence do not fix on one where such prevail, how can he be wise? |
| `phase3-chunking/chunks/analects_test_v2_chunk_076.txt` | " 2. The Master said, "Those who are without virtue cannot abide long either in a condition of poverty and hardship, or in a condition of enjoyment. The virtuous rest in virtue; the wise desire virtue. " 3. The Master said, "It is only the truly virtuous man, who can love, or who can hate, others. " The Master |
| `phase3-chunking/chunks/analects_test_v2_chunk_077.txt` | said, "If the will be set on virtue, there will be no practice of wickedness. |
| `phase3-chunking/chunks/analects_test_v2_chunk_078.txt` | " The Master said, "Riches and honors are what men desire. If they cannot be obtained in the proper way, they should not be held. Poverty and meanness are what men dislike. If they cannot be avoided in the proper way, they should not be avoided. "If a superior man abandon virtue, how can he fulfill the |
| `phase3-chunking/chunks/analects_test_v2_chunk_079.txt` | requirements of that name? "The superior man does not, even for the space of a single meal, act contrary to virtue. |
| `phase3-chunking/chunks/analects_test_v2_chunk_080.txt` | In moments of haste, he cleaves to it. In seasons of danger, he cleaves to it. " 6. The Master said, "I have not seen a person who loved virtue, or one who hated what was not virtuous. He who loved virtue, would esteem nothing above it. He who hated what is not virtuous, would practice virtue in such a way that |
| `phase3-chunking/chunks/analects_test_v2_chunk_081.txt` | he would not allow anything that is not virtuous to approach his person. |
| `phase3-chunking/chunks/analects_test_v2_chunk_082.txt` | "Is any one able for one day to apply his strength to virtue? I have not seen the case in which his strength would be insufficient. "Should there possibly be any such case, I have not seen it. " The Master said, "The faults of men are characteristic of the class to which they belong. By observing a man's |
| `phase3-chunking/chunks/analects_test_v2_chunk_083.txt` | " The Master said, "If a man in the morning hear the right way, he may die in the evening hear regret. " The Master said, "A scholar, whose mind is set on truth, and who is ashamed of bad clothes and bad food, is not fit to be discoursed with. " The Master said, "The superior man, in the world, does not set his |
| `phase3-chunking/chunks/analects_test_v2_chunk_084.txt` | mind either for anything, or against anything; what is right he will follow. |
| `phase3-chunking/chunks/analects_test_v2_chunk_085.txt` | " The Master said, "The superior man thinks of virtue; the small man thinks of comfort. The superior man thinks of the sanctions of law; the small man thinks of favorswhich he may receive. " The Master said: "He who acts with a constant view to his own advantage will be much murmured against. " The Master said, |
| `phase3-chunking/chunks/analects_test_v2_chunk_086.txt` | "If a prince is able to govern his kingdom with the complaisance proper to the rules of propriety, what difficulty will he have? |
| `phase3-chunking/chunks/analects_test_v2_chunk_087.txt` | If he cannot govern it withthat complaisance, what has he to do with the rules of propriety? " The Master said, "A man should say, I am not concerned that I have no place, I am concerned how I may fit myself for one. I am not concerned that I am not known, I seek to be worthy to be known. " The Master said, |
| `phase3-chunking/chunks/analects_test_v2_chunk_088.txt` | "Shan, my doctrine is that of an all-pervading unity. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_089.txt` | The disciple Tsang replied, "Yes. " The Master went out, and the other disciples asked, saying, "What do his words mean? " Tsang said, "The doctrine of our master is to be true to the principles of our nature and the benevolent exercise of them to others, this and nothing more. " The Master said, "The mind of |
| `phase3-chunking/chunks/analects_test_v2_chunk_090.txt` | the superior man is conversant with righteousness; the mind of the mean man is conversant with gain. |
| `phase3-chunking/chunks/analects_test_v2_chunk_091.txt` | " The Master said, "When we see men of worth, we should think of equaling them; when we see men of a contrary character, we should turn inwards and examine ourselves. " The Master said, "In serving his parents, a son may remonstrate with them, but gently; when he sees that they do not incline to follow his |
| `phase3-chunking/chunks/analects_test_v2_chunk_092.txt` | advice, he shows an increased degree of reverence, but does not abandon his purpose; and should they punish him, he does not allow himself to murmur. |
| `phase3-chunking/chunks/analects_test_v2_chunk_093.txt` | " The Master said, "While his parents are alive, the son may not go abroad to a distance. If he does go abroad, he must have a fixed place to which he goes. " The Master said, "If the son for three years does not alter from the way of his father, he may be called filial. " The Master said, "The years of parents |
| `phase3-chunking/chunks/analects_test_v2_chunk_094.txt` | may by no means not be kept in the memory, as an occasion at once for joy and for fear. |
| `phase3-chunking/chunks/analects_test_v2_chunk_095.txt` | " The Master said, "The reason why the ancients did not readily give utterance to their words, was that they feared lest their actions should not come up to them. " "1 The Master said, "The cautious seldom err. The Master said, "The superior man wishes to be slow in his speech and earnest in his conduct. " 25. |
| `phase3-chunking/chunks/analects_test_v2_chunk_096.txt` | The Master said, "Virtue is not left to stand alone. |
| `phase3-chunking/chunks/analects_test_v2_chunk_097.txt` | He who practices it will have neighbors. " 26. Tsze-yu said, "In serving a prince, frequent remonstrances lead to disgrace. Between friends, frequent reproofs make the friendship distant. " V. 1. The Master said of Kung-ye Ch'ang that he might be wived; although he was put in bonds, he had not been guilty of |
| `phase3-chunking/chunks/analects_test_v2_chunk_098.txt` | Accordingly, he gave him his own daughter to wife. Of Nan Yung he said that if the country were well governed he would not be out of office, and if it were in governed, he would escape punishment and disgrace. He gave him the daughter of his own elder brother to wife. The Master said of Tsze-chien, "Of superior |
| `phase3-chunking/chunks/analects_test_v2_chunk_099.txt` | If there were not virtuous men in Lu, how could this man have acquired this character? " Tsze-kung asked, "What do you say of me, Ts'ze! " The Master said, "You are a utensil. " "What utensil? " "A gemmed sacrificial utensil. " Some one said, "Yung is truly virtuous, but he is not ready with his tongue. " The |
| `phase3-chunking/chunks/analects_test_v2_chunk_100.txt` | Master said, "What is the good of being ready with the tongue? |
| `phase3-chunking/chunks/analects_test_v2_chunk_101.txt` | They who encounter men with smartness of speech for the most part procure themselves hatred. I know not whether he be truly virtuous, but why should he show readiness of the tongue? " 6. The Master was wishing Ch'i-tiao K'ai to enter an official employment. He replied, "I am not yet able to rest in the |
| `phase3-chunking/chunks/analects_test_v2_chunk_102.txt` | The Master was pleased. The Master said, "My doctrines make no way. I will get upon a raft, and float about on the sea. He that will accompany me will be Yu, I dare say. " Tsze-lu hearing this was glad, upon which the Master said, "Yu is fonder of daring than I am. He does not exercise his judgment upon |
| `phase3-chunking/chunks/analects_test_v2_chunk_103.txt` | " 8. Mang Wu asked about Tsze-lu, whether he was perfectly virtuous. The Master said, "I do not know. " He asked again, when the Master replied, "In a kingdom of a thousand chariots, Yu might be employed to manage the military levies, but I do not know whether he be perfectly virtuous. " "And what do you say of |
| `phase3-chunking/chunks/analects_test_v2_chunk_104.txt` | The Master replied, "In a city of a thousand families, or a clan of a hundred chariots, Ch'iu might be employed as governor, but I do not know whether he is perfectly virtuous. " "What do you say of Ch'ih? " The Master replied, "With his sash girt and standing in a court, Ch'ih might be employed to converse |
| `phase3-chunking/chunks/analects_test_v2_chunk_105.txt` | with the visitors and guests, but I do not know whether he is perfectly virtuous. |
| `phase3-chunking/chunks/analects_test_v2_chunk_106.txt` | " The Master said to Tsze-kung, "Which do you consider superior, yourself or Hui? " Tsze-kung replied, "How dare I compare myself with Hui? Hui hears one point and knows all about a subject; I hear one point, and know a second. " The Master said, "You are not equal to him. I grant you, you are not equal to him. |
| `phase3-chunking/chunks/analects_test_v2_chunk_107.txt` | Tsai Yu being asleep during the daytime, the Master said, "Rotten wood cannot be carved; a wall of dirty earth will not receive the trowel. This Yu, what is the use of my reproving him? " 5. The Master said, "At first, my way with men was to hear their words, and give them credit for their conduct. Now my way |
| `phase3-chunking/chunks/analects_test_v2_chunk_108.txt` | is to hear their words, and look at their conduct. |
| `phase3-chunking/chunks/analects_test_v2_chunk_109.txt` | It is from Yu that I have learned to make this change. " The Master said, "I have not seen a firm and unbending man. " Some one replied, "There is Shan Ch'ang. " "Ch'ang, " said the Master, "is under the influence of his passions; how can he be pronounced firm and unbending? " Tsze-kung said, "What I do not |
| `phase3-chunking/chunks/analects_test_v2_chunk_110.txt` | wish men to do to me, I also wish not to do to men. |
| `phase3-chunking/chunks/analects_test_v2_chunk_111.txt` | " The Master said, "Ts'ze, you have not attained to that. " Tsze-kung said, "The Master's personal displays of his principles and ordinary descriptions of them may be heard. His discourses about man's nature, and the way of Heaven, cannot be heard. " When Tsze-lu heard anything, if he had not yet succeeded in |
| `phase3-chunking/chunks/analects_test_v2_chunk_112.txt` | carrying it into practice, he was only afraid lest he should hear something else. |
| `phase3-chunking/chunks/analects_test_v2_chunk_113.txt` | Tsze-kung asked, saying, "On what ground did Kung-wan get that title of Wan? " The Master said, "He was of an active nature and yet fond of learning, and he was not to ashamed to ask and learn of his inferiors! On these grounds he has been styled Wan. " The Master said of Tsze-ch'an that he had four of the |
| `phase3-chunking/chunks/analects_test_v2_chunk_114.txt` | characteristics of a superior man in his conduct of himself, he was humble; in serving his superior, he was respectful; in nourishing the people, he was kind; in ordering the people, he was just. |
| `phase3-chunking/chunks/analects_test_v2_chunk_115.txt` | " The Master said, "Yen P'ing knew well how to maintain friendly intercourse. The acquaintance might be long, but he showed the same respect as at first. " The Master said, "Tsang Wan kept a large tortoise in a house, on the capitals of the pillars of which he had hills made, and with representations of |
| `phase3-chunking/chunks/analects_test_v2_chunk_116.txt` | duckweed on the small pillars above the beams supporting the rafters. |
| `phase3-chunking/chunks/analects_test_v2_chunk_117.txt` | Of what sort was his wisdom? " 19Tsze-chang asked, saying, "The minister Tsze-wan thrice took office, and manifested no joy in his countenance. Thrice he retired from office, and manifested no displeasure. He made it a point to inform the new minister of the way in which he had conducted the government; what do |
| `phase3-chunking/chunks/analects_test_v2_chunk_118.txt` | The Master replied. "He was loyal. " "Was he perfectly virtuous? " "I do not know. How can he be pronounced perfectly virtuous? " Tsze-chang proceeded, "When the officer Ch'ui killed the prince of Ch'i, Ch'an Wan, though he was the owner of forty horses, abandoned them and left the country. Coming to another |
| `phase3-chunking/chunks/analects_test_v2_chunk_119.txt` | state, he said, 'They are here like our great officer, Ch'ui, ' and left it. |
| `phase3-chunking/chunks/analects_test_v2_chunk_120.txt` | He came to a second state, and with the same observation left it also; -what do you say of him? " The Master replied, "He was pure. " "Was he perfectly virtuous? " "I do not know. How can he be pronounced perfectly virtuous? " Chi Wan thought thrice, and then acted. When the Master was informed of it, he said, |
| `phase3-chunking/chunks/analects_test_v2_chunk_121.txt` | " The Master said, "When good order prevailed in his country, Ning Wu acted the part of a wise man. When his country was in disorder, he acted the part of a stupid man. Others may equal his wisdom, but they cannot equal his stupidity. " 22. When the Master was in Ch'an, he said, "Let me return! Let me return! |
| `phase3-chunking/chunks/analects_test_v2_chunk_122.txt` | The little children of my school are ambitious and too hasty. |
| `phase3-chunking/chunks/analects_test_v2_chunk_123.txt` | They are accomplished and complete so far, but they do not know how to restrict and shape themselves. " 23. The Master said, "Po-i and Shu-ch'i did not keep the former wickednesses of men in mind, and hence the resentments directed towards them were few. " The Master said, "Who says of Weishang Kao that he is |
| `phase3-chunking/chunks/analects_test_v2_chunk_124.txt` | One begged some vinegar of him, and he begged it of a neighbor and gave it to the man. " The Master said, "Fine words, an insinuating appearance, and excessive respect; Tso Ch'iu-ming was ashamed of them. I also am ashamed of them. To conceal resentment against a person, and appear friendly with him; -Tso |
| `phase3-chunking/chunks/analects_test_v2_chunk_125.txt` | I also am ashamed of it. " Yen Yuan and Chi Lu being by his side, the Master said to them, "Come, let each of you tell his wishes. " Tsze-lu said, "I should like, having chariots and horses, and light fur clothes, to share them with my friends, and though they should spoil them, I would not be displeased. " Yen |
| `phase3-chunking/chunks/analects_test_v2_chunk_126.txt` | Yuan said, "I should like not to boast of my excellence, nor to make a display of my meritorious deeds. |
| `phase3-chunking/chunks/analects_test_v2_chunk_127.txt` | " Tsze-lu then said, "I should like, sir, to hear your wishes. " The Master said, "They are, in regard to the aged, to give them rest; in regard to friends, to show them sincerity; in regard to the young, to treat them tenderly. " 27. The Master said, "It is all over. I have not yet seen one who could perceive |
| `phase3-chunking/chunks/analects_test_v2_chunk_128.txt` | " 28. The Master said, "In a hamlet of ten families, there may be found one honorable and sincere as I am, but not so fond of learning. " The Master said, "There is Yung! -He might occupy the place of a prince. " Chung-kung asked about Tsze-sang Po-tsze. The Master said, "He may pass. He does not mind small |
| `phase3-chunking/chunks/analects_test_v2_chunk_129.txt` | " Chung-kung said, "If a man cherish in himself a reverential feeling of the necessity of attention to business, though he may be easy in small matters in his government of the people, that may be allowed. But if he cherish in himself that easy feeling, and also carry it out in his practice, is not such an |
| `phase3-chunking/chunks/analects_test_v2_chunk_130.txt` | " The Master said, "Yung's words are right. " The Duke Ai asked which of the disciples loved to learn. Confucius replied to him, "There was Yen Hui; he loved to learn. He did not transfer his anger; he did not repeat a fault. Unfortunately, his appointed time was short and he died; and now there is not such |
| `phase3-chunking/chunks/analects_test_v2_chunk_131.txt` | I have not yet heard of any one who loves to learn as he did. " Tsze-hwa being employed on a mission to Ch'i, the disciple Zan requested grain for his mother. The Master said, "Give her a fu. " Yen requested more. "Give her a yi, " said the Master. Yen gave her five ping. The Master said, "When Ch'ih was |
| `phase3-chunking/chunks/analects_test_v2_chunk_132.txt` | proceeding to Ch'i, he had fat horses to his carriage, and wore light furs. |
| `phase3-chunking/chunks/analects_test_v2_chunk_133.txt` | I have heard that a superior man helps the distressed, but does not add to the wealth of the rich. " Yuan Sze being made governor of his town by the Master, he gave him nine hundred measures of grain, but Sze declined them. The Master said, "Do not decline them. May you not give them away in the neighborhoods, |
| `phase3-chunking/chunks/analects_test_v2_chunk_134.txt` | " 6. The Master, speaking of Chung-kung, said, "If the calf of a brindled cow be red and homed, although men may not wish to use it, would the spirits of the mountains and rivers put it aside? " 7. The Master said, "Such was Hui that for three months there would be nothing in his mind contrary to perfect |
| `phase3-chunking/chunks/analects_test_v2_chunk_135.txt` | The others may attain to this on some days or in some months, but nothing more. " X. Chi K'ang asked about Chung-yu, whether he was fit to be employed as an officer of government. The Master said, "Yu is a man of decision; what difficulty would he find in being an officer of government? " K'ang asked, "Is Ts'ze |
| `phase3-chunking/chunks/analects_test_v2_chunk_136.txt` | fit to be employed as an officer of government? " and was answered, "Ts'ze is a man of intelligence; what difficulty would he find in being an officer of government? " |
| `phase3-chunking/chunks/analects_test_v2_chunk_137.txt` | And to the same question about Chiu the Master gave the same reply, saying, "Ch'iu is a man of various ability. " 9. The chief of the Chi family sent to ask Min Tsze-ch'ien to be governor of Pi. Min Tszech'ien said, "Decline the offer for me politely. If any one come again to me with a second invitation, I |
| `phase3-chunking/chunks/analects_test_v2_chunk_138.txt` | shall be obliged to go and live on the banks of the Wan. |
| `phase3-chunking/chunks/analects_test_v2_chunk_139.txt` | " 10. Po-niu being ill, the Master went to ask for him. He took hold of his hand through the window, and said, "It is him. It is the appointment of Heaven, alas! That such a man should have such a sickness! That such a man should have such a sickness! " 11. The Master said, "Admirable indeed was the virtue of |
| `phase3-chunking/chunks/analects_test_v2_chunk_140.txt` | With a single bamboo dish of rice, a single gourd dish of drink, and living in his mean narrow lane, while others could not have endured the distress, he did not allow his joy to be affected by it. Admirable indeed was the virtue of Hui! " 12. Yen Ch'iu said, "It is not that I do not delight in your doctrines, |
| `phase3-chunking/chunks/analects_test_v2_chunk_141.txt` | The Master said, "Those whose strength is insufficient give over in the middle of the way but now you limit yourself. " 13. The Master said to Tsze-hsia, "Do you be a scholar after the style of the superior man, and not after that of the mean man. " 14. Tsze-yu being governor of Wu-ch'ang, the Master said to |
| `phase3-chunking/chunks/analects_test_v2_chunk_142.txt` | He answered, "There is Tan-t'ai Miehming, who never in walking takes a short cut, and never comes to my office, excepting on public business. " The Master said, "Mang Chih-fan does not boast of his merit. Being in the rear on an occasion of flight, when they were about to enter the gate, he whipped up his |
| `phase3-chunking/chunks/analects_test_v2_chunk_143.txt` | My horse would not advance. " 16. The Master said, "Without the specious speech of the litanist To and the beauty of the prince Chao of Sung, it is difficult to escape in the present age. " The Master said, "Who can go out but by the door? How is it that men will not walk according to these ways? " 18. The |
| `phase3-chunking/chunks/analects_test_v2_chunk_144.txt` | Master said, "Where the solid qualities are in excess of accomplishments, we have rusticity; where the accomplishments are in excess of the solid qualities, we have the manners of a clerk. |
| `phase3-chunking/chunks/analects_test_v2_chunk_145.txt` | When the accomplishments and solid qualities are equally blended, we then have the man of virtue. " 19. The Master said, "Man is born for uprightness. If a man lose his uprightness, and yet live, his escape from death is the effect of mere good fortune. " 20. The Master said, "They who know the truth are not |
| `phase3-chunking/chunks/analects_test_v2_chunk_146.txt` | equal to those who love it, and they who love it are not equal to those who delight in it. |
| `phase3-chunking/chunks/analects_test_v2_chunk_147.txt` | " The Master said, "To those whose talents are above mediocrity, the highest subjects may be announced. To those who are below mediocrity, the highest subjects may not be announced. " Fan Ch'ih asked what constituted wisdom. The Master said, "To give one's self earnestly to the duties due to men, and, while |
| `phase3-chunking/chunks/analects_test_v2_chunk_148.txt` | respecting spiritual beings, to keep aloof from them, may be called wisdom. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_149.txt` | He asked about perfect virtue. The Master said, "The man of virtue makes the difficulty to be overcome his first business, and success only a subsequent consideration; this may be called perfect virtue. " The Master said, "The wise find pleasure in water; the virtuous find pleasure in hills. The wise are |
| `phase3-chunking/chunks/analects_test_v2_chunk_150.txt` | The wise are joyful; the virtuous are long-lived. " The Master said, "Ch'i, by one change, would come to the State of Lu. Lu, by one change, would come to a State where true principles predominated. " The Master said, "A cornered vessel without corners-a strange cornered vessel! A strange cornered vessel! " a |
| `phase3-chunking/chunks/analects_test_v2_chunk_151.txt` | Tsai Wo asked, saying, "A benevolent man, though it be told him, -'There man in the well" will go in after him, I suppose. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_152.txt` | Confucius said, "Why should he do so? " A superior man may be made to go to the well, but he cannot be made to go down into it. He may be imposed upon, but he cannot be fooled. " The Master said, "The superior man, extensively studying all learning, and keeping himself under the restraint of the rules of |
| `phase3-chunking/chunks/analects_test_v2_chunk_153.txt` | propriety, may thus likewise not overstep what is right. |
| `phase3-chunking/chunks/analects_test_v2_chunk_154.txt` | " 28. The Master having visited Nan-tsze, Tsze-lu was displeased, on which the Master swore, saying, "Wherein I have done improperly, may Heaven reject me, may Heaven reject me! " 24. The Master said, "Perfect is the virtue which is according to the Constant Mean! Rare for a long time has been its practice |
| `phase3-chunking/chunks/analects_test_v2_chunk_155.txt` | " Tsze-kung said, "Suppose the case of a man extensively conferring benefits on the people, and able to assist all, what would you say of him? Might he be called perfectly virtuous? " The Master said, "Why speak only of virtue in connection with him? Must he not have the qualities of a sage? Even Yao and Shun |
| `phase3-chunking/chunks/analects_test_v2_chunk_156.txt` | "Now the man of perfect virtue, wishing to be established himself, seeks also to establish others; wishing to be enlarged himself, he seeks also to enlarge others. "To be able to judge of others by what is nigh in ourselves; -this may be called the art of virtue. " VII. The Master said, "A transmitter and not a |
| `phase3-chunking/chunks/analects_test_v2_chunk_157.txt` | maker, believing in and loving the ancients, I venture to compare myself with our old P'ang. |
| `phase3-chunking/chunks/analects_test_v2_chunk_158.txt` | The Master said, "The silent treasuring up of knowledge; learning without satiety; and instructing others without being wearied: -which one of these things belongs to me? " The Master said, "The leaving virtue without proper cultivation; the not thoroughly discussing what is learned; not being able to move |
| `phase3-chunking/chunks/analects_test_v2_chunk_159.txt` | towards righteousness of which a knowledge is gained; and not being able to change what is not good: -these are the things which occasion me solicitude. |
| `phase3-chunking/chunks/analects_test_v2_chunk_160.txt` | " When the Master was unoccupied with business, his manner was easy, and he looked pleased. The Master said, "Extreme is my decay. For a long time, I have not dreamed, as I was wont to do, that I saw the duke of Chau. " The Master said, "Let the will be set on the path of duty. "Let every attainment in what is |
| `phase3-chunking/chunks/analects_test_v2_chunk_161.txt` | "Let perfect virtue be accorded with. "Let relaxation and enjoyment be found in the polite arts. " The Master said, "From the man bringing his bundle of dried flesh for my teaching upwards, I have never refused instruction to any one. " 7. The Master said, "I do not open up the truth to one who is not eager to |
| `phase3-chunking/chunks/analects_test_v2_chunk_162.txt` | get knowledge, nor help out any one who is not anxious to explain himself. |
| `phase3-chunking/chunks/analects_test_v2_chunk_163.txt` | When I have presented one corner of a subject to any one, and he cannot from it learn the other three, I do not repeat my lesson. " When the Master was eating by the side of a mourner, he never ate to the full. He did not sing on the same day in which he had been weeping. The Master said to Yen Yuan, "When |
| `phase3-chunking/chunks/analects_test_v2_chunk_164.txt` | called to office, to undertake its duties; when not so called, to he retired: -it is only I and you who have attained to this. |
| `phase3-chunking/chunks/analects_test_v2_chunk_165.txt` | " Tsze-lu said, "If you had the conduct of the armies of a great state, whom would you have to act with you? " The Master said, "I would not have him to act with me, who will unarmed attack a tiger, or cross a river without a boat, dying without any regret. My associate must be the man who proceeds to action |
| `phase3-chunking/chunks/analects_test_v2_chunk_166.txt` | full of solicitude, who is fond of adjusting his plans, and then carries them into execution. |
| `phase3-chunking/chunks/analects_test_v2_chunk_167.txt` | " The Master said, "If the search for riches is sure to be successful, though I should become a groom with whip in hand to get them, I will do so. As the search may not be successful, I will follow after that which I love. " The things in reference to which the Master exercised the greatest caution were |
| `phase3-chunking/chunks/analects_test_v2_chunk_168.txt` | When the Master was in Ch'i, he heard the Shao, and for three months did not know the taste of flesh. "I did not think"" he said, "that music could have been made so excellent as this. " Yen Yu said, "Is our Master for the ruler of Wei? " Tsze-kung said, "Oh! I will ask him. " He went in accordingly, and said, |
| `phase3-chunking/chunks/analects_test_v2_chunk_169.txt` | "They were ancient worthies, " said the Master. "Did they have any repinings because of their course? " The Master again replied, "They sought to act virtuously, and they did so; what was there for them to repine about? " On this, Tsze-kung went out and said, "Our Master is not for him. " The Master said, "With |
| `phase3-chunking/chunks/analects_test_v2_chunk_170.txt` | coarse rice to eat, with water to drink, and my bended arm for a pillow; I have still joy in the midst of these things. |
| `phase3-chunking/chunks/analects_test_v2_chunk_171.txt` | Riches and honors acquired by unrighteousness, are to me as a floating cloud. " 17. The Master said, "If some years were added to my life, I would give fifty to the study of the Yi, and then I might come to be without great faults. " 18. The Master's frequent themes of discourse were the Odes, the History, and |
| `phase3-chunking/chunks/analects_test_v2_chunk_172.txt` | On all these he frequently discoursed. 19. The Duke of Sheh asked Tsze-lu about Confucius, and Tsze-lu did not answer him. The Master said, "Why did you not say to him, -He is simply a man, who in his eager pursuit of knowledge forgets his food, who in the joy of its attainment forgets his sorrows, and who does |
| `phase3-chunking/chunks/analects_test_v2_chunk_173.txt` | " The Master said, "I am not one who was born in the possession of knowledge; I am one who is fond of antiquity, and earnest in seeking it there. " 21. The subjects on which the Master did not talk, were extraordinary things: feats of strength, disorder, and spiritual beings. The Master said, "When I walk along |
| `phase3-chunking/chunks/analects_test_v2_chunk_174.txt` | with two others, they may serve me as my teachers. |
| `phase3-chunking/chunks/analects_test_v2_chunk_175.txt` | I will select their good qualities and follow them, their bad qualities and avoid them. " 23. he do to me? " The Master said, "Heaven produced the virtue that is in me. Hwan T'ui-what can 24. The Master said, "Do you think, my disciples, that I have any concealments? I conceal nothing from you. There is nothing |
| `phase3-chunking/chunks/analects_test_v2_chunk_176.txt` | which I do that is not shown to you, my disciples; that is my way. |
| `phase3-chunking/chunks/analects_test_v2_chunk_177.txt` | " 25. There were four things which the Master taught, -letters, ethics, devotion of soul, and truthfulness. 26. The Master said, "A sage it is not mine to see; could I see a man of real talent and virtue, that would satisfy me. " The Master said, "A good man it is not mine to see; could I see a man possessed of |
| `phase3-chunking/chunks/analects_test_v2_chunk_178.txt` | "Having not and yet affecting to have, empty and yet affecting to be full, straitened and yet affecting to be at ease: - -it is difficult with such characteristics to have constancy. " The Master angled, but did not use a net. He shot, but not at birds perching. 28. The Master said, "There may be those who act |
| `phase3-chunking/chunks/analects_test_v2_chunk_179.txt` | I do not do so. Hearing much and selecting what is good and following it; seeing much and keeping it in memory: this is the second style of knowledge. " 29. It was difficult to talk profitably and reputably with the people of Hu-hsiang, and a lad of that place having had an interview with the Master, the |
| `phase3-chunking/chunks/analects_test_v2_chunk_180.txt` | The Master said, "I admit people's approach to me without committing myself as to what they may do when they have retired. Why must one be so severe? If a man purify himself to wait upon me, I receive him so purified, without guaranteeing his past conduct. " The Master said, "Is virtue a thing remote? I wish to |
| `phase3-chunking/chunks/analects_test_v2_chunk_181.txt` | " 31. The minister of crime of Ch'an asked whether the duke Chao knew propriety, and Confucius said, "He knew propriety. " Confucius having retired, the minister bowed to Wu-ma Ch'i to come forward, and said, "I have heard that the superior man is not a partisan. May the superior man be a partisan also? The |
| `phase3-chunking/chunks/analects_test_v2_chunk_182.txt` | prince married a daughter of the house of WU, of the same surname with himself, and called her, 'The elder Tsze of Wu. ' |
| `phase3-chunking/chunks/analects_test_v2_chunk_183.txt` | If the prince knew propriety, who does not know it? " Wu-ma Ch'i reported these remarks, and the Master said, "I am fortunate! If I have any errors, people are sure to know them. " When the Master was in company with a person who was singing, if he sang well, he would make him repeat the song, while he |
| `phase3-chunking/chunks/analects_test_v2_chunk_184.txt` | The Master said. "In letters I am perhaps equal to other men, but the character of the superior man, carrying out in his conduct what he professes, is what I have not yet attained to. " The Master said, "The sage and the man of perfect virtue; -how dare I rank myself with them? It may simply be said of me, that |
| `phase3-chunking/chunks/analects_test_v2_chunk_185.txt` | I strive to become such without satiety, and teach others without weariness. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_186.txt` | Kung-hsi Hwa said, "This is just what we, the disciples, cannot imitate you in. " The Master being very sick, Tsze-lu asked leave to pray for him. He said, "May such a thing be done? " Tsze-lu replied, "It may. In the Eulogies it is said, 'Prayer has been made for thee to the spirits of the upper and lower |
| `phase3-chunking/chunks/analects_test_v2_chunk_187.txt` | "" The Master said, "My praying has been for a long time. " The Master said, "Extravagance leads to insubordination, and parsimony to meanness. It is better to be mean than to be insubordinate. " The Master said, "The superior man is satisfied and composed; the mean man is always full of distress. " X The |
| `phase3-chunking/chunks/analects_test_v2_chunk_188.txt` | Master was mild, and yet dignified; majestic, and yet not fierce; respectful, and yet easy. |
| `phase3-chunking/chunks/analects_test_v2_chunk_189.txt` | The Master said, "T'ai-po may be said to have reached the highest point of virtuous action. Thrice he declined the kingdom, and the people in ignorance of his motives could not express their approbation of his conduct. " 2. The Master said, "Respectfulness, without the rules of propriety, becomes laborious |
| `phase3-chunking/chunks/analects_test_v2_chunk_190.txt` | bustle; carefulness, without the rules of propriety, becomes timidity; boldness, without the rules of propriety, becomes insubordination; straightforwardness, without the rules of propriety, becomes rudeness. |
| `phase3-chunking/chunks/analects_test_v2_chunk_191.txt` | "When those who are in high stations perform well all their duties to their relations, the people are aroused to virtue. When old friends are not neglected by them, the people are preserved from meanness. " The philosopher Tsang being ill, he cared to him the disciples of his school, and said, "Uncover my feet, |
| `phase3-chunking/chunks/analects_test_v2_chunk_192.txt` | It is said in the Book of Poetry, 'We should be apprehensive and cautious, as if on the brink of a deep gulf, as if treading on thin ice, I and so have I been. Now and hereafter, I know my escape from all injury to my person. O ye, my little children. " The philosopher Tsang being ill, Meng Chang went to ask |
| `phase3-chunking/chunks/analects_test_v2_chunk_193.txt` | "There are three principles of conduct which the man of high rank should consider specially important: -that in his deportment and manner he keep from violence and heedlessness; that in regulating his countenance he keep near to sincerity; and that in his words and tones he keep far from lowness and |
| `phase3-chunking/chunks/analects_test_v2_chunk_194.txt` | The philosopher Tsang said, "Gifted with ability, and yet putting questions to those who were not so; possessed of much, and yet putting questions to those possessed of little; having, as though he had not; full, and yet counting himself as empty; offended against, and yet entering into no altercation; formerly |
| `phase3-chunking/chunks/analects_test_v2_chunk_195.txt` | Tsang said to him, "When a bird is about to die, its notes are mournful; when a man is about to die, his words are good. As to such matters as attending to the sacrificial vessels, there are the proper officers for them. " 5. " The philosopher Tsang said, "Suppose that there is an individual who can be |
| `phase3-chunking/chunks/analects_test_v2_chunk_196.txt` | entrusted with the charge of a young orphan prince, and can be commissioned with authority over a state of a hundred li, and whom no emergency however great can drive from his principles: -is such a man a superior man? |
| `phase3-chunking/chunks/analects_test_v2_chunk_197.txt` | He is a superior man indeed. " 7. The philosopher Tsang said, "The officer may not be without breadth of mind and vigorous endurance. His burden is heavy and his course is long. "Perfect virtue is the burden which he considers it is his to sustain; -is it not heavy? Only with death does his course stop; -is it |
| `phase3-chunking/chunks/analects_test_v2_chunk_198.txt` | The Master said, "It is by the Odes that the mind is aroused. "It is by the Rules of Propriety that the character is established. "It is from Music that the finish is received. " The Master said, "The people may be made to follow a path of action, but they may 6. not be made to understand it. " The Master said, |
| `phase3-chunking/chunks/analects_test_v2_chunk_199.txt` | "The man who is fond of daring and is dissatisfied with poverty, will proceed to insubordination. |
| `phase3-chunking/chunks/analects_test_v2_chunk_200.txt` | So will the man who is not virtuous, when you carry your dislike of him to an extreme. " The Master said, "Though a man have abilities as admirable as those of the Duke of Chau, yet if he be proud and niggardly, those other things are really not worth being looked at. " The Master said, "It is not easy to find |
| `phase3-chunking/chunks/analects_test_v2_chunk_201.txt` | a man who has learned for three years without coming to be good. |
| `phase3-chunking/chunks/analects_test_v2_chunk_202.txt` | " The Master said, "With sincere faith he unites the love of learning; holding firm to death, he is perfecting the excellence of his course. "Such an one will not enter a tottering state, nor dwell in a disorganized one. When right principles of government prevail in the kingdom, he will show himself; when they |
| `phase3-chunking/chunks/analects_test_v2_chunk_203.txt` | "When a country is well governed, poverty and a mean condition are things to be ashamed of. When a country is ill governed, riches and honor are things to be ashamed of. " The Master said, "He who is not in any particular office has nothing to do with plans for the administration of its duties. " The Master |
| `phase3-chunking/chunks/analects_test_v2_chunk_204.txt` | said, "When the music master Chih first entered on his office, the finish of the Kwan Tsu was magnificent; -how it filled the ears! |
| `phase3-chunking/chunks/analects_test_v2_chunk_205.txt` | " The Master said, "Ardent and yet not upright, stupid and yet not attentive; simple and yet not sincere: -such persons I do not understand. " 17. The Master said, "Learn as if you could not reach your object, and were always fearing also lest you should lose it. " 18. The Master said, "How majestic was the |
| `phase3-chunking/chunks/analects_test_v2_chunk_206.txt` | manner in which Shun and Yu held possession of the empire, as if it were nothing to them! |
| `phase3-chunking/chunks/analects_test_v2_chunk_207.txt` | 19. The Master said, "Great indeed was Yao as a sovereign! How majestic was he! It is only Heaven that is grand, and only Yao corresponded to it. How vast was his virtue! The people could find no name for it. "How majestic was he in the works which he accomplished! How glorious in the elegant regulations which |
| `phase3-chunking/chunks/analects_test_v2_chunk_208.txt` | " 20. Shun had five ministers, and the empire was well governed. King Wu said, "I have ten able ministers. " Confucius said, "Is not the saying that talents are difficult to find, true? Only when the dynasties of T'ang and Yu met, were they more abundant than in this of Chau, yet there was a woman among them. |
| `phase3-chunking/chunks/analects_test_v2_chunk_209.txt` | "King Wan possessed two of the three parts of the empire, and with those he served the dynasty of Yin. The virtue of the house of Chau may be said to have reached the highest point indeed. " The Master said, "I can find no flaw in the character of Yu. He used himself coarse food and drink, but displayed the |
| `phase3-chunking/chunks/analects_test_v2_chunk_210.txt` | His ordinary garments were poor, but he displayed the utmost elegance in his sacrificial cap and apron. He lived in a low, mean house, but expended all his strength on the ditches and water channels. I can find nothing like a flaw in Yu. " IX. 1. The subjects of which the Master seldom spoke were: |
| `phase3-chunking/chunks/analects_test_v2_chunk_211.txt` | profitableness, and also the appointments of Heaven, and perfect virtue. |
| `phase3-chunking/chunks/analects_test_v2_chunk_212.txt` | A man of the village of Ta-hsiang said, "Great indeed is the philosopher K'ung! His learning is extensive, and yet he does not render his name famous by any particular thing. " The Master heard the observation, and said to his disciples, "What shall I practice? Shall I practice charioteering, or shall I |
| `phase3-chunking/chunks/analects_test_v2_chunk_213.txt` | I will practice charioteering. " 3. The Master said, "The linen cap is that prescribed by the rules of ceremony, but now a silk one is worn. It is economical, and I follow the common practice. "The rules of ceremony prescribe the bowing below the hall, but now the practice is to bow only after ascending it. |
| `phase3-chunking/chunks/analects_test_v2_chunk_214.txt` | I continue to bow below the hall, though I oppose the common practice. " 4. There were four things from which the Master was entirely free. He had no foregone conclusions, no arbitrary predeterminations, no obstinacy, and no egoism. The Master was put in fear in K'wang. 5. } He said, "After the death of King |
| `phase3-chunking/chunks/analects_test_v2_chunk_215.txt` | Wan, was not the cause of truth lodged here in me? |
| `phase3-chunking/chunks/analects_test_v2_chunk_216.txt` | "If Heaven had wished to let this cause of truth perish, then I, a future mortal! should nothave got such a relation to that cause. While Heaven does not let the cause of truth perish, what can the people of K'wang do to me? " A high officer asked Tsze-kung, saying, "May we not say that your Master is a sage? |
| `phase3-chunking/chunks/analects_test_v2_chunk_217.txt` | " Tsze-kung said, "Certainly Heaven has endowed him unlimitedly. He is about a sage. And, moreover, his ability is various. " The Master heard of the conversation and said, "Does the high officer know me? When I was young, my condition was low, and I acquired my ability in many things, butthey were mean |
| `phase3-chunking/chunks/analects_test_v2_chunk_218.txt` | Must the superior man have such variety of ability? He does notneed variety of ability. Lao said, "The Master said, 'Having no official employment, I acquired many arts. "" The Master said, "Am I indeed possessed of knowledge? I am not knowing. But if amean person, who appears quite empty-like, ask anything of |
| `phase3-chunking/chunks/analects_test_v2_chunk_219.txt` | me, I set it forth from one end to the other, and exhaust it. |
| `phase3-chunking/chunks/analects_test_v2_chunk_220.txt` | " The Master said, "The Fang bird does not come; the river sends forth no map: -it is all over with me! " When the Master saw a person in a mourning dress, or any one with the cap andupper and lower garments of full dress, or a blind person, on observing themapproaching, though they were younger than himself, |
| `phase3-chunking/chunks/analects_test_v2_chunk_221.txt` | he would rise up, and if he had to pass by them, he would do so hastily. |
| `phase3-chunking/chunks/analects_test_v2_chunk_222.txt` | Yen Yuan, in admiration of the Master's doctrines, sighed and said, "I looked up to them, and they seemed to become more high; I tried to penetrate them, and they seemedto become more firm; I looked at them before me, and suddenly they seemed to be behind. "The Master, by orderly method, skillfully leads men |
| `phase3-chunking/chunks/analects_test_v2_chunk_223.txt` | He enlarged my mind with learning, and taught me the restraints of propriety. "When I wish to give over the study of his doctrines, I cannot do so, and having exerted all my ability, there seems something to stand right up before me; but though I wish to follow and lay hold of it, I really find no way to do so. |
| `phase3-chunking/chunks/analects_test_v2_chunk_224.txt` | " The Master being very ill, Tsze-lu wished the disciples to act as ministers to him. |
| `phase3-chunking/chunks/analects_test_v2_chunk_225.txt` | During a remission of his illness, he said, "Long has the conduct of Yu been deceitful! By pretending to have ministers when I have them not, whom should I impose upon? Should I impose upon Heaven? "Moreover, than that I should die in the hands of ministers, is it not better that I should die in the hands of |
| `phase3-chunking/chunks/analects_test_v2_chunk_226.txt` | And though I may not get a great burial, shall I die upon the road? " 13. Tsze-kung said, "There is a beautiful gem here. Should I lay it up in a case and keep it? or should I seek for a good price and sell it? " The Master said, "Sell it! Sell it! But I would wait for one to offer the price. " 14. The Master |
| `phase3-chunking/chunks/analects_test_v2_chunk_227.txt` | was wishing to go and live among the nine wild tribes of the east. |
| `phase3-chunking/chunks/analects_test_v2_chunk_228.txt` | Some one said, "They are rude. How can you do such a thing? " The Master said, "If a superior man dwelt among them, what rudeness would there be? " 15. The Master said, "I returned from Wei to Lu, and then the music was reformed, and the pieces in the Royal songs and Praise songs all found their proper places. |
| `phase3-chunking/chunks/analects_test_v2_chunk_229.txt` | The Master said, "Abroad, to serve the high ministers and nobles; at home, to serve one's father and elder brothers; in all duties to the dead, not to dare not to exert one's self; and not to be overcome of wine: -which one of these things do I attain to? " The Master standing by a stream, said, "It passes on |
| `phase3-chunking/chunks/analects_test_v2_chunk_230.txt` | " 18. The Master said, "I have not seen one who loves virtue as he loves beauty. " 19. The Master said, "The prosecution of learning may be compared to what mayhappen in raising a mound. If there want but one basket of earth to complete the work, and I stop, the stopping is my own work. It may be compared to |
| `phase3-chunking/chunks/analects_test_v2_chunk_231.txt` | Though but one basketful is thrown at a time, the advancing with itmy own going forward. " 20. The Master said, "Never flagging when I set forth anything to him; -ah! that isHui. " 21. The Master said of Yen Yuan, "Alas! I saw his constant advance. I never saw himstop in his progress. " The Master said, "There |
| `phase3-chunking/chunks/analects_test_v2_chunk_232.txt` | are cases in which the blade springs, but the plant does not go on to flower! |
| `phase3-chunking/chunks/analects_test_v2_chunk_233.txt` | There are cases where it flowers but fruit is not subsequently produced! " 23. The Master said, "A youth is to be regarded with respect. How do we know that his future will not be equal to our present? If he reach the age of forty or fifty, and has not made himself heard of, then indeed he will not be worth |
| `phase3-chunking/chunks/analects_test_v2_chunk_234.txt` | " 24. The Master said, "Can men refuse to assent to the words of strict admonition? But it is reforming the conduct because of them which is valuable. Can men refuse to be pleased with words of gentle advice? But it is unfolding their aim which is valuable. If a man be pleased with these words, but does not |
| `phase3-chunking/chunks/analects_test_v2_chunk_235.txt` | unfold their aim, and assents to those, but does not reform his conduct, I can really do nothing with him. |
| `phase3-chunking/chunks/analects_test_v2_chunk_236.txt` | " The Master said, "Hold faithfulness and sincerity as first principles. Have no friends not equal to yourself. When you have faults, do not fear to abandon them. " 26. The Master said, "The commander of the forces of a large state may be carried off, but the will of even a common man cannot be taken from him. |
| `phase3-chunking/chunks/analects_test_v2_chunk_237.txt` | " The Master said, "Dressed himself in a tattered robe quilted with hemp, yet standing by the side of men dressed in furs, and not ashamed; -ah! |
| `phase3-chunking/chunks/analects_test_v2_chunk_238.txt` | it is Yu who is equal to this! "He dislikes none, he covets nothing; -what can he do but what is good! " Tsze-lu kept continually repeating these words of the ode, when the Master said, "Those things are by no means sufficient to constitute perfect excellence. " The Master said, "When the year becomes cold, |
| `phase3-chunking/chunks/analects_test_v2_chunk_239.txt` | then we know how the pine and the cypress are the last to lose their leaves. |
| `phase3-chunking/chunks/analects_test_v2_chunk_240.txt` | " 29. The Master said, "The wise are free from perplexities; the virtuous from anxiety; and the bold from fear. " The Master said, "There are some with whom we may study in common, but we shall find them unable to go along with us to principles. Perhaps we may go on with them to principles, but we shall find |
| `phase3-chunking/chunks/analects_test_v2_chunk_241.txt` | them unable to get established in those along with us. |
| `phase3-chunking/chunks/analects_test_v2_chunk_242.txt` | Or if we may get so established along with them, we shall find them unable to weigh occurring events along with us. " "How the flowers of the aspen-plum flutter and turn! Do I not think of you? But your house is distant. " The Master said, "It is the want of thought about it. How is it distant? " 1. Confucius, |
| `phase3-chunking/chunks/analects_test_v2_chunk_243.txt` | in his village, looked simple and sincere, and as if he were not able to speak. |
| `phase3-chunking/chunks/analects_test_v2_chunk_244.txt` | When he was in the prince's ancestral temple, or in the court, he spoke minutely on every point, but cautiously. When he was waiting at court, in speaking with the great officers of the lower grade, he spoke freely, but in a straightforward manner; in speaking with those of the higher grade, he did so blandly, |
| `phase3-chunking/chunks/analects_test_v2_chunk_245.txt` | X. When the ruler was present, his manner displayed respectful uneasiness; it was grave, but self-possessed. When the prince called him to employ him in the reception of a visitor, his countenance appeared to change, and his legs to move forward with difficulty. He inclined himself to the other officers among |
| `phase3-chunking/chunks/analects_test_v2_chunk_246.txt` | whom he stood, moving his left or right arm, as their position required, but keeping the skirts of his robe before and behind evenly adjusted. |
| `phase3-chunking/chunks/analects_test_v2_chunk_247.txt` | He hastened forward, with his arms like the wings of a bird. When the guest had retired, he would report to the prince, "The visitor is not turning round any more. " 3. When he entered the palace gate, he seemed to bend his body, as if it were not sufficient to admit him. When he was standing, he did not occupy |
| `phase3-chunking/chunks/analects_test_v2_chunk_248.txt` | the middle of the gateway; when he passed in or out, he did not tread upon the threshold. |
| `phase3-chunking/chunks/analects_test_v2_chunk_249.txt` | When he was passing the vacant place of the prince, his countenance appeared to change, and his legs to bend under him, and his words came as if he hardly had breath to utter them. He ascended the reception hall, holding up his robe with both his hands, and his body bent; holding in his breath also, as if he |
| `phase3-chunking/chunks/analects_test_v2_chunk_250.txt` | When he came out from the audience, as soon as he had descended one step, he began to relax his countenance, and had a satisfied look. When he had got the bottom of the steps, he advanced rapidly to his place, with his arms like wings, and on occupying it, his manner still showed respectful uneasiness. When he |
| `phase3-chunking/chunks/analects_test_v2_chunk_251.txt` | was carrying the scepter of his ruler, he seemed to bend his body, as if he were not able to bear its weight. |
| `phase3-chunking/chunks/analects_test_v2_chunk_252.txt` | He did not hold it higher than the position of the hands in making a bow, nor lower than their position in giving anything to another. His countenance seemed to change, and look apprehensive, and he dragged his feet along as if they were held by something to the ground. In presenting the presents with which he |
| `phase3-chunking/chunks/analects_test_v2_chunk_253.txt` | At his private audience, he looked highly pleased. The superior man did not use a deep purple, or a puce color, in the ornaments of his dress. Even in his undress, he did not wear anything of a red or reddish color. In warm weather, he had a single garment either of coarse or fine texture, but he wore it |
| `phase3-chunking/chunks/analects_test_v2_chunk_254.txt` | Over lamb's fur he wore a garment of black; over fawn's fur one of white; and over fox's fur one of yellow. The fur robe of his undress was long, with the right sleeve short. He required his sleeping dress to be half as long again as his body. When staying at home, he used thick furs of the fox or the badger. |
| `phase3-chunking/chunks/analects_test_v2_chunk_255.txt` | When he put off mourning, he wore all the appendages of the girdle. |
| `phase3-chunking/chunks/analects_test_v2_chunk_256.txt` | His undergarment, except when it was required to be of the curtain shape, was made of silk cut narrow above and wide below. He did not wear lamb's fur or a black cap on a visit of condolence. On the first day of the month he put on his court robes, and presented himself at court. When fasting, he thought it |
| `phase3-chunking/chunks/analects_test_v2_chunk_257.txt` | necessary to have his clothes brightly clean and made of linen cloth. |
| `phase3-chunking/chunks/analects_test_v2_chunk_258.txt` | I 6. When fasting, he thought it necessary to change his food, and also to change the place where he commonly sat in the apartment. He did not dislike to have his rice finely cleaned, nor to have his mince meat cut quite small. He did not eat rice which had been injured by heat or damp and turned sour, nor fish |
| `phase3-chunking/chunks/analects_test_v2_chunk_259.txt` | He did not eat what was discolored, or what was of a bad flavor, nor anything which was ill-cooked, or was not in season. He did not eat meat which was not cut properly, nor what was served without its proper sauce. Though there might be a large quantity of meat, he would not allow what he took to exceed the |
| `phase3-chunking/chunks/analects_test_v2_chunk_260.txt` | It was only in wine that he laid down no limit for himself, but he did not allow himself to be confused by it. He did not partake of wine and dried meat bought in the market. He was never without ginger when he When he had been assisting at the prince's sacrifice, he did not keep the flesh which he received |
| `phase3-chunking/chunks/analects_test_v2_chunk_261.txt` | The flesh of his family sacrifice he did not keep over three days. If kept over three days, people could not eat it. ate. He did not eat much. When eating, he did not converse. When in bed, he did not speak. Although his food might be coarse rice and vegetable soup, he would offer a little of it in sacrifice |
| `phase3-chunking/chunks/analects_test_v2_chunk_262.txt` | If his mat was not straight, he did not sit on it. When the villagers were drinking together, upon those who carried staffs going out, he also went out immediately after. When the villagers were going through their ceremonies to drive away pestilential influences, he put on his court robes and stood on the |
| `phase3-chunking/chunks/analects_test_v2_chunk_263.txt` | When he was sending complimentary inquiries to any one in another state, he bowed twice as he escorted the messenger away. 10. Chi K'ang having sent him a present of physic, he bowed and received it, saying, do not know it. I dare not taste it. " "I 11. The stable being burned down, when he was at court, on his |
| `phase3-chunking/chunks/analects_test_v2_chunk_264.txt` | He did not ask about the horses. 12. When the prince presented him with food, he would adjust his mat, first taste it, and then give it away to others. When the prince sent him a gift of undressed meat, he would have it cooked, and offer it to the spirits of his ancestors. When the prince sent alive. him a gift |
| `phase3-chunking/chunks/analects_test_v2_chunk_265.txt` | of a living animal, he would keep it When he was in attendance on the prince and joining in the entertainment, the prince only sacrificed. |
| `phase3-chunking/chunks/analects_test_v2_chunk_266.txt` | He first tasted everything. 13. When he was ill and the prince came to visit him, he had his head to the east, made his court robes be spread over him, and drew his girdle across them. 14. When the prince's order called him, without waiting for his carriage to be yoked, he went at once. 15. When he entered the |
| `phase3-chunking/chunks/analects_test_v2_chunk_267.txt` | ancestral temple of the state, he asked about everything. |
| `phase3-chunking/chunks/analects_test_v2_chunk_268.txt` | 16. When any of his friends died, if he had no relations offices, he would say, "I will bury him. " When a friend sent him a present, though it might be a carriage and horses, he did not bow. The only present for which he bowed was that of the flesh of sacrifice. 17. In bed, he did not lie like a corpse. At |
| `phase3-chunking/chunks/analects_test_v2_chunk_269.txt` | 18. When he saw any one in a mourning dress, though it might be an acquaintance, he would change countenance; when he saw any one wearing the cap of full dress, or a blind person, though he might be in his undress, he would salute him in a ceremonious manner. To any person in mourning he bowed forward to the |
| `phase3-chunking/chunks/analects_test_v2_chunk_270.txt` | crossbar of his carriage, he bowed in the same way to any one bearing the tables of population. |
| `phase3-chunking/chunks/analects_test_v2_chunk_271.txt` | When he was at an entertainment where there was an abundance of provisions set before him, he would change countenance and rise up. On a sudden clap of thunder, or a violent wind, he would change countenance. 19. When he was about to mount his carriage, he would stand straight, holding the cord. When he was in |
| `phase3-chunking/chunks/analects_test_v2_chunk_272.txt` | the carriage, he did not turn his head quite round, he did not talk hastily, he did not point with his hands. |
| `phase3-chunking/chunks/analects_test_v2_chunk_273.txt` | 20. Seeing the group approaching, the bird instantly rises. It flies around, and by and by settles. pheasant on the hill bridge. It knows how to preserve itself! " Tsze-lu made a motion to catch it. Thrice it cried and then flew away. The Master said, "The men of former times in the matters of ceremonies and |
| `phase3-chunking/chunks/analects_test_v2_chunk_274.txt` | music were rustics, it is said, while the men of these latter times, in ceremonies and music, are accomplished gentlemen. |
| `phase3-chunking/chunks/analects_test_v2_chunk_275.txt` | "If I have occasion to use those things, I follow the men of former times. " The Master said, "Of those who were with me in Ch'an and Ts'ai, there are none to be found to enter my door. " Distinguished for their virtuous principles and practice, there were Yen Yuan, Min Tsze-ch'ien, Zan Po-niu, and Chung-kung; |
| `phase3-chunking/chunks/analects_test_v2_chunk_276.txt` | for their ability in speech, Tsai Wo and Tsze kung; for their administrative talents, Zan Yu and Chi Lu; for their literary acquirements, Tsze-yu and Tsze-hsia. |
| `phase3-chunking/chunks/analects_test_v2_chunk_277.txt` | The Master said, "Hui gives me no assistance. There is nothing that I say in which he does not delight. " The Master said, "Filial indeed is Min Tsze-ch'ien! Other people say nothing of him different from the report of his parents and brothers. " Nan Yung was frequently repeating the lines about a white scepter |
| `phase3-chunking/chunks/analects_test_v2_chunk_278.txt` | Confucius gave him the daughter of his elder brother to wife. Chi K'ang asked which of the disciples loved to learn. Confucius replied to him, "There was Yen Hui; he loved to learn. Unfortunately his appointed time was short, and he died. Now there is no one who loves to learn, as he did. " When Yen Yuan died, |
| `phase3-chunking/chunks/analects_test_v2_chunk_279.txt` | Yen Lu begged the carriage of the Master to sell and get an outer shell for his son's coffin. |
| `phase3-chunking/chunks/analects_test_v2_chunk_280.txt` | The Master said, "Every one calls his son his son, whether he has talents or has not talents. There was Li; when he died, he had a coffin but no outer shell. I would not walk on foot to get a shell for him, because, having followed in the rear of the great officers, it was not proper that I should walk on foot. |
| `phase3-chunking/chunks/analects_test_v2_chunk_281.txt` | Heaven is destroying me! Heaven is destroying me! " When Yen Yuan died, the Master bewailed him exceedingly, and the disciples who were with him said, "Master, your grief is excessive! " "Is it excessive? " said he. "If I am not to mourn bitterly for this man, for whom should I mourn? " 11. When Yen Yuan died, |
| `phase3-chunking/chunks/analects_test_v2_chunk_282.txt` | the disciples wished to give him a great funeral, and the Master said, "You may not do so. |
| `phase3-chunking/chunks/analects_test_v2_chunk_283.txt` | " The disciples did bury him in great style. The Master said, "Hui behaved towards me as his father. I have not been able to treat him as my son. The fault is not mine; it belongs to you, O disciples. " 12. Chi Lu asked about serving the spirits of the dead. The Master said, "While you are not able to serve |
| `phase3-chunking/chunks/analects_test_v2_chunk_284.txt` | Chi Lu added, "I venture to ask about death? " He was answered, "While you do not know life, how can you know about death? " 13. The disciple Min was standing by his side, looking bland and precise; Tsze-lu, looking bold and soldierly; Zan Yu and Tsze-kung, with a free and straightforward manner. The Master was |
| `phase3-chunking/chunks/analects_test_v2_chunk_285.txt` | He said, "Yu, there! -he will not die a natural death. " 14. Some parties in Lu were going to take down and rebuild the Long Treasury. Min Tsze-ch'ien said, "Suppose it were to be repaired after its old style; -why must it be altered and made anew? " The Master said, "This man seldom speaks; when he does, he is |
| `phase3-chunking/chunks/analects_test_v2_chunk_286.txt` | " 15. The Master said, "What has the lute of Yu to do in my door? " The other disciples began not to respect Tszelu. The Master said, "Yu has ascended to the hall, though he has not yet passed into the inner apartments. " 16. Tsze-kung asked which of the two, Shih or Shang, was the superior. The Master said, |
| `phase3-chunking/chunks/analects_test_v2_chunk_287.txt` | "Shih goes beyond the due mean, and Shang does not come up to it. |
| `phase3-chunking/chunks/analects_test_v2_chunk_288.txt` | " "Then, " said Tsze-kung, "the superiority is with Shih, I suppose. " The Master said, "To go beyond is as wrong as to fall short. " 17. The head of the Chi family was richer than the duke of Chau had been, and yet Ch'iu collected his imposts for him, and increased his wealth. The Master said, "He is no |
| `phase3-chunking/chunks/analects_test_v2_chunk_289.txt` | My little children, beat the drum and assail him. " 18. Ch'ai is simple. Shan is dull. Shih is specious. Yu is coarse. The Master said, "There is Hui! He has nearly attained to perfect virtue. He is often in want. "Ts'ze does not acquiesce in the appointments of Heaven, and his goods are increased by him. Yet |
| `phase3-chunking/chunks/analects_test_v2_chunk_290.txt` | " 19. Tsze-chang asked what were the characteristics of the good man. The Master said, "He does not tread in the footsteps of others, but moreover, he does not enter thechamber of the sage. " The Master said, "If, because a man's discourse appears solid and sincere, we allow him to be a good man, is he really a |
| `phase3-chunking/chunks/analects_test_v2_chunk_291.txt` | or is his gravity only in appearance? " 20. Tsze-lu asked whether he should immediately carry into practice what he heard. The Master said, "There are your father and elder brothers to be consulted; -why should you act on that principle of immediately carrying into practice what you hear? " Zan Yu asked the |
| `phase3-chunking/chunks/analects_test_v2_chunk_292.txt` | same, whether he should immediately carry into practice what he heard, and the Master answered, "Immediately carry into practice what you hear. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_293.txt` | Kung hsi Hwa said, "Yu asked whether he should carry immediately into practice what he heard, and you said, 'There are your father and elder brothers to be consulted. ' Ch'iu asked whether he should immediately carry into practice what he heard, and you said, 'Carry it immediately into practice. ' I, Ch'ih, am |
| `phase3-chunking/chunks/analects_test_v2_chunk_294.txt` | perplexed, and venture to ask you for an explanation. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_295.txt` | The Master said, "Ch'iu is retiring and slow; therefore I urged him forward. Yu has more than his own share of energy; therefore I kept him back. " The Master was put in fear in K'wang and Yen Yuan fell behind. The Master, on his rejoining him, said, "I thought you had died. " Hui replied, "While you were |
| `phase3-chunking/chunks/analects_test_v2_chunk_296.txt` | " Chi Tsze-zan asked whether Chung Yu and Zan Ch'iu could be called great ministers. The Master said, "I thought you would ask about some extraordinary individuals, and you only ask about Yu and Ch'iu! "What is called a great minister, is one who serves his prince according to what is right, and when he finds |
| `phase3-chunking/chunks/analects_test_v2_chunk_297.txt` | "Now, as to Yu and Ch'iu, they may be called ordinary ministers. " Tsze-zan said, "Then they will always follow their chief; -win they? " The Master said, "In an act of parricide or regicide, they would not follow him. " Tsze-lu got Tsze-kao appointed governor of Pi. The Master said. "You are injuring a man's |
| `phase3-chunking/chunks/analects_test_v2_chunk_298.txt` | " Tsze-lu said, "There are, there, common people and officers; there are the altars of the spirits of the land and grain. Why must one read books before he can be considered to have learned? " The Master said, "It is on this account that I hate your glib-tongued people. " Tsze-lu, Tsang Hsi, Zan Yu, and Kunghsi |
| `phase3-chunking/chunks/analects_test_v2_chunk_299.txt` | He said to them, "Though I am a day or so older than you, do not think of that. "From day to day you are saying, 'We are not known. ' If some ruler were to know you, what would you like to do? " Tsze-lu hastily and lightly replied, "Suppose the case of a state of ten thousand chariots; let it be straitened |
| `phase3-chunking/chunks/analects_test_v2_chunk_300.txt` | between other large cities; let it be suffering from invading armies; and to this let there be added a famine in corn and in all vegetables: -if |
| `phase3-chunking/chunks/analects_test_v2_chunk_301.txt` | I were intrusted with the government of it, in three years' time I could make the people to be bold, and to recognize the rules of righteous conduct. " The Master smiled at him. Turning to Yen Yu, he said, "Ch'iu, what are your wishes? " Ch'iu replied, "Suppose a state of sixty or seventy li square, or one of |
| `phase3-chunking/chunks/analects_test_v2_chunk_302.txt` | fifty or sixty, and let me have the government of it; -in three years' time, I could make plenty to abound among the people. |
| `phase3-chunking/chunks/analects_test_v2_chunk_303.txt` | As to teaching them the principles of propriety, and music, I must wait for the rise of a superior man to do that. " "What are your wishes, Ch'ih, " said the Master next to Kung-hsi Hwa. Ch'ih replied, "I do not say that my ability extends to these things, but I should wish to learn them. At the services of the |
| `phase3-chunking/chunks/analects_test_v2_chunk_304.txt` | ancestral temple, and at the audiences of the princes with the sovereign, I should like, dressed in the dark square-made robe and the black linen cap, to act as a small assistant. |
| `phase3-chunking/chunks/analects_test_v2_chunk_305.txt` | " Last of all, the Master asked Tsang Hsi, "Tien, what are your wishes? " Tien, pausing as he was playing on his lute, while it was yet twanging, laid the instrument aside, and "My wishes, " he said, "are different from the cherished purposes of these three gentlemen. " "What harm is there in that? " said the |
| `phase3-chunking/chunks/analects_test_v2_chunk_306.txt` | Master; "do you also, as well as they, speak out your wishes. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_307.txt` | Tien then said, "In this, the last month of spring, with the dress of the season all complete, along with five or six young men who have assumed the cap, and six or seven boys, I would wash in the I, enjoy the breeze among the rain altars, and return home singing. " The Master heaved a sigh and said, "I give my |
| `phase3-chunking/chunks/analects_test_v2_chunk_308.txt` | " The three others having gone out, Tsang Hsi remained behind, and said, "What do you think of the words of these three friends? " The Master replied, "They simply told each one his wishes. " Hsi pursued, "Master, why did you smile at Yu? " He was answered, "The management of a state demands the rules of |
| `phase3-chunking/chunks/analects_test_v2_chunk_309.txt` | His words were not humble; therefore I smiled at him. " Hsi again said, "But was it not a state which Ch'iu proposed for himself? " The reply was, "Yes; did you ever see a territory of sixty or seventy li or one of fifty or sixty, which was not a state? " Once more, Hsi inquired, "And was it not a state which |
| `phase3-chunking/chunks/analects_test_v2_chunk_310.txt` | " The Master again replied, "Yes; who but princes have to do with ancestral temples, and with audiences but the sovereign? If Ch'ih were to be a small assistant in these services, who could be a great one? Yen Yuan asked about perfect virtue. The Master said, "To subdue one's self and return to propriety, is |
| `phase3-chunking/chunks/analects_test_v2_chunk_311.txt` | If a man can for one day subdue himself and return to propriety, an under heaven will ascribe perfect virtue to him. Is the practice of perfect virtue from a man himself, or is it from others? " Yen Yuan said, "I beg to ask the steps of that process. " The Master replied, "Look not at what is contrary to |
| `phase3-chunking/chunks/analects_test_v2_chunk_312.txt` | propriety; listen not to what is contrary to propriety; speak not what is contrary to propriety; make no movement which is contrary to propriety. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_313.txt` | Yen Yuan then said, "Though I am deficient in intelligence and vigor, I will make it my business to practice this lesson. " Chung-kung asked about perfect virtue. The Master said, "It is, when you go abroad, to behave to every one as if you were receiving a great guest; to employ the people as if you were |
| `phase3-chunking/chunks/analects_test_v2_chunk_314.txt` | assisting at a great sacrifice; not to do to others as you would not wish done to yourself; to have no murmuring against you in the country, and none in the family. |
| `phase3-chunking/chunks/analects_test_v2_chunk_315.txt` | " Chung-kung said, "Though I am deficient in intelligence and vigor, I will make it my business to practice this lesson. " Sze-ma Niu asked about perfect virtue. 3 The Master said, "The man of perfect virtue is cautious and slow in his speech. " "Cautious and slow in his speech! " said Niu; --"is this what is |
| `phase3-chunking/chunks/analects_test_v2_chunk_316.txt` | " The Master said, "When a man feels the difficulty of doing, can he be other than cautious and slow in speaking? " Sze-ma Niu asked about the superior man. The Master said, "The superior man has neither anxiety nor fear. " "Being without anxiety or fear! " said Nui; "does this constitute what we call the |
| `phase3-chunking/chunks/analects_test_v2_chunk_317.txt` | " The Master said, "When internal examination discovers nothing wrong, what is there to be anxious about, what is there to fear? " Sze-ma Niu, full of anxiety, said, "Other men all have their brothers, I only have5 not. " Tsze-hsia said to him, "There is the following saying which I have heard: 'Death and life |
| `phase3-chunking/chunks/analects_test_v2_chunk_318.txt` | have their determined appointment; riches and honors depend upon Heaven. |
| `phase3-chunking/chunks/analects_test_v2_chunk_319.txt` | ' "Let the superior man never fail reverentially to order his own conduct, and let him be respectful to others and observant of propriety: -then all within the four seas will be his brothers. What has the superior man to do with being distressed because he has no brothers? " 6. Tsze-chang asked what constituted |
| `phase3-chunking/chunks/analects_test_v2_chunk_320.txt` | The Master said, "He with whom neither slander that gradually soaks into the mind, nor statements that startle like a wound in the flesh, are successful may be called intelligent indeed. Yea, he with whom neither soaking slander, nor startling statements, are successful, may be called farseeing. " 7. Tsze-kung |
| `phase3-chunking/chunks/analects_test_v2_chunk_321.txt` | The Master said, "The requisites of government are that there be sufficiency of food, sufficiency of military equipment, and the confidence of the people in their ruler. " Tsze-kung said, "If it cannot be helped, and one of these must be dispensed with, which of the three should be foregone first? " "The |
| `phase3-chunking/chunks/analects_test_v2_chunk_322.txt` | Tsze-kung again asked, "If it cannot be helped, and one of the remaining two must be dispensed with, which of them should be foregone? " The Master answered, "Part with the food. From of old, death has been the lot of an men; but if the people have no faith in their rulers, there is no standing for the state. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_323.txt` | Chi Tsze-ch'ang said, "In a superior man it is only the substantial qualities which are wanted; -why should we seek for ornamental accomplishments? " Tsze-kung said, "Alas! Your words, sir, show you to be a superior man, but four horses cannot overtake the tongue. Ornament is as substance; substance is as |
| `phase3-chunking/chunks/analects_test_v2_chunk_324.txt` | The hide of a tiger or a leopard stripped of its hair, is like the hide of a dog or a goat stripped of its hair. " 9. The Duke Ai inquired of Yu Zo, saying, "The year is one of scarcity, and the returns for expenditure are not sufficient; -what is to be done? " Yu Zo replied to him, "Why not simply tithe the |
| `phase3-chunking/chunks/analects_test_v2_chunk_325.txt` | " "With two tenths, said the duke, "I find it not enough; -how could I do with that system of one tenth? " Yu Zo answered, "If the people have plenty, their prince will not be left to want alone. If the people are in want, their prince cannot enjoy plenty alone. " 10. Tsze-chang having asked how virtue was to |
| `phase3-chunking/chunks/analects_test_v2_chunk_326.txt` | be exalted, and delusions to be discovered, the Master said, "Hold faithfulness and sincerity as first principles, and be moving continually to what is right, this is the way to exalt one's virtue. |
| `phase3-chunking/chunks/analects_test_v2_chunk_327.txt` | "You love a man and wish him to live; you hate him and wish him to die. Having wished him to live, you also wish him to die. This is a case of delusion. 'It may not be on account of her being rich, yet you come to make a difference. "" 11. The Duke Ching, of Ch'i, asked Confucius about government. Confucius |
| `phase3-chunking/chunks/analects_test_v2_chunk_328.txt` | replied, "There is government, when the prince is prince, and the minister is minister; when the father is father, and the son is son. |
| `phase3-chunking/chunks/analects_test_v2_chunk_329.txt` | " "Good! " said the duke; "if, indeed, the prince be not prince, the not minister, the father not father, and the son not son, although I have my revenue, can I enjoy it? " 12. The Master said, "Ah! it is Yu, who could with half a word settle litigations! " Tsze-lu never slept over a promise. The Master said, |
| `phase3-chunking/chunks/analects_test_v2_chunk_330.txt` | "In hearing litigations, I am like any other body. |
| `phase3-chunking/chunks/analects_test_v2_chunk_331.txt` | What is necessary, however, is to cause the people to have no litigations. " Tsze-chang asked about government. The Master said, "The art of governing is to keep its affairs before the mind without weariness, and to practice them with undeviating consistency. " The Master said, "By extensively studying all |
| `phase3-chunking/chunks/analects_test_v2_chunk_332.txt` | learning, and keeping himself under the restraint of the rules of propriety, one may thus likewise not err from what is right. |
| `phase3-chunking/chunks/analects_test_v2_chunk_333.txt` | " The Master said, "The superior man seeks to perfect the admirable qualities of men, and does not seek to perfect their bad qualities. The mean man does the opposite of this. " Chi K'ang asked Confucius about government. Confucius replied, "To govern means to rectify. If you lead on the people with |
| `phase3-chunking/chunks/analects_test_v2_chunk_334.txt` | " Chi K'ang, distressed about the number of thieves in the state, inquired of Confucius how to do away with them. Confucius said, "If you, sir, were not covetous, although you should reward them to do it, they would not steal. " Chi K'ang asked Confucius about government, saying, "What do you say to killing the |
| `phase3-chunking/chunks/analects_test_v2_chunk_335.txt` | Confucius replied, "Sir, in carrying on your government, why should you use killing at all? Let your evinced desires be for what is good, and the people will be good. The relation between superiors and inferiors is like that between the wind and the grass. The grass must bend, when the wind blows across it. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_336.txt` | Tsze-chang asked, "What must the officer be, who may be said to be distinguished? |
| `phase3-chunking/chunks/analects_test_v2_chunk_337.txt` | " The Master said, "What is it you call being distinguished? " Tsze-chang replied, "It is to be heard of through the state, to be heard of throughout his clan. " The Master said, "That is notoriety, not distinction. "Now the man of distinction is solid and straightforward, and loves righteousness. He examines |
| `phase3-chunking/chunks/analects_test_v2_chunk_338.txt` | He is anxious to humble himself to others. Such a man will be distinguished in the country; he will be distinguished in his clan. "As to the man of notoriety, he assumes the appearance of virtue, but his actions are opposed to it, and he rests in this character without any doubts about himself. Such a man will |
| `phase3-chunking/chunks/analects_test_v2_chunk_339.txt` | be heard of in the country; he will be heard of in the clan. |
| `phase3-chunking/chunks/analects_test_v2_chunk_340.txt` | " Fan Ch'ih rambling with the Master under the trees about the rain altars, said, "I venture to ask how to exalt virtue, to correct cherished evil, and to discover delusions. " The Master said, "Truly a good question! "If doing what is to be done be made the first business, and success a secondary |
| `phase3-chunking/chunks/analects_test_v2_chunk_341.txt` | consideration: -is not this the way to exalt virtue? |
| `phase3-chunking/chunks/analects_test_v2_chunk_342.txt` | To assail one's own wickedness and not assail that of others; -is not this the way to correct cherished evil? For a morning's anger to disregard one's own life, and involve that of his parents; -is not this a case of delusion? " Fan Ch'ih asked about benevolence. The Master said, "It is to love all men. " He |
| `phase3-chunking/chunks/analects_test_v2_chunk_343.txt` | The Master said, "It is to know all men. " Fan Ch'ih did not immediately understand these answers. The Master said, "Employ the upright and put aside all the crooked; in this way the crooked can be made to be upright. " Fan Ch'ih retired, and, seeing Tsze-hsia, he said to him, "A Little while ago, I had an |
| `phase3-chunking/chunks/analects_test_v2_chunk_344.txt` | interview with our Master, and asked him about knowledge. |
| `phase3-chunking/chunks/analects_test_v2_chunk_345.txt` | He said, 'Employ the upright, and put aside all the crooked; -in this way, the crooked will be made to be upright. ' What did he mean? " Tsze-hsia said, "Truly rich is his saying! "Shun, being in possession of the kingdom, selected from among all the people, and employed Kai-yao-on which all who were devoid of |
| `phase3-chunking/chunks/analects_test_v2_chunk_346.txt` | T'ang, being in possession of the kingdom, selected from among all the people, and employed I Yin and any who were devoid of virtue disappeared. " 23. Tsze-kung asked about friendship. The Master said, "Faithfully admonish your friend, and skillfully lead him on. If you find him impracticable, stop. Do not |
| `phase3-chunking/chunks/analects_test_v2_chunk_347.txt` | " The philosopher Tsang said, "The superior man on grounds of culture meets with his friends, and by friendship helps his virtue. " 1. Tsze-lu asked about government. The Master said, "Go before the people with your example, and be laborious in their affairs. " He requested further instruction, and was |
| `phase3-chunking/chunks/analects_test_v2_chunk_348.txt` | " Chung-kung, being chief minister to the head of the Chi family, asked about government. The Master said, "Employ first the services of your various officers, pardon small faults, and raise to office men of virtue and talents. " Chung-kung said, "How shall I know the men of virtue and talent, so that I may |
| `phase3-chunking/chunks/analects_test_v2_chunk_349.txt` | He was answered, "Raise to office those whom you know. As to those whom you do not know, will others neglect them? " Tsze-lu said, "The ruler of Wei has been waiting for you, in order with you to administer the government. What will you consider the first thing to be done? " The Master replied, "What is |
| `phase3-chunking/chunks/analects_test_v2_chunk_350.txt` | " "So! indeed! " said Tsze-lu. "You are wide of the mark! Why must there be such rectification? " The Master said, "How uncultivated you are, Yu! A superior man, in regard to what he does not know, shows a cautious reserve. "If names be not correct, language is not in accordance with the truth of things. If |
| `phase3-chunking/chunks/analects_test_v2_chunk_351.txt` | language be not in accordance with the truth of things, affairs cannot be carried on to success. |
| `phase3-chunking/chunks/analects_test_v2_chunk_352.txt` | "When affairs cannot be carried on to success, proprieties and music do not flourish. When proprieties and music do not flourish, punishments will not be properly awarded. When punishments are not properly awarded, the people do not know how to move hand or foot. "Therefore a superior man considers it necessary |
| `phase3-chunking/chunks/analects_test_v2_chunk_353.txt` | that the names he uses may be spoken appropriately, and also that what he speaks may be carried out appropriately. |
| `phase3-chunking/chunks/analects_test_v2_chunk_354.txt` | What the superior man requires is just that in his words there may be nothing incorrect. " 4. Fan Ch'ih requested to be taught husbandry. The Master said, "I am not so good for that as an old husbandman. " He requested also to be taught gardening, and was answered, "I am not so good for that as an old gardener. |
| `phase3-chunking/chunks/analects_test_v2_chunk_355.txt` | " Fan Ch'ih having gone out, the Master said, "A small man, indeed, is Fan Hsu! |
| `phase3-chunking/chunks/analects_test_v2_chunk_356.txt` | If a superior man love propriety, the people will not dare not to be reverent. If he love righteousness, the people will not dare not to submit to his example. If he love good faith, the people will not dare not to be sincere. Now, when these things obtain, the people from all quarters will come to him, bearing |
| `phase3-chunking/chunks/analects_test_v2_chunk_357.txt` | their children on their backs; what need has he of a knowledge of husbandry? |
| `phase3-chunking/chunks/analects_test_v2_chunk_358.txt` | " 5. The Master said, "Though a man may be able to recite the three hundred odes, yet if, when intrusted with a governmental charge, he knows not how to act, or if, when sent to any quarter on a mission, he cannot give his replies unassisted, notwithstanding the extent of his learning, of what practical use is |
| `phase3-chunking/chunks/analects_test_v2_chunk_359.txt` | " 6. The Master said, "When a prince's personal conduct is correct, his government is effective without the issuing of orders. If his personal conduct is not correct, he may issue orders, but they will not be followed. " 7. The Master said, "The governments of Lu and Wei are brothers. " 8. The Master said of |
| `phase3-chunking/chunks/analects_test_v2_chunk_360.txt` | Ching, a scion of the ducal family of Wei, that he knew the economy of a family well. |
| `phase3-chunking/chunks/analects_test_v2_chunk_361.txt` | When he began to have means, he said, "Ha! here is a collection! " When they were a little increased, he said, "Ha! this is complete! " When he had become rich, he said, "Ha! this is admirable! " 9. When the Master went to Weil Zan Yu acted as driver of his carriage. The Master observed, "How numerous are the |
| `phase3-chunking/chunks/analects_test_v2_chunk_362.txt` | " Yu said, "Since they are thus numerous, what more shall be done for them? " "Enrich them, was the reply. "And when they have been enriched, what more shall be done? " The Master said, "Teach them. " 10. The Master said, "If there were any of the princes who would employ me, in the course of twelve months, I |
| `phase3-chunking/chunks/analects_test_v2_chunk_363.txt` | In three years, the government would be perfected. " 11. The Master said, "If good men were to govern a country in succession for a hundred years, they would be able to transform the violently bad, and dispense with capital punishments. ' True indeed is this saying! " 12. The Master said, "If a truly royal |
| `phase3-chunking/chunks/analects_test_v2_chunk_364.txt` | ruler were to arise, it would stir require a generation, and then virtue would prevail. |
| `phase3-chunking/chunks/analects_test_v2_chunk_365.txt` | " 13. The Master said, "If a minister make his own conduct correct, what difficulty will he have in assisting in government? If he cannot rectify himself, what has he to do with rectifying others? " The disciple Zan returning from the court, the Master said to him, "How are you so late? " He replied, "We had |
| `phase3-chunking/chunks/analects_test_v2_chunk_366.txt` | The Master said, "It must have been family affairs. If there had been government business, though I am not now in office, I should have been consulted about it. " The Duke Ting asked whether there was a single sentence which could make a country prosperous. Confucius replied, "Such an effect cannot be expected |
| `phase3-chunking/chunks/analects_test_v2_chunk_367.txt` | "There is a saying, however, which people have: 'To be a prince is difficult; to be a minister is not easy. " "If a ruler knows this, the difficulty of being a prince, may there not be expected from this one sentence the prosperity of his country? " The duke then said. "Is there a single sentence which can ruin |
| `phase3-chunking/chunks/analects_test_v2_chunk_368.txt` | Confucius replied, "Such an effect as that cannot be expected from one sentence. There is, however, the saying which people have: 'I have no pleasure in being a prince, but only in that no one can offer any opposition to what I say! ' "If a ruler's words be good, is it not also good that no one oppose them? But |
| `phase3-chunking/chunks/analects_test_v2_chunk_369.txt` | if they are not good, and no one opposes them, may there not be expected from this one sentence the ruin of his country? |
| `phase3-chunking/chunks/analects_test_v2_chunk_370.txt` | " The Duke of Sheh asked about government. The Master said, "Good government obtains when those who are near are made happy, and those who are far off are attracted. " Tsze-hsia! being governor of Chu-fu, asked about government. The Master said, "Do not be desirous to have things done quickly; do not look at |
| `phase3-chunking/chunks/analects_test_v2_chunk_371.txt` | Desire to have things done quickly prevents their being done thoroughly. Looking at small advantages prevents great affairs from being accomplished. " The Duke of Sheh informed Confucius, saying, "Among us here there are those who may be styled upright in their conduct. If their father have stolen a sheep, they |
| `phase3-chunking/chunks/analects_test_v2_chunk_372.txt` | " Confucius said, "Among us, in our part of the country, those who are upright are different from this. The father conceals the misconduct of the son, and the son conceals the misconduct of the father. Uprightness is to be found in this. " Fan Ch'ih asked about perfect virtue. The Master said, "It is, in |
| `phase3-chunking/chunks/analects_test_v2_chunk_373.txt` | retirement, to be sedately grave; in the management of business, to be reverently attentive; in intercourse with others, to be strictly sincere. |
| `phase3-chunking/chunks/analects_test_v2_chunk_374.txt` | Though a man go among rude, uncultivated tribes, these qualities may not be neglected. " Tsze-kung asked, saying, "What qualities must a man possess to entitle him to be called an officer? The Master said, "He who in his conduct of himself maintains a sense of shame, and when sent to any quarter will not |
| `phase3-chunking/chunks/analects_test_v2_chunk_375.txt` | disgrace his prince's commission, deserves to be called an officer. |
| `phase3-chunking/chunks/analects_test_v2_chunk_376.txt` | " Tsze-kung pursued, "I venture to ask who may be placed in the next lower rank? " And he was told, "He whom the circle of his relatives pronounce to be filial, whom his fellow villagers and neighbors pronounce to be fraternal. " Again the disciple asked, "I venture to ask about the class still next in order. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_377.txt` | The Master said, "They are determined to be sincere in what they say, and to carry out what they do. |
| `phase3-chunking/chunks/analects_test_v2_chunk_378.txt` | They are obstinate little men. Yet perhaps they may make the next class. " Tsze-kung finally inquired, "Of what sort are those of the present day, who engage in government? " The Master said "Pooh! they are so many pecks and hampers, not worth being taken into account. " The Master said, "Since I cannot get men |
| `phase3-chunking/chunks/analects_test_v2_chunk_379.txt` | pursuing the due medium, to whom I might communicate my instructions, I must find the ardent and the cautiously-decided. |
| `phase3-chunking/chunks/analects_test_v2_chunk_380.txt` | The ardent will advance and lay hold of truth; the cautiously-decided will keep themselves from what is wrong. " The Master said, "The people of the south have a saying: 'A man without constancy cannot be either a wizard or a doctor. ' Good! "Inconstant in his virtue, he will be visited with disgrace. " The |
| `phase3-chunking/chunks/analects_test_v2_chunk_381.txt` | Master said, "This arises simply from not attending to the prognostication. |
| `phase3-chunking/chunks/analects_test_v2_chunk_382.txt` | " 23. The Master said, "The superior man is affable, but not adulatory; the mean man is adulatory, but not affable. " 24, Tsze-kung asked, saying, "What do you say of a man who is loved by all the people of his neighborhood? " The Master replied, "We may not for that accord our approval of him. " "And what do |
| `phase3-chunking/chunks/analects_test_v2_chunk_383.txt` | you say of him who is hated by all the people of his neighborhood? |
| `phase3-chunking/chunks/analects_test_v2_chunk_384.txt` | " The Master said, "We may not for that conclude that he is bad. It is better than either of these cases that the good in the neighborhood love him, and the bad hate him. " The Master said, "The superior man is easy to serve and difficult to please. If you try to please him in any way which is not accordant |
| `phase3-chunking/chunks/analects_test_v2_chunk_385.txt` | But in his employment of men, he uses them according to their capacity. The mean man is difficult to serve, and easy to please. If you try to please him, though it be in a way which is not accordant with right, he may be pleased. But in his employment of men, he wishes them to be equal to everything. " The |
| `phase3-chunking/chunks/analects_test_v2_chunk_386.txt` | Master said, "The superior man has a dignified ease without pride. |
| `phase3-chunking/chunks/analects_test_v2_chunk_387.txt` | The mean man has pride without a dignified ease. " 27. The Master said, "The firm, the enduring, the simple, and the modest are near to virtue. " 28. Tsze-lu asked, saying, "What qualities must a man possess to entitle him to be called a scholar? " The Master said, "He must be thus: earnest, urgent, and bland |
| `phase3-chunking/chunks/analects_test_v2_chunk_388.txt` | among his friends: earnest and urgent; among his brethren: bland. |
| `phase3-chunking/chunks/analects_test_v2_chunk_389.txt` | " The Master said, "Let a good man teach the people seven years, and they may then likewise be employed in war. " The Master said. "To lead an uninstructed people to war, is to throw them away. " Hsien asked what was shameful. The Master said, "When good government prevails in a state, to be thinking only of |
| `phase3-chunking/chunks/analects_test_v2_chunk_390.txt` | salary; and, when bad government prevails, to be thinking, in the same way, only of salary; -this is shameful. |
| `phase3-chunking/chunks/analects_test_v2_chunk_391.txt` | " "When the love of superiority, boasting, resentments, and covetousness are repressed, this may be deemed perfect virtue. " The Master said. "This may be regarded as the achievement of what is difficult. But I do not know that it is to be deemed perfect virtue. " The Master said, "The scholar who cherishes the |
| `phase3-chunking/chunks/analects_test_v2_chunk_392.txt` | love of comfort is not fit to be deemed a scholar. |
| `phase3-chunking/chunks/analects_test_v2_chunk_393.txt` | " The Master said. "When good government prevails in a state, language may be lofty and bold, and actions the same. When bad government prevails, the actions may be lofty and bold, but the language may be with some reserve. " The Master said, "The virtuous will be sure to speak correctly, but those whose speech |
| `phase3-chunking/chunks/analects_test_v2_chunk_394.txt` | Men of principle are sure to be bold, but those who are bold may not always be men of principle. " 5. Nan-kung Kwo, submitting an inquiry to Confucius, said, "I was skillful at archery, and Ao could move a boat along upon the land, but neither of them died a natural death. and they became possessors ofYu and |
| `phase3-chunking/chunks/analects_test_v2_chunk_395.txt` | Chi personally wrought at the toils of husba the kingdom. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_396.txt` | The Master made no reply; but when Nan-kung Kwo went out, he said, "A superior man indeed is this! An esteemer of virtue indeed is this! " The Master said, "Superior men, and yet not always virtuous, there have been, alas! But there never has been a mean man, and, at the same time, virtuous. " The Master said, |
| `phase3-chunking/chunks/analects_test_v2_chunk_397.txt` | "Can there be love which does not lead to strictness with its object? |
| `phase3-chunking/chunks/analects_test_v2_chunk_398.txt` | Can there be loyalty which does not lead to the instruction of its object? " 8. The Master said, "In preparing the governmental notifications, P'i Shan first made the rough draft; Shi-shu examined and discussed its contents; Tsze-yu, the manager of foreign intercourse, then polished the style; and, finally, |
| `phase3-chunking/chunks/analects_test_v2_chunk_399.txt` | Tsze-ch'an of Tung-li gave it the proper elegance and finish. |
| `phase3-chunking/chunks/analects_test_v2_chunk_400.txt` | " Some one asked about Tsze-ch'an. The Master said, "He was a kind man. " He asked about Tsze-hsi. The Master said, "That man! That man! " He asked about Kwan Chung. "For him, " said the Master, "the city of Pien, with three hundred families, was taken from the chief of the Po family, who did not utter a |
| `phase3-chunking/chunks/analects_test_v2_chunk_401.txt` | murmuring word, though, to the end of his life, he had only coarse rice to eat. |
| `phase3-chunking/chunks/analects_test_v2_chunk_402.txt` | " 10. The Master said, "To be poor without murmuring is difficult. To be rich without being proud is easy. " 11. The Master said, "Mang Kung-ch'o is more than fit to be chief officer in the families of Chao and Wei, but he is not fit to be great officer to either of the states Tang or Hsieh. " 12. Tsze-lu asked |
| `phase3-chunking/chunks/analects_test_v2_chunk_403.txt` | The Master said, "Suppose a man with the knowledge of Tsang Wu-chung, the freedom from covetousness of Kung ch'o, the bravery of Chwang of Pien, and the varied talents of Zan Ch'iu; add to these the accomplishments of the rules of propriety and music; -such a one might be reckoned a COMPLETE man. " He then |
| `phase3-chunking/chunks/analects_test_v2_chunk_404.txt` | added, "But what is the necessity for a complete man of the present day to have all these things? |
| `phase3-chunking/chunks/analects_test_v2_chunk_405.txt` | The man, who in the view of gain, thinks of righteousness; who in the view of danger is prepared to give up his life; and who does not forget an old agreement however far back it extends: -such a man may be reckoned a COMPLETE man. " 13. The Master asked Kung-ming Chia about Kung-shu Wan, saying, "Is it true |
| `phase3-chunking/chunks/analects_test_v2_chunk_406.txt` | that your master speaks not, laughs not, and takes not? |
| `phase3-chunking/chunks/analects_test_v2_chunk_407.txt` | " Kung-ming Chia replied, "This has arisen from the reporters going beyond the truth. My master speaks when it is the time to speak, and so men do not get tired of his speaking. He laughs when there is occasion to be joyful, and so men do not get tired of his laughing. He takes when it is consistent with |
| `phase3-chunking/chunks/analects_test_v2_chunk_408.txt` | righteousness to do so, and so men do not get tired of his taking. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_409.txt` | The Master said, "So! But is it so with him? " The Master said, "Tsang Wu-chung, keeping possession of Fang, asked of the duke of Lu to appoint a successor to him in his family. Although it may be said that he was not using force with his sovereign, I believe he was. " 15. The Master said, "The duke Wan of Tsin |
| `phase3-chunking/chunks/analects_test_v2_chunk_410.txt` | The duke Hwan of Ch'i was upright and not crafty. " 16. Tsze-lu said, "The Duke Hwan caused his brother Chiu to be killed, when Shao Hu died, with his master, but Kwan Chung did not die. May not I say that he was wanting in virtue? " The Master said, "The Duke Hwan assembled all the princes together, and that |
| `phase3-chunking/chunks/analects_test_v2_chunk_411.txt` | not with weapons of war and chariots: -it was all through the influence of Kwan Chung. |
| `phase3-chunking/chunks/analects_test_v2_chunk_412.txt` | Whose beneficence was like his? Whose beneficence was like his? " Tsze-kung said, "Kwan Chung, I apprehend was wanting in virtue. When the Duke Hwan caused his brother Chiu to be killed, Kwan Chung was not able to die with him. Moreover, he became prime minister to Hwan. " The Master said, "Kwan Chung acted as |
| `phase3-chunking/chunks/analects_test_v2_chunk_413.txt` | prime minister to the Duke Hwan made him leader of all the princes, and united and rectified the whole kingdom. |
| `phase3-chunking/chunks/analects_test_v2_chunk_414.txt` | Down to the present day, the people enjoy the gifts which he conferred. But for Kwan Chung, we should now be wearing our hair unbound, and the lappets of our coats buttoning on the left side. "Will you require from him the small fidelity of common men and common women, who would commit suicide in a stream or |
| `phase3-chunking/chunks/analects_test_v2_chunk_415.txt` | " The great officer, Hsien, who had been family minister to Kung-shu Wan, ascended to the prince's court in company with Wan. The Master, having heard of it, said, "He deserved to be considered WAN (the accomplished). " The Master was speaking about the unprincipled course of the duke Ling of Weilwhen Ch'i |
| `phase3-chunking/chunks/analects_test_v2_chunk_416.txt` | K'ang said, "Since he is of such a character, how is it he does not lose his state? |
| `phase3-chunking/chunks/analects_test_v2_chunk_417.txt` | " Confucius said, "The Chung-shu Yu has the superintendence of his guests and of strangers; the litanist, T'o, has the management of his ancestral temple; and Wang-sun Chia has the direction of the army and forces: -with such officers as these, how should he lose his state? " The Master said, "He who speaks |
| `phase3-chunking/chunks/analects_test_v2_chunk_418.txt` | without modesty will find it difficult to make his words good. |
| `phase3-chunking/chunks/analects_test_v2_chunk_419.txt` | " Chan Ch'ang murdered the Duke Chien of Ch'i. Confucius bathed, went to court and informed the Duke Ai, saying, "Chan Hang has slain his sovereign. I beg that you will undertake to punish him. " The duke said, "Inform the chiefs of the three families of it. " Confucius retired, and said, "Following in the rear |
| `phase3-chunking/chunks/analects_test_v2_chunk_420.txt` | of the great officers, I did not dare not to represent such a matter, and my prince says, "Inform the chiefs of the three families of it. |
| `phase3-chunking/chunks/analects_test_v2_chunk_421.txt` | " He went to the chiefs, and informed them, but they would not act. Confucius then said, "Following in the rear of the great officers, I did not dare not to represent such a matter. " Tsze-lu asked how a ruler should be served. The Master said, "Do not impose on him, and, moreover, withstand him to his face. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_422.txt` | The Master said, "The progress of the superior man is upwards; the progress of the mean man is downwards. |
| `phase3-chunking/chunks/analects_test_v2_chunk_423.txt` | " The Master said, "In ancient times, men learned with a view to their own improvement. Nowadays, men learn with a view to the approbation of others. " 25. Chu Po-yu sent a messenger with friendly inquiries to Confucius. Confucius sat with him, and questioned him. "What, " said he! "is your master engaged in? " |
| `phase3-chunking/chunks/analects_test_v2_chunk_424.txt` | The messenger replied, "My master is anxious to make his faults few, but he has not yet succeeded. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_425.txt` | He then went out, and the Master said, "A messenger indeed! A messenger indeed! " The Master said, "He who is not in any particular office has nothing to do with plans for the administration of its duties. " The philosopher Tsang said, "The superior man, in his thoughts, does not go out of his place. " The |
| `phase3-chunking/chunks/analects_test_v2_chunk_426.txt` | Master said, "The superior man is modest in his speech, but exceeds in his actions. |
| `phase3-chunking/chunks/analects_test_v2_chunk_427.txt` | " 28. The Master said, "The way of the superior man is threefold, but I am not equal to it. Virtuous, he is free from anxieties; wise, he is free from perplexities; bold, he is free from fear. Tsze-kung said, "Master, that is what you yourself say. " Tsze-kung was in the habit of comparing men together. The |
| `phase3-chunking/chunks/analects_test_v2_chunk_428.txt` | Master said, "Tsze must have reached a high pitch of excellence! |
| `phase3-chunking/chunks/analects_test_v2_chunk_429.txt` | Now, I have not leisure for this. " The Master said, "I will not be concerned at men's not knowing me, I will be concerned at my own want of ability. " The Master said, "He who does not anticipate attempts to deceive him, nor think beforehand of his not being believed, and yet apprehends these things readily |
| `phase3-chunking/chunks/analects_test_v2_chunk_430.txt` | when they occur; -is he not a man of superior worth? |
| `phase3-chunking/chunks/analects_test_v2_chunk_431.txt` | " Wei-shang Mau said to Confucius, "Ch'iu, how is it that you keep roosting about? Is it not that you are an insinuating talker? Confucius said, "I do not dare to play the part of such a talker, but I hate obstinacy. " The Master said, "A horse is called a ch'i, not because of its strength, but because of its |
| `phase3-chunking/chunks/analects_test_v2_chunk_432.txt` | " Some one said. "What do you say concerning the principle that injury should be recompensed with kindness? " The Master said, "With what then will you recompense kindness? " "Recompense injury with justice, and recompense kindness with kindness. " The Master said, "Alas! there is no one that knows me. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_433.txt` | Tsze-kung said, "What do you mean by thus saying that no one knows you? " |
| `phase3-chunking/chunks/analects_test_v2_chunk_434.txt` | The Master replied, "I do not murmur against Heaven. I do not grumble against men. My studies lie low, and my penetration rises high. But there is Heaven; -that knows me! " The Kung-po Liao, having slandered Tsze-lu to Chi-sun, Tsze-fu Ching-po informed Confucius of it, saying, "Our master is certainly being |
| `phase3-chunking/chunks/analects_test_v2_chunk_435.txt` | led astray by the Kung po Liao, but I have still power enough left to cut Liao off, and expose his corpse in the market and in the court. |
| `phase3-chunking/chunks/analects_test_v2_chunk_436.txt` | " The Master said, "If my principles are to advance, it is so ordered. If they are to fall to the ground, it is so ordered. What can the Kung-po Liao do where such ordering is concerned? " The Master said, "Some men of worth retire from the world. Some retire from particular states. Some retire because of |
| `phase3-chunking/chunks/analects_test_v2_chunk_437.txt` | Some retire because of contradictory language. " The Master said, "Those who have done this are seven men. " "1 Tsze-lu happening to pass the night in Shih-man, the gatekeeper said to him, "Whom do you come from? " Tsze-lu said, "From Mr. K'ung. " "It is he, is it not? " said the other, "who knows the |
| `phase3-chunking/chunks/analects_test_v2_chunk_438.txt` | impracticable nature of the times and yet will be doing in them. |
| `phase3-chunking/chunks/analects_test_v2_chunk_439.txt` | " 39. The Master was playing, one day, on a musical stone in Weil when a man carryinga straw basket passed door of the house where Confucius was, and said, "His heart is full who so beats the musical stone. " A little while after, he added, "How contemptible is the one-ideaed obstinacy those sounds display! |
| `phase3-chunking/chunks/analects_test_v2_chunk_440.txt` | When one is taken no notice of, he has simply at once to give over his wish for public employment. |
| `phase3-chunking/chunks/analects_test_v2_chunk_441.txt` | 'Deep water must be crossed with the clothes on; shallow water may be crossed with the clothes held up. "" The Master said, "How determined is he in his purpose! But this not difficult! " 40. Tsze-chang said, "What is meant when the Shu says that Kao-tsung, while observing the usual imperial mourning, was for |
| `phase3-chunking/chunks/analects_test_v2_chunk_442.txt` | " The Master said, "Why must Kao-tsung be referred to as an example of this? The ancients all did so. When the sovereign died, the officers all attended to their several duties, taking instructions from the prime minister for three years. " The Master said, "When rulers love to observe the rules of propriety, |
| `phase3-chunking/chunks/analects_test_v2_chunk_443.txt` | the people respond readily to the calls on them for service. |
| `phase3-chunking/chunks/analects_test_v2_chunk_444.txt` | " 42. Tsze-lu asked what constituted the superior man. The Master said, "The cultivation of himself in reverential carefulness. " "And is this all? " said Tsze-lu. "He cultivates himself so as to give rest to others, " was the reply. "And is this all? " again asked Tsze-lu. The Master said, "He cultivates |
| `phase3-chunking/chunks/analects_test_v2_chunk_445.txt` | He cultivates himself so as to give rest to all the people: -even Yao and Shun were still solicitous about this. " 43. Yuan Zang was squatting on his heels, and so waited the approach of the Master, who said to him, "In youth not humble as befits a junior; in manhood, doing nothing worthy of being handed down; |
| `phase3-chunking/chunks/analects_test_v2_chunk_446.txt` | and living on to old age: -this is to be a pest. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_447.txt` | With this he hit him on the shank with his staff. 44. A youth of the village of Ch'ueh was employed by Confucius to carry the messages between him and his visitors. Some one asked about him, saying, "I suppose he has made great progress. " The Master said, "I observe that he is fond of occupying the seat of a |
| `phase3-chunking/chunks/analects_test_v2_chunk_448.txt` | full-grown man; I observe that he walks shoulder to shoulder with his elders. |
| `phase3-chunking/chunks/analects_test_v2_chunk_449.txt` | He is not one who is seeking to make progress in learning. He wishes quickly to become a man. " 1. The Duke Ling of Wei asked Confucius about tactics. Confucius replied, "I have heard all about sacrificial vessels, but I have not learned military matters. " On this, he took his departure the next day. When he |
| `phase3-chunking/chunks/analects_test_v2_chunk_450.txt` | was in Chan, their provisions were exhausted, and his followers became so in that they were unable to rise. |
| `phase3-chunking/chunks/analects_test_v2_chunk_451.txt` | Tsze-lu, with evident dissatisfaction, said, "Has the superior man likewise to endure in this way? " The Master said, "The superior man may indeed have to endure want, but the mean man, when he is in want, gives way to unbridled license. " The Master said, "Ts'ze, you think, I suppose, that I am one who learns |
| `phase3-chunking/chunks/analects_test_v2_chunk_452.txt` | " Tsze-kung replied, "Yes. -but perhaps it is not so? " "No. " was the answer: "I seek a unity all pervading. " The Master said, "May not Shun be instanced as having governed efficiently without exertion? What did he do? He did nothing but gravely and reverently occupy his royal seat. " Tsze-chang asked how a |
| `phase3-chunking/chunks/analects_test_v2_chunk_453.txt` | man should conduct himself, so as to be everywhere appreciated. |
| `phase3-chunking/chunks/analects_test_v2_chunk_454.txt` | The Master said, "Let his words be sincere and truthful and his actions honorable and careful: -such conduct may be practiced among the rude tribes of the South or the North. If his words be not sincere and truthful and his actions not honorable and carefull will he, with such conduct, be appreciated, even in |
| `phase3-chunking/chunks/analects_test_v2_chunk_455.txt` | "When he is standing, let him see those two things, as it were, fronting him. When he is in a carriage, let him see them attached to the yoke. Then may he subsequently carry them into practice. " Tsze-chang wrote these counsels on the end of his sash. The Master said, "Truly straightforward was the |
| `phase3-chunking/chunks/analects_test_v2_chunk_456.txt` | When good government prevailed in his state, he was like an arrow. When bad government prevailed, he was like an arrow. A superior man indeed is Chu Po-yu! When good government prevails in his state, he is to be found in office. When bad government prevails, he can roll his principles up, and keep them in his |
| `phase3-chunking/chunks/analects_test_v2_chunk_457.txt` | " The Master said, "When a man may be spoken with, not to speak to him is to err in reference to the man. When a man may not be spoken with, to speak to him is to err in reference to our words. The wise err neither in regard to their man nor to their words. " 9. The Master said, "The determined scholar and the |
| `phase3-chunking/chunks/analects_test_v2_chunk_458.txt` | man of virtue will not seek to live at the expense of injuring their virtue. |
| `phase3-chunking/chunks/analects_test_v2_chunk_459.txt` | They will even sacrifice their lives to preserve their virtue complete. " 10. Tsze-kung asked about the practice of virtue. The Master said, "The mechanic, who wishes to do his work well, must first sharpen his tools. When you are living in any state, take service with the most worthy among its great officers, |
| `phase3-chunking/chunks/analects_test_v2_chunk_460.txt` | and make friends of the most virtuous among its scholars. |
| `phase3-chunking/chunks/analects_test_v2_chunk_461.txt` | " Yen Yuan asked how the government of a country should be administered. The Master said, "Follow the seasons of Hsia. "Ride in the state carriage of Yin. "Wear the ceremonial cap of Chau. "Let the music be the Shao with its pantomimes. Banish the songs of Chang, and keep far from specious talkers. The songs of |
| `phase3-chunking/chunks/analects_test_v2_chunk_462.txt` | Chang are licentious; specious talkers are dangerous. |
| `phase3-chunking/chunks/analects_test_v2_chunk_463.txt` | " The Master said, "If a man take no thought about what is distant, he will find sorrow near at hand. " The Master said, "It is all over! I have not seen one who loves virtue as he loves beauty. " The Master said, "Was not Tsang Wan like one who had stolen his situation? He knew the virtue and the talents of |
| `phase3-chunking/chunks/analects_test_v2_chunk_464.txt` | Hui of Liu-hsia, and yet did not procure that he should stand with him in court. |
| `phase3-chunking/chunks/analects_test_v2_chunk_465.txt` | " The Master said, "He who requires much from himself and little from others, will keep himself from being the object of resentment. " The Master said, "When a man is not in the habit of saying: 'What shall I think of this? What shall I think of this? ' I can indeed do nothing with him! " The Master said, "When |
| `phase3-chunking/chunks/analects_test_v2_chunk_466.txt` | a number of people are together, for a whole day, without their conversation turning on righteousness, and when they are fond of carrying out the suggestions of a small shrewdness; -theirs is indeed a hard case. |
| `phase3-chunking/chunks/analects_test_v2_chunk_467.txt` | " The Master said, "The superior man in everything considers righteousness to be essential. He performs it according to the rules of propriety. He brings it forth in humility. He completes it with sincerity. This is indeed a superior man. " The Master said, "The superior man is distressed by his want of |
| `phase3-chunking/chunks/analects_test_v2_chunk_468.txt` | He is not distressed by men's not knowing him. " The Master said, "The superior man dislikes the thought of his name not being mentioned after his death. " The Master said, "What the superior man seeks, is in himself. What the mean man seeks, is in others. " The Master said, "The superior man is dignified, but |
| `phase3-chunking/chunks/analects_test_v2_chunk_469.txt` | He is sociable, but not a partisan. " The Master said, "The superior man does not promote a man simply on account of his words, nor does he put aside good words because of the man. " Tsze-kung asked, saying, "Is there one word which may serve as a rule of practice for all one's life? " The Master said, "Is not |
| `phase3-chunking/chunks/analects_test_v2_chunk_470.txt` | What you do not want done to yourself, do not do to others. " The Master said. "In my dealings with men, whose evil do I blame, whose goodness do I praise, beyond what is proper? If I do sometimes exceed in praise, there must be ground for it in my examination of the individual. "This people supplied the reason |
| `phase3-chunking/chunks/analects_test_v2_chunk_471.txt` | why the three dynasties pursued the path of straightforwardness. |
| `phase3-chunking/chunks/analects_test_v2_chunk_472.txt` | " The Master said, "Even in my early days, a historiographer would leave a blank in his text, and he who had a horse would lend him to another to ride. Now, alas! there are no such things. " The Master said, "Specious words confound virtue. Want of forbearance in small matters confounds great plans. " The |
| `phase3-chunking/chunks/analects_test_v2_chunk_473.txt` | Master said, "When the multitude hate a man, it is necessary to examine into the case. |
| `phase3-chunking/chunks/analects_test_v2_chunk_474.txt` | When the multitude like a man, it is necessary to examine into the case. " The Master said, "A man can enlarge the principles which he follows; those principles do not enlarge the man. " The Master said, "To have faults and not to reform them, -this, indeed, should be pronounced having faults. " The Master |
| `phase3-chunking/chunks/analects_test_v2_chunk_475.txt` | said, "I have been the whole day without eating, and the whole night without sleeping: occupied with thinking. |
| `phase3-chunking/chunks/analects_test_v2_chunk_476.txt` | It was of no use. better plan is to learn. " The Master said, "The object of the superior man is truth. Food is not his object. There is plowing; even in that there is sometimes want. So with learning; emolument may be found in it. The superior man is anxious lest he should not get truth; he is not anxious lest |
| `phase3-chunking/chunks/analects_test_v2_chunk_477.txt` | " 33. The Master said, "When a man's knowledge is sufficient to attain, and his virtue is not sufficient to enable him to hold, whatever he may have gained, he will lose again. "When his knowledge is sufficient to attain, and he has virtue enough to hold fast, if he cannot govern with dignity, the people will |
| `phase3-chunking/chunks/analects_test_v2_chunk_478.txt` | "When his knowledge is sufficient to attain, and he has virtue enough to hold fast; when he governs also with dignity, yet if he try to move the people contrary to the rules of propriety: -full excellence is not reached. " The Master said, "The superior man cannot be known in little matters; but he may be |
| `phase3-chunking/chunks/analects_test_v2_chunk_479.txt` | The small man may not be intrusted with great concerns, but he may be known in little matters. " 35. The Master said, "Virtue is more to man than either water or fire. I have seen men die from treading on water and fire, but I have never seen a man die from treading the course of virtue. " The Master said, "Let |
| `phase3-chunking/chunks/analects_test_v2_chunk_480.txt` | every man consider virtue as what devolves on himself. |
| `phase3-chunking/chunks/analects_test_v2_chunk_481.txt` | He may not yield the performance of it even to his teacher. " The Master said, "The superior man is correctly firm, and not firm merely. " 18. The Master said, "A minister, in serving his prince, reverently discharges his duties, and makes his emolument a secondary consideration. " The Master said, "In teaching |
| `phase3-chunking/chunks/analects_test_v2_chunk_482.txt` | " 40. The Master said, "Those whose courses are different cannot lay plans for one another. " The Master said, "In language it is simply required that it convey the meaning. " 41. The music master, Mien, having called upon him, when they came to the steps, the Master said, "Here are the steps. " When they came |
| `phase3-chunking/chunks/analects_test_v2_chunk_483.txt` | to the mat for the guest to sit upon, he said, "Here is the mat. " |
| `phase3-chunking/chunks/analects_test_v2_chunk_484.txt` | When all were seated, the Master informed him, saying, "So and so is here; so and so is here. " The music master, Mien, having gone out, Tsze-chang asked, saying. "Is it the rule to tell those things to the music master? " The Master said, "Yes. This is certainly the rule for those who lead the blind. " XVL The |
| `phase3-chunking/chunks/analects_test_v2_chunk_485.txt` | head of the Chi family was going to attack Chwan-yu. |
| `phase3-chunking/chunks/analects_test_v2_chunk_486.txt` | "Now, in regard to Chwan-yu, long ago, a former king appointed its ruler to preside over the sacrifices to the eastern Mang; moreover, it is in the midst of the territory of our state; and its ruler is a minister in direct connection with the sovereign: What has your chief to do with attacking it? " 1. Zan Yu |
| `phase3-chunking/chunks/analects_test_v2_chunk_487.txt` | and Chi-lu had an interview with Confucius, and said, "Our chief, Chil is going to commence operations against Chwan-yu. |
| `phase3-chunking/chunks/analects_test_v2_chunk_488.txt` | " Confucius said, "Ch'iu, is it not you who are in fault here? Zan Yu said. "Our master wishes the thing: neither of us two ministers wishes it. " Confucius said, "Ch'iu, there are the words of Chau Zan, -'When he can put forth his ability, he takes his place in the ranks of office; when he finds himself unable |
| `phase3-chunking/chunks/analects_test_v2_chunk_489.txt` | How can he be used as a guide to a blind man, who does not support him when tottering, nor raise him up when fallen? ' "And further, you speak wrongly. When a tiger or rhinoceros escapes from his cage; when a tortoise or piece of jade is injured in its repository: -whose is the fault? " Zan Yu said. "But at |
| `phase3-chunking/chunks/analects_test_v2_chunk_490.txt` | present, Chwan-yu is strong and near to Pi; if our chief do not now take it, it will hereafter be a sorrow to his descendants. |
| `phase3-chunking/chunks/analects_test_v2_chunk_491.txt` | "I have heard that rulers of states and chiefs of families are not troubled lest their people should be few, but are troubled lest they should not keep their several places; that they are not troubled with fears of poverty, but are troubled with fears of a want of contented repose among the people in their |
| `phase3-chunking/chunks/analects_test_v2_chunk_492.txt` | " Confucius said. "Ch'iu, the superior man hates those declining to say, 'I want such and such a thing, and framing explanations for their conduct. For when the people keep their several places, there will be no poverty; when harmony prevails, there will be no scarcity of people: and when there is such a |
| `phase3-chunking/chunks/analects_test_v2_chunk_493.txt` | contented repose, there will be no rebellious upsettings. |
| `phase3-chunking/chunks/analects_test_v2_chunk_494.txt` | "So it is. Therefore, if remoter people are not submissive, all the influences of civil culture and virtue are to be cultivated to attract them to be so; and when they have been so attracted, they must be made contented and tranquil. "Now, here are you, Yu and Ch'iu, assisting your chief. Remoter people are not |
| `phase3-chunking/chunks/analects_test_v2_chunk_495.txt` | submissive, and, with your help, he cannot attract them to him. |
| `phase3-chunking/chunks/analects_test_v2_chunk_496.txt` | In his own territory there are divisions and downfalls, leavings and separations, and, with your help, he cannot preserve it. "And yet he is planning these hostile movements within the state. -I am afraid that the sorrow of the Chi-sun family will not be on account of Chwan-yu, but will be found within the |
| `phase3-chunking/chunks/analects_test_v2_chunk_497.txt` | " Confucius said, "When good government prevails in the empire, ceremonies, music, and punitive military expeditions proceed from the son of Heaven. When bad government prevails in the empire, ceremonies, music, and punitive military expeditions proceed from the princes. When these things proceed from the |
| `phase3-chunking/chunks/analects_test_v2_chunk_498.txt` | princes, as a rule, the cases will be few in which they do not lose their power in ten generations. |
| `phase3-chunking/chunks/analects_test_v2_chunk_499.txt` | When they proceed from the great officers of the princes, as a rule, the case will be few in which they do not lose their power in five generations. When the subsidiary ministers of the great officers hold in their grasp the orders of the state, as a rule the cases will be few in which they do not lose their |
| `phase3-chunking/chunks/analects_test_v2_chunk_500.txt` | "When right principles prevail in the kingdom, government will not be in the hands of the great officers. "When right principles prevail in the kingdom, there will be no discussions among the common people. " Confucius said, "The revenue of the state has left the ducal house now for five generations. The |
| `phase3-chunking/chunks/analects_test_v2_chunk_501.txt` | government has been in the hands of the great officers for four generations. |
| `phase3-chunking/chunks/analects_test_v2_chunk_502.txt` | On this account, the descendants of the three Hwan are much reduced. " A Confucius said, "There are three friendships which are advantageous, and three which are injurious. Friendship with the uplight; friendship with the sincere, and friendship with the man of much observation: -these are advantageous. |
| `phase3-chunking/chunks/analects_test_v2_chunk_503.txt` | Friendship with the man of specious airs; friendship with the insinuatingly soft; and friendship with the glib-tongued: -these are injurious. |
| `phase3-chunking/chunks/analects_test_v2_chunk_504.txt` | " 5. Confucius said, "There are three things men find enjoyment in which are advantageous, and three things they find enjoyment in which are injurious. To find enjoyment in the discriminating study of ceremonies and music; to find enjoyment in speaking of the goodness of others; to find enjoyment in having many |
| `phase3-chunking/chunks/analects_test_v2_chunk_505.txt` | To find enjoyment in extravagant pleasures; to find enjoyment in idleness and sauntering; to find enjoyment in the pleasures of feasting: -these are injurious. " Confucius said, "There are three errors to which they who stand in the presence of a man of virtue and station are liable. They may speak when it does |
| `phase3-chunking/chunks/analects_test_v2_chunk_506.txt` | not come to them to speak; this is called rashness. |
| `phase3-chunking/chunks/analects_test_v2_chunk_507.txt` | They may not speak when it comes to them to speak; this is called concealment. They may speak without looking at the countenance of their superior; this is called blindness. " Confucius said, "There are three things which the superior man guards against. In youth, when the physical powers are not yet settled, |
| `phase3-chunking/chunks/analects_test_v2_chunk_508.txt` | When he is strong and the physical powers are full of vigor, he guards against quarrelsomeness. When he is old, and the animal powers are decayed, he guards against covetousness. " Confucius said, "There are three things of which the superior man stands in awe. He stands in awe of the ordinances of Heaven. He |
| `phase3-chunking/chunks/analects_test_v2_chunk_509.txt` | He stands in awe of the words of sages. "The mean man does not know the ordinances of Heaven, and consequently does not stand in awe of them. He is disrespectful to great men. He makes sport of the words of sages. " Confucius said, "Those who are born with the possession of knowledge are the highest class of |
| `phase3-chunking/chunks/analects_test_v2_chunk_510.txt` | Those who learn, and so readily get possession of knowledge, are the next. Those who are dull and stupid, and yet compass the learning, are another class next to these. As to those who are dull and stupid and yet do not learn; -they are the lowest of the people. " Confucius said, "The superior man has nine |
| `phase3-chunking/chunks/analects_test_v2_chunk_511.txt` | things which are subjects with him of thoughtful consideration. |
| `phase3-chunking/chunks/analects_test_v2_chunk_512.txt` | In regard to the use of his eyes, he is anxious to see clearly. In regard to the use of his ears, he is anxious to hear distinctly. In regard to his countenance, he is anxious that it should be benign. In regard to his demeanor, he is anxious that it should be respectful. In regard to his speech, he is anxious |
| `phase3-chunking/chunks/analects_test_v2_chunk_513.txt` | In regard to his doing of business, he is anxious that it should be reverently careful. In regard to what he doubts about, he is anxious to question others. When he is angry, he thinks of the difficulties his anger may involve him in. When he sees gain to be got, he thinks of righteousness. " Confucius said, |
| `phase3-chunking/chunks/analects_test_v2_chunk_514.txt` | "Contemplating good, and pursuing it, as if they could not reach it; contemplating evil! |
| `phase3-chunking/chunks/analects_test_v2_chunk_515.txt` | and shrinking from it, as they would from thrusting the hand into boiling water: -I have seen such men, as I have heard such words. "Living in retirement to study their aims, and practicing righteousness to carry out their principles: I have heard these words, but I have not seen such men. " The Duke Ching of |
| `phase3-chunking/chunks/analects_test_v2_chunk_516.txt` | Ch'i had a thousand teams, each of four horses, but on the day of his death, the people did not praise him for a single virtue. |
| `phase3-chunking/chunks/analects_test_v2_chunk_517.txt` | Po-i and Shu-ch'i died of hunger at the foot of the Shau-yang mountains, and the people, down to the present time, praise them. "Is not that saying illustrated by this? " Ch'an K'ang asked Po-yu, saying, "Have you heard any lessons from your father different from what we have all heard? " Po-yu replied, "No. He |
| `phase3-chunking/chunks/analects_test_v2_chunk_518.txt` | was standing alone once, when I passed below the hall with hasty steps, and said to me. |
| `phase3-chunking/chunks/analects_test_v2_chunk_519.txt` | 'Have you learned the Odes? ' On my replying 'Not yet, ' he added, If you do not learn the Odes, you will not be fit to converse with. ' I retired and studied the Odes. "Another day, he was in the same way standing alone, when I passed by below the hall with hasty steps, and said to me, 'Have you learned the |
| `phase3-chunking/chunks/analects_test_v2_chunk_520.txt` | On my replying 'Not yet, ' he added, 'If you do not learn the rules of Propriety, your character cannot be established. I then retired, and learned the rules of Propriety. "I have heard only these two things from him. " Ch'ang K'ang retired, and, quite delighted, said, "I asked one thing, and I have got three |
| `phase3-chunking/chunks/analects_test_v2_chunk_521.txt` | I have heard about the Odes. I have heard about the rules of Propriety. I have also heard that the superior man maintains a distant reserve towards his son. " 14. The wife of the prince of a state is called by him Fu Zan. She calls herself Hsiao Tung. The people of the state call her Chun Fu Zan, and, to the |
| `phase3-chunking/chunks/analects_test_v2_chunk_522.txt` | Hsiao Chun. The people of other states also call her Chun Fu Zan. WIL Yang Ho wished to see Confucius, but Confucius would not go to see him. On this, he sent a present of a pig to Confucius, who, having chosen a time when Ho was not at home went to pay his respects for the gift. He met him, however, on the |
| `phase3-chunking/chunks/analects_test_v2_chunk_523.txt` | Ho said to Confucius, "Come, let me speak with you. " He then asked, "Can he be called benevolent who keeps his jewel in his bosom, and leaves his country to confusion? " Confucius replied, "No. " "Can he be called wise, who is anxious to be engaged in public employment, and yet is constantly losing the |
| `phase3-chunking/chunks/analects_test_v2_chunk_524.txt` | Confucius again said, "No. " "The days and months are passing away; the years do not wait for us. " Confucius said, "Right; I will go into office. " 2. The Master said, "By nature, men are nearly alike; by practice, they get to be wide apart. " The Master said, "There are only the wise of the highest class, and |
| `phase3-chunking/chunks/analects_test_v2_chunk_525.txt` | the stupid of thelowest class, who cannot be changed. |
| `phase3-chunking/chunks/analects_test_v2_chunk_526.txt` | " The Master, having come to Wu-ch'ang, heard there the sound of stringedinstruments and singing. Well pleased and smiling, he said, "Why use an ox knife to kill a fowl? " Tsze-yu replied, "Formerly, Master, I heard you say, 'When the man of high station is well instructed, he loves men; when the man of low |
| `phase3-chunking/chunks/analects_test_v2_chunk_527.txt` | "" The Master said, "My disciples, Yen's words are right. What I said was only in sport. " 4. Kung-shan Fu-zao, when he was holding Pi, and in an attitude of rebellion, invitedthe Master to visit him, who was rather inclined to go. Tsze-lu was displeased. and said, "Indeed, you cannot go! Why must you think of |
| `phase3-chunking/chunks/analects_test_v2_chunk_528.txt` | " The Master said, "Can it be without some reason that he has invited ME? If any one employ me, may I not make an eastern Chau? " 5. Tsze-chang asked Confucius about perfect virtue. Confucius said, "To be able to practice five things everywhere under heaven constitutes perfect virtue. " He begged to ask what |
| `phase3-chunking/chunks/analects_test_v2_chunk_529.txt` | they were, and was told, "Gravity, generosity of soul, sincerity, earnestness, and kindness. |
| `phase3-chunking/chunks/analects_test_v2_chunk_530.txt` | If you are grave, you will not be treated with disrespect. If you are generous, you will win all. If you are sincere, people will repose trust in you. If you are earnest, you will accomplish much. If you are kind, this will enable you to employ the services of others. Pi Hsi inviting him to visit him, the |
| `phase3-chunking/chunks/analects_test_v2_chunk_531.txt` | Tsze-lu said, "Master, formerly I have heard you say, 'When a man in his own person is guilty of doing evil, a superior man will not associate with him. ' Pi Hsi is in rebellion, holding possession of Chung-mau; if you go to him, what shall be said? " The Master said, "Yes. I did use these words. But is it not |
| `phase3-chunking/chunks/analects_test_v2_chunk_532.txt` | said, that, if a thing be really hard, it may be ground without being made thin? |
| `phase3-chunking/chunks/analects_test_v2_chunk_533.txt` | Is it not said, that, if a thing be really white, it may be steeped in a dark fluid without being made black? "Am I a bitter gourd? How can I be hung up out of the way of being eaten? " The Master said. "Yu, have you heard the six words to which are attached six becloudings? " Yu replied. "I have not. " "Sit |
| `phase3-chunking/chunks/analects_test_v2_chunk_534.txt` | "There is the love of being benevolent without the love of learning; --the beclouding here leads to a foolish simplicity. There is the love of knowing without the love of learning: the beclouding here leads to dissipation of mind. There is the love of being sincere without the love of learning; -the beclouding |
| `phase3-chunking/chunks/analects_test_v2_chunk_535.txt` | here leads to an injurious disregard of consequences. |
| `phase3-chunking/chunks/analects_test_v2_chunk_536.txt` | There is the love of straightforwardness without the love of learning: -the beclouding here leads to rudeness. There is the love of boldness without the love of learning: the beclouding here leads to insubordination. There is the love of firmness without the love of learning; -the beclouding here leads to |
| `phase3-chunking/chunks/analects_test_v2_chunk_537.txt` | " The Master said, "My children, why do you not study the Book of Poetry? "The Odes serve to stimulate the mind. "They may be used for purposes of self-contemplation. "They teach the art of sociability. "They show how to regulate feelings of resentment. "From them you learn the more immediate duty of serving |
| `phase3-chunking/chunks/analects_test_v2_chunk_538.txt` | one's father, and the remoter one of serving one's prince. |
| `phase3-chunking/chunks/analects_test_v2_chunk_539.txt` | "From them we become largely acquainted with the names of birds, beasts, and plants. " The Master said to Po-yu, "Do you give yourself to the Chau-nan and the Shao-nan. The man who has not studied the Chau-nan and the Shao-nan is like one who stands with his face right against a wall. Is he not so? " The Master |
| `phase3-chunking/chunks/analects_test_v2_chunk_540.txt` | said, "It is according to the rules of propriety, ' they say. |
| `phase3-chunking/chunks/analects_test_v2_chunk_541.txt` | 'It is according to the rules of propriety, ' they say. Are gems and silk all that is meant by propriety? 'It is music, ' they say. -'It is music, ' they say. Are hers and drums all that is meant by music? " The Master said, "He who puts on an appearance of stern firmness, while inwardly he is weak, is like one |
| `phase3-chunking/chunks/analects_test_v2_chunk_542.txt` | of the small, mean people; -yea, is he not like the thief who breaks through, or climbs over, a wall? |
| `phase3-chunking/chunks/analects_test_v2_chunk_543.txt` | " The Master said, "Your good, careful people of the villages are the thieves of virtue. " The Master said, To tell, as we go along, what we have heard on the way, is to cast away our virtue. " The Master said, "There are those mean creatures! How impossible it is along with them to serve one's prince! "While |
| `phase3-chunking/chunks/analects_test_v2_chunk_544.txt` | they have not got their aims, their anxiety is how to get them. |
| `phase3-chunking/chunks/analects_test_v2_chunk_545.txt` | When they have got them, their anxiety is lest they should lose them. "When they are anxious lest such things should be lost, there is nothing to which theywill not proceed. " 14. The Master said, "Anciently, men had three failings, which now perhaps are not to be found. "The high-mindedness of antiquity showed |
| `phase3-chunking/chunks/analects_test_v2_chunk_546.txt` | itself in a disregard of small things; the high mindedness of the present day shows itself in wild license. |
| `phase3-chunking/chunks/analects_test_v2_chunk_547.txt` | The stern dignity of antiquity showed itself in grave reserve; the stern dignity of the present day shows itself in quarrelsome perverseness. The stupidity of antiquity showed itself in straightforwardness; the stupidity of the present day shows itself in sheer deceit. " The Master said, "Fine words and an |
| `phase3-chunking/chunks/analects_test_v2_chunk_548.txt` | insinuating appearance are seldom associatedwith virtue. |
| `phase3-chunking/chunks/analects_test_v2_chunk_549.txt` | " The Master said, "I hate the manner in which purple takes away the luster of vermilion. I hate the way in which the songs of Chang confound the music of the Ya. Ihate those who with their sharp mouths overthrow kingdoms and families. " The Master said, "I would prefer not speaking. " Tsze-kung said, "If you, |
| `phase3-chunking/chunks/analects_test_v2_chunk_550.txt` | Master, do not speak, what shall we, your disciples, have to record? |
| `phase3-chunking/chunks/analects_test_v2_chunk_551.txt` | " The Master said, "Does Heaven speak? The four seasons pursue their courses, and all things are continually being produced, but does Heaven say anything? " Zu Pei wished to see Confucius, but Confucius declined, on the ground of being sick, to see him. When the bearer of this message went out at the door, the |
| `phase3-chunking/chunks/analects_test_v2_chunk_552.txt` | Master took his lute and sang to it, in order that Pei might hear him. |
| `phase3-chunking/chunks/analects_test_v2_chunk_553.txt` | Tsai Wo asked about the three years' mourning for parents, saying that one year was long enough. "If the superior man, " said he, "abstains for three years from the observances of propriety, those observances will be quite lost. If for three years he abstains from music, music will be ruined. Within a year the |
| `phase3-chunking/chunks/analects_test_v2_chunk_554.txt` | old grain is exhausted, and the new grain has sprung up, and, in procuring fire by friction, we go through all the changes of wood for that purpose. |
| `phase3-chunking/chunks/analects_test_v2_chunk_555.txt` | After a complete year, the mourning may stop. " The Master said, "If you were, after a year, to eat good rice, and wear embroidered clothes, would you feel at ease? " "I should, " replied Wo. The Master said, "If you can feel at ease, do it. But a superior man, during the whole period of mourning, does not |
| `phase3-chunking/chunks/analects_test_v2_chunk_556.txt` | enjoy pleasant food which he may eat, nor derive pleasure from music which he may hear. |
| `phase3-chunking/chunks/analects_test_v2_chunk_557.txt` | He also does not feel at ease, if he is comfortably lodged. Therefore he does not do what you propose. But now you feel at ease and may do it. " Tsai Wo then went out, and the Master said, "This shows Yu's want of virtue. It is not till a child is three years old that it is allowed to leave the arms of its |
| `phase3-chunking/chunks/analects_test_v2_chunk_558.txt` | And the three years' mourning is universally observed throughout the empire. Did Yu enjoy the three years' love of his parents? " 20. The Master said, "Hard is it to deal with who will stuff himself with food the whole day, without applying his mind to anything good! Are there not gamesters and chess players? |
| `phase3-chunking/chunks/analects_test_v2_chunk_559.txt` | To be one of these would still be better than doing nothing at all. |
| `phase3-chunking/chunks/analects_test_v2_chunk_560.txt` | " Tsze-lu said, "Does the superior man esteem valor? " The Master said, "The superior man holds righteousness to be of highest importance. A man in a superior situation, having valor without righteousness, will be guilty of insubordination; one of the lower people having valor without righteousness, will commit |
| `phase3-chunking/chunks/analects_test_v2_chunk_561.txt` | " 22. Tsze-kung said, "Has the superior man his hatreds also? " The Master said, "He hashis hatreds. He hates those who proclaim the evil of others. He hates the man who, being in a low station, slanders his superiors. He hates those who have valor merely, and are unobservant of propriety. He hates those who |
| `phase3-chunking/chunks/analects_test_v2_chunk_562.txt` | are forward and determined, and, at the same time, of contracted understanding. |
| `phase3-chunking/chunks/analects_test_v2_chunk_563.txt` | " The Master then inquired, "Ts'ze, have you also your hatreds? " Tsze-kung replied, "I hatethose who pry out matters, and ascribe the knowledge to their wisdom. I hate those who are only not modest, and think that they are valorous. I hate those who make known secrets, and think that they are straightforward. |
| `phase3-chunking/chunks/analects_test_v2_chunk_564.txt` | The Master said, "Of all people, girls and servants are the most difficult to behave to. If you are familiar with them, they lose their humility. If you maintain a reserve towards them, they are discontented. " 24. The Master said, "When a man at forty is the object of dislike, he will always continue what he |
| `phase3-chunking/chunks/analects_test_v2_chunk_565.txt` | " XVIII. The Viscount of Wei withdrew from the court. The Viscount of Chi became a slave to Chau. Pi-kan remonstrated with him and died. Confucius said, "The Yin dynasty possessed these three men of virtue. " 2. Hui of Liu-hsia, being chief criminal judge, was thrice dismissed from his office. Some one said to |
| `phase3-chunking/chunks/analects_test_v2_chunk_566.txt` | him, "Is it not yet time for you, sir, to leave this? " |
| `phase3-chunking/chunks/analects_test_v2_chunk_567.txt` | He replied, "Serving men in an upright way, where shall I to, and not experience such a thrice-repeated dismissal? If I choose to serve men in a crooked way, what necessity is there for me to leave the country of my parents? " 3. The duke Ching of Ch'i, with reference to the manner in which he should treat |
| `phase3-chunking/chunks/analects_test_v2_chunk_568.txt` | Confucius, said, "I cannot treat him as I would the chief of the Chi family. |
| `phase3-chunking/chunks/analects_test_v2_chunk_569.txt` | I will treat him in a manner between that accorded to the chief of the Chil and that given to the chief of the Mang family. " He also said, "I am old; I cannot use his doctrines. " Confucius tookhis departure. The people of Ch'i sent to Lu a present of female musicians, which Chi Hwan received, and for three |
| `phase3-chunking/chunks/analects_test_v2_chunk_570.txt` | Confucius took his departure. The madman of Ch'u, Chieh-yu, passed by Confucius, singing and saying, "O FANG! O FANG! How is your virtue degenerated! As to the past, reproof is useless; butthe future may still be provided against. Give up your vain pursuit. Give up your vain pursuit. Peril awaits those who now |
| `phase3-chunking/chunks/analects_test_v2_chunk_571.txt` | " Confucius alighted and wished to converse with him, but Chieh-yu hastened away, sothat he could not talk with him. 6. Ch'ang-tsu and Chieh-ni were at work in the field together, when Confucius passed by them, and sent Tsze-lu to inquire for the ford. Ch'ang-tsu said, "Who is he that holds the reins in the |
| `phase3-chunking/chunks/analects_test_v2_chunk_572.txt` | Tsze-lu told him, "It is K'ung Ch'iu. ', "Is it not K'ung of Lu? " asked he. "Yes, " was the reply, to which the other rejoined, "He knows the ford. " Tee-lu then inquired of Chich-ni, who said to him, "Who are you, sir? " He answered, "I am Chung Yu. " "Are you not the disciple of Kung Chiu of Lu? " asked the |
| `phase3-chunking/chunks/analects_test_v2_chunk_573.txt` | "I am, " replied he, and then Chich-ni said to him, "Disorder, like a swelling flood, spreads over the whole empire, and who is he that will change its state for you? Rather than follow one who mereh withdraws from this one and that one, had you not better follow those who have withdrawn from the world |
| `phase3-chunking/chunks/analects_test_v2_chunk_574.txt` | With this he fell to covering up the seed, and proceeded with his work, without stopping. Tee-ku went and reported their remarks, when the Master observed with a sigh, "It is impossible to associate with birds and beasts, as if they were the same with us. If I associate not with these people with mankind, with |
| `phase3-chunking/chunks/analects_test_v2_chunk_575.txt` | If right principles prevailed through the empire, there would be no use for me to change its Tse-hu following the Master, happened to fall behind, when he met an old man, carrying across his shoulder on a staff a basket for weeds. Tsze-lu said to him, "Have you seen my master, sir? The old man replied, "Your |
| `phase3-chunking/chunks/analects_test_v2_chunk_576.txt` | four limbs are unaccustomed to toil; you cannot distinguish the five kinds of grain: -who is your master? " |
| `phase3-chunking/chunks/analects_test_v2_chunk_577.txt` | With this, he planted his staff in the ground, and proceeded to weed. Telu joined his hands across his breast, and stood before him. The old man kept Isze-lu to pass the night in his house, killed a fowl, prepared millet, and feasted him. He also introduced to him his two sons. Next day, Tsze-lu went on his |
| `phase3-chunking/chunks/analects_test_v2_chunk_578.txt` | The Master said, "He is a recluse, " and sent Tsze-lu back to see him again, but when he got to the place, the old man was gone. Tse-iu then said to the family, "Not to take office is not righteous. If the relations between old and young may not be neglected, how is it that he sets aside the duties thatshould |
| `phase3-chunking/chunks/analects_test_v2_chunk_579.txt` | Wishing to maintain his personalpurity, he allows that great relation to come to confusion. A superior man takes office, and performs the righteous duties belonging to it. As to the failure of right principles to make progress, he is aware of that. " The men who have retired to privacy from the world have been |
| `phase3-chunking/chunks/analects_test_v2_chunk_580.txt` | Po-i, Shu-ch'i, Yuchung, I-yi, Chu-chang, Hui of Liu-hsia, and Shao-lien. |
| `phase3-chunking/chunks/analects_test_v2_chunk_581.txt` | The Master said. "Refusing to surrender their wills, or to submit to any taint in their persons: such. I think, were Po-i and Shu-ch'i. "It may be said of Hui of Liu-hsia! and of Shaolien, that they surrendered their wills, andsubmitted to taint in their persons, but their words corresponded with reason, and |
| `phase3-chunking/chunks/analects_test_v2_chunk_582.txt` | their actions were such as men are anxious to see. |
| `phase3-chunking/chunks/analects_test_v2_chunk_583.txt` | This is all that is to be remarked in them. "It may be said of Yu-chung and I-yi, that, while they hid themselves in their seclusion, they gave a license to their words; but in their persons, they succeeded in preserving their purity, and, in their retirement, they acted according to the exigency of the times. |
| `phase3-chunking/chunks/analects_test_v2_chunk_584.txt` | I have no course for which I am predetermined, and no course against which I am predetermined. " The grand music master, Chih, went to Ch'i. Kan, the master of the band at the second meal, went to Ch'u. Liao, the band master at the third meal, went to Ts'ai, Chueh, the band master at the fourth meal, went to |
| `phase3-chunking/chunks/analects_test_v2_chunk_585.txt` | Fang-shu, the drum master, withdrew to the north of the river. Wu, the master of the hand drum, withdrew to the Han. Yang, the assistant music master, and Hsiang, master of the musical stone, withdrew to an island in the sea. The duke of Chau addressed his son, the duke of Lu, saying, "The virtuous prince does |
| `phase3-chunking/chunks/analects_test_v2_chunk_586.txt` | He does not cause the great ministers to repine at his not employing them. Without some great cause, he does not dismiss from their offices the members of old families. He does not seek in one man talents for every employment. " To Chau belonged the eight officers, Po-ta, Po-kwo, Chung-tu, Chung-hwu, Shu ya, |
| `phase3-chunking/chunks/analects_test_v2_chunk_587.txt` | Tsze-chang said, "The scholar, trained for public duty, seeing threatening danger, is prepared to sacrifice his life. When the opportunity of gain is presented to him, he thinks of righteousness. In sacrificing, his thoughts are reverential. In mourning, his thoughts are about the grief which he should feel. |
| `phase3-chunking/chunks/analects_test_v2_chunk_588.txt` | Such a man commands our approbation indeed Tsze-chang said, "When a man holds fast to virtue, but without seeking to enlarge it, and believes in right principles, but without firm sincerity, what account can be made of his existence or non-existence? |
| `phase3-chunking/chunks/analects_test_v2_chunk_589.txt` | " The disciples of Tsze-hsia asked Tsze-chang about the principles that should characterize mutual intercourse. Tsze-chang asked, "What does Tsze-hsia say on the subject? " They replied, "Tsze-hsia says: 'Associate with those who can advantage you. Put away from you those who cannot do so. "" Tsze-chang |
| `phase3-chunking/chunks/analects_test_v2_chunk_590.txt` | observed, "This is different from what I have learned. |
| `phase3-chunking/chunks/analects_test_v2_chunk_591.txt` | The superior man honors the talented and virtuous, and bears with all. He praises the good, and pities the incompetent. Am I possessed of great talents and virtue? --who is there among men whom I will not bear with? Am I devoid of talents and virtue? -men will put me away from them. What have we to do with the |
| `phase3-chunking/chunks/analects_test_v2_chunk_592.txt` | " Tsze-hsia said, "Even in inferior studies and employments there is something worth being looked at; but if it be attempted to carry them out to what is remote, there is a danger of their proving inapplicable. Therefore, the superior man does not practice them. " Tsze-hsia said, "He, who from day to day |
| `phase3-chunking/chunks/analects_test_v2_chunk_593.txt` | recognizes what he has not yet, and from month to month does not forget what he has attained to, may be said indeed to love to learn. |
| `phase3-chunking/chunks/analects_test_v2_chunk_594.txt` | " 6. Tsze-hsia said, "There are learning extensively, and having a firm and sincere aim; inquiring with earnestness, and reflecting with self-application: -virtue is in such a course. " Tsze-hsia said, "Craftsmen have their shops to dwell in, in order to accomplish their works. The superior man learns, in order |
| `phase3-chunking/chunks/analects_test_v2_chunk_595.txt` | " Tsze-hsia said, "The mean man is sure to gloss his faults. " Tsze-hsia said, "The superior man undergoes three changes. Looked at from a distance, he appears stern; when approached, he is mild; when he is heard to speak, his language is firm and decided. " 10. Tsze-hsia said, "The superior man, having |
| `phase3-chunking/chunks/analects_test_v2_chunk_596.txt` | obtained their confidence, may then impose labors on his people. |
| `phase3-chunking/chunks/analects_test_v2_chunk_597.txt` | If he have not gained their confidence, they will think thathe is oppressing them. Having obtained the confidence of his prince, one may thenremonstrate with him. If he have not gained his confidence, the prince will think that he is vilifying him. " 11. Tsze-hsia said, "When a person does not transgress the |
| `phase3-chunking/chunks/analects_test_v2_chunk_598.txt` | boundary line in the great virtues, he may pass and repass it in the small virtues. |
| `phase3-chunking/chunks/analects_test_v2_chunk_599.txt` | " Tsze-yu said, "The disciples and followers of Tsze-hsia, in sprinkling and sweepingthe ground, in answering and replying, in advancing and receding, are sufficientlyaccomplished. But these are only the branches of learning, and they are left ignorant ofwhat is essential. -How can they be acknowledged as |
| `phase3-chunking/chunks/analects_test_v2_chunk_600.txt` | " Tsze-hsia heard of the remark and said, "Alas! Yen Yu is wrong. According to the way of the superior man in teaching, what departments are there which he considers of primeimportance, and delivers? what are there which he considers of secondary importance, and allows himself to be idle about? But as in the |
| `phase3-chunking/chunks/analects_test_v2_chunk_601.txt` | case of plants, which are assorted according to their classes, so he deals with his disciples. |
| `phase3-chunking/chunks/analects_test_v2_chunk_602.txt` | How can the way of a superior S. man be such as to make fools of any of them? Is it not the sage alone, who can unite in one the beginning and the consummation of learning? " Tsze-hsia said, "The officer, having discharged all his duties, should devote his leisure to learning. The student, having completed his |
| `phase3-chunking/chunks/analects_test_v2_chunk_603.txt` | " Tsze-hsia said, "Mourning, having been carried to the utmost degree of grief, should stop with that. " 15. Tsze-hsia said, "My friend Chang can do things which are hard to be done, but yet he is not perfectly virtuous. " 16. The philosopher Tsang said, "How imposing is the manner of Chang! It is difficult |
| `phase3-chunking/chunks/analects_test_v2_chunk_604.txt` | " 17. The philosopher Tsang said, "I heard this from our Master: 'Men may not have shown what is in them to the full extent, and yet they will be found to do so, on the occasion of mourning for their parents. " 18. The philosopher Tsang said, "I have heard this from our Master: -'The filial piety of Mang |
| `phase3-chunking/chunks/analects_test_v2_chunk_605.txt` | Chwang, in other matters, was what other men are competent to, but, as seen in his not changing the ministers of his father, nor his father's mode of government, it is difficult to be attained to. |
| `phase3-chunking/chunks/analects_test_v2_chunk_606.txt` | "" The chief of the Mang family having appointed Yang Fu to be chief criminal judge, the latter consulted the philosopher Tsang. Tsang said, "The rulers have failed in their duties, and the people consequently have been disorganized for a long time. When you have found out the truth of any accusation, be |
| `phase3-chunking/chunks/analects_test_v2_chunk_607.txt` | grieved for and pity them, and do not feel joy at your own ability. |
| `phase3-chunking/chunks/analects_test_v2_chunk_608.txt` | " 20. Tsze-kung said, "Chau's wickedness was not so great as that name implies. Therefore, the superior man hates to dwell in a low-lying situation, where all the evil of the world will flow in upon him. " 21. Tsze-kung said, "The faults of the superior man are like the eclipses of the sun and moon. He has his |
| `phase3-chunking/chunks/analects_test_v2_chunk_609.txt` | faults, and all men see them; he changes again, and all men look up to him. |
| `phase3-chunking/chunks/analects_test_v2_chunk_610.txt` | " Kung-sun Ch'ao of Wei asked Tszekung, saying. "From whom did Chung-ni get his learning? " Tsze-kung replied, "The doctrines of Wan and Wu have not yet fallen to the ground. They are to be found among men. Men of talents and virtue remember the greater principles of them, and others, not possessing such |
| `phase3-chunking/chunks/analects_test_v2_chunk_611.txt` | Thus, all possess the doctrines of Wan and Wu. Where could our Master go that he should not have an opportunity of learning them? And yet what necessity was there for his having a regular master? " Shu-sun Wu-shu observed to the great officers in the court, saying, "Tsze-kung is superior to Chung-ni. " Tsze-fu |
| `phase3-chunking/chunks/analects_test_v2_chunk_612.txt` | Ching-po reported the observation to Tsze-kung, who said, "Let me use the comparison of a house and its encompassing wall. |
| `phase3-chunking/chunks/analects_test_v2_chunk_613.txt` | My wall only reaches to the shoulders. One may peep over it, and see whatever is valuable in the apartments. "The wall of my Master is several fathoms high. If one do not find the door and enter by it, he cannot see the ancestral temple with its beauties, nor all the officers in their rich array. "But I may |
| `phase3-chunking/chunks/analects_test_v2_chunk_614.txt` | Was not the observation of the chief only what might have been expected? " Shu-sun Wu-shu having spoken revilingly of Chung-ni, Tsze-kung said, "It is of no use doing so. Chung-ni cannot be reviled. The talents and virtue of other men are hillocks and mounds which may be stepped over. Chung-ni is the sun or |
| `phase3-chunking/chunks/analects_test_v2_chunk_615.txt` | Although a man may wish to cut himself off from the sage, what harm can he do to the sun or moon? He only shows that he does not know his own capacity. Ch'an Tsze-ch' in, addressing Tsze-kung, said, "You are too modest. How can Chung-ni be said to be superior to you? " Tsze-kung said to him, "For one word a man |
| `phase3-chunking/chunks/analects_test_v2_chunk_616.txt` | is often deemed to be wise, and for oneword he is often deemed to be foolish. |
| `phase3-chunking/chunks/analects_test_v2_chunk_617.txt` | "Were our Master in the position of the ruler of a state or the chief of a family, we shouldfind verified the description which has been given of a sage's rule: -he would plant thepeople, and forthwith they would be established; he would lead them on, and forthwiththey would follow him; he would make them |
| `phase3-chunking/chunks/analects_test_v2_chunk_618.txt` | happy, and forthwith multitudes wouldresort to his dominions; he would stimulate them, and forthwith they would beharmonious. |
| `phase3-chunking/chunks/analects_test_v2_chunk_619.txt` | We ought to be careful indeed in what we say. "Our Master cannot be attained to, just in the same way as the heavens cannot be gone up by the steps of a stair. While he lived, he would be glorious. When he died, he would be bitterly lamented. How is it possible for him to be attained to? " Yao said, "Oh! you, |
| `phase3-chunking/chunks/analects_test_v2_chunk_620.txt` | Shun, the Heaven-determined order of succession now rests in your person. |
| `phase3-chunking/chunks/analects_test_v2_chunk_621.txt` | Sincerely hold fast the due Mean. If there shall be distress and want within the four seas, the Heavenly revenue will come to a perpetual end. " Shun also used the same language in giving charge to Yu. T'ang said, "I the child Li, presume to use a dark-colored victim, and presume to announce to Thee, O most |
| `phase3-chunking/chunks/analects_test_v2_chunk_622.txt` | great and sovereign God, that the sinner I dare not pardon, and thy ministers, O God, I do not keep in obscurity. |
| `phase3-chunking/chunks/analects_test_v2_chunk_623.txt` | The examination of them is by thy mind, O God. If, in my person, I commit offenses, they are not to be attributed to you, the people of the myriad regions. If you in the myriad regions commit offenses, these offenses must rest on my person. " Chau conferred great gifts, and the good were enriched. "Although he |
| `phase3-chunking/chunks/analects_test_v2_chunk_624.txt` | has his near relatives, they are not equal to my virtuous men. |
| `phase3-chunking/chunks/analects_test_v2_chunk_625.txt` | The people are throwing blame upon me, the One man. " He carefully attended to the weights and measures, examined the body of the laws, restored the discarded officers, and the good government of the kingdom took its course. He revived states that had been extinguished, restored families whose line of |
| `phase3-chunking/chunks/analects_test_v2_chunk_626.txt` | succession had been broken, and called to office those who had retired into obscurity, so that throughout the kingdom the hearts of the people turned towards him. |
| `phase3-chunking/chunks/analects_test_v2_chunk_627.txt` | What he attached chief importance to were the food of the people, the duties of mourning, and sacrifices. By his generosity, he won all. By his sincerity, he made the people repose trust in him. By his earnest activity, his achievements were great. By his justice, all were delighted. Tsze-chang asked Confucius, |
| `phase3-chunking/chunks/analects_test_v2_chunk_628.txt` | saying, "In what way should a person in authority act in order that he may conduct government properly? " |
| `phase3-chunking/chunks/analects_test_v2_chunk_629.txt` | The Master replied, "Let him honor the five excellent, and banish away the four bad, things; -then may he conduct government properly. " Tsze-chang said, "What are meant by the five excellent things? " The Master said, "When the person in authority is beneficent without great expenditure; when he lays tasks on |
| `phase3-chunking/chunks/analects_test_v2_chunk_630.txt` | the people without their repining; when he pursues what he desires without being covetous; when he maintains a dignified ease without being proud; when he is majestic without being fierce. |
| `phase3-chunking/chunks/analects_test_v2_chunk_631.txt` | " Tsze-chang said, "What is meant by being beneficent without great expenditure? " The Master replied, "When the person in authority makes more beneficial to the people the things from which they naturally derive benefit; -is not this being beneficent without great expenditure? When he chooses the labors which |
| `phase3-chunking/chunks/analects_test_v2_chunk_632.txt` | are proper, and makes them labor on them, who will repine? |
| `phase3-chunking/chunks/analects_test_v2_chunk_633.txt` | When his desires are set on benevolent government, and he secures it, who will accuse him of covetousness? Whether he has to do with many people or few, or with things great or small, he does not dare to indicate any disrespect; -is not this to maintain a dignified ease without any pride? He adjusts his clothes |
| `phase3-chunking/chunks/analects_test_v2_chunk_634.txt` | and cap, and throws a dignity into his looks, so that, thus dignified, he is looked at with awe; -is not this to be majestic without being fierce? |
| `phase3-chunking/chunks/analects_test_v2_chunk_635.txt` | " Tsze-chang then asked, "What are meant by the four bad things? " The Master said, "To put the people to death without having instructed them; -this is called cruelty. To require from them, suddenly, the full tale of work, without having given them warning; --this is called oppression. To issue orders as if |
| `phase3-chunking/chunks/analects_test_v2_chunk_636.txt` | without urgency, at first, and, when the time comes, to insist on them with severity; this is called injury. |
| `phase3-chunking/chunks/analects_test_v2_chunk_637.txt` | And, generally, in the giving pay or rewards to men, to do it in a stingy way; this is called acting the part of a mere official. " The Master said, "Without recognizing the ordinances of Heaven, it is impossible to be a superior man. "Without an acquaintance with the rules of Propriety, it is impossible for |
| `phase3-chunking/chunks/analects_test_v2_chunk_638.txt` | "Without knowing the force of words, it is impossible to know men. " |
| `phase3-chunking/chunks/temp_test_chunk_001.txt` | One dollar and eighty-seven cents. That was all. She had put it aside, one cent and then another and then another, in her careful buying of meat and other food. Della counted it three times. One dollar and eighty-seven cents. |
| `phase3-chunking/chunks/test_magi_chunk_chunk_001.txt` | One dollar and eighty-seven cents. That was all. And sixty cents of it was in pennies. Pennies saved one and two at a time by bulldozing the grocer and the vegetable man and the butcher until one's cheeks burned with the silent imputation of parsimony that such close dealing implied. Three times Della counted |
| `phase3-chunking/chunks/test_magi_chunk_chunk_002.txt` | One dollar and eighty-seven cents. And the next day would be Christmas. |
| `phase3-chunking/chunks/test_story_chunk_001.txt` | The Quick Brown Fox |
| `phase3-chunking/chunks/test_story_chunk_002.txt` | It sprinted across meadows, leaped over |
| `phase3-chunking/test_chapter_detection.py` | Pattern for Roman numerals at start of line (I., II., III., etc.) |
| `phase3-chunking/test_genre_aware.py` | Quick Test Script for Phase 3 Genre-Aware Chunking |
| `phase3-chunking/tests/test_chunk_optimization.py` | Test duration prediction using character count. |
| `phase3-chunking/tests/test_chunking.py` | Additional tests for coverage |
| `phase4_tts/Chatterbox-TTS-Extended/test.wav` | RIFFHI WAVEfmt      ]   w    fact   @  PEAK      h |
| `phase4_tts/Chatterbox-TTS-Extended/test_tts.py` | Inferred from filename: tests test tts |
| `phase4_tts/voice_comparison_test/voice_test_agnes_moorehead.wav` | RIFFH WAVEfmt      ]   w    fact     PEAK      he^?p< data                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `phase4_tts/voice_comparison_test/voice_test_bob_neufeld.wav` | RIFFH( WAVEfmt      ]   w    fact     |
| `phase4_tts/voice_comparison_test/voice_test_david_leeson.wav` | RIFFH WAVEfmt      ]   w    fact   z PEAK      ɇhM? data                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                !9UYұco1	3 |
| `phase4_tts/voice_comparison_test/voice_test_de_wittkower.wav` | RIFFH WAVEfmt      ]   w    fact   @ PEAK      hÅ?uw data                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `phase4_tts/voice_comparison_test/voice_test_geoffrey_edwards.wav` | RIFFH WAVEfmt      ]   w    fact     PEAK      khk^?u data                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        y1@2+m#L53_3X0 ԴCx.)qt䔶.-]9 |
| `phase4_tts/voice_comparison_test/voice_test_greenman.wav` | RIFFH WAVEfmt      ]   w    fact   * PEAK      hp}??  data                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      q23:4TM3x4]4.56@	65x |
| `phase4_tts/voice_comparison_test/voice_test_maryann_spiegel.wav` | RIFFHV WAVEfmt      ]   w    fact    PEAK       |
| `phase4_tts/voice_comparison_test/voice_test_mercedes_mccambridge.wav` | RIFFH WAVEfmt      ]   w    fact     PEAK      $hk?X |
| `phase4_tts/voice_comparison_test/voice_test_neutral_narrator.wav` | RIFFH WAVEfmt      ]   w    fact   + PEAK      Fhp}?'S  data                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       ]3ԝ4)/5tT}5^55- |
| `phase4_tts/voice_comparison_test/voice_test_results.json` | { |
| `phase4_tts/voice_comparison_test/voice_test_ruth_golding_local.wav` | RIFFH WAVEfmt      ]   w    fact     PEAK      ~h!s?  data                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              FEҸJ05#/ |
| `phase4_tts/voice_comparison_test/voice_test_vincent_price_01.wav` | RIFFHc WAVEfmt      ]   w    fact   X PEAK      ׈hp}?F data c                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      o=6j),77n8[.8zM8=\8I!b8a8l8Z88<8d8;M8a!8&7n77w,8	  |
| `phase4_tts/voice_comparison_test/voice_test_vincent_price_02.wav` | RIFFH |
| `phase4_tts/voice_comparison_test/voice_test_vincent_price_03.wav` | RIFFH WAVEfmt      ]   w    fact    PEAK      hp}? data                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               1Q0-XY;8+1S 305'd5(66X"6*,7H=7Cfn7770k7~H78 |
| `phase5_enhancement/apply_fix_and_test.bat` | Step 1: Apply the fixed version |
| `phase5_enhancement/fix_and_test.bat` | Inferred from filename: tests fix and test |
| `phase5_enhancement/QUICK_TEST.md` | # Quick Test Commands - Phase 5 Clipping Fix |
| `phase5_enhancement/SINGLE_CHUNK_TEST.md` | # Phase 5 Single Chunk Test - FIXED |
| `phase5_enhancement/test_integration.bat` | Clean up previous test outputs |
| `phase5_enhancement/tests/test_main.py` | Add src directory to path for imports |
| `phase5_enhancement/tests/test_subtitles.py` | Sample subtitle segments for testing. |
| `phase6_orchestrator/cleanup_test_files.bat` | Inferred from filename: tests cleanup test files |
| `phase6_orchestrator/COVERAGE_TEST_FIXES.md` | ## Coverage Test Fixes Applied |
| `phase6_orchestrator/COVERAGE_TEST_GUIDE.md` | # Coverage Test Guide |
| `phase6_orchestrator/COVERAGE_TEST_RESULTS.md` | # Coverage Test Results Summary |
| `phase6_orchestrator/create_test_chunks.bat` | Create chunks directory |
| `phase6_orchestrator/quick_test.bat` | Quick test script for Phase 6 Orchestrator |
| `phase6_orchestrator/QUICK_TEST.md` | # Quick Test - Phase 4 Fix |
| `phase6_orchestrator/run_coverage_tests.bat` | Inferred from filename: tests run coverage tests |
| `phase6_orchestrator/setup_and_test_phase3.bat` | Inferred from filename: tests setup and test phase3 |
| `phase6_orchestrator/test.bat` | Inferred from filename: tests test |
| `phase6_orchestrator/test_conda.py` | Test Phase 4 Conda environment setup |
| `phase6_orchestrator/test_coverage_manual.py` | Add tests directory to path |
| `phase6_orchestrator/test_gift_of_magi.bat` | Inferred from filename: tests test gift of magi |
| `phase6_orchestrator/test_language_fix.py` | Read orchestrator.py and check for --language parameter |
| `phase6_orchestrator/test_minimal.py` | Setup |
| `phase6_orchestrator/test_orchestrator.bat` | Inferred from filename: tests test orchestrator |
| `phase6_orchestrator/test_orchestrator_v2.bat` | Inferred from filename: tests test orchestrator v2 |
| `phase6_orchestrator/test_phase3_direct.bat` | Inferred from filename: tests test phase3 direct |
| `phase6_orchestrator/test_phase3_quick.bat` | Inferred from filename: tests test phase3 quick |
| `phase6_orchestrator/test_phase4_5.bat` | Inferred from filename: tests test phase4 5 |
| `phase6_orchestrator/test_phase4_direct.py` | Settings |
| `phase6_orchestrator/test_phase4_env.py` | Check if Conda is installed |
| `phase6_orchestrator/test_phase5_fix.bat` | Test Phase 5 Fix |
| `phase6_orchestrator/test_phases_4_5.bat` | Inferred from filename: tests test phases 4 5 |
| `phase6_orchestrator/test_simple.bat` | Inferred from filename: tests test simple |
| `phase6_orchestrator/test_skip_phase3.bat` | Inferred from filename: tests test skip phase3 |
| `phase6_orchestrator/tests/test_coverage.py` | Try to import librosa for audio checks |
| `phase7_batch/TESTING_CHECKLIST.md` | # Phase 7 Testing Checklist |
| `phase7_batch/tests/test_cli.py` | Test BatchConfig model |
| `phase7_batch/tests/test_main.py` | Test default configuration creation |
| `phase_audio_cleanup/test_cleanup.bat` | Test script for audio cleanup tool |
| `phase_audio_cleanup/tests/test_cleaner.py` | Test basic cleaner initialization. |
| `pipeline_test.json` | { |
| `setup_and_run_voice_test.py` | Verify conda environment is activated. |
| `temp_test.txt` | One dollar and eighty-seven cents. That was all. She had put it aside, one cent and then another and then another, in her careful buying of meat and other food. Della counted it three times. One dollar and eighty-seven cents. |
| `test_all_voices.ps1` | Test All 14 Voices on Gift of the Magi Chunk |
| `test_all_voices_magi.py` | Add phase4_tts to path |
| `test_chunk_sort.py` | Extract chunk number from filename like 'Gift of the Magi_chunk_001.wav |
| `test_existing_chunk.ps1` | Test All 14 Voices on Existing Gift of the Magi Chunk |
| `test_magi_chunk.txt` | One dollar and eighty-seven cents. That was all. And sixty cents of it was in pennies. Pennies saved one and two at a time by bulldozing the grocer and the vegetable man and the butcher until one's cheeks burned with the silent imputation of parsimony that such close dealing implied. Three times Della counted it. One dollar and eighty-seven cents. And the next day would be Christmas. |
| `test_phase4_chunks.py` | Test chunks: 1, 100, 200, 300, 624 |
| `test_single_chunk.bat` | Test processing a single failed file to see the actual error |
| `test_story.txt` | The Quick Brown Fox |
| `VALIDATION_TESTS.md` | # Quick Validation Guide - Test All Fixes |
| `VOICE_SYSTEM_TESTING.md` | # Quick Start Testing Guide - Voice Override System |

## 3. Markdown Documentation
| File | First Heading | Size |
| --- | --- | --- |
| `ALL_UNICODE_FIXES_COMPLETE.md` | All Unicode Symbols Fixed - Complete | 2.3 KB |
| `ARCHITECTURE_DECISION.md` | Pipeline Architecture Decision: Structure Detection Strategy | 4.4 KB |
| `BATCH_SUMMARY.md` | BATCH ANALYSIS COMPLETE ✅ | 5.2 KB |
| `BUG_AUDIT_REPORT.md` | Audiobook Pipeline - Comprehensive Bug Audit Report | 17.0 KB |
| `BUGS_FIXED_SUMMARY.md` | Bug Fixes Applied - 2025-10-03 | 9.5 KB |
| `FIXES_APPLIED.md` | TTS Skipping Issue - Fixes Applied (2025-10-03) | 8.2 KB |
| `phase1-validation/README.md` | No heading detected | 0.0 KB |
| `phase2-extraction/backup/custom_instructions.md` | No heading detected | 1.8 KB |
| `phase2-extraction/backup/phases_steps.md` | No heading detected | 6.3 KB |
| `phase2-extraction/backup/README.md` | No heading detected | 0.0 KB |
| `phase2-extraction/EXTRACTION_FIX.md` | Phase 2 Extraction Fix for Font Encoding Issues | 3.4 KB |
| `phase2-extraction/FIX_GUIDE.md` | 🔧 Phase 2 Gibberish Fix - Step-by-Step Guide | 4.0 KB |
| `phase2-extraction/IMPLEMENTATION_SUMMARY.md` | Phase 2 Enhancement - Implementation Summary | 11.9 KB |
| `phase2-extraction/INSTALL_NEMO_TN.md` | Installing NVIDIA NeMo Text Processing | 3.6 KB |
| `phase2-extraction/QUICK_START.md` | 🚀 Quick Start: Self-Correcting Extraction | 5.9 KB |
| `phase2-extraction/QUICKSTART.md` | Phase 2 Enhancement - Quick Start Guide | 3.9 KB |
| `phase2-extraction/README.md` | phase2_extraction | 0.0 KB |
| `phase2-extraction/README_NEW.md` | Phase 2: Multi-Format Text Extraction & Normalization | 10.1 KB |
| `phase2-extraction/READY_TO_TEST.md` | 🎯 READY TO TEST - Extraction Accuracy Tools | 5.5 KB |
| `phase2-extraction/SELF_CORRECTING_EXTRACTION_GUIDE.md` | Self-Correcting Extraction - Complete Guide | 9.7 KB |
| `phase2-extraction/SETUP_SUMMARY.md` | Phase 2 Cleaner - Setup Summary | 1.7 KB |
| `phase2-extraction/TEST_SCRIPTS_README.md` | Test Scripts for Phase 2 Text Cleaner | 1.6 KB |
| `phase2-extraction/TESTING_GUIDE.md` | 🧪 Phase 2 Extraction Testing Guide | 9.0 KB |
| `phase2-extraction/TESTING_SUMMARY.md` | Phase 2 Testing Summary - Systematic Theology | 2.9 KB |
| `phase2-extraction/TTS_GRADE_UPDATES.md` | TTS-Grade Extraction Updates for extraction.py | 8.4 KB |
| `phase2-extraction/TTS_READY_ACTION_PLAN.md` | 🎯 TTS-Ready Extraction - Final Action Plan | 6.3 KB |
| `phase2-extraction/UPDATE_COMPLETE.md` | Phase 2 Update Complete! 🎉 | 7.1 KB |
| `phase2-extraction/URGENT_FIX.md` | 🚨 URGENT FIX: Phase 2 Quality Issue | 3.2 KB |
| `phase3-chunking/COMPLETION_FIX.md` | Fix for Incomplete Chunk Endings | 4.2 KB |
| `phase3-chunking/PHASE3_FIX_IMPLEMENTATION.md` | Phase 3 Chunking Fix - Flexible Limits Implementation | 10.9 KB |
| `phase3-chunking/PHASE3_UPGRADE_SUMMARY.md` | Phase 3 Genre-Aware Chunking Upgrade | 7.0 KB |
| `PHASE3_4_ANALYSIS.md` | PHASE 3/4 ANALYSIS & FIXES COMPLETE | 12.1 KB |
| `PHASE3_CHUNKING_FIXES.md` | Phase 3 Chunking Fixes - Analysis & Implementation | 9.5 KB |
| `phase4_tts/Chatterbox-TTS-Extended/README.md` | 🚀 Chatterbox-TTS-Extended — All Features & Technical Explanations | 11.0 KB |
| `phase4_tts/PHASE4_VALIDATION_GUIDE.md` | Phase 4 Audio Validation System | 13.2 KB |
| `phase4_tts/UPGRADE_MULTI_VOICE.md` | Phase 4 Multi-Voice Upgrade Guide | 14.6 KB |
| `phase4_tts/VALIDATION_QUICK_REF.md` | Phase 4 Validation - Quick Reference Card | 2.0 KB |
| `phase5_enhancement/CLIPPING_FIX_SUMMARY.md` | Phase 5 Clipping Fix - Summary | 6.9 KB |
| `phase5_enhancement/COMPLETION_SUMMARY.md` | 🎉 Phase 5 Integration: COMPLETE! | 8.6 KB |
| `phase5_enhancement/INDEX.md` | Phase 5 Enhancement - Documentation Index | 4.4 KB |
| `phase5_enhancement/INTEGRATED_README.md` | Phase 5: Integrated Audio Enhancement with Phrase Cleanup | 7.9 KB |
| `phase5_enhancement/INTEGRATION_CHECKLIST.md` | Phase 5 Integration Checklist ✅ | 5.9 KB |
| `phase5_enhancement/INTEGRATION_SUMMARY.md` | Phase 5 Integration Complete! 🎉 | 8.5 KB |
| `phase5_enhancement/QUICK_REFERENCE.md` | Phase 5 Enhancement - Quick Reference & Known Issues | 4.6 KB |
| `phase5_enhancement/QUICK_TEST.md` | Quick Test Commands - Phase 5 Clipping Fix | 2.4 KB |
| `phase5_enhancement/README.md` | No heading detected | 0.0 KB |
| `phase5_enhancement/SESSION_SUMMARY_Nov2025.md` | Session Summary: Meditations Audiobook Phrase Cleaning | 11.6 KB |
| `phase5_enhancement/SINGLE_CHUNK_TEST.md` | Phase 5 Single Chunk Test - FIXED | 3.2 KB |
| `phase5_enhancement/START_HERE.md` | ✅ Unicode Fix Applied - Ready to Test! | 2.2 KB |
| `phase5_enhancement/tree.md` | No heading detected | 22.4 KB |
| `phase5_enhancement/UNICODE_FIX_SUMMARY.md` | Unicode Encoding Fix - Complete Solution | 10.5 KB |
| `PHASE5_GUIDE.md` | Phase 5 Execution Guide - Audio Enhancement | 8.7 KB |
| `phase6_orchestrator/CHUNK_ORDER_BUG_FIX.md` | 🐛 CRITICAL BUG FOUND & FIXED - Chunk Order Issue | 4.3 KB |
| `phase6_orchestrator/COVERAGE_TEST_FIXES.md` | Coverage Test Fixes Applied | 1.4 KB |
| `phase6_orchestrator/COVERAGE_TEST_GUIDE.md` | Coverage Test Guide | 4.0 KB |
| `phase6_orchestrator/COVERAGE_TEST_RESULTS.md` | Coverage Test Results Summary | 4.2 KB |
| `phase6_orchestrator/CRITICAL_ISSUES_FOUND.md` | 🚨 CRITICAL ISSUES FOUND - Gift of the Magi Run | 4.6 KB |
| `phase6_orchestrator/custom_instructions.md` | No heading detected | 8.7 KB |
| `phase6_orchestrator/EMERGENCY_FIX_README.md` | 🚨 Emergency Fix for Phase 5 | 5.1 KB |
| `phase6_orchestrator/EMERGENCY_FIX_V2_README.md` | 🔴 Why Emergency Fix v1 Failed | 3.3 KB |
| `phase6_orchestrator/EMERGENCY_FIX_V3_EXPLANATION.md` | Emergency Fix v3 - THE PATH RESOLUTION BUG 🐛 | 2.4 KB |
| `phase6_orchestrator/FAILURE_ANALYSIS.md` | 🚨 Phase 5 Failure Analysis & Fix | 5.6 KB |
| `phase6_orchestrator/GIFT_OF_MAGI_GUIDE.md` | 🎄 Gift of the Magi - Pipeline Test Guide | 6.8 KB |
| `phase6_orchestrator/GOOD_NEWS_ANALYSIS.md` | 🎉 GOOD NEWS - Gift of the Magi Analysis | 5.2 KB |
| `phase6_orchestrator/LANGUAGE_FIX_COMPLETE.md` | Phase 4 Gibberish Fix - Complete Solution | 6.2 KB |
| `phase6_orchestrator/PATH_AUDIT.md` | Phase 6 Orchestrator Path Audit | 5.6 KB |
| `phase6_orchestrator/PHASE3_FIX_CLEAN_TEXT.md` | Phase 3 Clean Text Fix | 3.1 KB |
| `phase6_orchestrator/PHASE3_FIX_SUMMARY.md` | Phase 3 Fix Summary | 6.2 KB |
| `phase6_orchestrator/PHASE3_STATUS.md` | 📋 Phase 3 Status - Complete Analysis | 6.7 KB |
| `phase6_orchestrator/PHASE4_BUGS_FIXED.md` | Phase 4 Bug Fixes | 1.9 KB |
| `phase6_orchestrator/PHASE4_FIX.md` | Phase 4 Fix - File ID Mismatch | 5.8 KB |
| `phase6_orchestrator/PHASE4_FIX_V2.md` | Phase 4 Fix v2 - Relative Paths Issue | 2.2 KB |
| `phase6_orchestrator/PHASE5_FIX_EXPLANATION.md` | Phase 5 Fix - Complete Explanation | 7.3 KB |
| `phase6_orchestrator/PHASE5_TROUBLESHOOTING.md` | Phase 5 Troubleshooting Guide | 4.4 KB |
| `phase6_orchestrator/QUICK_START.md` | 🚀 Quick Start Guide - Phase 3 Fixed | 4.7 KB |
| `phase6_orchestrator/QUICK_TEST.md` | Quick Test - Phase 4 Fix | 1.3 KB |
| `phase6_orchestrator/README.md` | Phase 6: Orchestrator | 4.2 KB |
| `phase6_orchestrator/SETUP_COMPLETE.md` | Phase 6 Orchestrator - Setup Complete | 4.6 KB |
| `phase6_orchestrator/TROUBLESHOOTING.md` | 🔧 Troubleshooting Guide - Phase 3 | 6.0 KB |
| `phase7_batch/BUGFIX_APPLIED.md` | Quick Bug Fixes Applied | 1.2 KB |
| `phase7_batch/BUILD_COMPLETE.md` | Phase 7 Build Complete - Summary | 12.0 KB |
| `phase7_batch/IMPLEMENTATION_SUMMARY.md` | Phase 7 Implementation Summary | 13.8 KB |
| `phase7_batch/INDEX.md` | Phase 7 Documentation Index | 8.0 KB |
| `phase7_batch/MIGRATION_GUIDE.md` | Migrating from Old Phase 7 to New Phase 7 | 11.0 KB |
| `phase7_batch/QUICKSTART.md` | Phase 7 Quick Start Guide | 6.1 KB |
| `phase7_batch/README.md` | Phase 7: Batch Processing | 12.9 KB |
| `phase7_batch/START_HERE.md` | 🎉 Phase 7 Build Complete! | 9.0 KB |
| `phase7_batch/TESTING_CHECKLIST.md` | Phase 7 Testing Checklist | 8.5 KB |
| `phase7_batch/tree.md` | Tree generated on 2025-09-26; Scan duration: 0.45s | 8.3 KB |
| `phase7_batch/UNICODE_FIX_COMPLETE.md` | Unicode Fix Applied | 1.2 KB |
| `PHASE_5.5_SUBTITLES_PLAN.md` | Phase 5.5: Subtitle Generation - Implementation Plan | 1.5 KB |
| `PHASE_6.5_PUBLISHING_PLAN.md` | Phase 6.5: Publishing & Release Package Plan | 1.7 KB |
| `phase_audio_cleanup/QUICKSTART.md` | Audio Cleanup - Quick Start Guide | 2.9 KB |
| `phase_audio_cleanup/README.md` | Audio Phrase Cleanup - Standalone Utility | 8.2 KB |
| `PROJECT_AUDIT.md` | Project Audit | 5849.5 KB |
| `PYTHON_VERSION_FIX.md` | Phase 1 Python Version Fix | 0.9 KB |
| `STRUCTURE_ENHANCEMENT_README.md` | Phase 2 & 3 Enhancements: Structure-Based Chunking | 3.6 KB |
| `VALIDATION_TESTS.md` | Quick Validation Guide - Test All Fixes | 5.2 KB |
| `VOICE_OVERRIDE_GUIDE.md` | Voice Override Guide | 8.3 KB |
| `VOICE_OVERRIDE_INTEGRATION.md` | Voice Override System - Integration Summary | 13.9 KB |
| `VOICE_OVERRIDE_USAGE_GUIDE.md` | Voice Override System - Complete Guide | 8.8 KB |
| `VOICE_SELECTION_GUIDE.md` | Voice Selection & Override Guide | 12.0 KB |
| `VOICE_SYSTEM_COMPLETE.md` | Voice Override System - Implementation Complete ✅ | 10.0 KB |
| `VOICE_SYSTEM_TESTING.md` | Quick Start Testing Guide - Voice Override System | 9.6 KB |

## 4. Config Files (JSON / YAML / TOML)
| File | Type | Size |
| --- | --- | --- |
| `configs/voice_references.json` | json | 1.0 KB |
| `configs/voices.json` | json | 8.6 KB |
| `phase1-validation/config.yaml` | yaml | 0.2 KB |
| `phase1-validation/pipeline.json` | json | 1.4 KB |
| `phase1-validation/pyproject.toml` | toml | 0.7 KB |
| `phase2-extraction/config.yaml` | yaml | 0.3 KB |
| `phase2-extraction/extracted_text/analects_test_meta.json` | json | 1.0 KB |
| `phase2-extraction/extracted_text/analects_test_v2_meta.json` | json | 1.1 KB |
| `phase2-extraction/pipeline.json` | json | 2.9 KB |
| `phase2-extraction/poetry.toml` | toml | 0.0 KB |
| `phase2-extraction/pyproject.toml` | toml | 1.0 KB |
| `phase2-extraction/src/pipeline.json` | json | 0.8 KB |
| `phase3-chunking/.claude/settings.local.json` | json | 0.7 KB |
| `phase3-chunking/config.yaml` | yaml | 0.8 KB |
| `phase3-chunking/pipeline.json` | json | 5763.8 KB |
| `phase3-chunking/poetry.toml` | toml | 0.0 KB |
| `phase3-chunking/pyproject.toml` | toml | 0.7 KB |
| `phase3-chunking/src/phase3_chunking/config.yaml` | yaml | 0.3 KB |
| `phase4_tts/config.yaml` | yaml | 1.1 KB |
| `phase4_tts/configs/voice_references.json` | json | 12.2 KB |
| `phase4_tts/validation_config.yaml` | yaml | 1.8 KB |
| `phase4_tts/voice_comparison_test/voice_test_results.json` | json | 5.6 KB |
| `phase5_enhancement/.claude/settings.local.json` | json | 0.2 KB |
| `phase5_enhancement/config.yaml` | yaml | 1.0 KB |
| `phase5_enhancement/poetry.toml` | toml | 0.0 KB |
| `phase5_enhancement/pyproject.toml` | toml | 0.8 KB |
| `phase5_enhancement/src/phase5_enhancement/config.yaml` | yaml | 1.1 KB |
| `phase5_enhancement/src/phase5_enhancement/config_integrated.yaml` | yaml | 1.1 KB |
| `phase6_orchestrator/config.yaml` | yaml | 0.3 KB |
| `phase6_orchestrator/pyproject.toml` | toml | 0.7 KB |
| `phase7_batch/config.yaml` | yaml | 0.8 KB |
| `phase7_batch/my_config.yaml` | yaml | 0.4 KB |
| `phase7_batch/pyproject.toml` | toml | 0.8 KB |
| `phase_audio_cleanup/config/phrases.yaml` | yaml | 0.8 KB |
| `phase_audio_cleanup/pyproject.toml` | toml | 0.6 KB |
| `pipeline.json` | json | 34803.2 KB |
| `pipeline_backup.json` | json | 1094.3 KB |
| `pipeline_magi.json` | json | 1554.9 KB |
| `pipeline_summary.json` | json | 0.9 KB |
| `pipeline_test.json` | json | 0.8 KB |

## 5. TODO / FIXME / HACK Tracker
| Location | Tag | Context |
| --- | --- | --- |
| `PROJECT_AUDIT.md:62833` | TODO | \| `phase2-extraction/.venv/Lib/site-packages/pygments/lexers/testing.py:200` \| TODO \| (r'(?i)\bTODO\b', Comment.Preproc), \| |
| `PROJECT_AUDIT.md:62834` | TODO | \| `phase3-chunking/.venv/Lib/site-packages/pygments/lexers/testing.py:200` \| TODO \| (r'(?i)\bTODO\b', Comment.Preproc), \| |
| `PROJECT_AUDIT.md:62835` | TODO | \| `phase5_enhancement/.venv/Lib/site-packages/pygments/lexers/testing.py:200` \| TODO \| (r'(?i)\bTODO\b', Comment.Preproc), \| |
| `PROJECT_AUDIT.md:62836` | TODO | \| `phase6_orchestrator/.venv/Lib/site-packages/pygments/lexers/testing.py:200` \| TODO \| (r'(?i)\bTODO\b', Comment.Preproc), \| |
| `PROJECT_AUDIT.md:62837` | TODO | \| `phase7_batch/.venv/Lib/site-packages/pygments/lexers/testing.py:200` \| TODO \| (r'(?i)\bTODO\b', Comment.Preproc), \| |

## 6. pyproject.toml Dependencies
### `phase1-validation/pyproject.toml`
- No runtime dependencies declared

### `phase2-extraction/pyproject.toml`
**Runtime dependencies**
- `pdfplumber` – 0.11.4
- `pdfminer.six` – 20231228
- `pymupdf` – 1.26.4
- `unstructured` – 0.18.15
- `easyocr` – 1.7.2
- `nostril` – 0.1.1
- `nltk` – 3.9.1
- `langdetect` – 1.0.9
- `numpy` – 2.3.3
- `pydantic` – 2.11.9
- `pyyaml` – ^6.0.1
- `charset-normalizer` – ^3.4.3
- `num2words` – ^0.5.14
- `unidecode` – ^1.4.0
- `clean-text` – ^0.6.0
- `python-docx` – ^1.1.0
- `ebooklib` – ^0.18
- `beautifulsoup4` – ^4.12.0
- `lxml` – ^5.0.0
- `python-magic` – ^0.4.27
- `readability-lxml` – ^0.8.1
- `pdf2image` – ^1.17.0
- `pypdf` – ^5.1.0
- `python-magic-bin` – ^0.4.14
**[dev] group**
- `pytest` – ^8.3.3

### `phase3-chunking/pyproject.toml`
**Runtime dependencies**
- `spacy` – 3.8.4
- `sentence-transformers` – 5.1.0
- `gensim` – 4.3.3
- `textstat` – 0.7.4
- `nltk` – 3.9.1
- `ftfy` – 6.3.1
- `pyyaml` – ^6.0.1
- `filelock` – ^3.19.1
- `langdetect` – 1.0.9
- `charset-normalizer` – ^3.4.3
**[dev] group**
- `pytest` – ^8.4.2
- `pytest-cov` – ^7.0.0

### `phase5_enhancement/pyproject.toml`
**Runtime dependencies**
- `noisereduce` – 3.0.3
- `pyloudnorm` – 0.1.1
- `pydub` – 0.25.1
- `mutagen` – 1.47.0
- `librosa` – 0.11.0
- `pydantic` – 2.11.9
- `pyyaml` – ^6.0.2
- `soundfile` – ^0.13.1
- `psutil` – ^7.1.0
- `charset-normalizer` – ^3.4.3
- `faster-whisper` – ^1.0.0
- `python-dateutil` – ^2.8.2
- `requests` – ^2.32.5
- `webvtt-py` – ^0.5.1
- `jiwer` – ^3.0.3
- `srt` – ^3.5.3
**[dev] group**
- `pytest` – 8.4.2
- `pytest-mock` – 3.15.1

### `phase6_orchestrator/pyproject.toml`
**Runtime dependencies**
- `pydantic` – ^2.0
- `rich` – ^13.0
- `pyyaml` – ^6.0
- `charset-normalizer` – ^3.4.3
- `python-docx` – ^1.2.0
- `ebooklib` – ^0.19
- `beautifulsoup4` – ^4.14.2
- `lxml` – ^6.0.2
- `readability-lxml` – ^0.8.4.1
- `pdf2image` – ^1.17.0
- `pypdf` – ^6.1.1
- `python-magic-bin` – ^0.4.14

### `phase7_batch/pyproject.toml`
**Runtime dependencies**
- `trio==0.31.0` – unspecified
- `tqdm==4.67.1` – unspecified
- `psutil==7.1.0` – unspecified
- `pyyaml>=6.0.2,<7.0.0` – unspecified
- `pydantic==2.11.9` – unspecified
- `rich==14.1.0` – unspecified

### `phase_audio_cleanup/pyproject.toml`
**Runtime dependencies**
- `faster-whisper` – ^1.0.0
- `pydub` – ^0.25.1
- `pyyaml` – ^6.0
- `python-dateutil` – ^2.8.2
- `requests` – ^2.32.5
