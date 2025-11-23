"""
Re-run Phase 5 on Meditations Chunks with Phrase Cleaning
This will clean the phrases BEFORE concatenation, preserving all content.
"""

import sys
from pathlib import Path

# Add phase5 to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from phase5_enhancement.main import main as phase5_main
import argparse


def run_phase5_on_meditations():
    """Run Phase 5 with meditations_chunks as input."""

    # Override config with our settings
    args = argparse.Namespace(
        config="config.yaml",
        input_dir="meditations_chunks",  # ← Our chunks directory
        output_dir="processed",  # ← Output directory
        pipeline_json=None,  # We'll handle this separately
        enable_phrase_cleanup=True,  # ← Enable cleaning!
        resume=False,
    )

    print("=" * 70)
    print("RE-RUNNING PHASE 5 ON MEDITATIONS CHUNKS")
    print("=" * 70)
    print("Input:  meditations_chunks/")
    print("Output: processed/")
    print("Phrase cleanup: ENABLED ✓")
    print("=" * 70)
    print()

    # Run Phase 5
    phase5_main(args)

    print()
    print("=" * 70)
    print("✅ DONE!")
    print("Check: processed/meditations_audiobook.mp3")
    print("=" * 70)


if __name__ == "__main__":
    run_phase5_on_meditations()
