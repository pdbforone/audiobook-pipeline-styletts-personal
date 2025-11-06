# Instructions for integrating phrase cleanup into main.py

"""
INTEGRATION STEPS:

1. Add import at top of main.py:
   from phrase_cleaner import PhraseCleaner, PhraseCleanerConfig

2. Initialize cleaner in main() after loading config:
   # Initialize phrase cleaner
   cleaner_config = PhraseCleanerConfig(
       enabled=config.enable_phrase_cleanup,
       target_phrases=config.cleanup_target_phrases,
       model_size=config.cleanup_whisper_model,
       save_transcripts=config.cleanup_save_transcripts
   )
   phrase_cleaner = PhraseCleaner(cleaner_config)

3. Modify enhance_chunk() function signature to accept phrase_cleaner:
   def enhance_chunk(
       metadata: AudioMetadata,
       config: EnhancementConfig,
       temp_dir: str,
       phrase_cleaner: PhraseCleaner  # ADD THIS
   ) -> tuple[AudioMetadata, np.ndarray]:

4. Add cleanup step at the beginning of enhance_chunk(), before loading audio:
   # Phrase cleanup (if enabled)
   cleaned_audio, cleanup_sr, cleanup_metadata = phrase_cleaner.clean_audio(Path(wav_path))
   metadata.cleanup_status = cleanup_metadata['status']
   metadata.phrases_removed = cleanup_metadata.get('phrases_removed', 0)
   metadata.cleanup_processing_time = cleanup_metadata.get('processing_time', 0.0)
   
   # Load audio (use cleaned version if available)
   if cleaned_audio is not None:
       logger.info(f"Using cleaned audio for chunk {metadata.chunk_id}")
       audio = cleaned_audio
       sr = cleanup_sr
   else:
       # Original loading logic
       audio, sr = librosa.load(wav_path, sr=config.sample_rate, mono=True)

5. Update the executor.submit() call in main() to pass phrase_cleaner:
   futures = {
       executor.submit(enhance_chunk, chunk, config, temp_dir, phrase_cleaner): chunk
       for chunk in chunks
   }

6. Update metrics aggregation in main() to include cleanup stats:
   cleanup_stats = {
       'chunks_cleaned': sum(1 for m in processed_metadata if m.cleanup_status == 'cleaned'),
       'chunks_already_clean': sum(1 for m in processed_metadata if m.cleanup_status == 'clean'),
       'total_phrases_removed': sum(m.phrases_removed or 0 for m in processed_metadata),
       'avg_cleanup_time': np.mean([m.cleanup_processing_time for m in processed_metadata if m.cleanup_processing_time]) if any(m.cleanup_processing_time for m in processed_metadata) else 0.0
   }
   phase5_data['metrics']['cleanup'] = cleanup_stats

"""

# This file contains instructions only
# The actual integration requires modifying the existing main.py
# Run install_with_cleanup.bat first, then manually integrate these changes
