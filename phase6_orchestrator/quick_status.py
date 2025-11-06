#!/usr/bin/env python3
"""Quick status check for current pipeline state"""

import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

def main():
    # Read pipeline JSON
    json_path = Path("../pipeline_magi.json")
    if not json_path.exists():
        console.print("[red]❌ pipeline_magi.json not found[/red]")
        return
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Create status table
    table = Table(title="Pipeline Status")
    table.add_column("Phase", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")
    
    # Check each phase
    for phase_num in range(1, 6):
        phase_key = f"phase{phase_num}"
        if phase_key in data:
            phase = data[phase_key]
            status = phase.get("status", "unknown")
            
            # Get relevant details
            details = ""
            if phase_key == "phase4" and "files" in phase:
                file_ids = list(phase["files"].keys())
                if file_ids:
                    chunks = phase["files"][file_ids[0]].get("chunk_audio_paths", [])
                    details = f"{len(chunks)} audio chunks"
            elif phase_key == "phase5":
                if "processed_chunks" in phase:
                    total = phase.get("total_chunks", "?")
                    processed = phase.get("processed_chunks", 0)
                    details = f"{processed}/{total} chunks"
                elif "files" in phase:
                    file_ids = list(phase["files"].keys())
                    if file_ids:
                        file_data = phase["files"][file_ids[0]]
                        if "enhanced_chunks" in file_data:
                            details = f"{len(file_data['enhanced_chunks'])} enhanced"
            
            table.add_row(f"Phase {phase_num}", status, details)
        else:
            table.add_row(f"Phase {phase_num}", "not started", "")
    
    console.print(table)
    
    # Check for output files
    console.print("\n[bold cyan]Output Files:[/bold cyan]")
    phase5_output = Path("../phase5_enhancement/output/audiobook.mp3")
    if phase5_output.exists():
        size_mb = phase5_output.stat().st_size / (1024 * 1024)
        console.print(f"✅ audiobook.mp3 exists ({size_mb:.1f} MB)")
    else:
        console.print("❌ audiobook.mp3 not found")
    
    # Check processed chunks
    processed_dir = Path("../phase5_enhancement/processed")
    if processed_dir.exists():
        enhanced_files = list(processed_dir.glob("enhanced_*.wav"))
        console.print(f"ℹ️  {len(enhanced_files)} enhanced WAV files in processed/")
    
    # Check for errors
    if "phase5" in data:
        phase5 = data["phase5"]
        if "errors" in phase5 and phase5["errors"]:
            console.print(f"\n[red]⚠️  Phase 5 has {len(phase5['errors'])} errors[/red]")

if __name__ == "__main__":
    main()
