"""
Phase AD catalog reporter: write catalog artifacts (read-only).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

from phaseAD_catalog.schema import validate_catalog


def _prepare_output_dir(base_dir: Path) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)


def _write_version(base_dir: Path, version: str) -> None:
    version_path = base_dir / "version.txt"
    version_path.write_text(version + "\n", encoding="utf-8")


def write_catalog(catalog: Dict, base_dir: str = ".pipeline/capability_catalog") -> Tuple[Path, Path]:
    """
    Write catalog artifacts. Does not mutate runtime state.
    Returns (pointer_path, content_path).
    """
    if not validate_catalog(catalog):
        raise ValueError("Catalog failed schema validation.")

    base_path = Path(base_dir)
    _prepare_output_dir(base_path)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    content_path = base_path / f"catalog_{ts}.json"
    content_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    pointer_path = base_path / "catalog.json"
    if pointer_path.exists():
        backup_path = base_path / f"catalog_backup_{ts}.json"
        try:
            pointer_path.replace(backup_path)
        except Exception:
            pass
    # Write fresh pointer file with full catalog content
    pointer_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    _write_version(base_path, catalog.get("metadata", {}).get("scanner_version", "AD-1.0"))

    return pointer_path, content_path


if __name__ == "__main__":
    from phaseAD_catalog.capability_scanner import scan_capabilities
    from phaseAD_catalog.catalog_builder import build_catalog

    raw = scan_capabilities()
    catalog = build_catalog(raw)
    pointer, content = write_catalog(catalog)
    print(f"Catalog written to {content}")
    print(f"Pointer updated at {pointer}")
