#!/usr/bin/env python3
"""
Process ONLY Confucius audiobook
Removes Gift of Magi from JSON and processes Confucius chunks
"""

import json
import shutil
from pathlib import Path
from rich.console import Console

console = Console()

def main():
    console.print("\n[bold cyan]Process Confucius Audiobook[/bold cyan]\n")
    
    # Paths
    json_path = Path("../pipeline_magi.json")
    backup_path = Path("../pipeline_magi.json.backup")
    
    # Backup
    console.print("📋 Creating backup...")
    shutil.copy(json_path, backup_path)
    console.print(f"✅ Backed up to: {backup_path.name}\n")
    
    # Load JSON
    console.print("📖 Loading pipeline JSON...")
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Check Phase 4
    phase4 = data.get("phase4", {})
    files = phase4.get("files", {})
    
    console.print(f"Found {len(files)} file(s) in Phase 4:\n")
    
    # Show what we found
    confucius_file_id = None
    for file_id in files.keys():
        chunks = len(files[file_id].get("chunk_audio_paths", []))
        if "Gift" in file_id or "magi" in file_id.lower():
            console.print(f"  🎁 Gift of Magi: {file_id} ({chunks} chunks)")
        else:
            console.print(f"  📚 Confucius: {file_id} ({chunks} chunks)")
            confucius_file_id = file_id
    
    if not confucius_file_id:
        console.print("\n[red]❌ ERROR: Could not find Confucius in Phase 4 data![/red]")
        return
    
    if len(files) == 1:
        console.print("\n[green]✅ Only Confucius in JSON - ready to process![/green]")
        console.print("\nRun: .\\run_phase5_direct.bat")
        return
    
    # Remove non-Confucius files
    console.print(f"\n🔧 Cleaning JSON...")
    console.print(f"✅ Keeping: {confucius_file_id}")
    
    # Keep only Confucius
    phase4["files"] = {confucius_file_id: files[confucius_file_id]}
    data["phase4"] = phase4
    
    # Remove Phase 5 so it re-runs
    if "phase5" in data:
        console.print("🗑️  Removing old Phase 5 data")
        data.pop("phase5")
    
    # Save
    console.print("\n💾 Saving updated JSON...")
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    console.print("\n[bold green]✅ SUCCESS![/bold green]")
    console.print("\n📊 JSON now contains:")
    console.print(f"  • Only Confucius ({len(files[confucius_file_id]['chunk_audio_paths'])} chunks)")
    console.print(f"  • Phase 5 data cleared (ready to process)")
    
    console.print("\n🎯 Next Step:")
    console.print("  .\\run_phase5_direct.bat")
    console.print("\nThis will process all 637 Confucius chunks and create the audiobook.")

if __name__ == "__main__":
    main()
