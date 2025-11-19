from __future__ import annotations

import json
import logging
import re
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ui.models import VoiceMetadata

logger = logging.getLogger(__name__)

ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


class VoiceManager:
    """Manage voice metadata with atomic writes."""

    def __init__(self, config_path: Path, custom_voice_dir: Path) -> None:
        self.config_path = Path(config_path)
        self.custom_voice_dir = Path(custom_voice_dir)
        self._lock = threading.Lock()
        self._voices: Dict[str, VoiceMetadata] = self._load()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {"voice_references": {}}
        try:
            with open(self.config_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except json.JSONDecodeError as exc:
            logger.warning("Voice config corrupted: %s", exc)
            return {"voice_references": {}}
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Failed to read voice config: %s", exc)
            return {"voice_references": {}}

    def _atomic_write(self, data: Dict[str, Any]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=self.config_path.parent) as tmp:
            json.dump(data, tmp, indent=2, ensure_ascii=False)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        tmp_path.replace(self.config_path)

    def _load(self) -> Dict[str, VoiceMetadata]:
        config = self._load_config()
        voices = config.get("voice_references", {}) or {}
        return {vid: VoiceMetadata.from_dict(vid, meta) for vid, meta in voices.items()}

    def _normalize_voice_id(self, raw_id: str) -> str:
        slug = re.sub(r"[^a-z0-9_]+", "_", (raw_id or "").strip().lower())
        slug = re.sub(r"_+", "_", slug)
        return slug.strip("_")

    def _resolve_audio_source(self, upload: Any) -> Optional[Path]:
        def _candidate_path(value: Optional[str]) -> Optional[Path]:
            if not value:
                return None
            path = Path(value)
            return path if path.exists() else None

        if not upload:
            return None

        if isinstance(upload, (str, Path)):
            return _candidate_path(str(upload))

        if isinstance(upload, dict):
            for key in ("path", "name"):
                candidate = _candidate_path(upload.get(key))
                if candidate:
                    return candidate
            return None

        for attr in ("name", "path"):
            if hasattr(upload, attr):
                candidate = _candidate_path(getattr(upload, attr))
                if candidate:
                    return candidate

        if isinstance(upload, (list, tuple)):
            for item in upload:
                candidate = self._resolve_audio_source(item)
                if candidate:
                    return candidate

        return None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def refresh(self) -> Dict[str, VoiceMetadata]:
        with self._lock:
            self._voices = self._load()
            return self._voices

    def list_dropdown(self) -> List[str]:
        return [meta.to_dropdown_label() for meta in self._voices.values()]

    def get_voice(self, selection: str) -> Optional[VoiceMetadata]:
        voice_id = (selection or "").split(":")[0].strip()
        return self._voices.get(voice_id)

    def add_voice(
        self,
        voice_name: str,
        voice_file: Any,
        narrator_name: str,
        genre_tags: str,
    ) -> Dict[str, Any]:
        """Add a voice and return a structured response."""
        with self._lock:
            if not voice_name or not voice_file:
                return {"ok": False, "message": "❌ Please provide a voice ID and audio sample"}

            voice_id = self._normalize_voice_id(voice_name)
            if not voice_id:
                return {"ok": False, "message": "❌ Voice ID must contain letters or numbers"}

            source_path = self._resolve_audio_source(voice_file)
            if not source_path or not source_path.exists():
                return {"ok": False, "message": "❌ Uploaded audio file could not be found on disk"}

            extension = (source_path.suffix or "").lower() or ".wav"
            if extension not in ALLOWED_AUDIO_EXTENSIONS:
                allowed = ", ".join(sorted(ALLOWED_AUDIO_EXTENSIONS))
                return {"ok": False, "message": f"❌ Unsupported audio type '{extension}'. Please upload one of: {allowed}"}

            config = self._load_config()
            voice_refs = config.setdefault("voice_references", {})
            if voice_id in voice_refs:
                return {"ok": False, "message": f"❌ Voice ID '{voice_id}' already exists"}

            self.custom_voice_dir.mkdir(parents=True, exist_ok=True)
            destination = self.custom_voice_dir / f"{voice_id}{extension}"

            try:
                shutil.copy2(source_path, destination)
            except Exception as exc:
                logger.exception("Failed to copy new voice sample")
                return {"ok": False, "message": f"❌ Failed to store audio sample: {exc}"}

            tags = [tag.strip() for tag in (genre_tags or "").split(",") if tag.strip()]
            narrator = (narrator_name or "").strip() or voice_id.replace("_", " ").title()
            description = f"Custom voice for {', '.join(tags)}" if tags else "Custom voice added via UI"
            notes = f"Added via UI on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
            local_path = destination.relative_to(self.custom_voice_dir.parent.parent).as_posix()

            voice_refs[voice_id] = {
                "local_path": local_path,
                "narrator_name": narrator,
                "preferred_profiles": tags or ["custom"],
                "description": description,
                "notes": notes,
            }
            config["voice_references"] = dict(sorted(voice_refs.items()))

            try:
                self._atomic_write(config)
            except Exception as exc:
                logger.exception("Failed to update voice configuration")
                return {"ok": False, "message": f"❌ Could not save voice configuration: {exc}"}

            self._voices = self._load()
            refreshed_meta = self._voices.get(voice_id, VoiceMetadata.from_dict(voice_id, voice_refs[voice_id]))
            return {
                "ok": True,
                "voice_id": voice_id,
                "metadata": refreshed_meta,
                "message": f"✅ Voice '{voice_id}' added successfully!\\n\\nNarrator: {narrator}\\nStored at: {local_path}",
                "choices": self.list_dropdown(),
            }
