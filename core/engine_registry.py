"""
Engine Registry - Canonical source of TTS engine capabilities.

Loads engine_registry.yaml and provides type-safe access to:
- Text limits (token-based, with safety margins)
- Performance characteristics
- Quality metrics
- Fallback strategies
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default registry path
DEFAULT_REGISTRY_PATH = Path(__file__).parent.parent / "phase4_tts" / "engine_registry.yaml"


@dataclass
class TextLimits:
    """Text length limits for an engine."""

    max_tokens: int = 400
    chars_per_token: float = 4.0
    max_chars: int = 1400
    soft_max_chars: int = 1000
    min_chars: int = 50
    emergency_max: int = 2000

    @property
    def safe_max_chars(self) -> int:
        """Maximum chars with 10% safety margin."""
        return int(self.max_chars * 0.9)

    def should_split(self, text: str) -> bool:
        """Check if text exceeds soft limit and should be split."""
        return len(text) > self.soft_max_chars

    def must_split(self, text: str) -> bool:
        """Check if text exceeds hard limit and MUST be split."""
        return len(text) > self.max_chars

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return int(len(text) / self.chars_per_token)


@dataclass
class PerformanceProfile:
    """Performance characteristics of an engine."""

    typical_rtf_cpu: float = 3.0
    typical_rtf_gpu: Optional[float] = None
    memory_mb: int = 4000
    load_time_sec: float = 10.0
    warmup_chunks: int = 2


@dataclass
class QualityProfile:
    """Quality characteristics of an engine."""

    mos_estimate: float = 4.0
    prosody: str = "good"
    consistency: str = "good"
    failure_modes: List[str] = field(default_factory=list)


@dataclass
class EngineCapabilities:
    """Complete capability profile for a TTS engine."""

    name: str
    class_path: str
    display_name: str

    # Capability flags
    cpu_friendly: bool = True
    gpu_accelerated: bool = False
    supports_cloning: bool = False
    supports_emotions: bool = False
    supports_streaming: bool = False
    enabled: bool = True

    # Languages
    languages: List[str] = field(default_factory=lambda: ["en"])

    # Limits and profiles
    limits: TextLimits = field(default_factory=TextLimits)
    performance: PerformanceProfile = field(default_factory=PerformanceProfile)
    quality: QualityProfile = field(default_factory=QualityProfile)

    # License info
    license_name: str = "Unknown"
    commercial_use: bool = False

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "EngineCapabilities":
        """Create EngineCapabilities from registry dict."""
        limits_data = data.get("limits", {})
        perf_data = data.get("performance", {})
        quality_data = data.get("quality", {})
        license_data = data.get("license", {})

        return cls(
            name=name,
            class_path=data.get("class", ""),
            display_name=data.get("display_name", name),
            cpu_friendly=data.get("cpu_friendly", True),
            gpu_accelerated=data.get("gpu_accelerated", False),
            supports_cloning=data.get("supports_cloning", False),
            supports_emotions=data.get("supports_emotions", False),
            supports_streaming=data.get("supports_streaming", False),
            enabled=data.get("enabled", True),
            languages=data.get("languages", ["en"]),
            limits=TextLimits(
                max_tokens=limits_data.get("max_tokens", 400),
                chars_per_token=limits_data.get("chars_per_token", 4.0),
                max_chars=limits_data.get("max_chars", 1400),
                soft_max_chars=limits_data.get("soft_max_chars", 1000),
                min_chars=limits_data.get("min_chars", 50),
                emergency_max=limits_data.get("emergency_max", 2000),
            ),
            performance=PerformanceProfile(
                typical_rtf_cpu=perf_data.get("typical_rtf_cpu", 3.0),
                typical_rtf_gpu=perf_data.get("typical_rtf_gpu"),
                memory_mb=perf_data.get("memory_mb", 4000),
                load_time_sec=perf_data.get("load_time_sec", 10.0),
                warmup_chunks=perf_data.get("warmup_chunks", 2),
            ),
            quality=QualityProfile(
                mos_estimate=quality_data.get("mos_estimate", 4.0),
                prosody=quality_data.get("prosody", "good"),
                consistency=quality_data.get("consistency", "good"),
                failure_modes=quality_data.get("failure_modes", []),
            ),
            license_name=license_data.get("name", "Unknown"),
            commercial_use=license_data.get("commercial", False),
        )


class EngineRegistry:
    """
    Singleton registry for TTS engine capabilities.

    Loads from engine_registry.yaml and provides:
    - Engine capability lookup
    - Text limit calculations
    - Fallback chain recommendations
    - Genre-based engine selection
    """

    _instance: Optional["EngineRegistry"] = None
    _initialized: bool = False

    def __new__(cls, registry_path: Optional[Path] = None) -> "EngineRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, registry_path: Optional[Path] = None):
        if self._initialized:
            return

        self.registry_path = registry_path or DEFAULT_REGISTRY_PATH
        self.engines: Dict[str, EngineCapabilities] = {}
        self.default_engine: str = "xtts"
        self.fallback_order: List[str] = ["kokoro", "piper"]
        self.rtf_fallback_threshold: float = 4.0
        self.genre_preferences: Dict[str, Dict[str, str]] = {}

        self._load_registry()
        self._initialized = True

    def _load_registry(self) -> None:
        """Load engine registry from YAML file."""
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed, using defaults")
            self._load_defaults()
            return

        if not self.registry_path.exists():
            logger.warning(f"Registry not found at {self.registry_path}, using defaults")
            self._load_defaults()
            return

        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Load engines
            for name, engine_data in data.get("engines", {}).items():
                try:
                    self.engines[name] = EngineCapabilities.from_dict(name, engine_data)
                    logger.debug(f"Loaded engine: {name}")
                except Exception as e:
                    logger.warning(f"Failed to load engine {name}: {e}")

            # Load selection config
            selection = data.get("selection", {})
            self.default_engine = selection.get("default", "xtts")
            self.fallback_order = selection.get("fallback_order", ["kokoro", "piper"])
            self.rtf_fallback_threshold = selection.get("rtf_fallback_threshold", 4.0)
            self.genre_preferences = selection.get("genre_preferences", {})

            logger.info(
                f"Loaded {len(self.engines)} engines from registry: {list(self.engines.keys())}"
            )

        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            self._load_defaults()

    def _load_defaults(self) -> None:
        """Load hardcoded defaults if YAML unavailable."""
        self.engines = {
            "xtts": EngineCapabilities(
                name="xtts",
                class_path="phase4_tts.engines.xtts_engine.XTTSEngine",
                display_name="XTTS v2 (Expressive)",
                supports_cloning=True,
                supports_emotions=True,
                limits=TextLimits(
                    max_tokens=400,
                    max_chars=1400,
                    soft_max_chars=1000,
                ),
                performance=PerformanceProfile(typical_rtf_cpu=3.2),
            ),
            "kokoro": EngineCapabilities(
                name="kokoro",
                class_path="phase4_tts.engines.kokoro_engine.KokoroEngine",
                display_name="Kokoro-82M (Fast CPU)",
                limits=TextLimits(
                    max_tokens=512,
                    max_chars=1800,
                    soft_max_chars=1200,
                ),
                performance=PerformanceProfile(
                    typical_rtf_cpu=1.3,
                    memory_mb=800,
                ),
            ),
        }
        logger.info("Using default engine registry (2 engines)")

    def get(self, engine_name: str) -> Optional[EngineCapabilities]:
        """Get capabilities for an engine."""
        return self.engines.get(engine_name)

    def get_limits(self, engine_name: str) -> TextLimits:
        """Get text limits for an engine, with fallback to defaults."""
        engine = self.engines.get(engine_name)
        if engine:
            return engine.limits
        return TextLimits()  # Safe defaults

    def get_max_chars(self, engine_name: str) -> int:
        """Get maximum character limit for an engine."""
        return self.get_limits(engine_name).max_chars

    def get_soft_max_chars(self, engine_name: str) -> int:
        """Get soft (optimal) character limit for an engine."""
        return self.get_limits(engine_name).soft_max_chars

    def should_split(self, engine_name: str, text: str) -> bool:
        """Check if text should be split for this engine."""
        return self.get_limits(engine_name).should_split(text)

    def must_split(self, engine_name: str, text: str) -> bool:
        """Check if text MUST be split for this engine."""
        return self.get_limits(engine_name).must_split(text)

    def get_fallback_chain(self, failed_engine: str) -> List[str]:
        """Get ordered list of fallback engines."""
        return [e for e in self.fallback_order if e != failed_engine and e in self.engines]

    def get_engine_for_genre(self, genre: str) -> str:
        """Get recommended engine for a genre."""
        pref = self.genre_preferences.get(genre, {})
        engine = pref.get("primary", self.default_engine)
        if engine in self.engines:
            return engine
        return self.default_engine

    def list_enabled_engines(self) -> List[str]:
        """List all enabled engines."""
        return [name for name, eng in self.engines.items() if eng.enabled]

    def estimate_rtf(self, engine_name: str, use_gpu: bool = False) -> float:
        """Estimate real-time factor for an engine."""
        engine = self.engines.get(engine_name)
        if not engine:
            return 3.0  # Conservative default

        if use_gpu and engine.performance.typical_rtf_gpu:
            return engine.performance.typical_rtf_gpu
        return engine.performance.typical_rtf_cpu

    def estimate_memory(self, engine_name: str) -> int:
        """Estimate memory usage in MB for an engine."""
        engine = self.engines.get(engine_name)
        return engine.performance.memory_mb if engine else 4000

    def can_run_concurrently(self, engines: List[str], available_ram_mb: int) -> bool:
        """Check if multiple engines can run concurrently given RAM."""
        total_memory = sum(self.estimate_memory(e) for e in engines)
        return total_memory < available_ram_mb * 0.8  # 20% safety margin

    def get_fastest_cpu_engine(self) -> str:
        """Get the fastest engine for CPU inference."""
        cpu_engines = [
            (name, eng)
            for name, eng in self.engines.items()
            if eng.enabled and eng.cpu_friendly
        ]
        if not cpu_engines:
            return self.default_engine

        return min(cpu_engines, key=lambda x: x[1].performance.typical_rtf_cpu)[0]

    def get_highest_quality_engine(self) -> str:
        """Get the highest quality engine."""
        enabled = [(name, eng) for name, eng in self.engines.items() if eng.enabled]
        if not enabled:
            return self.default_engine

        return max(enabled, key=lambda x: x[1].quality.mos_estimate)[0]


# Convenience function for quick access
def get_registry() -> EngineRegistry:
    """Get the singleton engine registry."""
    return EngineRegistry()
