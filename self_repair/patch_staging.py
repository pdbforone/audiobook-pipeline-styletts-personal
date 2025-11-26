"""
Patch staging helper to collect repair suggestions safely.

- Never auto-applies patches
- Writes human-reviewable JSON files to .pipeline/staged_patches/
- Accepts raw RepairLoop suggestions or simple dict payloads
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_STAGING_DIR = Path(".pipeline") / "staged_patches"


class PatchStaging:
    """Utility class to stage repair suggestions without applying them."""

    def __init__(self, staging_dir: Path = DEFAULT_STAGING_DIR):
        self.staging_dir = Path(staging_dir)
        self.staging_dir.mkdir(parents=True, exist_ok=True)

    def stage_suggestions(
        self,
        suggestions: List[Dict[str, Any]],
        *,
        source: str = "orchestrator",
        label: str = "analysis",
    ) -> Optional[Path]:
        """
        Persist a batch of suggestions to a single JSON file for review.

        Suggestions that already contain a "patch_file" (staged elsewhere)
        are skipped to avoid duplication.
        """
        if not suggestions:
            return None

        serialized = []
        for item in suggestions:
            if isinstance(item, dict) and item.get("patch_file"):
                # Already staged by a reasoner/agent
                continue
            serialized.append(self._serialize(item))

        if not serialized:
            return None

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = self.staging_dir / f"{timestamp}_{source}_{label}.json"

        payload = {
            "created_at": timestamp + "Z",
            "source": source,
            "label": label,
            "suggestions": serialized,
            "status": "pending_review",
        }

        path.write_text(json.dumps(payload, indent=2))
        logger.info("Staged %d suggestion(s) to %s", len(serialized), path)
        return path

    @staticmethod
    def _serialize(suggestion: Any) -> Dict[str, Any]:
        """Best-effort serialization of RepairLoop suggestion items."""
        if isinstance(suggestion, dict):
            item = dict(suggestion)
            event = item.get("event")
            if event is not None and not isinstance(event, dict):
                item["event"] = {
                    "category": getattr(event, "category", None),
                    "message": getattr(event, "message", None),
                    "chunk_id": getattr(event, "chunk_id", None),
                    "file_id": getattr(event, "file_id", None),
                    "phase": getattr(event, "phase", None),
                    "severity": getattr(event, "severity", None),
                    "timestamp": getattr(event, "timestamp", None),
                }
            return item

        return {"raw": str(suggestion)}
