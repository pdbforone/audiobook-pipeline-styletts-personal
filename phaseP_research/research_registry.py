"""Phase P: Research registry (append-only, opt-in)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class ResearchRegistry:
    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if self.registry_path.exists():
            try:
                data = json.loads(self.registry_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                return {"keys": {}}
        return {"keys": {}}

    def save(self, data: Dict[str, Any]) -> None:
        payload = data or {"keys": {}}
        self.registry_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _ensure_entry(self, data: Dict[str, Any], key: str) -> Dict[str, Any]:
        keys = data.setdefault("keys", {})
        if key not in keys:
            now = datetime.utcnow().isoformat()
            keys[key] = {"created": now, "updated": now, "payload": {}}
        return data

    def add_entry(self, key: str, payload: Dict[str, Any]) -> None:
        data = self.load()
        data = self._ensure_entry(data, key)
        now = datetime.utcnow().isoformat()
        data["keys"][key]["created"] = now
        data["keys"][key]["updated"] = now
        data["keys"][key]["payload"] = payload or {}
        self.save(data)

    def update_entry(self, key: str, payload: Dict[str, Any]) -> None:
        data = self.load()
        data = self._ensure_entry(data, key)
        data["keys"][key]["updated"] = datetime.utcnow().isoformat()
        data["keys"][key]["payload"].update(payload or {})
        self.save(data)

    def resolve(self, key: str) -> Optional[Dict[str, Any]]:
        data = self.load()
        return data.get("keys", {}).get(key)
