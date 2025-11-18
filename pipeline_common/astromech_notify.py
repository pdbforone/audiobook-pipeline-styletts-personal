"""Lightweight astromech notification beeps for local alerts.

Usage:
    from pipeline_common.astromech_notify import play_success_beep, play_alert_beep
    play_success_beep()
"""
from __future__ import annotations

import platform
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = REPO_ROOT / "assets" / "notifications"


def _play_with_winsound(wav_path: Path) -> bool:
    if platform.system().lower() != "windows":
        return False
    try:
        import winsound

        winsound.PlaySound(str(wav_path), winsound.SND_FILENAME | winsound.SND_NODEFAULT)
        return True
    except Exception as exc:  # pragma: no cover - best-effort only
        logger.debug("winsound playback failed: %s", exc)
        return False


def _play_with_sounddevice(wav_path: Path) -> bool:
    try:
        import soundfile as sf
        import sounddevice as sd

        audio, sr = sf.read(wav_path, dtype="float32")
        sd.play(audio, sr)
        sd.wait()
        return True
    except Exception as exc:  # pragma: no cover - best-effort only
        logger.debug("sounddevice playback failed: %s", exc)
        return False


def _play_asset(name: str) -> None:
    wav_path = ASSET_DIR / name
    if not wav_path.exists():
        logger.warning("Astromech notification sound not found: %s", wav_path)
        return

    if _play_with_winsound(wav_path):
        return
    if _play_with_sounddevice(wav_path):
        return

    # Fallback: log the path so a caller can handle playback externally
    logger.info("Notification ready (manual playback): %s", wav_path)


def play_success_beep() -> None:
    """Play the astromech success beep (non-blocking fallback logs path)."""
    _play_asset("droid_success.wav")


def play_alert_beep() -> None:
    """Play the astromech alert beep (non-blocking fallback logs path)."""
    _play_asset("droid_alert.wav")

