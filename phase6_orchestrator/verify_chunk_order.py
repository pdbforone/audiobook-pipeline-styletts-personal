#!/usr/bin/env python3
"""
Verify that Gift of Magi chunks are in correct order
Checks both the enhanced files and analyzes the concatenation
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
    match = re.search(r'_chunk_(\d+)', filename)
    if match:
        return int(match.group(1))
    match = re.search(r'enhanced_(\d+)', filename)
    if match:
        return int(match.group(1))
    match = re.search(r'(\d+)', filename)
    if match:
        return int(match.group(1))
    return 0

def main():
    console.print("\n[bold cyan]Gift of Magi - Order Verification[/bold cyan]\n")
    
    # Check enhanced files order
    processed_dir = Path("../phase5_enhancement/processed")
    enhanced_files = list(processed_dir.glob("enhanced_*.wav"))
    
    if not enhanced_files:
        console.print("[red]❌ No enhanced files found![/red]")
        console.print("Phase 5 may not have run yet.")
        return
    
    # Sort by filename (should be enhanced_0001.wav, enhanced_0002.wav, etc.)
    enhanced_files_sorted = sorted(enhanced_files, key=lambda f: f.name)
    
    console.print(f"[yellow]Enhanced Files Check[/yellow]")
    console.print(f"  📊 Total files: {len(enhanced_files_sorted)}")
    
    # Extract chunk numbers
    chunk_numbers = []
    for f in enhanced_files_sorted:
        chunk_num = extract_chunk_number(str(f))
        chunk_numbers.append(chunk_num)
    
    console.print(f"  📝 First 10: {chunk_numbers[:10]}")
    console.print(f"  📝 Last 5: {chunk_numbers[-5:]}")
    
    # Check if sequential
    expected = list(range(1, len(chunk_numbers) + 1))
    is_correct = chunk_numbers == expected
    
    if is_correct:
        console.print("  ✅ [bold green]Chunks are in CORRECT ORDER![/bold green]")
    else:
        console.print("  ❌ [bold red]Chunks are OUT OF ORDER![/bold red]")
        
        # Show mismatches
        table = Table(title="Order Mismatches")
        table.add_column("Position", style="cyan")
        table.add_column("Expected", style="green")
        table.add_column("Actual", style="red")
        
        mismatches = 0
        for i, (exp, act) in enumerate(zip(expected, chunk_numbers), 1):
            if exp != act:
                table.add_row(str(i), str(exp), str(act))
                mismatches += 1
                if mismatches >= 10:  # Show first 10 mismatches
                    break
        
        console.print(table)
        console.print(f"\n  Total mismatches: {sum(1 for e, a in zip(expected, chunk_numbers) if e != a)}")
    
    # Check audiobook
    audiobook_path = processed_dir / "audiobook.mp3"
    
    console.print(f"\n[yellow]Audiobook Check[/yellow]")
    if audiobook_path.exists():
        size_mb = audiobook_path.stat().st_size / (1024 * 1024)
        console.print(f"  ✅ audiobook.mp3 exists ({size_mb:.1f} MB)")
        
        # Estimate expected size
        # 41 chunks * ~12 seconds/chunk * ~128 kbps = ~7-8 MB
        expected_size_range = (7, 15)
        if expected_size_range[0] <= size_mb <= expected_size_range[1]:
            console.print(f"  ✅ Size looks reasonable")
        else:
            console.print(f"  ⚠️  Size outside expected range ({expected_size_range[0]}-{expected_size_range[1]} MB)")
    else:
        console.print(f"  ❌ audiobook.mp3 NOT FOUND")
    
    # Check Phase 5 log
    log_path = Path("../phase5_enhancement/audio_enhancement.log")
    if log_path.exists():
        console.print(f"\n[yellow]Phase 5 Log Check[/yellow]")
        
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Read last 100 lines
            lines = f.readlines()
            last_lines = lines[-100:]
        
        # Look for sorting confirmation
        sort_msgs = [l for l in last_lines if 'Creating final audiobook' in l or 'chunks in order' in l]
        if sort_msgs:
            console.print("  ✅ Found concatenation log:")
            for msg in sort_msgs[-3:]:  # Show last 3 relevant messages
                console.print(f"    {msg.strip()}")
        
        # Check for errors
        error_msgs = [l for l in last_lines if 'ERROR' in l or 'Failed' in l]
        if error_msgs:
            console.print(f"\n  ⚠️  Found {len(error_msgs)} errors in log")
    
    # Final verdict
    console.print(f"\n[bold cyan]Verdict:[/bold cyan]")
    
    if is_correct and audiobook_path.exists():
        console.print("\n✅ [bold green]SUCCESS! Audiobook should play in correct order.[/bold green]")
        console.print("\n🎧 Listen to verify:")
        console.print("   Story should start: 'ONE DOLLAR AND EIGHTY-SEVEN CENTS...'")
        console.print("   And flow naturally through the complete story.")
        console.print(f"\n   Play: start \"\" \"{audiobook_path.absolute()}\"")
    elif not is_correct:
        console.print("\n❌ [bold red]PROBLEM: Chunks are still out of order[/bold red]")
        console.print("\nThe fix may not have been applied correctly.")
        console.print("Try running: .\\fix_chunk_order.bat")
    else:
        console.print("\n⚠️  [yellow]Chunks are ordered correctly, but audiobook is missing[/yellow]")
        console.print("Re-run Phase 5 to create the audiobook.")

if __name__ == "__main__":
    main()
