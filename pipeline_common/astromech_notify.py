"""Notification beeps that fail gracefully across platforms."""

from __future__ import annotations

import logging
import platform
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = REPO_ROOT / "assets" / "notifications"

# Toggle to globally enable/disable beeps.
ENABLE_BEEPS: bool = True


def set_beep_enabled(enabled: bool) -> None:
    """Globally enable or disable audio notifications."""
    global ENABLE_BEEPS
    ENABLE_BEEPS = bool(enabled)


def _play_with_winsound(wav_path: Path) -> bool:
    if platform.system().lower() != "windows":
        return False
    try:
        import winsound

        winsound.PlaySound(
            str(wav_path), winsound.SND_FILENAME | winsound.SND_NODEFAULT
        )
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
    if not ENABLE_BEEPS:
        logger.debug("Beep disabled via flag; skipping %s", name)
        return

    wav_path = ASSET_DIR / name
    if not wav_path.exists():
        logger.warning("Astromech notification sound not found: %s", wav_path)
        return

    try:
        if _play_with_winsound(wav_path):
            return
        if _play_with_sounddevice(wav_path):
            return

        # Final fallback: best-effort system bell or just log.
        try:
            print("\a", end="", flush=True)
        except Exception:
            pass
        logger.warning(
            "Beep not available on this platform; file at %s", wav_path
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Notification playback failed: %s", exc)


def play_success_beep(silence_mode: bool = False) -> None:
    """Play the astromech success beep (no exceptions on failure)."""
    if silence_mode:
        logger.debug("Silence mode enabled; skipping success beep.")
        return
    _play_asset("droid_success.wav")


def play_alert_beep(silence_mode: bool = False) -> None:
    """Play the astromech alert beep (no exceptions on failure)."""
    if silence_mode:
        logger.debug("Silence mode enabled; skipping alert beep.")
        return
    _play_asset("droid_alert.wav")
