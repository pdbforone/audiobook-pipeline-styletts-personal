#!/usr/bin/env python3
"""
Quick diagnostic to check Phase 5 results
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
phase4_audio_dir = PROJECT_ROOT / "phase4_tts" / "audio_chunks"
phase5_processed_dir = PROJECT_ROOT / "phase5_enhancement" / "processed"
phase5_output_dir = PROJECT_ROOT / "phase5_enhancement" / "output"
pipeline_json = PROJECT_ROOT / "pipeline.json"

print("=" * 70)
print("PHASE 5 RESULTS DIAGNOSTIC")
print("=" * 70)

# Check Phase 4 audio chunks
print("\n📁 Phase 4 Audio Chunks:")
if phase4_audio_dir.exists():
    phase4_files = sorted(phase4_audio_dir.glob("*.wav"))
    print(f"   Total: {len(phase4_files)} files")
    if phase4_files:
        print(f"   First: {phase4_files[0].name}")
        print(f"   Last:  {phase4_files[-1].name}")
else:
    print(f"   ❌ Directory not found: {phase4_audio_dir}")

# Check Phase 5 processed chunks
print("\n📁 Phase 5 Processed Chunks:")
if phase5_processed_dir.exists():
    phase5_files = sorted(phase5_processed_dir.glob("enhanced_*.wav"))
    print(f"   Total: {len(phase5_files)} files")
    if phase5_files:
        print(f"   First: {phase5_files[0].name}")
        print(f"   Last:  {phase5_files[-1].name}")

        # Check for gaps
        expected_count = (
            len(phase4_files) if phase4_audio_dir.exists() else 637
        )
        if len(phase5_files) < expected_count:
            print(f"   ⚠️  MISSING: {expected_count - len(phase5_files)} files")
            print(f"   Expected: {expected_count} files")
        else:
            print("   ✅ All chunks processed!")
else:
    print(f"   ❌ Directory not found: {phase5_processed_dir}")

# Check final audiobook
print("\n📁 Final Audiobook:")
if phase5_output_dir.exists():
    audiobook = phase5_output_dir / "audiobook.mp3"
    if audiobook.exists():
        size_mb = audiobook.stat().st_size / (1024 * 1024)
        print(f"   ✅ audiobook.mp3 exists ({size_mb:.1f} MB)")
    else:
        print("   ❌ audiobook.mp3 NOT FOUND")
else:
    print(f"   ❌ Output directory not found: {phase5_output_dir}")

# Check pipeline.json
print("\n📄 Pipeline.json Status:")
if pipeline_json.exists():
    with open(pipeline_json, "r") as f:
        data = json.load(f)

    phase5_data = data.get("phase5", {})
    if phase5_data:
        status = phase5_data.get("status", "unknown")
        chunks = phase5_data.get("chunks", [])
        metrics = phase5_data.get("metrics", {})

        print(f"   Status: {status}")
        print(f"   Chunks recorded: {len(chunks)}")

        if metrics:
            successful = metrics.get("successful", 0)
            failed = metrics.get("failed", 0)
            print(f"   Successful: {successful}")
            print(f"   Failed: {failed}")

            if successful > 0:
                print(f"   ✅ Phase 5 completed with {successful} chunks")
            if failed > 0:
                print(f"   ⚠️  {failed} chunks failed")
    else:
        print("   ❌ No phase5 data in pipeline.json")
else:
    print("   ❌ pipeline.json not found")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

# Count files
phase4_count = (
    len(list(phase4_audio_dir.glob("*.wav")))
    if phase4_audio_dir.exists()
    else 0
)
phase5_count = (
    len(list(phase5_processed_dir.glob("enhanced_*.wav")))
    if phase5_processed_dir.exists()
    else 0
)

if phase5_count == phase4_count and phase5_count > 0:
    print(f"✅ SUCCESS: All {phase5_count} chunks processed")
    print("✅ Ready to listen to audiobook.mp3")
elif phase5_count > 0:
    print(f"⚠️  PARTIAL: {phase5_count}/{phase4_count} chunks processed")
    print(f"⚠️  Missing {phase4_count - phase5_count} chunks")
    print("\n💡 Recommendation: Run direct mode to process missing chunks")
else:
    print("❌ FAILED: No chunks processed")
    print("\n💡 Recommendation: Check Phase 5 logs for errors")

print("=" * 70)
