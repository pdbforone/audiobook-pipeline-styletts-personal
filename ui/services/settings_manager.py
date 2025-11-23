from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

from ui.models import UISettings

logger = logging.getLogger(__name__)


class SettingsManager:
    """Persist and retrieve UI settings safely."""

    def __init__(self, settings_path: Path, project_root: Path) -> None:
        self.settings_path = Path(settings_path)
        self.project_root = Path(project_root)
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> UISettings:
        if not self.settings_path.exists():
            return UISettings(
                input_dir=str(self.project_root / "input"),
                output_dir=str(
                    self.project_root / "phase5_enhancement" / "processed"
                ),
            )
        try:
            with open(self.settings_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return UISettings.from_dict(data, project_root=self.project_root)
        except Exception as exc:
            logger.warning(
                "Failed to load UI settings, using defaults: %s", exc
            )
            return UISettings(
                input_dir=str(self.project_root / "input"),
                output_dir=str(
                    self.project_root / "phase5_enhancement" / "processed"
                ),
            )

    def save(self, settings: UISettings) -> bool:
        payload = settings.to_dict()
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                delete=False,
                encoding="utf-8",
                dir=self.settings_path.parent,
            ) as tmp:
                json.dump(payload, tmp, indent=2)
                tmp.write("\n")
                tmp_path = Path(tmp.name)
            tmp_path.replace(self.settings_path)
            return True
        except Exception as exc:
            logger.exception("Failed to persist UI settings: %s", exc)
            return False
