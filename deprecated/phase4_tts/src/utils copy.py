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

from models import TTSConfig, TTSRecord

logger = logging.getLogger(__name__)
nltk.download('punkt', quiet=True)  # For splitting

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

def synthesize_chunk(model, text: str, ref_path: str, output_path: str, config: TTSConfig, chunk_id: str) -> Tuple[bool, Dict]:
    """Synthesize audio for a chunk with optional splitting. Why: Fork/original handles cloning via audio_prompt; split long text."""
    start = time.perf_counter()
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

    ta.save(output_path, full_audio, config.sample_rate)
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

    # Update overall status
    data["phase4"]["status"] = "success" if all(r["status"] == "success" for r in data["phase4"]["files"][file_id].values()) else "partial"

    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)