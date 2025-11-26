"""Pipeline Training Book generator (read-only, offline reference)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from pipeline_common.schema import CANONICAL_SCHEMA_VERSION
from tools.ui_manifest import generate_ui_capabilities, PHASE_ORDER_ALPHA, PHASE_ORDER_CORE

try:
    from phaseT_consistency import schema_registry
except Exception:  # noqa: BLE001
    schema_registry = None  # type: ignore

try:
    from phaseV_migrations import schema_versions
except Exception:  # noqa: BLE001
    schema_versions = None  # type: ignore


def _schema_section() -> Dict[str, Any]:
    """Build schema summary from registry modules."""
    phase_registry = schema_registry._SCHEMAS if schema_registry and hasattr(schema_registry, "_SCHEMAS") else {}  # type: ignore[attr-defined]
    versioned = schema_versions.SCHEMAS if schema_versions and hasattr(schema_versions, "SCHEMAS") else {}  # type: ignore[attr-defined]
    versioned_compact = {}
    for name, info in versioned.items():
        versioned_compact[name] = {
            "current_version": getattr(info, "current_version", None),
            "supported_versions": getattr(info, "supported_versions", {}),
        }
    return {
        "pipeline_state_version": CANONICAL_SCHEMA_VERSION,
        "phase_registry": phase_registry,
        "versioned_registry": versioned_compact,
    }


def _render_markdown(book: Dict[str, Any]) -> str:
    """Convert the training book JSON into a Markdown reference."""
    lines: List[str] = []
    lines.append("# Pipeline Training Book")
    lines.append("")
    lines.append(f"*Generated:* {book.get('generated_at')}")
    lines.append(f"*Source config:* {book.get('source_config')}")
    lines.append("")
    lines.append("## Phases (A–Z + core)")
    for phase in book.get("phases", []):
        label = phase.get("label") or phase.get("phase_key")
        key = phase.get("phase_key")
        enabled = phase.get("enabled_by_default", False)
        gates = phase.get("safety_gates", {})
        lines.append(f"- **{label}** (`{key}`) — enable={enabled}, safety={gates}")
    lines.append("")
    lines.append("## Schemas")
    schemas = book.get("schemas", {})
    lines.append(f"- pipeline_state_version: `{schemas.get('pipeline_state_version')}`")
    if isinstance(schemas.get("phase_registry"), dict):
        lines.append("- phase_registry entries:")
        for name in sorted(schemas["phase_registry"].keys()):
            lines.append(f"  - `{name}`")
    if isinstance(schemas.get("versioned_registry"), dict):
        lines.append("- versioned_registry:")
        for name, info in schemas["versioned_registry"].items():
            lines.append(f"  - `{name}` v{info.get('current_version')}")
    lines.append("")
    lines.append("## Safety")
    for rule in book.get("safety", []):
        lines.append(f"- {rule}")
    lines.append("")
    lines.append("## Override Paths")
    for item in book.get("override_paths", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Execution Model")
    for item in book.get("execution_model", []):
        lines.append(f"- {item}")
    return "\n".join(lines)


def generate_pipeline_book(
    config_path: Path = Path("phase6_orchestrator/config.yaml"),
    output_dir: Path = Path(".pipeline/reference"),
) -> Dict[str, Any]:
    """Generate both JSON and Markdown training book references."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = generate_ui_capabilities(config_path=config_path, output_path=output_dir / "ui_capabilities.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    phases = manifest.get("phases", [])

    book = {
        "version": "2.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source_config": str(config_path),
        "phases": phases,
        "schemas": _schema_section(),
        "config_paths": {
            "config_yaml": str(config_path),
            "pipeline_state_schema": "pipeline_common/schema.json",
        },
        "safety": [
            "Autonomy remains disabled; supervised thresholds are informational.",
            "Engines limited to XTTS/Kokoro; Piper disabled.",
            "Docs are read-only; no runtime or engine changes are applied.",
        ],
        "override_paths": [
            "policy_engine.* (observe/enforce/tune) - telemetry only",
            "autonomy.budget.allowed_fields - supervised overrides only",
            "phase4.tuning_overrides.json (if present) - user-approved only",
        ],
        "execution_model": [
            "Core phases run sequentially (1→5) under orchestrator control.",
            "Extended phases (A–Z) are opt-in informational layers gated by config.",
            "Autonomous layers stay in supervised/disabled states unless explicitly enabled by the user.",
            "Reference exports live under .pipeline/reference and are safe to regenerate any time.",
        ],
    }

    json_path = output_dir / "pipeline_training_book.json"
    json_path.write_text(json.dumps(book, indent=2), encoding="utf-8")

    md_path = output_dir / "pipeline_training_book.md"
    md_path.write_text(_render_markdown(book), encoding="utf-8")

    return book


def verify_reference_bundle(
    manifest: Dict[str, Any],
    book: Dict[str, Any],
    *,
    output_dir: Path = Path(".pipeline/reference"),
    config_path: Path = Path("phase6_orchestrator/config.yaml"),
) -> Dict[str, Any]:
    """Perform lightweight verification checks for the reference artifacts."""
    files_present = {
        "ui_capabilities": (output_dir / "ui_capabilities.json").exists(),
        "book_json": (output_dir / "pipeline_training_book.json").exists(),
        "book_md": (output_dir / "pipeline_training_book.md").exists(),
    }

    phase_keys = {entry.get("phase_key") for entry in manifest.get("phases", []) if isinstance(entry, dict)}
    missing_alpha = [key for key in PHASE_ORDER_ALPHA if key not in phase_keys]
    missing_config_keys = [
        entry.get("phase_key")
        for entry in manifest.get("phases", [])
        if entry.get("phase_key") in PHASE_ORDER_ALPHA and not entry.get("config_keys")
    ]

    autonomy_entry = next((p for p in manifest.get("phases", []) if p.get("phase_key") == "phaseG"), {})
    gates = autonomy_entry.get("safety_gates", {}) if isinstance(autonomy_entry, dict) else {}
    autonomy_ok = (
        isinstance(gates, dict)
        and "enable" in gates
        and "supervised_threshold" in gates
        and "override_limits" in gates
    )

    schemas = book.get("schemas", {})
    expected_phase_schema_names = set(schema_registry._SCHEMAS.keys()) if schema_registry and hasattr(schema_registry, "_SCHEMAS") else set()  # type: ignore[attr-defined]
    recorded_phase_schema_names = set(schemas.get("phase_registry", {}).keys()) if isinstance(schemas.get("phase_registry"), dict) else set()
    schemas_match = expected_phase_schema_names.issubset(recorded_phase_schema_names)
    pipeline_state_version_ok = schemas.get("pipeline_state_version") == CANONICAL_SCHEMA_VERSION

    results = {
        "directories_exist": output_dir.exists(),
        "files_present": files_present,
        "phases_a_z_present": len(missing_alpha) == 0,
        "missing_alpha": missing_alpha,
        "config_keys_present": len(missing_config_keys) == 0,
        "missing_config_keys": missing_config_keys,
        "autonomy_fields_ok": autonomy_ok,
        "schema_registry_match": schemas_match,
        "pipeline_state_version_ok": pipeline_state_version_ok,
        "runtime_mutated": False,  # Documentation-only operation
    }

    overall_ok = (
        results["directories_exist"]
        and all(files_present.values())
        and results["phases_a_z_present"]
        and results["config_keys_present"]
        and results["autonomy_fields_ok"]
        and results["schema_registry_match"]
        and results["pipeline_state_version_ok"]
    )
    return {"status": "pass" if overall_ok else "fail", "results": results, "generated_at": datetime.utcnow().isoformat() + "Z", "source_config": str(config_path)}


def export_reference_bundle(
    config_path: Path = Path("phase6_orchestrator/config.yaml"),
    output_dir: Path = Path(".pipeline/reference"),
) -> Dict[str, Any]:
    """Generate manifest + training book, then run verification."""
    manifest_path = generate_ui_capabilities(config_path=config_path, output_path=output_dir / "ui_capabilities.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    book = generate_pipeline_book(config_path=config_path, output_dir=output_dir)
    summary = verify_reference_bundle(manifest, book, output_dir=output_dir, config_path=config_path)
    summary["artifact_paths"] = {
        "ui_capabilities": str(manifest_path),
        "book_json": str(output_dir / "pipeline_training_book.json"),
        "book_md": str(output_dir / "pipeline_training_book.md"),
    }
    return summary


__all__ = ["generate_pipeline_book", "export_reference_bundle", "verify_reference_bundle"]


if __name__ == "__main__":
    result = export_reference_bundle()
    print(json.dumps(result, indent=2))
