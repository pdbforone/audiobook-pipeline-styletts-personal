#!/usr/bin/env python3
"""
Test the improved Phase 1 classification on Systematic Theology.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_phase1_classification():
    """Test Phase 1 with improved classification."""
    phase1_dir = PROJECT_ROOT / "phase1-validation"
    pdf_path = PROJECT_ROOT / "input" / "Systematic Theology.pdf"

    print("🧪 Testing Improved Phase 1 Classification")
    print("=" * 60)

    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return False

    print(f"📄 Testing: {pdf_path.name}")
    print(f"   Location: {pdf_path}")

    # Run Phase 1 directly to test classification
    print("\n🔄 Running Phase 1 classification test...")
    print("   (This tests the new logic without full orchestrator)")

    # Build test command
    cmd = [
        "poetry",
        "run",
        "python",
        str(phase1_dir / "src" / "phase1_validation" / "validation.py"),
        f"--file={pdf_path}",
        "--json_path=../pipeline_test.json",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(phase1_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            print("\n❌ Phase 1 failed:")
            print(result.stderr[-500:])
            return False

        print("\n✅ Phase 1 completed successfully!")

        # Check the result
        import json

        test_json = PROJECT_ROOT / "pipeline_test.json"
        if test_json.exists():
            with open(test_json, "r") as f:
                data = json.load(f)

            files = data.get("phase1", {}).get("files", {})
            for file_id, file_data in files.items():
                if "Systematic" in file_id:
                    classification = file_data.get("classification", "unknown")
                    print("\n📊 Classification Result:")
                    print(f"   File: {file_id}")
                    print(f"   Classification: {classification}")

                    if classification == "text":
                        print("\n   ✅ CORRECT! Classified as 'text'")
                        print("   Phase 2 will now use fast pypdf extraction!")
                        return True
                    else:
                        print(
                            f"\n   ❌ WRONG! Still classified as '{classification}'"
                        )
                        print("   Expected: 'text'")
                        return False

        print(
            "\n⚠️  Could not verify classification (check pipeline_test.json)"
        )
        return False

    except subprocess.TimeoutExpired:
        print("\n❌ Phase 1 timeout (30s)")
        return False
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    print(
        """
This test will:
1. Run Phase 1 with the IMPROVED classification logic
2. Check if Systematic Theology is now correctly classified as 'text'
3. Verify the fix prevents the 158-minute OCR waste

Press Enter to continue...
"""
    )
    input()

    success = test_phase1_classification()

    if success:
        print(f"\n{'='*60}")
        print("🎉 SUCCESS! Classification is now correct!")
        print(f"{'='*60}")
        print("\n💡 Next Steps:")
        print(
            "  1. Run full orchestrator: python orchestrator.py <file> --phases 1 2"
        )
        print("  2. Phase 1 will classify as 'text' (5 seconds)")
        print("  3. Phase 2 will use pypdf (2-3 minutes, not 158!)")
        print("  4. Output will have 0 spacing errors (TTS-ready)")
    else:
        print(f"\n{'='*60}")
        print("❌ Test failed - classification still needs work")
        print(f"{'='*60}")

    sys.exit(0 if success else 1)
