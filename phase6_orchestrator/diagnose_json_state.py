#!/usr/bin/env python3
"""
Quick diagnosis of pipeline_magi.json state
Shows which books are in the JSON and what Phase 5 processed
"""

import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()

def main():
    console.print("\n[bold cyan]Pipeline JSON Diagnosis[/bold cyan]\n")
    
    # Load JSON
    json_path = Path("../pipeline_magi.json")
    if not json_path.exists():
        console.print("[red]❌ pipeline_magi.json not found[/red]")
        return
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Check Phase 4
    console.print("[bold yellow]Phase 4 (TTS Synthesis)[/bold yellow]")
    phase4 = data.get("phase4", {})
    files = phase4.get("files", {})
    
    table = Table(title="Phase 4 Audio Chunks")
    table.add_column("Book", style="cyan")
    table.add_column("File ID", style="yellow")
    table.add_column("Chunks", style="green")
    
    for file_id, file_data in files.items():
        chunk_paths = file_data.get("chunk_audio_paths", [])
        book_name = "Gift of Magi" if "Gift" in file_id or "magi" in file_id.lower() else "Confucius"
        table.add_row(book_name, file_id, str(len(chunk_paths)))
    
    console.print(table)
    
    # Check Phase 5
    console.print("\n[bold yellow]Phase 5 (Audio Enhancement)[/bold yellow]")
    phase5 = data.get("phase5", {})
    
    if not phase5:
        console.print("[yellow]⚠️  Phase 5 has no data in JSON[/yellow]")
        console.print("This means Phase 5 hasn't updated the JSON yet.")
    else:
        phase5_files = phase5.get("files", {})
        
        if phase5_files:
            table2 = Table(title="Phase 5 Processing Status")
            table2.add_column("Book", style="cyan")
            table2.add_column("Status", style="yellow")
            table2.add_column("Processed", style="green")
            
            for file_id, file_data in phase5_files.items():
                book_name = "Gift of Magi" if "Gift" in file_id or "magi" in file_id.lower() else "Confucius"
                status = file_data.get("status", "unknown")
                enhanced_chunks = file_data.get("enhanced_chunks", [])
                table2.add_row(book_name, status, str(len(enhanced_chunks)))
            
            console.print(table2)
        else:
            console.print("[yellow]⚠️  Phase 5 files dict is empty[/yellow]")
    
    # Check actual files on disk
    console.print("\n[bold yellow]Actual Files on Disk[/bold yellow]")
    
    audio_chunks_dir = Path("../phase4_tts/audio_chunks")
    if audio_chunks_dir.exists():
        magi_chunks = list(audio_chunks_dir.glob("Gift*"))
        conf_chunks = list(audio_chunks_dir.glob("The_Analects*"))
        
        console.print(f"📁 Phase 4 audio_chunks/")
        console.print(f"  • Gift of Magi: {len(magi_chunks)} files")
        console.print(f"  • Confucius: {len(conf_chunks)} files")
    
    processed_dir = Path("../phase5_enhancement/processed")
    if processed_dir.exists():
        enhanced_files = list(processed_dir.glob("enhanced_*.wav"))
        audiobook = processed_dir / "audiobook.mp3"
        
        console.print(f"\n📁 Phase 5 processed/")
        console.print(f"  • Enhanced chunks: {len(enhanced_files)} files")
        console.print(f"  • audiobook.mp3: {'✅ EXISTS' if audiobook.exists() else '❌ MISSING'}")
        
        if audiobook.exists():
            size_mb = audiobook.stat().st_size / (1024 * 1024)
            console.print(f"  • Size: {size_mb:.1f} MB")
    
    # Recommendation
    console.print("\n[bold green]Recommendation:[/bold green]")
    console.print("\nBased on the diagnosis:")
    
    if len(files) > 1:
        console.print("[yellow]⚠️  Multiple books in pipeline_magi.json[/yellow]")
        console.print("\nYou should:")
        console.print("1. Run check_and_fix_json.py to clean up the JSON")
        console.print("2. Choose which book to keep (Confucius or Gift of Magi)")
        console.print("3. Run Phase 5 for that book")
    else:
        console.print("[green]✅ Only one book in JSON - looks good![/green]")
        console.print("\nYou can run Phase 5 directly:")
        console.print("  .\\run_phase5_direct.bat")

if __name__ == "__main__":
    main()
