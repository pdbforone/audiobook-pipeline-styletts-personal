"""
Smart Retry Strategies for TTS Validation Failures

Engine-specific parameter tuning based on failure type.
Reference: TTS_VALIDATION_RESEARCH_FINDINGS.md Phase 3
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryStrategy:
    """Recommended retry parameters based on failure analysis."""
    should_retry: bool
    use_fallback_engine: bool
    parameter_adjustments: Dict[str, Any]
    fallback_voice: Optional[str]
    reason: str


# Kokoro voice rotation order
KOKORO_VOICE_ROTATION = ["af_bella", "af_sarah", "bf_emma", "am_adam", "bm_george"]

# XTTS voice rotation order
XTTS_VOICE_ROTATION = ["claribel_dervla", "gracie_wise", "ana_florence"]


def analyze_failure_and_recommend(
    validation_reason: str,
    validation_details: Dict[str, Any],
    engine_used: str,
    current_voice: str,
    retry_count: int,
    engine_kwargs: Dict[str, Any],
) -> RetryStrategy:
    """
    Analyze validation failure and recommend retry strategy.

    Args:
        validation_reason: From ValidationResult.reason (e.g., "duration_mismatch")
        validation_details: From ValidationResult.details
        engine_used: "kokoro" or "xtts"
        current_voice: Voice ID used in failed attempt
        retry_count: How many retries have been attempted
        engine_kwargs: Current engine parameters

    Returns:
        RetryStrategy with recommended adjustments
    """
    # Max retries before giving up on same engine
    MAX_SAME_ENGINE_RETRIES = 3

    if retry_count >= MAX_SAME_ENGINE_RETRIES:
        return RetryStrategy(
            should_retry=True,
            use_fallback_engine=True,
            parameter_adjustments={},
            fallback_voice=None,  # Let get_fallback_voice() handle this
            reason=f"Max retries ({MAX_SAME_ENGINE_RETRIES}) reached, switching engine"
        )

    # XTTS-specific strategies
    if engine_used == "xtts":
        return _analyze_xtts_failure(
            validation_reason, validation_details,
            current_voice, retry_count, engine_kwargs
        )

    # Kokoro-specific strategies
    if engine_used == "kokoro":
        return _analyze_kokoro_failure(
            validation_reason, validation_details,
            current_voice, retry_count, engine_kwargs
        )

    # Unknown engine - use fallback
    return RetryStrategy(
        should_retry=True,
        use_fallback_engine=True,
        parameter_adjustments={},
        fallback_voice=None,
        reason=f"Unknown engine '{engine_used}', using fallback"
    )


def _analyze_xtts_failure(
    reason: str,
    details: Dict[str, Any],
    current_voice: str,
    retry_count: int,
    kwargs: Dict[str, Any],
) -> RetryStrategy:
    """XTTS-specific failure analysis."""

    current_rep_penalty = kwargs.get("repetition_penalty", 2.0)

    if reason == "duration_mismatch":
        expected = details.get("expected_duration", 0)
        actual = details.get("actual_duration", 0)

        if actual > expected * 1.5:
            # Duration too long - likely repetition loop
            new_penalty = min(current_rep_penalty + 0.5, 5.0)
            return RetryStrategy(
                should_retry=True,
                use_fallback_engine=False,
                parameter_adjustments={"repetition_penalty": new_penalty},
                fallback_voice=None,
                reason=f"Duration too long ({actual:.1f}s vs {expected:.1f}s expected), "
                       f"increasing repetition_penalty: {current_rep_penalty} → {new_penalty}"
            )
        elif actual < expected * 0.5:
            # Duration too short - likely early stopping
            new_penalty = max(current_rep_penalty - 0.3, 1.0)
            return RetryStrategy(
                should_retry=True,
                use_fallback_engine=False,
                parameter_adjustments={"repetition_penalty": new_penalty},
                fallback_voice=None,
                reason=f"Duration too short ({actual:.1f}s vs {expected:.1f}s expected), "
                       f"decreasing repetition_penalty: {current_rep_penalty} → {new_penalty}"
            )

    if reason in ("rms_too_low", "rms_too_high", "too_quiet"):
        # Amplitude issues after mastering - try different voice
        next_voice = _get_next_voice(current_voice, XTTS_VOICE_ROTATION)
        if next_voice:
            return RetryStrategy(
                should_retry=True,
                use_fallback_engine=False,
                parameter_adjustments={},
                fallback_voice=next_voice,
                reason=f"Amplitude issue with {current_voice}, trying {next_voice}"
            )

    if reason == "silence_gap":
        # Unnatural pauses - increase penalty to reduce hallucinated silence
        new_penalty = min(current_rep_penalty + 0.3, 4.0)
        return RetryStrategy(
            should_retry=True,
            use_fallback_engine=False,
            parameter_adjustments={"repetition_penalty": new_penalty},
            fallback_voice=None,
            reason=f"Silence gap detected, increasing repetition_penalty to {new_penalty}"
        )

    # Default: switch to Kokoro
    return RetryStrategy(
        should_retry=True,
        use_fallback_engine=True,
        parameter_adjustments={},
        fallback_voice=None,
        reason=f"XTTS failed with '{reason}', switching to Kokoro"
    )


def _analyze_kokoro_failure(
    reason: str,
    details: Dict[str, Any],
    current_voice: str,
    retry_count: int,
    kwargs: Dict[str, Any],
) -> RetryStrategy:
    """Kokoro-specific failure analysis."""

    if reason == "duration_mismatch":
        # Kokoro alignment issues are often voice-specific
        # Try different voice to force different alignment path
        next_voice = _get_next_voice(current_voice, KOKORO_VOICE_ROTATION)
        if next_voice:
            return RetryStrategy(
                should_retry=True,
                use_fallback_engine=False,
                parameter_adjustments={},
                fallback_voice=next_voice,
                reason=f"Duration mismatch with {current_voice} (alignment issue), "
                       f"trying {next_voice}"
            )
        else:
            # Exhausted all Kokoro voices, try XTTS
            return RetryStrategy(
                should_retry=True,
                use_fallback_engine=True,
                parameter_adjustments={},
                fallback_voice=None,
                reason="All Kokoro voices failed, switching to XTTS"
            )

    if reason in ("rms_too_low", "rms_too_high", "too_quiet"):
        # Try different voice
        next_voice = _get_next_voice(current_voice, KOKORO_VOICE_ROTATION)
        if next_voice:
            return RetryStrategy(
                should_retry=True,
                use_fallback_engine=False,
                parameter_adjustments={},
                fallback_voice=next_voice,
                reason=f"Amplitude issue, rotating voice: {current_voice} → {next_voice}"
            )

    # Default: switch to XTTS
    return RetryStrategy(
        should_retry=True,
        use_fallback_engine=True,
        parameter_adjustments={},
        fallback_voice=None,
        reason=f"Kokoro failed with '{reason}', switching to XTTS"
    )


def _get_next_voice(current_voice: str, rotation: list) -> Optional[str]:
    """Get next voice in rotation, or None if exhausted."""
    try:
        idx = rotation.index(current_voice)
        if idx + 1 < len(rotation):
            return rotation[idx + 1]
    except ValueError:
        # Current voice not in rotation, start from beginning
        if rotation:
            return rotation[0]
    return None
