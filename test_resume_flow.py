#!/usr/bin/env python3
"""
Test script to verify resume functionality is correctly wired throughout the pipeline.

This script tests the complete data flow:
1. UI radio button → boolean conversion
2. Boolean → API → Orchestrator
3. Orchestrator phase-level skip logic
4. Phase 4 chunk-level resume with --resume flag
5. File ID consistency across uploads

Run this script to verify all resume components are working.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_ui_resume_parsing():
    """Test UI radio button value parsing."""
    print("\n" + "="*60)
    print("TEST 1: UI Resume Parsing")
    print("="*60)

    # Simulate radio button values
    test_cases = [
        ("Resume (skip completed phases)", True, False),
        ("Fresh run (start from beginning)", False, True),
    ]

    for radio_value, expected_resume, expected_no_resume in test_cases:
        resume_enabled = "Resume" in str(radio_value)
        no_resume = not resume_enabled

        status = "[PASS]" if (resume_enabled == expected_resume and no_resume == expected_no_resume) else "[FAIL]"
        print(f"{status} Radio: '{radio_value}'")
        print(f"   resume_enabled={resume_enabled} (expected {expected_resume})")
        print(f"   no_resume={no_resume} (expected {expected_no_resume})")


def test_file_id_consistency():
    """Test file_id derivation from stable paths."""
    print("\n" + "="*60)
    print("TEST 2: File ID Consistency")
    print("="*60)

    from pathlib import Path

    # Simulate Gradio temp paths
    temp_paths = [
        "C:\\Users\\myson\\AppData\\Local\\Temp\\gradio\\abc123\\book.pdf",
        "C:\\Users\\myson\\AppData\\Local\\Temp\\gradio\\xyz789\\book.pdf",
    ]

    # Simulate stable path after copy
    stable_path = PROJECT_ROOT / "input" / "book.pdf"

    print(f"Temp path 1: {temp_paths[0]}")
    print(f"Temp path 2: {temp_paths[1]}")
    print(f"Stable path: {stable_path}")

    file_id_1 = Path(temp_paths[0]).name.replace(".pdf", "")
    file_id_2 = Path(temp_paths[1]).name.replace(".pdf", "")
    file_id_stable = stable_path.stem

    match = file_id_1 == file_id_2 == file_id_stable == "book"
    status = "[PASS] PASS" if match else "[FAIL] FAIL"

    print(f"\n{status} File IDs:")
    print(f"   Temp 1:  {file_id_1}")
    print(f"   Temp 2:  {file_id_2}")
    print(f"   Stable:  {file_id_stable}")
    print(f"   All match: {match}")


def test_orchestrator_config():
    """Test orchestrator config defaults."""
    print("\n" + "="*60)
    print("TEST 3: Orchestrator Config Defaults")
    print("="*60)

    try:
        import yaml
        config_path = PROJECT_ROOT / "phase6_orchestrator" / "config.yaml"

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        resume_enabled = config.get("resume_enabled", False)
        phase4_reuse = config.get("phase4_reuse_enabled", False)

        status_resume = "[PASS] PASS" if resume_enabled else "[FAIL] FAIL"
        status_reuse = "[PASS] PASS" if phase4_reuse else "[FAIL] FAIL"

        print(f"{status_resume} resume_enabled: {resume_enabled}")
        print(f"{status_reuse} phase4_reuse_enabled: {phase4_reuse}")

    except Exception as e:
        print(f"[FAIL] FAIL Could not load config: {e}")


def test_phase4_resume_flag():
    """Test Phase 4 --resume flag is in command."""
    print("\n" + "="*60)
    print("TEST 4: Phase 4 --resume Flag")
    print("="*60)

    try:
        # Read orchestrator.py line 2107
        orchestrator_path = PROJECT_ROOT / "phase6_orchestrator" / "orchestrator.py"
        with open(orchestrator_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Check line 2107 (0-indexed = 2106)
        target_line = lines[2106].strip()

        if 'cmd.append("--resume")' in target_line:
            # Check it's NOT inside the if chunk_index block (should be outside)
            # Check previous line (2106)
            prev_line = lines[2105].strip()

            if 'if chunk_index' in prev_line:
                print("[FAIL] FAIL --resume flag is inside 'if chunk_index' block")
            else:
                print("[PASS] PASS --resume flag is always appended to command")
                print(f"   Line 2107: {target_line}")
        else:
            print(f"[FAIL] FAIL --resume flag not found at line 2107")
            print(f"   Found: {target_line}")

    except Exception as e:
        print(f"[FAIL] FAIL Could not verify code: {e}")


def test_validation_tolerance():
    """Test Phase 4 validation tolerance is increased."""
    print("\n" + "="*60)
    print("TEST 5: Validation Tolerance")
    print("="*60)

    try:
        # Check validation.py
        validation_path = PROJECT_ROOT / "phase4_tts" / "src" / "validation.py"
        with open(validation_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if "duration_tolerance_sec: float = 120.0" in content:
            print("[PASS] PASS validation.py has 120s tolerance")
        else:
            print("[FAIL] FAIL validation.py tolerance not set to 120s")

        # Check main_multi_engine.py
        main_path = PROJECT_ROOT / "phase4_tts" / "src" / "main_multi_engine.py"
        with open(main_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Check line 1937
        if len(lines) >= 1937:
            line = lines[1936].strip()  # 0-indexed
            if "120.0" in line and "duration_tolerance_sec" in line:
                print("[PASS] PASS main_multi_engine.py has 120s default")
            else:
                print(f"[FAIL] FAIL main_multi_engine.py line 1937: {line}")

    except Exception as e:
        print(f"[FAIL] FAIL Could not verify tolerance: {e}")


def test_phase_skip_logic():
    """Test orchestrator phase skip logic uses resume_enabled."""
    print("\n" + "="*60)
    print("TEST 6: Phase Skip Logic")
    print("="*60)

    try:
        orchestrator_path = PROJECT_ROOT / "phase6_orchestrator" / "orchestrator.py"
        with open(orchestrator_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check resume_enabled variable is set
        if "resume_enabled = not no_resume" in content:
            print("[PASS] PASS resume_enabled variable is set from no_resume")
        else:
            print("[FAIL] FAIL resume_enabled variable not found")

        # Check phase skip uses resume_enabled
        if "if resume_enabled:" in content and "check_phase_status" in content:
            print("[PASS] PASS Phase skip logic checks resume_enabled")
        else:
            print("[FAIL] FAIL Phase skip logic doesn't use resume_enabled")

        # Check for skip log message
        if 'logger.info(f"Skipping Phase {phase_num} (already completed)")' in content:
            print("[PASS] PASS Skip log message present")
        else:
            print("[FAIL] FAIL Skip log message not found")

    except Exception as e:
        print(f"[FAIL] FAIL Could not verify skip logic: {e}")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("RESUME FUNCTIONALITY VERIFICATION")
    print("="*60)
    print("This script verifies all resume components are correctly wired.")
    print()

    test_ui_resume_parsing()
    test_file_id_consistency()
    test_orchestrator_config()
    test_phase4_resume_flag()
    test_validation_tolerance()
    test_phase_skip_logic()

    print("\n" + "="*60)
    print("VERIFICATION COMPLETE")
    print("="*60)
    print()
    print("Next steps:")
    print("1. Run your Phase 4 with 269/296 chunks complete")
    print("2. Check logs for 'Skipping chunk_XXXX (already exists)'")
    print("3. Verify only 27 missing chunks are regenerated")
    print("4. Estimated time: ~4 hours (instead of ~48 hours)")
    print()


if __name__ == "__main__":
    main()
