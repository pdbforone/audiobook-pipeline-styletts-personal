# main.py - Phase 4 Entry Point with Validation (UPDATED)
# Why: Handles TTS synthesis with voice cloning + Two-tier validation system
# New: Tier 1 (fast checks) + Tier 2 (Whisper) validation to catch corruption early
# Run: python src/main.py --file_id The_Analects_of_Confucius_20240228 --json_path ../pipeline.json

import argparse
import logging
import sys
import time
import yaml
import json
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parent

# Add fork to path (why: Local clone in phase4_tts/Chatterbox-TTS-Extended)
sys.path.insert(0, str(MODULE_ROOT.parent / "Chatterbox-TTS-Extended" / "chatterbox" / "src"))

try:
    from chatterbox.tts import ChatterboxTTS
except ImportError as e:
    logging.error(f"Import failed: {e}. Ensure Chatterbox-TTS-Extended is cloned in phase4_tts/Chatterbox-TTS-Extended.")
    sys.exit(1)

import torch
try:
    from .models import TTSConfig, TTSRecord
    from .utils import (
        prepare_reference_audio, 
        prepare_voice_references,
        get_selected_voice_from_phase3,
        resolve_pipeline_file,
        synthesize_chunk, 
        evaluate_mos_proxy, 
        merge_to_pipeline_json
    )
    from .validation import (
        ValidationConfig,
        validate_audio_chunk,
    )
except ImportError:
    sys.path.insert(0, str(MODULE_ROOT))
    from models import TTSConfig, TTSRecord
    from utils import (
        prepare_reference_audio, 
        prepare_voice_references,
        get_selected_voice_from_phase3,
        resolve_pipeline_file,
        synthesize_chunk, 
        evaluate_mos_proxy, 
        merge_to_pipeline_json
    )
    from validation import (
        ValidationConfig,
        validate_audio_chunk,
    )

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def get_chunk_file_path(json_path: str, file_id: str, chunk_id: str = None) -> tuple[list[str] | str, str]:
    """Load chunk paths from phase3 in pipeline.json."""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        resolved_key, phase3_entry = resolve_pipeline_file(data, "phase3", file_id)
        if not phase3_entry:
            return [], f"File '{file_id}' not found in phase3 output"

        if resolved_key and resolved_key != file_id:
            logger.info(f"Using Phase 3 entry '{resolved_key}' for requested file_id '{file_id}'")

        chunks = phase3_entry.get("chunk_paths", [])
        if not chunks:
            return [], "No chunk paths recorded for requested file"

        if chunk_id is not None:
            try:
                index = int(chunk_id)
            except ValueError:
                return [], f"Invalid chunk_id '{chunk_id}' (expected integer index)"

            if index < 0 or index >= len(chunks):
                return [], f"Chunk index {index} out of range (0-{len(chunks) - 1})"
            return chunks[index], ""

        return chunks, ""
    except Exception as e:
        return [], f"Error loading chunks: {e}"

def load_config(config_path: str = "config.yaml") -> TTSConfig:
    """Load YAML config from src/."""
    try:
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        return TTSConfig(**data)
    except:
        logger.warning("Config load failed; using defaults")
        return TTSConfig(ref_url="https://www.archive.org/download/roughing_it_jg/rough_09_twain.mp3")


def load_validation_config(config_path: str = "validation_config.yaml") -> ValidationConfig:
    """Load validation configuration from YAML."""
    try:
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        validation_data = data.get("validation", {})
        tier1 = validation_data.get("tier1", {})
        tier2 = validation_data.get("tier2", {})
        
        return ValidationConfig(
            enable_tier1=tier1.get("enabled", True),
            duration_tolerance_sec=tier1.get("duration_tolerance_sec", 5.0),
            silence_threshold_sec=tier1.get("silence_threshold_sec", 2.0),
            min_amplitude_db=tier1.get("min_amplitude_db", -40.0),
            enable_tier2=tier2.get("enabled", True),
            whisper_model=tier2.get("whisper_model", "base"),
            whisper_sample_rate=tier2.get("whisper_sample_rate", 0.05),
            whisper_first_n=tier2.get("whisper_first_n", 10),
            whisper_last_n=tier2.get("whisper_last_n", 10),
            max_wer=tier2.get("max_wer", 0.10),
            error_phrases=validation_data.get("error_phrases", []),
        )
    except Exception as e:
        logger.warning(f"Validation config load failed: {e}, using defaults")
        return ValidationConfig()


def retry_chunk_synthesis(model, text, ref_path, output_path, config, chunk_id, max_attempts=3, delay_sec=5.0):
    """
    Retry chunk synthesis with exponential backoff.
    
    Args:
        model: TTS model
        text: Chunk text
        ref_path: Reference audio path
        output_path: Output wav path
        config: TTS config
        chunk_id: Chunk identifier
        max_attempts: Maximum retry attempts
        delay_sec: Delay between retries (seconds)
    
    Returns:
        (success: bool, split_meta: dict)
    """
    for attempt in range(max_attempts):
        if attempt > 0:
            logger.info(f"Retry attempt {attempt+1}/{max_attempts} for chunk {chunk_id}")
            time.sleep(delay_sec * attempt)  # Exponential backoff
        
        success, split_meta = synthesize_chunk(model, text, ref_path, str(output_path), config, chunk_id)
        
        if success:
            return True, split_meta
    
    logger.error(f"Chunk {chunk_id} failed after {max_attempts} attempts")
    return False, {}


def main():
    parser = argparse.ArgumentParser(description="Phase 4: TTS Synthesis with Voice Cloning + Validation")
    parser.add_argument("--file_id", required=True, help="File ID from Phase 3")
    parser.add_argument("--chunk_id", help="Specific chunk ID (optional; else all)")
    parser.add_argument("--json_path", default="../pipeline.json", help="Pipeline JSON")
    parser.add_argument("--config", default="config.yaml", help="TTS config YAML")
    parser.add_argument("--validation_config", default="validation_config.yaml", help="Validation config YAML")
    parser.add_argument("--voice_id", help="Override voice selection (key from configs/voice_references.json)")
    parser.add_argument("--skip_validation", action="store_true", help="Skip validation (not recommended)")
    args = parser.parse_args()

    config = load_config(args.config)
    validation_config = load_validation_config(args.validation_config)
    
    json_path = Path(args.json_path).resolve()
    output_dir = Path(config.output_dir).resolve()
    output_dir.mkdir(exist_ok=True)

    # 🆕 NEW: Prepare all voice references (downloads + caches)
    logger.info("Preparing voice references...")
    voice_references = prepare_voice_references(
        voice_config_path="configs/voice_references.json",
        cache_dir="voice_references"
    )
    
    if not voice_references:
        logger.error("No voice references prepared. Falling back to legacy ref_url method.")
        ref_path = prepare_reference_audio(config)
        selected_voice = "default"
    else:
        # 🆕 NEW: Get voice selection from Phase 3
        selected_voice = get_selected_voice_from_phase3(str(json_path), args.file_id)
        # CLI override if provided
        if args.voice_id:
            if args.voice_id in voice_references:
                selected_voice = args.voice_id
                logger.info(f"Using overridden voice: {selected_voice}")
            else:
                logger.warning(f"Override voice_id '{args.voice_id}' not found in voice_references. Ignoring.")
        
        if selected_voice and selected_voice in voice_references:
            ref_path = voice_references[selected_voice]
            logger.info(f"✅ Using voice: {selected_voice} ({ref_path})")
        else:
            # Fallback to neutral_narrator or first available voice
            if "neutral_narrator" in voice_references:
                ref_path = voice_references["neutral_narrator"]
                selected_voice = "neutral_narrator"
                logger.warning(f"Voice '{selected_voice}' not found, using neutral_narrator")
            else:
                # Use first available voice
                selected_voice = list(voice_references.keys())[0]
                ref_path = voice_references[selected_voice]
                logger.warning(f"Using fallback voice: {selected_voice}")

    # Load model (CPU-only)
    try:
        original_load = torch.load
        def cpu_load(*args, **kwargs):
            kwargs['map_location'] = 'cpu'
            return original_load(*args, **kwargs)
        torch.load = cpu_load

        model = ChatterboxTTS.from_pretrained(device="cpu")
        model.sr = config.sample_rate

        torch.load = original_load
        logger.info("Model loaded on CPU")
    except Exception as e:
        logger.error(f"Model load failed: {e}. Check internet or deps.")
        return 1

    # Get chunks
    chunks, error = get_chunk_file_path(str(json_path), args.file_id, args.chunk_id)
    if error or not chunks:
        logger.error(f"No chunks: {error}")
        return 1

    success_count = 0
    validation_stats = {
        "tier1_pass": 0,
        "tier1_fail": 0,
        "tier2_pass": 0,
        "tier2_fail": 0,
        "tier2_sampled": 0,
        "retries": 0,
    }
    
    # Convert to list if single chunk
    chunks_to_process = [chunks] if isinstance(chunks, str) else chunks
    total_chunks = len(chunks_to_process)
    
    logger.info(f"{'='*80}")
    logger.info(f"Starting Phase 4 TTS with Validation")
    logger.info(f"Total chunks: {total_chunks}")
    logger.info(f"Validation enabled: {'Yes' if not args.skip_validation else 'No'}")
    if not args.skip_validation:
        logger.info(f"  - Tier 1 (fast): {'Enabled' if validation_config.enable_tier1 else 'Disabled'}")
        logger.info(f"  - Tier 2 (Whisper): {'Enabled' if validation_config.enable_tier2 else 'Disabled'}")
        logger.info(f"  - Whisper model: {validation_config.whisper_model}")
        logger.info(f"  - Sample rate: {validation_config.whisper_sample_rate*100:.1f}%")
    logger.info(f"{'='*80}\n")
    
    for idx, chunk_path in enumerate(chunks_to_process):
        chunk_file = Path(chunk_path).resolve()
        if not chunk_file.exists():
            logger.error(f"Chunk missing: {chunk_file}")
            continue

        with open(chunk_file, 'r', encoding='utf-8') as f:
            text = f.read().strip()

        chunk_id = Path(chunk_path).stem
        output_wav = output_dir / f"{chunk_id}.wav"
        torch.manual_seed(42 + int(chunk_id.split('_')[-1]))

        logger.info(f"\n{'='*80}")
        logger.info(f"Processing chunk {idx+1}/{total_chunks}: {chunk_id}")
        logger.info(f"{'='*80}")

        # Synthesize chunk (with retry logic)
        start_phase = time.perf_counter()
        success, split_meta = retry_chunk_synthesis(
            model, text, ref_path, str(output_wav), config, chunk_id,
            max_attempts=3, delay_sec=5.0
        )
        duration_phase = time.perf_counter() - start_phase

        if not success:
            # Synthesis failed - log and continue
            mos = 0.0
            metrics = {}
            errors = ["Synthesis failed after retries"]
            validation_result = {
                "tier1": None,
                "tier2": None,
                "validation_passed": False
            }
            logger.error(f"❌ Chunk {chunk_id} synthesis failed")
        else:
            # Synthesis succeeded - validate
            mos = evaluate_mos_proxy(str(output_wav), config.sample_rate)
            metrics = {
                "duration_per_chunk": duration_phase,
                "splitting_enabled": config.enable_splitting,
                "selected_voice": selected_voice
            }
            errors = []
            
            # 🆕 NEW: Run validation checks
            validation_result = {
                "tier1": None,
                "tier2": None,
                "validation_passed": True
            }
            
            if not args.skip_validation:
                logger.info(f"\n--- Running Validation for {chunk_id} ---")
                
                tier1_result, tier2_result = validate_audio_chunk(
                    text, str(output_wav), idx, total_chunks, validation_config
                )
                
                # Store validation results
                validation_result["tier1"] = {
                    "passed": tier1_result.is_valid,
                    "reason": tier1_result.reason,
                    "details": tier1_result.details,
                    "duration_sec": tier1_result.duration_sec
                }
                
                if not tier1_result.is_valid:
                    validation_stats["tier1_fail"] += 1
                    validation_result["validation_passed"] = False
                    logger.error(f"❌ Tier 1 validation failed: {tier1_result.reason}")
                    errors.append(f"validation_tier1_{tier1_result.reason}")
                else:
                    validation_stats["tier1_pass"] += 1
                    logger.info(f"✅ Tier 1 validation passed")
                
                if tier2_result:
                    validation_stats["tier2_sampled"] += 1
                    validation_result["tier2"] = {
                        "passed": tier2_result.is_valid,
                        "reason": tier2_result.reason,
                        "details": tier2_result.details,
                        "duration_sec": tier2_result.duration_sec
                    }
                    
                    if not tier2_result.is_valid:
                        validation_stats["tier2_fail"] += 1
                        validation_result["validation_passed"] = False
                        logger.error(f"❌ Tier 2 validation failed: {tier2_result.reason}")
                        errors.append(f"validation_tier2_{tier2_result.reason}")
                    else:
                        validation_stats["tier2_pass"] += 1
                        logger.info(f"✅ Tier 2 validation passed (WER: {tier2_result.details.get('wer', 'N/A')})")
                
                # Add validation results to metrics
                metrics["validation"] = validation_result
                
                logger.info(f"--- Validation Complete ---\n")
            
            if validation_result["validation_passed"]:
                success_count += 1
        
        # Merge to pipeline.json
        timestamps = {"start": start_phase, "end": time.perf_counter(), "duration": duration_phase}
        
        merge_to_pipeline_json(
            str(json_path), args.file_id, chunk_id, success, str(output_wav), 
            mos, metrics, errors, timestamps, split_metadata=split_meta
        )

        status = "✅ SUCCESS" if success and validation_result["validation_passed"] else "❌ FAILED"
        logger.info(f"Chunk {chunk_id}: {status}, MOS: {mos:.2f}")

    # Print summary
    logger.info(f"\n{'='*80}")
    logger.info(f"PHASE 4 SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Total chunks: {total_chunks}")
    logger.info(f"Successful: {success_count}/{total_chunks} ({success_count/total_chunks*100:.1f}%)")
    
    if not args.skip_validation:
        logger.info(f"\nValidation Statistics:")
        logger.info(f"  Tier 1 Pass: {validation_stats['tier1_pass']}")
        logger.info(f"  Tier 1 Fail: {validation_stats['tier1_fail']}")
        if validation_stats['tier2_sampled'] > 0:
            logger.info(f"  Tier 2 Sampled: {validation_stats['tier2_sampled']}")
            logger.info(f"  Tier 2 Pass: {validation_stats['tier2_pass']}")
            logger.info(f"  Tier 2 Fail: {validation_stats['tier2_fail']}")
    logger.info(f"{'='*80}\n")
    
    overall_status = "success" if success_count == total_chunks else "partial"
    logger.info(f"Phase 4 {overall_status}: {success_count}/{total_chunks} chunks")
    return 0 if overall_status == "success" else 1

if __name__ == "__main__":
    exit(main())
