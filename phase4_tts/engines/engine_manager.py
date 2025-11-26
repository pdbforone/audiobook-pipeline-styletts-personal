"""
TTS Engine Manager
Coordinates multiple TTS engines and provides unified interface

Enhanced with registry-based capability lookup for:
- Token-based text limits per engine
- Intelligent fallback ordering
- Performance-aware engine selection
"""

import logging
import time
from typing import Any, Dict, Optional, List, Tuple, Union
from pathlib import Path
import numpy as np

from . import TTSEngine

logger = logging.getLogger(__name__)

# Lazy import of registry to avoid circular imports
_registry = None


def _get_registry():
    """Lazy-load the engine registry."""
    global _registry
    if _registry is None:
        try:
            from core.engine_registry import EngineRegistry
            _registry = EngineRegistry()
        except ImportError:
            logger.debug("Engine registry not available, using defaults")
            _registry = None
    return _registry


class EngineManager:
    """Manages multiple TTS engines and provides selection/fallback logic."""

    def __init__(self, device: str = "cpu"):
        self.device = device
        self.engines: Dict[str, TTSEngine] = {}
        self.loaded_engines: Dict[str, TTSEngine] = {}
        self.default_engine: Optional[str] = None

    def register_engine(self, name: str, engine_class: type) -> None:
        """
        Register an engine class

        Args:
            name: Engine identifier (e.g., "f5", "xtts")
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
        return_engine: bool = False,
        est_dur_sec: Optional[float] = None,
        rtf_fallback_threshold: Optional[float] = None,
        **kwargs,
    ) -> Union[np.ndarray, Tuple[np.ndarray, str]]:
        """
        Synthesize speech using specified engine with fallback

        Args:
            text: Text to synthesize
            reference_audio: Reference audio path
            engine: Engine name (or None for default)
            language: Language code
            fallback: Whether to fallback to other engines on failure
            return_engine: When True, return (audio, engine_name) so callers
                can record which engine produced the clip
            **kwargs: Engine-specific parameters

        Returns:
            Audio array (float32, mono) or tuple (audio, engine_name)
        """
        # Use default if not specified
        if engine is None:
            engine = self.default_engine

        # Try primary engine
        try:
            tts_engine = self.get_engine(engine)
            start_time = time.time()
            audio = tts_engine.synthesize(
                text=text,
                reference_audio=reference_audio,
                language=language,
                **kwargs,
            )
            elapsed = time.time() - start_time
            rt_factor = elapsed / est_dur_sec if est_dur_sec else None
            # Optional RTF-based fallback: if primary is unusually slow and fallback allowed, try first fallback engine.
            if (
                fallback
                and est_dur_sec
                and rtf_fallback_threshold
                and est_dur_sec > 0
            ):
                logger.info(
                    "Engine '%s' RTF %.2f (threshold %.2f)",
                    engine,
                    rt_factor,
                    rtf_fallback_threshold,
                )
                if rt_factor > rtf_fallback_threshold:
                    fallback_order = self._get_fallback_order(engine)
                    if fallback_order:
                        fb = fallback_order[0]
                        logger.warning(
                            "Engine '%s' RTF %.2f > %.2f; attempting fallback '%s'",
                            engine,
                            rt_factor,
                            rtf_fallback_threshold,
                            fb,
                        )
                        try:
                            fb_engine = self.get_engine(fb)
                            fb_start = time.time()
                            fb_audio = fb_engine.synthesize(
                                text=text,
                                reference_audio=reference_audio,
                                language=language,
                                **kwargs,
                            )
                            fb_elapsed = time.time() - fb_start
                            fb_rt = (
                                fb_elapsed / est_dur_sec
                                if est_dur_sec
                                else None
                            )
                            if fb_rt is not None:
                                logger.info(
                                    "Fallback '%s' RTF %.2f vs primary %.2f",
                                    fb,
                                    fb_rt,
                                    rt_factor,
                                )
                            if return_engine:
                                return fb_audio, fb
                            return fb_audio
                        except Exception as fb_exc:  # noqa: BLE001
                            logger.warning(
                                "Fallback '%s' failed after slow RTF on '%s': %s",
                                fb,
                                engine,
                                fb_exc,
                            )
                    else:
                        logger.info(
                            "No fallback engines configured after slow RTF on '%s'.",
                            engine,
                        )
            elif rtf_fallback_threshold and rt_factor is not None:
                logger.info(
                    "Engine '%s' RTF %.2f (threshold %.2f)",
                    engine,
                    rt_factor,
                    rtf_fallback_threshold,
                )
            if return_engine:
                return audio, engine
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
                        **kwargs,
                    )
                    logger.info(f"Fallback successful: {fallback_engine}")
                    if return_engine:
                        return audio, fallback_engine
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
        """
        Determine fallback order based on failed engine.

        Uses registry fallback_order if available, otherwise defaults.
        """
        registry = _get_registry()

        if registry:
            # Get registry-defined fallback chain
            fallback = registry.get_fallback_chain(failed_engine)
            # Filter to only registered engines
            return [e for e in fallback if e in self.engines]

        # Fallback to hardcoded priority
        all_engines = list(self.engines.keys())
        fallback = [e for e in all_engines if e != failed_engine]

        # Prefer stable engines for fallback
        priority_order = ["xtts", "kokoro", "piper"]
        fallback.sort(
            key=lambda e: (
                priority_order.index(e) if e in priority_order else 999
            )
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

    # -------------------------------------------------------------------------
    # Registry-based capability methods
    # -------------------------------------------------------------------------

    def get_max_chars(self, engine_name: Optional[str] = None) -> int:
        """
        Get maximum character limit for an engine from registry.

        Args:
            engine_name: Engine name, or None for default engine

        Returns:
            Maximum characters per synthesis call
        """
        engine_name = engine_name or self.default_engine
        registry = _get_registry()

        if registry:
            return registry.get_max_chars(engine_name)

        # Fallback defaults if registry unavailable
        defaults = {"xtts": 1400, "kokoro": 1800, "piper": 3500}
        return defaults.get(engine_name, 1200)

    def get_soft_max_chars(self, engine_name: Optional[str] = None) -> int:
        """
        Get soft (optimal) character limit for an engine.

        Text exceeding this should be split for best quality.
        """
        engine_name = engine_name or self.default_engine
        registry = _get_registry()

        if registry:
            return registry.get_soft_max_chars(engine_name)

        defaults = {"xtts": 1000, "kokoro": 1200, "piper": 2000}
        return defaults.get(engine_name, 800)

    def should_split_text(self, text: str, engine_name: Optional[str] = None) -> bool:
        """
        Check if text should be split for optimal quality.

        Args:
            text: Text to check
            engine_name: Engine name

        Returns:
            True if text exceeds soft limit and should be split
        """
        return len(text) > self.get_soft_max_chars(engine_name)

    def must_split_text(self, text: str, engine_name: Optional[str] = None) -> bool:
        """
        Check if text MUST be split (exceeds hard limit).

        Args:
            text: Text to check
            engine_name: Engine name

        Returns:
            True if text exceeds hard limit and MUST be split
        """
        return len(text) > self.get_max_chars(engine_name)

    def get_engine_capabilities(self, engine_name: Optional[str] = None) -> Dict:
        """
        Get full capabilities for an engine from registry.

        Returns dict with:
        - limits: {max_chars, soft_max_chars, max_tokens, ...}
        - performance: {typical_rtf_cpu, memory_mb, ...}
        - quality: {mos_estimate, prosody, ...}
        """
        engine_name = engine_name or self.default_engine
        registry = _get_registry()

        if registry:
            caps = registry.get(engine_name)
            if caps:
                return {
                    "name": caps.display_name,
                    "limits": {
                        "max_chars": caps.limits.max_chars,
                        "soft_max_chars": caps.limits.soft_max_chars,
                        "max_tokens": caps.limits.max_tokens,
                        "min_chars": caps.limits.min_chars,
                    },
                    "performance": {
                        "typical_rtf_cpu": caps.performance.typical_rtf_cpu,
                        "memory_mb": caps.performance.memory_mb,
                    },
                    "quality": {
                        "mos_estimate": caps.quality.mos_estimate,
                        "prosody": caps.quality.prosody,
                    },
                    "supports_cloning": caps.supports_cloning,
                    "supports_emotions": caps.supports_emotions,
                }

        # Minimal fallback
        return {
            "name": engine_name,
            "limits": {"max_chars": self.get_max_chars(engine_name)},
        }

    def estimate_rtf(self, engine_name: Optional[str] = None) -> float:
        """Estimate real-time factor for an engine."""
        engine_name = engine_name or self.default_engine
        registry = _get_registry()

        if registry:
            return registry.estimate_rtf(engine_name)

        defaults = {"xtts": 3.2, "kokoro": 1.3, "piper": 0.3}
        return defaults.get(engine_name, 3.0)

    def get_fastest_engine(self) -> str:
        """Get the fastest registered engine."""
        registry = _get_registry()

        if registry:
            fastest = registry.get_fastest_cpu_engine()
            if fastest in self.engines:
                return fastest

        # Fallback: check registered engines
        if "piper" in self.engines:
            return "piper"
        if "kokoro" in self.engines:
            return "kokoro"
        return self.default_engine or "xtts"

    def get_highest_quality_engine(self) -> str:
        """Get the highest quality registered engine."""
        registry = _get_registry()

        if registry:
            best = registry.get_highest_quality_engine()
            if best in self.engines:
                return best

        # Fallback
        if "xtts" in self.engines:
            return "xtts"
        return self.default_engine or list(self.engines.keys())[0]

    # ------------------------------------------------------------------
    # Safe hook for repaired chunks (opt-in via orchestrator)
    # ------------------------------------------------------------------
    def try_repaired_chunk(self, chunk_id: str, repair_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Accept a repaired chunk (if confidence high) and return a synthetic result.

        This does NOT alter engine behavior or selection; it only provides
        a structured response the orchestrator can use for optional substitution.
        """
        return {
            "chunk_id": chunk_id,
            "engine_used": repair_result.get("engine_used"),
            "audio": repair_result.get("audio"),
            "sample_rate": repair_result.get("sample_rate", 24000),
            "metadata": {
                "confidence": repair_result.get("rewrite_confidence") or repair_result.get("confidence"),
                "notes": repair_result.get("notes"),
            },
        }
