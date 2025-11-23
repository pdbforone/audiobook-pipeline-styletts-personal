#!/usr/bin/env python3
"""
Clear Phase 5 from pipeline.json so it processes all chunks fresh.
"""

import json
import sys
from pathlib import Path

# Paths
project_root = Path(__file__).parent.parent
pipeline_json = project_root / "pipeline.json"

print("=" * 80)
print("Clear Phase 5 from pipeline.json")
print("=" * 80)
print()

try:
    # Load pipeline.json
    with open(pipeline_json, "r") as f:
        pipeline = json.load(f)

    # Check if phase5 exists
    if "phase5" in pipeline:
        print("Found Phase 5 entry in pipeline.json")

        # Show what's being removed
        phase5_data = pipeline["phase5"]
        if "chunks" in phase5_data:
            completed = sum(
                1
                for c in phase5_data["chunks"]
                if c.get("status") == "complete"
            )
            total = len(phase5_data["chunks"])
            print(f"  - {completed} completed chunks out of {total} total")

        # Remove phase5
        del pipeline["phase5"]
        print("  ✓ Removed Phase 5 entry")
    else:
        print("No Phase 5 entry found (already clear)")

    # Write back
    with open(pipeline_json, "w") as f:
        json.dump(pipeline, f, indent=4)

    print()
    print("=" * 80)
    print("SUCCESS! Phase 5 cleared from pipeline.json")
    print("=" * 80)
    print()
    print("Now Phase 5 will process all 637 chunks fresh.")
    print()

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
