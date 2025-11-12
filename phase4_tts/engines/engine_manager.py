"""
TTS Engine Manager
Coordinates multiple TTS engines and provides unified interface
"""

import logging
from typing import Dict, Optional, List
from pathlib import Path
import numpy as np

from . import TTSEngine
from .kokoro_engine import KokoroEngine
from .f5_engine import F5TTSEngine
from .xtts_engine import XTTSEngine

logger = logging.getLogger(__name__)


class EngineManager:
    """
    Manages multiple TTS engines and provides selection/fallback logic

    Usage:
        manager = EngineManager(device="cpu")
        manager.register_engine("f5", F5TTSEngine)
        manager.register_engine("xtts", XTTSEngine)
        manager.register_engine("chatterbox", ChatterboxEngine)

        audio = manager.synthesize(
            engine="f5",
            text="Hello world",
            reference_audio=Path("ref.wav")
        )
    """

    def __init__(self, device: str = "cpu"):
        self.device = device
        self.engines: Dict[str, TTSEngine] = {}
        self.loaded_engines: Dict[str, TTSEngine] = {}
        self.default_engine: Optional[str] = None

    def register_engine(self, name: str, engine_class: type) -> None:
        """
        Register an engine class

        Args:
            name: Engine identifier (e.g., "f5", "xtts", "chatterbox")
            engine_class: Engine class (not instance)
        """
        self.engines[name] = engine_class
        logger.info(f"Registered engine: {name}")

        # Set first engine as default
        if self.default_engine is None:
            self.default_engine = name

    def get_engine(self, name: str) -> TTSEngine:
        """
        Get or load an engine instance

        Args:
            name: Engine identifier

        Returns:
            Loaded engine instance
        """
        # Return if already loaded
        if name in self.loaded_engines:
            return self.loaded_engines[name]

        # Check if registered
        if name not in self.engines:
            raise ValueError(
                f"Engine '{name}' not registered. "
                f"Available: {list(self.engines.keys())}"
            )

        # Instantiate and load
        try:
            logger.info(f"Loading engine: {name}")
            engine_class = self.engines[name]
            engine = engine_class(device=self.device)
            engine.load_model()

            self.loaded_engines[name] = engine
            return engine

        except Exception as e:
            logger.error(f"Failed to load engine '{name}': {e}")
            raise

    def synthesize(
        self,
        text: str,
        reference_audio: Path,
        engine: Optional[str] = None,
        language: str = "en",
        fallback: bool = True,
        **kwargs
    ) -> np.ndarray:
        """
        Synthesize speech using specified engine with fallback

        Args:
            text: Text to synthesize
            reference_audio: Reference audio path
            engine: Engine name (or None for default)
            language: Language code
            fallback: Whether to fallback to other engines on failure
            **kwargs: Engine-specific parameters

        Returns:
            Audio array (float32, mono)
        """
        # Use default if not specified
        if engine is None:
            engine = self.default_engine

        # Try primary engine
        try:
            tts_engine = self.get_engine(engine)
            audio = tts_engine.synthesize(
                text=text,
                reference_audio=reference_audio,
                language=language,
                **kwargs
            )
            return audio

        except Exception as e:
            logger.error(f"Engine '{engine}' failed: {e}")

            if not fallback:
                raise

            # Try fallback engines
            fallback_order = self._get_fallback_order(engine)
            for fallback_engine in fallback_order:
                try:
                    logger.warning(
                        f"Attempting fallback to '{fallback_engine}'"
                    )
                    tts_engine = self.get_engine(fallback_engine)
                    audio = tts_engine.synthesize(
                        text=text,
                        reference_audio=reference_audio,
                        language=language,
                        **kwargs
                    )
                    logger.info(f"Fallback successful: {fallback_engine}")
                    return audio

                except Exception as fallback_error:
                    logger.error(
                        f"Fallback '{fallback_engine}' failed: {fallback_error}"
                    )
                    continue

            # All engines failed
            raise RuntimeError(
                f"All engines failed to synthesize. Primary: {engine}, "
                f"Fallbacks: {fallback_order}"
            )

    def _get_fallback_order(self, failed_engine: str) -> List[str]:
        """Determine fallback order based on failed engine"""
        # Fallback priority: fast and reliable engines last
        all_engines = list(self.engines.keys())

        # Remove failed engine
        fallback = [e for e in all_engines if e != failed_engine]

        # Prefer stable engines for fallback
        # kokoro is fastest/most reliable, so use it first
        priority_order = ["kokoro", "xtts", "f5", "styletts"]

        # Sort by priority
        fallback.sort(
            key=lambda e: priority_order.index(e) if e in priority_order else 999
        )

        return fallback

    def list_engines(self) -> Dict[str, Dict]:
        """List all registered engines and their capabilities"""
        result = {}
        for name, engine_class in self.engines.items():
            # Create temporary instance to get capabilities
            temp_engine = engine_class(device=self.device)
            result[name] = {
                "name": temp_engine.name,
                "supports_emotions": temp_engine.supports_emotions,
                "sample_rate": temp_engine.get_sample_rate(),
                "languages": temp_engine.get_supported_languages(),
                "loaded": name in self.loaded_engines,
            }
        return result

    def set_default_engine(self, name: str) -> None:
        """Set default engine"""
        if name not in self.engines:
            raise ValueError(f"Engine '{name}' not registered")
        self.default_engine = name
        logger.info(f"Default engine set to: {name}")

    def unload_engine(self, name: str) -> None:
        """Unload an engine to free memory"""
        if name in self.loaded_engines:
            del self.loaded_engines[name]
            logger.info(f"Unloaded engine: {name}")

    def unload_all(self) -> None:
        """Unload all engines"""
        self.loaded_engines.clear()
        logger.info("All engines unloaded")
