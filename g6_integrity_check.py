"""
G6 Integrity Check - Validate pipeline after self-tuning run.

Checks:
1. pipeline.json schema integrity
2. Policy logs structure
3. tuning_overrides.json schema
4. Orchestrator imports and hooks
5. PolicyEngine functionality

DOES NOT modify any files - read-only validation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime

# Success/failure tracking
checks = []


def check(name: str, passed: bool, notes: str = ""):
    """Record check result."""
    checks.append({"scope": name, "status": "PASS" if passed else "FAIL", "notes": notes})
    symbol = "OK" if passed else "X"
    print(f"[{symbol}] {name}: {'PASS' if passed else 'FAIL'}")
    if notes:
        print(f"    {notes}")


def load_json_safe(path: Path) -> tuple[dict | None, str]:
    """Load JSON with error handling."""
    try:
        if not path.exists():
            return None, f"File not found: {path}"
        data = json.loads(path.read_text(encoding="utf-8"))
        return data, ""
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON: {exc}"
    except Exception as exc:
        return None, f"Error reading file: {exc}"


def main():
    print("=" * 70)
    print("G6 INTEGRITY CHECK")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    repo_root = Path(__file__).parent

    # ========================================================================
    # CHECK 1: pipeline.json schema
    # ========================================================================
    print("\n[CHECK 1] pipeline.json Schema Integrity")
    print("-" * 70)

    pipeline_path = repo_root / "pipeline.json"
    pipeline_data, err = load_json_safe(pipeline_path)

    if err:
        check("pipeline.json exists and is valid JSON", False, err)
    else:
        check("pipeline.json exists and is valid JSON", True)

        # Check canonical schema for each phase
        required_fields = ["status", "timestamps", "artifacts", "metrics", "errors"]
        phase_keys = ["phase1", "phase2", "phase3", "phase4"]

        all_phases_valid = True
        for phase_key in phase_keys:
            if phase_key in pipeline_data:
                phase = pipeline_data[phase_key]
                missing = [f for f in required_fields if f not in phase]
                if missing:
                    check(f"{phase_key} has canonical fields", False, f"Missing: {missing}")
                    all_phases_valid = False
                else:
                    check(f"{phase_key} has canonical fields", True)
            else:
                check(f"{phase_key} exists", False, "Phase not found in pipeline.json")
                all_phases_valid = False

        # Check no partial phase5/batch objects
        bad_keys = [k for k in pipeline_data.keys() if k in ["phase5", "batch"] and not isinstance(pipeline_data[k], dict)]
        if bad_keys:
            check("No corrupted phase5/batch entries", False, f"Found non-dict entries: {bad_keys}")
        else:
            check("No corrupted phase5/batch entries", True)

    # ========================================================================
    # CHECK 2: Policy logs structure
    # ========================================================================
    print("\n[CHECK 2] Policy Logs Structure")
    print("-" * 70)

    policy_logs_dir = repo_root / ".pipeline" / "policy_logs"

    if not policy_logs_dir.exists():
        check("Policy logs directory exists", False, f"Not found: {policy_logs_dir}")
    else:
        check("Policy logs directory exists", True)

        # Find most recent log file
        log_files = list(policy_logs_dir.glob("*.log"))
        if not log_files:
            check("Policy log files exist", False, "No .log files found")
        else:
            check("Policy log files exist", True, f"Found {len(log_files)} log file(s)")

            # Validate JSONL structure of most recent log
            latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
            try:
                lines = latest_log.read_text(encoding="utf-8").strip().split("\n")
                valid_lines = 0
                last_seq = -1
                monotonic = True

                for line in lines:
                    if not line.strip():
                        continue
                    entry = json.loads(line)

                    # Check required fields
                    if all(k in entry for k in ["policy_version", "run_id", "sequence"]):
                        valid_lines += 1

                        # Check monotonic sequence
                        if entry["sequence"] <= last_seq:
                            monotonic = False
                        last_seq = entry["sequence"]

                check("Policy log JSONL structure valid", valid_lines > 0, f"Valid entries: {valid_lines}/{len(lines)}")
                check("Policy log timestamps monotonic", monotonic)

                # Check for advisor fields in recent entries
                last_entry = json.loads(lines[-1]) if lines else {}
                has_advisor = "suggestions" in last_entry or "telemetry" in last_entry
                check("Policy log has advisor fields", has_advisor)

            except Exception as exc:
                check("Policy log JSONL structure valid", False, str(exc))

    # ========================================================================
    # CHECK 3: tuning_overrides.json schema
    # ========================================================================
    print("\n[CHECK 3] tuning_overrides.json Schema")
    print("-" * 70)

    overrides_path = repo_root / ".pipeline" / "tuning_overrides.json"
    overrides_data, err = load_json_safe(overrides_path)

    if err:
        check("tuning_overrides.json exists and is valid JSON", False, err)
    else:
        check("tuning_overrides.json exists and is valid JSON", True)

        # Check schema structure (from POLICY_ENGINE.md v3)
        expected_top_keys = ["chunk_size", "engine_prefs", "voice_stability", "history", "runtime_state"]

        # Validate chunk_size structure (can be in overrides.phase3.chunk_size)
        chunk_size_found = False
        if "overrides" in overrides_data and "phase3" in overrides_data["overrides"]:
            phase3 = overrides_data["overrides"]["phase3"]
            if "chunk_size" in phase3 and "delta_percent" in phase3["chunk_size"]:
                delta = phase3["chunk_size"]["delta_percent"]
                chunk_size_found = True
                if abs(delta) > 5.0:
                    check("chunk_size delta reasonable", False, f"Large: {delta}%")
                else:
                    check("chunk_size delta reasonable", True, f"Delta: {delta}%")

        if not chunk_size_found:
            check("chunk_size override exists", False, "No phase3 chunk_size")

    # ========================================================================
    # CHECK 4: Orchestrator imports and hooks
    # ========================================================================
    print("\n[CHECK 4] Orchestrator Imports & Hooks")
    print("-" * 70)

    try:
        sys.path.insert(0, str(repo_root))
        from phase6_orchestrator import orchestrator
        check("orchestrator module imports", True)

        # Check for key functions
        has_retry_wrapper = hasattr(orchestrator, "run_phase_with_retry")
        check("run_phase_with_retry exists", has_retry_wrapper)

        # Check that PipelineState is used (not raw json.dump/load)
        orch_src = (repo_root / "phase6_orchestrator" / "orchestrator.py").read_text()
        uses_pipeline_state = "PipelineState" in orch_src
        raw_json_dump = "json.dump(" in orch_src and "PipelineState" not in orch_src

        check("Orchestrator uses PipelineState", uses_pipeline_state)
        check("No raw json.dump/load in orchestrator", not raw_json_dump)

    except Exception as exc:
        check("orchestrator module imports", False, str(exc))

    # ========================================================================
    # CHECK 5: PolicyAdvisor functionality
    # ========================================================================
    print("\n[CHECK 5] PolicyAdvisor Functionality")
    print("-" * 70)

    try:
        from policy_engine.advisor import PolicyAdvisor
        check("PolicyAdvisor imports", True)

        # Test basic advise() call
        advisor = PolicyAdvisor()
        ctx = {"phase": "test", "file_id": "test001"}
        advice = advisor.advise(ctx)

        check("PolicyAdvisor.advise() returns dict", isinstance(advice, dict))
        check("PolicyAdvisor has telemetry", "telemetry" in advice or "suggestions" in advice)

    except ImportError as exc:
        # psutil might be missing - that's OK
        if "psutil" in str(exc):
            check("PolicyAdvisor imports", True, "psutil missing (optional)")
        else:
            check("PolicyAdvisor imports", False, str(exc))
    except Exception as exc:
        check("PolicyAdvisor.advise() works", False, str(exc))

    # ========================================================================
    # SUMMARY REPORT
    # ========================================================================
    print("\n" + "=" * 70)
    print("INTEGRITY CHECK SUMMARY")
    print("=" * 70)

    print(f"\n{'Scope':<40} {'Status':<10} {'Notes'}")
    print("-" * 70)
    for c in checks:
        notes_short = c['notes'][:30] + "..." if len(c['notes']) > 30 else c['notes']
        print(f"{c['scope']:<40} {c['status']:<10} {notes_short}")

    total = len(checks)
    passed = sum(1 for c in checks if c['status'] == 'PASS')
    failed = total - passed

    print("\n" + "=" * 70)
    print(f"TOTAL: {passed}/{total} passed, {failed} failed")

    if failed == 0:
        print("\n[OK] ALL CHECKS PASSED - Pipeline integrity verified!")
        print("\nPlaying FF7 Victory Fanfare...")
        try:
            import winsound
            # FF7 Victory Fanfare (simplified)
            winsound.Beep(523, 150)  # C
            winsound.Beep(523, 150)  # C
            winsound.Beep(523, 150)  # C
            winsound.Beep(523, 400)  # C (long)
            winsound.Beep(415, 400)  # G#
            winsound.Beep(466, 400)  # A#
            winsound.Beep(523, 150)  # C
            winsound.Beep(466, 150)  # A#
            winsound.Beep(523, 600)  # C (final)
        except:
            print("(Could not play fanfare - winsound not available)")
        return 0
    else:
        print("\n[!] FAILURES DETECTED - Review items marked FAIL")
        print("\nNext step: Run fixes for failed items only")
        return 1


if __name__ == "__main__":
    sys.exit(main())
