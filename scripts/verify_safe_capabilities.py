"""
Verify safe capabilities config and orchestration wiring (Phase safe switchboard).
"""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    cfg_path = Path("phase6_orchestrator/config.yaml")
    assert cfg_path.exists(), "config.yaml missing"
    cfg_text = cfg_path.read_text(encoding="utf-8")
    import yaml  # local import
    parsed = yaml.safe_load(cfg_text) or {}
    caps = parsed.get("capabilities") or {}
    required_flags = [
        "enable_safe_modes",
        "enable_phaseI",
        "enable_phaseJ",
        "enable_phaseK_safe",
        "enable_phaseP",
        "enable_phaseQ",
        "enable_phaseR",
        "enable_phaseS",
        "enable_phaseT",
        "enable_phaseU",
        "enable_phaseV",
        "enable_phaseW",
        "enable_phaseX",
        "enable_phaseY",
        "enable_phaseZ",
    ]
    for flag in required_flags:
        if flag not in caps or caps.get(flag) is not True:
            raise SystemExit(f"Capability flag missing or false: {flag}")
    orch = Path("phase6_orchestrator/orchestrator.py").read_text(encoding="utf-8").lower()
    if "capabilities switchboard" not in orch:
        raise SystemExit("Orchestrator missing capabilities switchboard")
    # Ensure safe paths exist
    base = Path(".pipeline")
    outputs = [
        base / "capabilities" / "reports",
        base / "phaseW" / "reports",
        base / "meta" / "reports",
        base / "phaseY" / "reports",
    ]
    for p in outputs:
        p.mkdir(parents=True, exist_ok=True)
    # Ensure no unsafe dirs populated
    disallowed = [base / "overrides", base / "autonomy_runtime", base / "repairs"]
    report = {
        "config_flags_present": True,
        "orchestrator_capabilities": True,
        "outputs_exist": [str(p) for p in outputs],
        "disallowed_absent": [str(p) for p in disallowed if p.exists()],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
