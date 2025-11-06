"""
Text cleaner for TTS preprocessing using NVIDIA NeMo Text Processing.

This module uses production-grade WFST (Weighted Finite State Transducer) 
algorithms to normalize text for TTS. It handles:
- Currency ($1.87 → "one dollar and eighty-seven cents")
- Numbers (123 → "one hundred twenty-three")
- Dates (3/4/2024 → "March fourth twenty twenty-four")
- Times (3:45pm → "three forty-five p m")
- Abbreviations (Mr., Dr., Inc., etc.)
- And much more...

Requires: nemo-text-processing (install via conda + pip, see INSTALL_NEMO_TN.md)
"""

import re
from pathlib import Path
from typing import Optional
import time

# Try to import NeMo TN - if not installed, fall back to basic cleaning
try:
    from nemo_text_processing.text_normalization.normalize import Normalizer
    NEMO_AVAILABLE = True
except ImportError:
    NEMO_AVAILABLE = False
    print("WARNING: NeMo Text Processing not installed. Using basic cleaning only.")
    print("For proper TTS normalization, install: pip install nemo-text-processing")
    print("See INSTALL_NEMO_TN.md for details.")


class TTSTextCleaner:
    """
    Production-grade text cleaner for TTS preprocessing.
    Uses NVIDIA NeMo Text Normalization when available.
    """
    
    def __init__(self, language: str = "en", use_context: bool = False):
        """
        Initialize the text cleaner.
        
        Args:
            language: Language code (default: "en" for English)
            use_context: If True, uses context-aware normalization (slower but more accurate)
                        If False, uses fast deterministic normalization
        """
        self.language = language
        self.use_context = use_context
        
        if NEMO_AVAILABLE:
            # Initialize NeMo normalizer
            # input_case='cased' preserves capitalization (handles proper nouns better)
            self.normalizer = Normalizer(
                input_case='cased',
                lang=language,
                cache_dir=None,  # No caching for simpler setup
                overwrite_cache=False
            )
            print(f"✓ NeMo Text Normalizer initialized (language={language})")
        else:
            self.normalizer = None
            print("✗ Using fallback cleaner (basic regex only)")
    
    def clean_for_tts(self, raw_text: str) -> str:
        """
        Clean and normalize text for TTS.
        
        This is the main entry point. It:
        1. Fixes encoding artifacts
        2. Removes OCR noise (stray characters)
        3. Normalizes with NeMo TN (if available)
        4. Falls back to basic regex cleaning (if NeMo unavailable)
        
        Args:
            raw_text: Raw extracted text
            
        Returns:
            Cleaned and normalized text ready for TTS
        """
        text = raw_text
        
        # Step 1: Fix encoding artifacts (common in PDFs)
        text = self._fix_encoding(text)
        
        # Step 2: Remove OCR artifacts
        text = self._remove_ocr_artifacts(text)
        
        # Step 3: Normalize with NeMo (if available)
        if NEMO_AVAILABLE and self.normalizer:
            text = self._normalize_with_nemo(text)
        else:
            # Fallback: basic regex normalization
            text = self._basic_normalization(text)
        
        # Step 4: Final whitespace cleanup
        text = self._normalize_whitespace(text)
        
        return text.strip()
    
    def _fix_encoding(self, text: str) -> str:
        """Fix common PDF encoding artifacts."""
        # Smart quotes
        text = text.replace('â€œ', '"').replace('â€', '"')
        text = text.replace('â€™', "'").replace('â€˜', "'")
        # Em/en dashes
        text = text.replace('â€"', '—').replace('â€"', '–')
        
        # Convert to ASCII (handles remaining non-ASCII gracefully)
        try:
            from unidecode import unidecode
            text = unidecode(text)
        except ImportError:
            # If unidecode not installed, just skip (NeMo will handle most cases)
            pass
        
        return text
    
    def _remove_ocr_artifacts(self, text: str) -> str:
        """Remove OCR noise like single letters on their own lines."""
        # Remove single-letter lines (common OCR error)
        text = re.sub(r'^\s*[a-zA-Z]\s*
    
    def _normalize_with_nemo(self, text: str) -> str:
        """
        Normalize text using NeMo Text Processing.
        
        Handles:
        - Currency: $1.87 → "one dollar and eighty-seven cents"
        - Numbers: 123 → "one hundred twenty-three"
        - Dates: 3/4/2024 → "March fourth twenty twenty-four"
        - Times: 3:45pm → "three forty-five p m"
        - Abbreviations: Mr., Dr., Inc., etc.
        - And much more...
        """
        try:
            # NeMo's normalize() expects sentence-split text for best results
            # Split on sentence boundaries
            sentences = re.split(r'([.!?]+\s+)', text)
            normalized_sentences = []
            
            for sentence in sentences:
                if sentence.strip():
                    # Normalize each sentence
                    normalized = self.normalizer.normalize(
                        sentence,
                        verbose=False,  # Don't print debug info
                        punct_post_process=True  # Clean up punctuation
                    )
                    normalized_sentences.append(normalized)
            
            return ''.join(normalized_sentences)
        
        except Exception as e:
            print(f"Warning: NeMo normalization failed: {e}")
            print("Falling back to basic normalization")
            return self._basic_normalization(text)
    
    def _basic_normalization(self, text: str) -> str:
        """
        Fallback normalization using regex (if NeMo unavailable).
        
        This is a BASIC fallback and doesn't handle complex cases.
        Install NeMo Text Processing for proper TTS normalization.
        """
        # Handle currency (basic)
        def normalize_currency(match):
            amount_str = match.group(1).replace(' ', '')
            try:
                from num2words import num2words
                amount = float(amount_str)
                return num2words(amount, to='currency', currency='USD')
            except (ImportError, ValueError):
                return match.group(0)
        
        text = re.sub(r'\$\s*(\d+\.\d{2})', normalize_currency, text)
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace (collapse multiple spaces, preserve paragraphs)."""
        # Multiple spaces → single space
        text = re.sub(r' +', ' ', text)
        # Preserve paragraph breaks (max 2 newlines)
        text = re.sub(r'\n\n+', '\n\n', text)
        # Ensure space after punctuation
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        
        return text
    
    def clean_text_file(self, input_path: Path, output_path: Path) -> dict:
        """
        Clean a text file and return metrics.
        
        Args:
            input_path: Path to raw extracted text
            output_path: Path to save cleaned text
            
        Returns:
            Dict with metrics (duration, char counts, etc.)
        """
        start_time = time.perf_counter()
        
        # Read raw text
        raw_text = input_path.read_text(encoding='utf-8')
        
        # Clean it
        cleaned_text = self.clean_for_tts(raw_text)
        
        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(cleaned_text, encoding='utf-8')
        
        # Calculate metrics
        duration = time.perf_counter() - start_time
        metrics = {
            "cleaning_duration": duration,
            "original_chars": len(raw_text),
            "cleaned_chars": len(cleaned_text),
            "reduction_percent": 100 * (1 - len(cleaned_text) / len(raw_text)),
            "normalizer": "NeMo" if NEMO_AVAILABLE else "Fallback"
        }
        
        return metrics


# Convenience function for quick use
def clean_for_tts(raw_text: str, language: str = "en") -> str:
    """
    Quick convenience function for cleaning text.
    
    Args:
        raw_text: Raw extracted text
        language: Language code (default: "en")
    
    Returns:
        Cleaned text ready for TTS
    """
    cleaner = TTSTextCleaner(language=language)
    return cleaner.clean_for_tts(raw_text)


# Backward compatibility - keep the old function name
__all__ = ['TTSTextCleaner', 'clean_for_tts']
, '', text, flags=re.MULTILINE)
        
        # Fix spaced-out words (e.g., "T h e" → "The")
        # Look for sequences of 3+ single letters separated by spaces
        # Pattern: \b[a-zA-Z]\b matches a single letter as a complete word
        # (?:\s+\b[a-zA-Z]\b){2,} matches 2+ more single-letter words after it
        # This will match "T h e" or "T h e G i f t" but NOT normal words
        
        def collapse_single_letters(match):
            # Remove all spaces from matched single-letter sequence
            return match.group(0).replace(' ', '')
        
        # Apply the pattern globally
        text = re.sub(r'\b[a-zA-Z]\b(?:\s+\b[a-zA-Z]\b){2,}', 
                      collapse_single_letters, 
                      text)
        
        return text
    
    def _normalize_with_nemo(self, text: str) -> str:
        """
        Normalize text using NeMo Text Processing.
        
        Handles:
        - Currency: $1.87 → "one dollar and eighty-seven cents"
        - Numbers: 123 → "one hundred twenty-three"
        - Dates: 3/4/2024 → "March fourth twenty twenty-four"
        - Times: 3:45pm → "three forty-five p m"
        - Abbreviations: Mr., Dr., Inc., etc.
        - And much more...
        """
        try:
            # NeMo's normalize() expects sentence-split text for best results
            # Split on sentence boundaries
            sentences = re.split(r'([.!?]+\s+)', text)
            normalized_sentences = []
            
            for sentence in sentences:
                if sentence.strip():
                    # Normalize each sentence
                    normalized = self.normalizer.normalize(
                        sentence,
                        verbose=False,  # Don't print debug info
                        punct_post_process=True  # Clean up punctuation
                    )
                    normalized_sentences.append(normalized)
            
            return ''.join(normalized_sentences)
        
        except Exception as e:
            print(f"Warning: NeMo normalization failed: {e}")
            print("Falling back to basic normalization")
            return self._basic_normalization(text)
    
    def _basic_normalization(self, text: str) -> str:
        """
        Fallback normalization using regex (if NeMo unavailable).
        
        This is a BASIC fallback and doesn't handle complex cases.
        Install NeMo Text Processing for proper TTS normalization.
        """
        # Handle currency (basic)
        def normalize_currency(match):
            amount_str = match.group(1).replace(' ', '')
            try:
                from num2words import num2words
                amount = float(amount_str)
                return num2words(amount, to='currency', currency='USD')
            except (ImportError, ValueError):
                return match.group(0)
        
        text = re.sub(r'\$\s*(\d+\.\d{2})', normalize_currency, text)
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace (collapse multiple spaces, preserve paragraphs)."""
        # Multiple spaces → single space
        text = re.sub(r' +', ' ', text)
        # Preserve paragraph breaks (max 2 newlines)
        text = re.sub(r'\n\n+', '\n\n', text)
        # Ensure space after punctuation
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        
        return text
    
    def clean_text_file(self, input_path: Path, output_path: Path) -> dict:
        """
        Clean a text file and return metrics.
        
        Args:
            input_path: Path to raw extracted text
            output_path: Path to save cleaned text
            
        Returns:
            Dict with metrics (duration, char counts, etc.)
        """
        start_time = time.perf_counter()
        
        # Read raw text
        raw_text = input_path.read_text(encoding='utf-8')
        
        # Clean it
        cleaned_text = self.clean_for_tts(raw_text)
        
        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(cleaned_text, encoding='utf-8')
        
        # Calculate metrics
        duration = time.perf_counter() - start_time
        metrics = {
            "cleaning_duration": duration,
            "original_chars": len(raw_text),
            "cleaned_chars": len(cleaned_text),
            "reduction_percent": 100 * (1 - len(cleaned_text) / len(raw_text)),
            "normalizer": "NeMo" if NEMO_AVAILABLE else "Fallback"
        }
        
        return metrics


# Convenience function for quick use
def clean_for_tts(raw_text: str, language: str = "en") -> str:
    """
    Quick convenience function for cleaning text.
    
    Args:
        raw_text: Raw extracted text
        language: Language code (default: "en")
    
    Returns:
        Cleaned text ready for TTS
    """
    cleaner = TTSTextCleaner(language=language)
    return cleaner.clean_for_tts(raw_text)


# Backward compatibility - keep the old function name
__all__ = ['TTSTextCleaner', 'clean_for_tts']
