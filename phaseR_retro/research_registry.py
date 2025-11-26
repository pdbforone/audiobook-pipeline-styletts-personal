"""In-memory research registry for Phase R (opt-in, read-only)."""

from __future__ import annotations

from typing import Dict


class ResearchRegistry:
    """Simple, non-persistent registry for research artifacts."""

    def __init__(self) -> None:
        self._store: Dict[str, dict] = {}

    def register(self, key: str, value: dict) -> None:
        if not isinstance(key, str):
            return
        if value is None:
            return
        self._store[key] = dict(value)

    def get(self, key: str) -> dict:
        return dict(self._store.get(key, {}))

    def has(self, key: str) -> bool:
        return key in self._store

    def all(self) -> dict:
        return dict(self._store)
