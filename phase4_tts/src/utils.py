# utils.py - Helper Functions for Phase 4
# Why: Modularizes logic (e.g., ref prep, synthesis) for reuse/testability. Handles splitting to prevent truncation.
# Dependencies: Add to pyproject.toml or pip in env: torchaudio, librosa, requests, nltk.
# For HQ cloning: Ref audio trimmed to 10-20s clean speech; model uses zero-shot via audio_prompt_path.

import os
import json
import logging
import librosa
import requests
import nltk
from nltk.tokenize import sent_tokenize
from pathlib import Path, PureWindowsPath
from typing import Tuple, Optional, Dict
import numpy as np
import soundfile as sf
import re
import unicodedata
import difflib

try:
    from .models import TTSConfig
except ImportError:
    from models import TTSConfig

logger = logging.getLogger(__name__)
_PUNKT_READY = False


def ensure_punkt_tokenizer() -> None:
    """Lazily ensure the punkt tokenizer is available without downloading on import."""
    global _PUNKT_READY
    if _PUNKT_READY:
        return
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        logger.info("Downloading NLTK punkt tokenizer (one-time setup).")
        nltk.download("punkt", quiet=True)
    _PUNKT_READY = True


def _slugify(value: Optional[str]) -> str:
    """
    Create a normalized slug for fuzzy file_id comparisons.
    Lowercases, strips accents, and collapses non-alphanumeric characters.
    """
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(
        ch for ch in normalized if not unicodedata.combining(ch)
    )
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")


def _resolve_filesystem_path(path_str: str) -> Path:
    """
    Resolve paths that might be stored in Windows format when running under WSL.

    When Phase 3 runs on Windows it records absolute chunk/voice paths using
    ``C:\\`` style prefixes. Those paths are not directly readable inside WSL,
    so we convert them to ``/mnt/c/...`` when needed.
    """
    if not path_str:
        return Path(path_str)

    candidate = Path(path_str)
    if candidate.exists():
        return candidate

    normalized = path_str.strip().strip('"')

    # Translate Windows drive prefix (e.g. C:\foo) to /mnt/c/foo
    if os.name != "nt" and re.match(r"^[A-Za-z]:[\\/]", normalized):
        win_path = PureWindowsPath(normalized)
        drive = win_path.drive.rstrip(":").lower()
        relative_parts = win_path.parts[1:]
        if drive:
            wsl_path = Path("/mnt") / drive / Path(*relative_parts)
            if wsl_path.exists():
                return wsl_path

    return candidate


def resolve_pipeline_file(
    data: Dict[str, dict], phase: str, file_id: str
) -> Tuple[Optional[str], Optional[dict]]:
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
            logger.info(
                f"Resolved {phase} file_id '{file_id}' -> '{key}' (slug match)"
            )
            return key, files[key]

    for key, slug in slugged_items:
        if target_slug and target_slug in slug:
            logger.info(
                f"Resolved {phase} file_id '{file_id}' -> '{key}' (substring match)"
            )
            return key, files[key]

    for key, slug in slugged_items:
        if slug and slug in target_slug:
            logger.info(
                f"Resolved {phase} file_id '{file_id}' -> '{key}' (reverse substring match)"
            )
            return key, files[key]

    candidates = [slug for _, slug in slugged_items if slug]
    if candidates:
        match = difflib.get_close_matches(
            target_slug, candidates, n=1, cutoff=0.6
        )
        if match:
            matched_slug = match[0]
            for key, slug in slugged_items:
                if slug == matched_slug:
                    logger.info(
                        f"Resolved {phase} file_id '{file_id}' -> '{key}' (fuzzy match)"
                    )
                    return key, files[key]

    return None, None


def get_selected_voice_from_phase3(
    json_path: str, file_id: str
) -> Optional[str]:
    """
    Read selected voice from Phase 3 output.

    Args:
        json_path: Path to pipeline.json
        file_id: File identifier

    Returns:
        Voice ID or None if not found
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        resolved_key, phase3_data = resolve_pipeline_file(
            data, "phase3", file_id
        )
        if not phase3_data:
            logger.warning(f"No Phase 3 entry found for file_id '{file_id}'")
            return None

        if resolved_key and resolved_key != file_id:
            logger.info(
                f"Using Phase 3 entry '{resolved_key}' for requested file_id '{file_id}'"
            )

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
    cache_dir: str = "voice_references",
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
        with open(voice_config_path, "r", encoding="utf-8") as f:
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
            local_file = _resolve_filesystem_path(local_path)
            if local_file.exists():
                try:
                    # Load and validate local file
                    y, sr = librosa.load(str(local_file), sr=None, mono=True)
                    duration = len(y) / sr

                    # Resample if needed
                    if sr != target_sr:
                        y_resampled = librosa.resample(
                            y, orig_sr=sr, target_sr=target_sr
                        )
                        # Save resampled version to cache
                        sf.write(str(output_path), y_resampled, target_sr)
                        prepared_refs[voice_id] = str(output_path)
                        logger.info(
                            f"✅ Loaded local reference {voice_id}: {duration:.1f}s (resampled {sr}→{target_sr}Hz)"
                        )
                    else:
                        # Use original file directly
                        prepared_refs[voice_id] = str(local_file.resolve())
                        logger.info(
                            f"✅ Using local reference {voice_id}: {duration:.1f}s"
                        )
                    continue
                except Exception as e:
                    logger.error(
                        f"Failed to load local reference {voice_id} from {local_path}: {e}"
                    )
            else:
                logger.warning(
                    f"Local path not found for {voice_id}: {local_path}"
                )

        # Skip if already prepared and valid (for URL-based voices)
        if output_path.exists():
            try:
                y, sr = librosa.load(str(output_path), sr=None)
                duration = len(y) / sr
                min_dur = prep_settings.get("target_duration_min", 10)
                max_dur = prep_settings.get("target_duration_max", 30)

                if min_dur <= duration <= max_dur and sr == target_sr:
                    logger.info(
                        f"Using existing reference: {voice_id} ({duration:.1f}s)"
                    )
                    prepared_refs[voice_id] = str(output_path)
                    continue
            except Exception as e:
                logger.warning(
                    f"Cached reference {voice_id} invalid: {e}, re-downloading"
                )

        # Download and prepare (for URL-based voices)
        logger.info(f"Preparing reference for {voice_id}...")

        try:
            source_url = voice_data.get("source_url")
            if not source_url:
                logger.error(
                    f"No source_url or local_path for {voice_id}, skipping"
                )
                continue

            # Download MP3
            mp3_path = cache_path / f"temp_{voice_id}.mp3"
            logger.debug(f"Downloading from: {source_url}")
            response = requests.get(source_url, timeout=30)
            response.raise_for_status()

            with open(mp3_path, "wb") as f:
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
                logger.warning(
                    f"Trim range invalid for {voice_id}, using first 20s"
                )
                y_trimmed = y[: int(20 * sr)]

            # Normalize
            if prep_settings.get("normalize_audio", True):
                y_norm = librosa.util.normalize(y_trimmed)
            else:
                y_norm = y_trimmed

            # Resample to target sample rate
            if sr != target_sr:
                y_resampled = librosa.resample(
                    y_norm, orig_sr=sr, target_sr=target_sr
                )
            else:
                y_resampled = y_norm

            # Save
            sf.write(str(output_path), y_resampled, target_sr)

            # Clean up temp file
            mp3_path.unlink()

            prepared_refs[voice_id] = str(output_path)

            duration = len(y_resampled) / target_sr
            logger.info(
                f"✅ Prepared {voice_id}: {output_path} ({duration:.1f}s)"
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Download failed for {voice_id}: {e}")
        except Exception as e:
            logger.error(f"Failed to prepare {voice_id}: {e}")
            import traceback

            logger.debug(traceback.format_exc())

    if not prepared_refs:
        logger.warning("No voice references prepared successfully")
    else:
        logger.info(
            f"Prepared {len(prepared_refs)}/{len(voice_refs)} voice references"
        )

    return prepared_refs


def prepare_reference_audio(
    config: TTSConfig, output_path: str = "ref_trimmed.wav"
) -> str:
    """Download and prepare HQ ref audio for cloning. Why: Zero-shot cloning needs clean 10-20s sample."""
    if os.path.exists(output_path):
        try:
            y, sr = librosa.load(output_path, sr=None)
            if 10 <= len(y) / sr <= 20:  # Valid length
                return output_path
        except Exception:
            pass

    # Download MP3
    mp3_path = "temp_ref.mp3"
    response = requests.get(config.ref_url)
    with open(mp3_path, "wb") as f:
        f.write(response.content)

    # Load, trim, resample, normalize
    y, sr = librosa.load(mp3_path, sr=None, mono=True)
    y_trim = librosa.effects.trim(y, top_db=20)[0]  # Trim silence
    if len(y_trim) > config.sample_rate * 20:
        y_trim = y_trim[: config.sample_rate * 20]  # Cap at 20s
    y_norm = librosa.util.normalize(y_trim)
    y_resampled = librosa.resample(
        y_norm, orig_sr=sr, target_sr=config.sample_rate
    )
    sf.write(output_path, y_resampled, config.sample_rate)
    os.remove(mp3_path)
    return output_path


def sanitize_text_for_tts(
    text: str,
    enable_g2p: bool = False,
    normalize_numbers: bool = True,
    custom_overrides: Optional[Dict[str, str]] = None,
    pronunciation_lexicon: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Sanitize text before sending to TTS to prevent artifacts.

    Fixes:
    - Normalizes quotation marks
    - Removes problematic punctuation patterns
    - Handles special characters
    - Warns about incomplete chunks
    - Applies custom pronunciations from a lexicon.

    Why: Chatterbox interprets certain character sequences as control codes,
    causing weird pauses, sounds, or truncation.
    """
    original_text = text

    # Apply pronunciation lexicon first, as it's the most specific override
    if pronunciation_lexicon:
        for word, pronunciation in pronunciation_lexicon.items():
            arpabet = pronunciation.get("arpabet")
            if arpabet:
                # Use word boundaries to avoid replacing parts of words. Case-insensitive replacement.
                pattern = r"\b" + re.escape(word) + r"\b"
                replacement = f"[[{word}|{arpabet}]]"
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        if text != original_text:
            logger.info("Applied custom pronunciations from lexicon.")

    if enable_g2p and normalize_numbers:
        try:
            from g2p_en import (
                expand_numbers,
            )  # Lightweight CPU number/text normalizer

            text = expand_numbers(text)
        except ImportError:
            logger.debug("g2p_en not installed; skipping number expansion")
        except Exception as exc:
            logger.debug(f"g2p_en normalization failed: {exc}")

    # Optional heuristic overrides for common abbreviations
    if enable_g2p:
        overrides = {
            "e.g.": "for example",
            "i.e.": "that is",
            "vs.": "versus",
            "St.": "Saint",
            "Dr.": "Doctor",
        }
        if custom_overrides:
            overrides.update(custom_overrides)
        for token, replacement in overrides.items():
            text = re.sub(
                rf"\b{re.escape(token)}\b",
                replacement,
                text,
                flags=re.IGNORECASE,
            )

    # Remove footnote markers (e.g., [FOOTNOTE], [1], [FOOTNOTE][1])
    text = re.sub(r"\[FOOTNOTE\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[\d+\]", "", text)  # Remove numbered references like [1], [2]

    # Normalize unicode (smart quotes → straight quotes)
    text = unicodedata.normalize("NFKC", text)

    # Replace smart quotes with straight quotes
    smart_quotes = {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2039": "'",
        "\u203a": "'",
    }
    for smart, ascii_quote in smart_quotes.items():
        text = text.replace(smart, ascii_quote)

    # Fix double spaces
    text = re.sub(r"\s+", " ", text)

    # Remove standalone closing braces/brackets that might cause pauses
    text = re.sub(r"\s+}\s*$", ".", text)  # Trailing }
    text = re.sub(r"\s+]\s*$", ".", text)  # Trailing ]

    # Fix period-quote patterns that cause artifacts (. " → ." )
    text = re.sub(r'\.\s+"', '." ', text)

    # Warn if chunk ends incompletely
    incomplete_patterns = [
        (r"\bsaid,?\s*$", 'ends with "said"'),
        (r"\breplied,?\s*$", 'ends with "replied"'),
        (r'"\s*$', "ends with standalone quote"),
        (r"\bof\s*$", 'ends with "of"'),
        (r"\band\s*$", 'ends with "and"'),
    ]

    for pattern, description in incomplete_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"Incomplete chunk detected: {description}")
            logger.debug(f"Text ends with: ...{text[-100:]}")

    # Check for unbalanced quotes
    if text.count('"') % 2 != 0:
        logger.warning("Unbalanced quotes in chunk")
        # Try to balance by removing trailing quote
        if text.rstrip().endswith('"'):
            text = text.rstrip()[:-1].rstrip()

    if text != original_text:
        logger.info("Text sanitized for TTS")
        logger.debug(f"Before: ...{original_text[-50:]}")
        logger.debug(f"After:  ...{text[-50:]}")

    return text.strip()


def synthesize_chunk(
    model,
    text: str,
    ref_path: str,
    output_path: str,
    config: TTSConfig,
    chunk_id: str,
) -> Tuple[bool, Dict]:
    """Synthesize audio for a chunk with optional splitting. Why: Fork/original handles cloning via audio_prompt; split long text."""

    # 🔧 NEW: Sanitize text before processing to prevent TTS artifacts
    text = sanitize_text_for_tts(text)

    split_metadata = {
        "split_applied": False,
        "num_sub_chunks": 1,
        "failed_sub_chunks": [],
    }

    split_threshold = getattr(config, "split_char_limit", 300)
    if config.enable_splitting and len(text) > split_threshold:
        ensure_punkt_tokenizer()
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

    # LEGACY: This function is no longer used by XTTS/Kokoro engines
    # Engines now handle synthesis directly and return numpy arrays
    # Removed torch-dependent code to support isolated Kokoro environment
    logger.error(
        "synthesize_and_stitch_chunk() is legacy StyleTTS code - use engine.synthesize() instead"
    )
    return False, split_metadata


def evaluate_mos_proxy(audio_path: str, sr: int) -> float:
    """Simple MOS proxy (e.g., spectral centroid for clarity). Why: Basic quality metric; real MOS needs models."""
    y, _ = librosa.load(audio_path, sr=sr)
    if len(y) == 0:
        return 0.0
    centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
    return min(centroid / 2000, 5.0)  # Normalize to 0-5 scale (heuristic)
