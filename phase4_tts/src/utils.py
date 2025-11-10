# utils.py - Helper Functions for Phase 4
# Why: Modularizes logic (e.g., ref prep, synthesis) for reuse/testability. Handles splitting to prevent truncation.
# Dependencies: Add to pyproject.toml or pip in env: torchaudio, librosa, requests, nltk.
# For HQ cloning: Ref audio trimmed to 10-20s clean speech; model uses zero-shot via audio_prompt_path.

import os
import json
import time
import logging
import torch
import torchaudio as ta
import librosa
import requests
import nltk
from nltk.tokenize import sent_tokenize
from pathlib import Path
from typing import Tuple, Optional, Dict, List
import numpy as np
import re
import unicodedata
import difflib

try:
    from .models import TTSConfig, TTSRecord
except ImportError:
    from models import TTSConfig, TTSRecord

logger = logging.getLogger(__name__)
nltk.download('punkt', quiet=True)  # For splitting


def _slugify(value: Optional[str]) -> str:
    """
    Create a normalized slug for fuzzy file_id comparisons.
    Lowercases, strips accents, and collapses non-alphanumeric characters.
    """
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")


def resolve_pipeline_file(data: Dict[str, dict], phase: str, file_id: str) -> Tuple[Optional[str], Optional[dict]]:
    """
    Resolve a file entry from pipeline data using flexible matching.

    Returns the resolved key and the corresponding payload, or (None, None) if not found.
    """
    if not file_id:
        return None, None

    phase_section = data.get(phase, {})
    files = phase_section.get("files", {})
    if not isinstance(files, dict) or not files:
        return None, None

    if file_id in files:
        return file_id, files[file_id]

    target_slug = _slugify(file_id)
    if not target_slug:
        return None, None

    slugged_items = [(key, _slugify(key)) for key in files.keys()]

    for key, slug in slugged_items:
        if slug == target_slug:
            logger.info(f"Resolved {phase} file_id '{file_id}' -> '{key}' (slug match)")
            return key, files[key]

    for key, slug in slugged_items:
        if target_slug and target_slug in slug:
            logger.info(f"Resolved {phase} file_id '{file_id}' -> '{key}' (substring match)")
            return key, files[key]

    for key, slug in slugged_items:
        if slug and slug in target_slug:
            logger.info(f"Resolved {phase} file_id '{file_id}' -> '{key}' (reverse substring match)")
            return key, files[key]

    candidates = [slug for _, slug in slugged_items if slug]
    if candidates:
        match = difflib.get_close_matches(target_slug, candidates, n=1, cutoff=0.6)
        if match:
            matched_slug = match[0]
            for key, slug in slugged_items:
                if slug == matched_slug:
                    logger.info(f"Resolved {phase} file_id '{file_id}' -> '{key}' (fuzzy match)")
                    return key, files[key]

    return None, None

def get_selected_voice_from_phase3(json_path: str, file_id: str) -> Optional[str]:
    """
    Read selected voice from Phase 3 output.
    
    Args:
        json_path: Path to pipeline.json
        file_id: File identifier
        
    Returns:
        Voice ID or None if not found
    """
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        resolved_key, phase3_data = resolve_pipeline_file(data, "phase3", file_id)
        if not phase3_data:
            logger.warning(f"No Phase 3 entry found for file_id '{file_id}'")
            return None

        if resolved_key and resolved_key != file_id:
            logger.info(f"Using Phase 3 entry '{resolved_key}' for requested file_id '{file_id}'")

        selected_voice = phase3_data.get("suggested_voice")
        if not selected_voice:
            chunk_metrics = phase3_data.get("chunk_metrics", {})
            selected_voice = chunk_metrics.get("selected_voice")
        
        if selected_voice:
            logger.info(f"Phase 3 selected voice: {selected_voice}")
            return selected_voice
        else:
            logger.warning("No voice selection found in Phase 3 output")
            return None
            
    except Exception as e:
        logger.error(f"Could not read Phase 3 voice selection: {e}")
        return None


def prepare_voice_references(
    voice_config_path: str = "configs/voice_references.json",
    cache_dir: str = "voice_references"
) -> Dict[str, str]:
    """
    Prepare all voice references from voice_references.json.
    
    Downloads and prepares audio samples for each voice, caching them locally.
    If a reference already exists and is valid, skips re-downloading.
    
    Args:
        voice_config_path: Path to voice_references.json
        cache_dir: Directory to cache prepared voice references
        
    Returns:
        Dict mapping voice_id → reference wav path
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(exist_ok=True)
    
    try:
        with open(voice_config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error(f"Voice references config not found: {voice_config_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in voice references config: {e}")
        return {}
    
    voice_refs = config.get("voice_references", {})
    prep_settings = config.get("reference_prep_settings", {})
    
    target_sr = prep_settings.get("target_sample_rate", 24000)
    
    prepared_refs = {}
    
    for voice_id, voice_data in voice_refs.items():
        output_path = cache_path / f"{voice_id}.wav"
        
        # Check for local_path first (NEW: support for pre-processed local samples)
        local_path = voice_data.get("local_path")
        if local_path:
            local_file = Path(local_path)
            if local_file.exists():
                try:
                    # Load and validate local file
                    y, sr = librosa.load(str(local_file), sr=None, mono=True)
                    duration = len(y) / sr
                    
                    # Resample if needed
                    if sr != target_sr:
                        y_resampled = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
                        # Save resampled version to cache
                        ta.save(str(output_path), torch.tensor(y_resampled).unsqueeze(0), target_sr)
                        prepared_refs[voice_id] = str(output_path)
                        logger.info(f"✅ Loaded local reference {voice_id}: {duration:.1f}s (resampled {sr}→{target_sr}Hz)")
                    else:
                        # Use original file directly
                        prepared_refs[voice_id] = str(local_file)
                        logger.info(f"✅ Using local reference {voice_id}: {duration:.1f}s")
                    continue
                except Exception as e:
                    logger.error(f"Failed to load local reference {voice_id} from {local_path}: {e}")
            else:
                logger.warning(f"Local path not found for {voice_id}: {local_path}")
        
        # Skip if already prepared and valid (for URL-based voices)
        if output_path.exists():
            try:
                y, sr = librosa.load(str(output_path), sr=None)
                duration = len(y) / sr
                min_dur = prep_settings.get("target_duration_min", 10)
                max_dur = prep_settings.get("target_duration_max", 30)
                
                if min_dur <= duration <= max_dur and sr == target_sr:
                    logger.info(f"Using existing reference: {voice_id} ({duration:.1f}s)")
                    prepared_refs[voice_id] = str(output_path)
                    continue
            except Exception as e:
                logger.warning(f"Cached reference {voice_id} invalid: {e}, re-downloading")
        
        # Download and prepare (for URL-based voices)
        logger.info(f"Preparing reference for {voice_id}...")
        
        try:
            source_url = voice_data.get("source_url")
            if not source_url:
                logger.error(f"No source_url or local_path for {voice_id}, skipping")
                continue
            
            # Download MP3
            mp3_path = cache_path / f"temp_{voice_id}.mp3"
            logger.debug(f"Downloading from: {source_url}")
            response = requests.get(source_url, timeout=30)
            response.raise_for_status()
            
            with open(mp3_path, 'wb') as f:
                f.write(response.content)
            
            # Load and process
            y, sr = librosa.load(str(mp3_path), sr=None, mono=True)
            
            # Trim to specified range
            trim_start = voice_data.get("trim_start", 0)
            trim_end = voice_data.get("trim_end", 20)
            
            start_sample = int(trim_start * sr)
            end_sample = int(trim_end * sr)
            
            if start_sample < len(y) and end_sample <= len(y):
                y_trimmed = y[start_sample:end_sample]
            else:
                logger.warning(f"Trim range invalid for {voice_id}, using first 20s")
                y_trimmed = y[:int(20 * sr)]
            
            # Normalize
            if prep_settings.get("normalize_audio", True):
                y_norm = librosa.util.normalize(y_trimmed)
            else:
                y_norm = y_trimmed
            
            # Resample to target sample rate
            if sr != target_sr:
                y_resampled = librosa.resample(y_norm, orig_sr=sr, target_sr=target_sr)
            else:
                y_resampled = y_norm
            
            # Save
            ta.save(str(output_path), torch.tensor(y_resampled).unsqueeze(0), target_sr)
            
            # Clean up temp file
            mp3_path.unlink()
            
            prepared_refs[voice_id] = str(output_path)
            
            duration = len(y_resampled) / target_sr
            logger.info(f"✅ Prepared {voice_id}: {output_path} ({duration:.1f}s)")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Download failed for {voice_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to prepare {voice_id}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    if not prepared_refs:
        logger.warning("No voice references prepared successfully")
    else:
        logger.info(f"Prepared {len(prepared_refs)}/{len(voice_refs)} voice references")
    
    return prepared_refs

def prepare_reference_audio(config: TTSConfig, output_path: str = "ref_trimmed.wav") -> str:
    """Download and prepare HQ ref audio for cloning. Why: Zero-shot cloning needs clean 10-20s sample."""
    if os.path.exists(output_path):
        try:
            y, sr = librosa.load(output_path, sr=None)
            if 10 <= len(y)/sr <= 20:  # Valid length
                return output_path
        except:
            pass

    # Download MP3
    mp3_path = "temp_ref.mp3"
    response = requests.get(config.ref_url)
    with open(mp3_path, 'wb') as f:
        f.write(response.content)

    # Load, trim, resample, normalize
    y, sr = librosa.load(mp3_path, sr=None, mono=True)
    y_trim = librosa.effects.trim(y, top_db=20)[0]  # Trim silence
    if len(y_trim) > config.sample_rate * 20:
        y_trim = y_trim[:config.sample_rate * 20]  # Cap at 20s
    y_norm = librosa.util.normalize(y_trim)
    y_resampled = librosa.resample(y_norm, orig_sr=sr, target_sr=config.sample_rate)
    ta.save(output_path, torch.tensor(y_resampled).unsqueeze(0), config.sample_rate)
    os.remove(mp3_path)
    return output_path

def sanitize_text_for_tts(text: str) -> str:
    """
    Sanitize text before sending to TTS to prevent artifacts.
    
    Fixes:
    - Normalizes quotation marks
    - Removes problematic punctuation patterns
    - Handles special characters
    - Warns about incomplete chunks
    
    Why: Chatterbox interprets certain character sequences as control codes,
    causing weird pauses, sounds, or truncation.
    """
    original_text = text
    
    # Normalize unicode (smart quotes → straight quotes)
    text = unicodedata.normalize('NFKC', text)
    
    # Replace smart quotes with straight quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    # Fix double spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Remove standalone closing braces/brackets that might cause pauses
    text = re.sub(r'\s+}\s*$', '.', text)  # Trailing }
    text = re.sub(r'\s+]\s*$', '.', text)  # Trailing ]
    
    # Fix period-quote patterns that cause artifacts (. " → ." )
    text = re.sub(r'\.\s+"', '." ', text)
    
    # Warn if chunk ends incompletely
    incomplete_patterns = [
        (r'\bsaid,?\s*$', 'ends with "said"'),
        (r'\breplied,?\s*$', 'ends with "replied"'),
        (r'"\s*$', 'ends with standalone quote'),
        (r'\bof\s*$', 'ends with "of"'),
        (r'\band\s*$', 'ends with "and"'),
    ]
    
    for pattern, description in incomplete_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"Incomplete chunk detected: {description}")
            logger.debug(f"Text ends with: ...{text[-100:]}")
    
    # Check for unbalanced quotes
    if text.count('"') % 2 != 0:
        logger.warning(f"Unbalanced quotes in chunk")
        # Try to balance by removing trailing quote
        if text.rstrip().endswith('"'):
            text = text.rstrip()[:-1].rstrip()
    
    if text != original_text:
        logger.info(f"Text sanitized for TTS")
        logger.debug(f"Before: ...{original_text[-50:]}")
        logger.debug(f"After:  ...{text[-50:]}")
    
    return text.strip()

def synthesize_chunk(model, text: str, ref_path: str, output_path: str, config: TTSConfig, chunk_id: str) -> Tuple[bool, Dict]:
    """Synthesize audio for a chunk with optional splitting. Why: Fork/original handles cloning via audio_prompt; split long text."""
    start = time.perf_counter()
    
    # 🔧 NEW: Sanitize text before processing to prevent TTS artifacts
    text = sanitize_text_for_tts(text)
    
    split_metadata = {"split_applied": False, "num_sub_chunks": 1, "failed_sub_chunks": []}

    if config.enable_splitting and len(text) > 300:  # Threshold for splitting (adjust per model limits)
        sentences = sent_tokenize(text)
        sub_chunks = []
        current = ""
        for sent in sentences:
            if len(current + sent) < 300:
                current += " " + sent
            else:
                sub_chunks.append(current.strip())
                current = sent
        sub_chunks.append(current.strip())
        split_metadata["split_applied"] = True
        split_metadata["num_sub_chunks"] = len(sub_chunks)
    else:
        sub_chunks = [text]

    full_audio = torch.zeros(1, 0, dtype=torch.float32)  # Initialize as 2D empty [channels=1, samples=0]
    for i, sub_text in enumerate(sub_chunks):
        try:
            # Generate with cloning
            wav = model.generate(
                sub_text,
                language_id=config.language,
                audio_prompt_path=ref_path,
                exaggeration=config.exaggeration,
                cfg_weight=config.cfg_weight,
                temperature=config.temperature
            )
            # Ensure wav is 2D (channels, samples)
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)  # Add channel dimension
            # Log shapes before concat (for debugging)
            logger.info(f"Before concat: full_audio={full_audio.shape}, wav={wav.shape}")
            full_audio = torch.cat([full_audio, wav], dim=1)
        except Exception as e:
            logger.error(f"Sub-chunk {i} generation failed: {e}")
            split_metadata["failed_sub_chunks"].append(i)
            # Insert silence fallback
            silence_samples = int(config.silence_duration * config.sample_rate)
            silence = torch.zeros(1, silence_samples, dtype=torch.float32)
            # Log shapes before concat
            logger.info(f"Before concat silence: full_audio shape={full_audio.shape}, silence shape={silence.shape}")
            full_audio = torch.cat([full_audio, silence], dim=1) if full_audio.numel() > 0 else silence
            for _ in range(config.sub_chunk_retries - 1):  # Retries
                try:
                    wav = model.generate(sub_text, language_id=config.language, audio_prompt_path=ref_path)
                    # Ensure wav is 2D
                    if wav.dim() == 1:
                        wav = wav.unsqueeze(0)
                    logger.info(f"Retry success: replacing silence with wav={wav.shape}")
                    full_audio = torch.cat([full_audio[:, :-silence_samples], wav], dim=1)  # Replace silence (slice time dim)
                    break
                except Exception as retry_e:
                    logger.warning(f"Retry failed for sub-chunk {i}: {retry_e}")

    if full_audio.numel() == 0:
        return False, split_metadata

    # Save audio with proper error handling
    try:
        # Normalize path for Windows
        output_path_normalized = str(Path(output_path).resolve())

        # Remove existing file if present (may be locked or corrupted from previous run)
        if os.path.exists(output_path_normalized):
            try:
                os.remove(output_path_normalized)
                logger.debug(f"Removed existing file: {output_path_normalized}")
            except Exception as rm_e:
                logger.warning(f"Could not remove existing file: {rm_e}")

        # Ensure audio is on CPU and contiguous for saving
        full_audio_cpu = full_audio.cpu().contiguous()

        # Save with explicit format
        ta.save(output_path_normalized, full_audio_cpu, config.sample_rate, format="wav")
        logger.info(f"Successfully saved audio to: {output_path_normalized}")

    except Exception as save_error:
        logger.error(f"Failed to save audio file: {save_error}")
        logger.error(f"Output path: {output_path_normalized}")
        logger.error(f"Audio shape: {full_audio.shape}, dtype: {full_audio.dtype}")
        logger.error(f"Sample rate: {config.sample_rate}")

        # Try to provide more diagnostic information
        output_dir = Path(output_path_normalized).parent
        logger.error(f"Output directory exists: {output_dir.exists()}")
        logger.error(f"Output directory writable: {os.access(output_dir, os.W_OK)}")

        return False, split_metadata

    duration = time.perf_counter() - start
    return True, split_metadata

def evaluate_mos_proxy(audio_path: str, sr: int) -> float:
    """Simple MOS proxy (e.g., spectral centroid for clarity). Why: Basic quality metric; real MOS needs models."""
    y, _ = librosa.load(audio_path, sr=sr)
    if len(y) == 0:
        return 0.0
    centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
    return min(centroid / 2000, 5.0)  # Normalize to 0-5 scale (heuristic)

def merge_to_pipeline_json(json_path: str, file_id: str, chunk_id: str, success: bool, audio_path: str, mos: float, metrics: Dict, errors: List, timestamps: Dict, split_metadata: Dict):
    """Update phase4 in pipeline.json. Why: Single source of truth; append per chunk."""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except:
        data = {}

    if "phase4" not in data:
        data["phase4"] = {"files": {}, "status": "partial"}

    if file_id not in data["phase4"]["files"]:
        data["phase4"]["files"][file_id] = {}

    record = {
        "chunk_id": chunk_id,
        "audio_path": audio_path,
        "status": "success" if success else "failed",
        "mos_score": mos,
        "metrics": metrics,
        "errors": errors,
        "timestamps": timestamps,
        "split_metadata": split_metadata
    }
    data["phase4"]["files"][file_id][chunk_id] = record

    chunk_records = [
        rec for rec in data["phase4"]["files"][file_id].values()
        if isinstance(rec, dict) and "status" in rec
    ]

    if chunk_records:
        file_status = "success" if all(rec["status"] == "success" for rec in chunk_records) else "partial"
        data["phase4"]["status"] = file_status
        data["phase4"]["files"][file_id]["status"] = file_status

        # Maintain convenience fields if present
        if "total_chunks" in data["phase4"]["files"][file_id]:
            data["phase4"]["files"][file_id]["total_chunks"] = max(
                data["phase4"]["files"][file_id].get("total_chunks", 0),
                len(chunk_records)
            )
        if "chunk_audio_paths" in data["phase4"]["files"][file_id]:
            paths = data["phase4"]["files"][file_id].setdefault("chunk_audio_paths", [])
            if audio_path not in paths:
                paths.append(audio_path)

    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)
