"""
Diagnostic script for Phase 5 chunk loading issues.

This script helps identify why Phase 5 might be creating fewer enhanced files than expected.
It checks:
1. How many chunks Phase 4 created
2. What paths are in pipeline.json
3. Which chunks Phase 5 can actually find
4. Path resolution issues

Usage:
    python diagnose_phase5.py --file_id "376953453-The-World-of-Universals"
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_pipeline_json(json_path: Path) -> Dict[str, Any]:
    """Load pipeline.json safely."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ ERROR: pipeline.json not found at {json_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in pipeline.json: {e}")
        sys.exit(1)


def check_phase4_output(file_id: str, pipeline_data: Dict) -> tuple:
    """Check Phase 4 output for the given file_id."""
    phase4_files = pipeline_data.get("phase4", {}).get("files", {})

    if file_id not in phase4_files:
        print(f"❌ File ID '{file_id}' not found in Phase 4 output")
        print(f"   Available file IDs: {list(phase4_files.keys())}")
        return None, []

    file_data = phase4_files[file_id]
    status = file_data.get("status", "unknown")
    chunks_completed = file_data.get("chunks_completed", 0)
    total_chunks = file_data.get("total_chunks", 0)

    # Get chunk paths
    chunk_paths_direct = file_data.get("chunk_audio_paths", [])
    chunk_paths_artifacts = file_data.get("artifacts", {}).get("chunk_audio_paths", [])
    chunk_paths = chunk_paths_direct or chunk_paths_artifacts

    print(f"\n📊 Phase 4 Status for '{file_id}':")
    print(f"   Status: {status}")
    print(f"   Chunks completed: {chunks_completed}/{total_chunks}")
    print(f"   chunk_audio_paths (direct): {len(chunk_paths_direct)} entries")
    print(f"   chunk_audio_paths (artifacts): {len(chunk_paths_artifacts)} entries")
    print(f"   Using: {len(chunk_paths)} chunk paths")

    return file_data, chunk_paths


def check_physical_chunks(audio_dir: Path, file_id: str) -> List[Path]:
    """Check what chunk files actually exist on disk."""
    search_dirs = [
        audio_dir,
        audio_dir / file_id,
        audio_dir.parent / file_id,
    ]

    all_chunks = []
    print(f"\n📁 Searching for physical chunk files:")

    for search_dir in search_dirs:
        if not search_dir.exists():
            print(f"   ❌ {search_dir} - does not exist")
            continue

        chunks = sorted(search_dir.glob("chunk_*.wav"))
        if chunks:
            print(f"   ✅ {search_dir} - found {len(chunks)} chunks")
            all_chunks.extend(chunks)
        else:
            print(f"   ⚠️  {search_dir} - exists but no chunks found")

    return list(set(all_chunks))  # Remove duplicates


def analyze_path_resolution(chunk_paths: List[str], phase5_input_dir: Path) -> None:
    """Analyze how Phase 5 would resolve these paths."""
    print(f"\n🔍 Path Resolution Analysis:")
    print(f"   Phase 5 input_dir: {phase5_input_dir}")
    print(f"   input_dir exists: {phase5_input_dir.exists()}")

    print(f"\n   Checking each chunk path:")
    for i, path_str in enumerate(chunk_paths[:5], 1):  # Show first 5
        path = Path(path_str)
        print(f"\n   Chunk {i}: {path_str}")
        print(f"      Is absolute: {path.is_absolute()}")
        print(f"      Exists as-is: {path.exists()}")

        if not path.is_absolute():
            # Phase 5 logic: config.input_dir / Path(wav_path).name
            resolved = phase5_input_dir / path.name
            print(f"      Phase 5 would look for: {resolved}")
            print(f"      Exists: {resolved.exists()}")
        else:
            print(f"      Phase 5 would use: {path} (absolute)")

    if len(chunk_paths) > 5:
        print(f"\n   ... and {len(chunk_paths) - 5} more chunks")


def check_phase5_config(config_path: Path) -> Dict:
    """Load Phase 5 config.yaml."""
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"⚠️  Phase 5 config not found: {config_path}")
        return {}
    except Exception as e:
        print(f"⚠️  Error loading Phase 5 config: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose Phase 5 chunk loading issues"
    )
    parser.add_argument(
        "--file_id",
        required=True,
        help="File ID to diagnose (e.g., '376953453-The-World-of-Universals')"
    )
    parser.add_argument(
        "--pipeline_json",
        default="pipeline.json",
        help="Path to pipeline.json (default: pipeline.json)"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("Phase 5 Diagnostic Tool")
    print("=" * 80)

    # Load pipeline.json
    pipeline_path = Path(args.pipeline_json).resolve()
    print(f"\n📄 Loading pipeline.json from: {pipeline_path}")
    pipeline_data = load_pipeline_json(pipeline_path)

    # Check Phase 4 output
    file_data, chunk_paths = check_phase4_output(args.file_id, pipeline_data)
    if file_data is None:
        sys.exit(1)

    # Check physical chunks
    phase4_audio_dir = Path("phase4_tts/audio_chunks").resolve()
    physical_chunks = check_physical_chunks(phase4_audio_dir, args.file_id)

    print(f"\n📈 Summary:")
    print(f"   Chunks in pipeline.json: {len(chunk_paths)}")
    print(f"   Chunks found on disk: {len(physical_chunks)}")

    if len(chunk_paths) != len(physical_chunks):
        print(f"\n⚠️  WARNING: Mismatch between JSON and disk!")
        print(f"   This may cause Phase 5 to process fewer chunks than expected.")

    # Check Phase 5 configuration
    phase5_config_path = Path("phase5_enhancement/src/phase5_enhancement/config.yaml")
    if phase5_config_path.exists():
        config = check_phase5_config(phase5_config_path)
        input_dir_template = config.get("input_dir", "../../phase4_tts/audio_chunks")
        print(f"\n⚙️  Phase 5 Configuration:")
        print(f"   input_dir (template): {input_dir_template}")

        # Resolve actual input dir that Phase 5 would use
        phase5_src_dir = Path("phase5_enhancement/src/phase5_enhancement").resolve()
        base_input_dir = (phase5_src_dir / input_dir_template).resolve()
        actual_input_dir = base_input_dir / args.file_id

        print(f"   Resolved base: {base_input_dir}")
        print(f"   With file_id: {actual_input_dir}")
        print(f"   Exists: {actual_input_dir.exists()}")

        # Analyze path resolution
        if chunk_paths:
            analyze_path_resolution(chunk_paths, actual_input_dir)

    # Recommendations
    print(f"\n💡 Recommendations:")
    if len(chunk_paths) == 0:
        print("   1. ❌ No chunk_audio_paths in pipeline.json!")
        print("      → Phase 4 may not have written results correctly")
        print("      → Check Phase 4 logs for errors")
    elif len(chunk_paths) < len(physical_chunks):
        print("   1. ⚠️  pipeline.json has fewer chunks than disk")
        print("      → Re-run Phase 4 to update pipeline.json")
    elif len(physical_chunks) == 0:
        print("   1. ❌ No physical chunks found!")
        print("      → Check if Phase 4 output directory is correct")
        print("      → Expected: phase4_tts/audio_chunks/<file_id>/")
    else:
        print("   1. ✅ Chunk count looks good")
        print("   2. Check Phase 5 logs to see if chunks are being skipped")
        print("   3. Look for 'Audio file not found' warnings")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
