#!/usr/bin/env python3
"""
Diagnose chunk ordering issue in Phase 5
Checks the order at every stage of processing
"""

import json
import re
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()


def extract_chunk_number(filepath: str) -> int:
    """Extract chunk number from filename"""
    filename = Path(filepath).name
    # Try pattern: _chunk_NNN
    match = re.search(r"_chunk_(\d+)", filename)
    if match:
        return int(match.group(1))
    # Try pattern: chunk_NNN
    match = re.search(r"chunk_(\d+)", filename)
    if match:
        return int(match.group(1))
    # Try pattern: enhanced_NNNN
    match = re.search(r"enhanced_(\d+)", filename)
    if match:
        return int(match.group(1))
    # Fallback: any number
    match = re.search(r"(\d+)", filename)
    if match:
        return int(match.group(1))
    return 0


def main():
    console.print(
        "\n[bold cyan]Gift of Magi - Chunk Order Diagnosis[/bold cyan]\n"
    )

    # Check pipeline.json order
    console.print(
        "[yellow]1. Pipeline JSON - Phase 4 chunk_audio_paths order[/yellow]"
    )
    json_path = Path("../pipeline_magi.json")

    if not json_path.exists():
        console.print("[red]❌ pipeline_magi.json not found[/red]")
        return

    with open(json_path, "r") as f:
        data = json.load(f)

    phase4 = data.get("phase4", {})
    files = phase4.get("files", {})

    # Find Gift of Magi
    magi_file_id = None
    for file_id in files.keys():
        if "Gift" in file_id or "magi" in file_id.lower():
            magi_file_id = file_id
            break

    if not magi_file_id:
        console.print("[red]❌ Gift of Magi not found in Phase 4[/red]")
        return

    chunk_audio_paths = files[magi_file_id].get("chunk_audio_paths", [])
    console.print(f"  📊 Total chunks in JSON: {len(chunk_audio_paths)}")

    # Extract chunk numbers from JSON paths
    json_chunk_numbers = []
    for path in chunk_audio_paths:
        chunk_num = extract_chunk_number(path)
        json_chunk_numbers.append(chunk_num)

    # Show first 10 and last 5
    console.print(f"  📝 Order in JSON (first 10): {json_chunk_numbers[:10]}")
    console.print(f"  📝 Order in JSON (last 5): {json_chunk_numbers[-5:]}")

    # Check if sorted
    is_sorted = json_chunk_numbers == sorted(json_chunk_numbers)
    if is_sorted:
        console.print("  ✅ Chunks are in correct order in JSON")
    else:
        console.print("  ❌ [red]CHUNKS ARE OUT OF ORDER IN JSON![/red]")
        console.print(f"  Expected: {sorted(json_chunk_numbers)[:10]}")

    # Check Phase 4 audio files on disk
    console.print(
        "\n[yellow]2. Phase 4 audio_chunks/ directory order[/yellow]"
    )
    audio_chunks_dir = Path("../phase4_tts/audio_chunks")
    magi_audio_files = sorted(audio_chunks_dir.glob("Gift*.wav"))

    console.print(f"  📊 Files on disk: {len(magi_audio_files)}")

    disk_chunk_numbers = []
    for f in magi_audio_files:
        chunk_num = extract_chunk_number(str(f))
        disk_chunk_numbers.append(chunk_num)

    console.print(
        f"  📝 First 10 files: {[f.name for f in magi_audio_files[:10]]}"
    )
    console.print(f"  📝 Chunk numbers: {disk_chunk_numbers[:10]}")

    # Check Phase 5 enhanced files
    console.print(
        "\n[yellow]3. Phase 5 processed/ enhanced files order[/yellow]"
    )
    processed_dir = Path("../phase5_enhancement/processed")
    enhanced_files = sorted(processed_dir.glob("enhanced_*.wav"))

    console.print(f"  📊 Enhanced files: {len(enhanced_files)}")

    if enhanced_files:
        enhanced_chunk_numbers = []
        for f in enhanced_files:
            chunk_num = extract_chunk_number(str(f))
            enhanced_chunk_numbers.append(chunk_num)

        console.print(
            f"  📝 First 10: {[f.name for f in enhanced_files[:10]]}"
        )
        console.print(f"  📝 Chunk numbers: {enhanced_chunk_numbers[:10]}")
        console.print(f"  📝 Last 5: {[f.name for f in enhanced_files[-5:]]}")
        console.print(f"  📝 Chunk numbers: {enhanced_chunk_numbers[-5:]}")

        # Check if enhanced files are sorted
        is_enhanced_sorted = enhanced_chunk_numbers == sorted(
            enhanced_chunk_numbers
        )
        if is_enhanced_sorted:
            console.print("  ✅ Enhanced files are in correct order")
        else:
            console.print("  ❌ [red]ENHANCED FILES ARE OUT OF ORDER![/red]")

    # Summary
    console.print("\n[bold green]Analysis:[/bold green]")

    if not is_sorted:
        console.print(
            "\n🔴 [bold red]PROBLEM FOUND: pipeline.json has chunks in wrong order![/bold red]"
        )
        console.print(
            "\nThis is the root cause. Phase 5 processes chunks in the order"
        )
        console.print("they appear in pipeline.json, which is incorrect.")
        console.print(
            "\nSolution: Fix Phase 4 to write chunk_audio_paths in correct order,"
        )
        console.print("OR fix Phase 5 to sort chunks before processing.")
    else:
        console.print("\n✅ pipeline.json has chunks in correct order")
        console.print(
            "\nIf audiobook is still out of order, the issue is in Phase 5's"
        )
        console.print(
            "concatenation logic (ThreadPoolExecutor completion order)."
        )

    # Create comparison table
    console.print("\n[bold cyan]Detailed Comparison:[/bold cyan]")
    table = Table(title="First 10 Chunks")
    table.add_column("Index", style="cyan")
    table.add_column("JSON Order", style="yellow")
    table.add_column("Expected", style="green")
    table.add_column("Match", style="white")

    for i in range(min(10, len(json_chunk_numbers))):
        expected = i + 1
        actual = json_chunk_numbers[i]
        match = "✅" if actual == expected else "❌"
        table.add_row(str(i), str(actual), str(expected), match)

    console.print(table)


if __name__ == "__main__":
    main()
