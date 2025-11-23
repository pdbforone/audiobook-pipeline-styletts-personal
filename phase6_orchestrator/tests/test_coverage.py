"""
Coverage Verification Test for Audiobook Pipeline
Tests that no text is skipped between Phase 2 → Phase 3 → Phase 4
"""

import json
import random
from pathlib import Path
import difflib
from typing import Tuple, Dict
import sys

# Try to import librosa for audio checks
try:
    import librosa

    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print(
        "⚠️  Warning: librosa not available. Audio duration checks will be skipped."
    )


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison by:
    - Lowercasing
    - Removing extra whitespace
    - Removing punctuation (optional - can be too aggressive)
    - Stripping leading/trailing whitespace
    """
    # Remove extra whitespace
    text = " ".join(text.split())
    # Lowercase for comparison
    text = text.lower()
    # Strip
    text = text.strip()
    return text


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two texts using difflib."""
    return difflib.SequenceMatcher(None, text1, text2).ratio()


def test_phase2_to_phase3_coverage(
    pipeline_json_path: Path, file_id: str, show_diff: bool = False
) -> Tuple[bool, Dict]:
    """
    Test that Phase 3 chunks cover all Phase 2 extracted text.

    Args:
        pipeline_json_path: Path to pipeline.json
        file_id: File ID to test
        show_diff: Whether to show diff if texts don't match

    Returns:
        Tuple of (success: bool, results: dict)
    """
    print(f"\n{'='*70}")
    print("TEST 1: Phase 2 → Phase 3 Text Coverage")
    print(f"{'='*70}")

    with open(pipeline_json_path, "r", encoding="utf-8") as f:
        pipeline = json.load(f)

    # Get Phase 2 extracted text path
    try:
        phase2_data = pipeline["phase2"]["files"][file_id]
        extracted_text_path_str = phase2_data.get(
            "extracted_text_path"
        ) or phase2_data.get("output_file")
        extracted_text_path = Path(extracted_text_path_str)

        # Resolve relative paths from pipeline root
        if not extracted_text_path.is_absolute():
            extracted_text_path = (
                pipeline_json_path.parent / extracted_text_path
            ).resolve()
    except KeyError as e:
        return False, {"error": f"Phase 2 data not found for {file_id}: {e}"}

    # Get Phase 3 chunk paths
    try:
        phase3_data = pipeline["phase3"]["files"][file_id]
        chunk_paths_data = phase3_data.get("chunk_paths", [])

        # Handle both list and dict formats
        chunk_paths = []
        if isinstance(chunk_paths_data, list):
            # List format: just paths as strings
            for chunk_path_str in chunk_paths_data:
                chunk_path = Path(chunk_path_str)
                # Resolve relative paths
                if not chunk_path.is_absolute():
                    chunk_path = (
                        pipeline_json_path.parent / chunk_path
                    ).resolve()
                chunk_paths.append(chunk_path)
        elif isinstance(chunk_paths_data, dict):
            # Dict format: {chunk_id: {path: "...", ...}} or {chunk_id: "path"}
            for chunk_id in sorted(
                chunk_paths_data.keys(),
                key=lambda x: int(x.split("_")[-1]) if "_" in x else int(x),
            ):
                chunk_info = chunk_paths_data[chunk_id]
                chunk_path_str = (
                    chunk_info.get("path")
                    if isinstance(chunk_info, dict)
                    else chunk_info
                )
                chunk_path = Path(chunk_path_str)
                # Resolve relative paths
                if not chunk_path.is_absolute():
                    chunk_path = (
                        pipeline_json_path.parent / chunk_path
                    ).resolve()
                chunk_paths.append(chunk_path)

    except KeyError as e:
        return False, {"error": f"Phase 3 data not found for {file_id}: {e}"}

    # Read Phase 2 extracted text
    try:
        with open(extracted_text_path, "r", encoding="utf-8") as f:
            original_text = f.read()
    except Exception as e:
        return False, {"error": f"Could not read Phase 2 text: {e}"}

    # Read and concatenate Phase 3 chunks
    chunk_texts = []
    missing_chunks = []
    for i, chunk_path in enumerate(chunk_paths):
        try:
            with open(chunk_path, "r", encoding="utf-8") as f:
                chunk_texts.append(f.read())
        except FileNotFoundError:
            missing_chunks.append((i, str(chunk_path)))
            chunk_texts.append("")  # Add empty to maintain order

    if missing_chunks:
        print(f"❌ Missing {len(missing_chunks)} chunk file(s):")
        for idx, path in missing_chunks[:5]:  # Show first 5
            print(f"   - Chunk {idx}: {path}")
        if len(missing_chunks) > 5:
            print(f"   ... and {len(missing_chunks) - 5} more")

    concatenated_text = "".join(chunk_texts)

    # Normalize for comparison
    original_norm = normalize_text(original_text)
    concat_norm = normalize_text(concatenated_text)

    # Calculate similarity
    similarity = calculate_text_similarity(original_norm, concat_norm)

    # Check if they match
    exact_match = original_norm == concat_norm

    results = {
        "original_length": len(original_text),
        "concatenated_length": len(concatenated_text),
        "original_normalized_length": len(original_norm),
        "concatenated_normalized_length": len(concat_norm),
        "similarity_ratio": similarity,
        "exact_match": exact_match,
        "num_chunks": len(chunk_paths),
        "missing_chunks": len(missing_chunks),
    }

    print("\n📊 Results:")
    print(f"  Original text length: {len(original_text):,} chars")
    print(f"  Concatenated chunks: {len(concatenated_text):,} chars")
    print(f"  Similarity ratio: {similarity:.4f} ({similarity*100:.2f}%)")
    print(f"  Number of chunks: {len(chunk_paths)}")

    if exact_match:
        print("  ✅ EXACT MATCH - All text preserved!")
        success = True
    elif similarity > 0.99:
        print(
            f"  ⚠️  NEAR MATCH - {similarity*100:.2f}% similar (may be whitespace differences)"
        )
        success = True
    else:
        print(f"  ❌ MISMATCH - Only {similarity*100:.2f}% similar")
        success = False

        if show_diff:
            print("\n🔍 First 500 chars of difference:")
            diff = difflib.unified_diff(
                original_norm[:500].splitlines(),
                concat_norm[:500].splitlines(),
                lineterm="",
                n=0,
            )
            for line in list(diff)[:20]:  # Show first 20 lines
                print(f"  {line}")

    return success, results


def test_phase3_to_phase4_coverage(
    pipeline_json_path: Path,
    file_id: str,
    sample_ratio: float = 0.2,
    min_samples: int = 5,
) -> Tuple[bool, Dict]:
    """
    Test that Phase 4 has audio for all Phase 3 chunks.
    Validates random samples for audio quality.

    Args:
        pipeline_json_path: Path to pipeline.json
        file_id: File ID to test
        sample_ratio: Ratio of chunks to sample for audio validation (0.0-1.0)
        min_samples: Minimum number of chunks to sample

    Returns:
        Tuple of (success: bool, results: dict)
    """
    print(f"\n{'='*70}")
    print("TEST 2: Phase 3 → Phase 4 Audio Coverage")
    print(f"{'='*70}")

    with open(pipeline_json_path, "r", encoding="utf-8") as f:
        pipeline = json.load(f)

    # Get Phase 3 chunk count
    try:
        phase3_data = pipeline["phase3"]["files"][file_id]
        chunk_paths_data = phase3_data.get("chunk_paths", [])
        # Handle both list and dict formats
        if isinstance(chunk_paths_data, list):
            num_text_chunks = len(chunk_paths_data)
        elif isinstance(chunk_paths_data, dict):
            num_text_chunks = len(chunk_paths_data)
        else:
            num_text_chunks = 0
    except KeyError as e:
        return False, {"error": f"Phase 3 data not found: {e}"}

    # Get Phase 4 audio paths
    try:
        phase4_data = pipeline["phase4"]["files"][file_id]
        audio_paths_raw = phase4_data.get("chunk_audio_paths", [])

        # Resolve relative paths from pipeline root
        audio_paths = []
        for audio_path_str in audio_paths_raw:
            audio_path = Path(audio_path_str)
            if not audio_path.is_absolute():
                audio_path = (pipeline_json_path.parent / audio_path).resolve()
            audio_paths.append(audio_path)
    except KeyError as e:
        return False, {"error": f"Phase 4 data not found: {e}"}

    print("\n📊 Counts:")
    print(f"  Phase 3 text chunks: {num_text_chunks}")
    print(f"  Phase 4 audio files: {len(audio_paths)}")

    # Check if counts match
    if num_text_chunks != len(audio_paths):
        print(
            f"  ❌ MISMATCH: {abs(num_text_chunks - len(audio_paths))} chunks difference!"
        )
        count_match = False
    else:
        print("  ✅ MATCH: All chunks have audio")
        count_match = True

    # Check for missing audio files
    missing_audio = []
    empty_audio = []

    for i, audio_path in enumerate(audio_paths):
        # audio_path is already a Path object
        if not audio_path.exists():
            missing_audio.append((i, str(audio_path)))

    if missing_audio:
        print(f"\n❌ Missing {len(missing_audio)} audio file(s):")
        for idx, path in missing_audio[:5]:
            print(f"   - Audio {idx}: {path}")
        if len(missing_audio) > 5:
            print(f"   ... and {len(missing_audio) - 5} more")
    else:
        print("  ✅ All audio files exist")

    # Sample random chunks for quality validation
    num_samples = max(min_samples, int(len(audio_paths) * sample_ratio))
    num_samples = min(num_samples, len(audio_paths))  # Don't exceed total

    if num_samples > 0 and LIBROSA_AVAILABLE:
        print(f"\n🎵 Validating {num_samples} random audio samples...")
        sample_indices = random.sample(range(len(audio_paths)), num_samples)

        for idx in sample_indices:
            audio_path = audio_paths[idx]  # Already a Path object
            if not audio_path.exists():
                continue

            try:
                y, sr = librosa.load(audio_path, sr=None)
                duration = len(y) / sr
                rms = librosa.feature.rms(y=y)[0].mean()

                if duration < 0.5:
                    empty_audio.append(
                        (idx, str(audio_path), f"too short: {duration:.2f}s")
                    )
                elif rms < 0.001:
                    empty_audio.append(
                        (idx, str(audio_path), f"silent: RMS={rms:.6f}")
                    )

            except Exception as e:
                empty_audio.append((idx, str(audio_path), f"error: {e}"))

        if empty_audio:
            print(f"  ⚠️  Found {len(empty_audio)} problematic audio file(s):")
            for idx, path, reason in empty_audio[:5]:
                print(f"     - Chunk {idx}: {reason}")
        else:
            print("  ✅ All sampled audio files have valid content")

    results = {
        "num_text_chunks": num_text_chunks,
        "num_audio_files": len(audio_paths),
        "count_match": count_match,
        "missing_audio": len(missing_audio),
        "empty_audio": len(empty_audio),
        "samples_tested": num_samples if LIBROSA_AVAILABLE else 0,
    }

    success = count_match and len(missing_audio) == 0 and len(empty_audio) == 0

    return success, results


def run_coverage_tests(
    pipeline_json_path: str = "../pipeline.json",
    file_id: str = None,
    show_diff: bool = False,
) -> bool:
    """
    Run all coverage tests.

    Args:
        pipeline_json_path: Path to pipeline.json
        file_id: File ID to test (if None, uses first available)
        show_diff: Show text differences if mismatch

    Returns:
        True if all tests pass
    """
    pipeline_path = Path(pipeline_json_path)

    if not pipeline_path.exists():
        print(f"❌ Error: pipeline.json not found at {pipeline_path}")
        return False

    # Load pipeline to get file_id if not provided
    with open(pipeline_path, "r", encoding="utf-8") as f:
        pipeline = json.load(f)

    if file_id is None:
        # Get first file_id from phase2
        try:
            file_id = list(pipeline["phase2"]["files"].keys())[0]
            print(f"📁 Using file_id: {file_id}")
        except (KeyError, IndexError):
            print("❌ Error: No files found in pipeline.json")
            return False

    # Run tests
    test1_success, test1_results = test_phase2_to_phase3_coverage(
        pipeline_path, file_id, show_diff
    )

    test2_success, test2_results = test_phase3_to_phase4_coverage(
        pipeline_path, file_id
    )

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(
        f"Test 1 (Phase 2→3 Text Coverage): {'✅ PASS' if test1_success else '❌ FAIL'}"
    )
    print(
        f"Test 2 (Phase 3→4 Audio Coverage): {'✅ PASS' if test2_success else '❌ FAIL'}"
    )

    overall_success = test1_success and test2_success

    if overall_success:
        print("\n🎉 ALL TESTS PASSED - No text skipped!")
    else:
        print("\n❌ SOME TESTS FAILED - Review results above")

    print(f"{'='*70}\n")

    return overall_success


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Test coverage: verify no text is skipped in the pipeline"
    )
    parser.add_argument(
        "--pipeline-json",
        default="../pipeline.json",
        help="Path to pipeline.json (default: ../pipeline.json)",
    )
    parser.add_argument(
        "--file-id", help="File ID to test (default: use first file)"
    )
    parser.add_argument(
        "--show-diff",
        action="store_true",
        help="Show text differences if mismatch found",
    )

    args = parser.parse_args()

    success = run_coverage_tests(
        pipeline_json_path=args.pipeline_json,
        file_id=args.file_id,
        show_diff=args.show_diff,
    )

    sys.exit(0 if success else 1)
