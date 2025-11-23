#!/usr/bin/env python3
"""
Ensure pipeline.json only has Gift of Magi before running Phase 5
Removes Confucius and other books
"""

import json
import shutil
from pathlib import Path
from rich.console import Console

console = Console()


def main():
    console.print("\n[bold cyan]Switch to Gift of Magi Only[/bold cyan]\n")

    json_path = Path("../pipeline_magi.json")
    backup_path = Path("../pipeline_magi.json.backup")

    if not json_path.exists():
        console.print("[red]❌ pipeline_magi.json not found[/red]")
        return False

    # Backup
    console.print("📋 Creating backup...")
    shutil.copy(json_path, backup_path)
    console.print(f"✅ Backed up to: {backup_path.name}\n")

    # Load JSON
    with open(json_path, "r") as f:
        data = json.load(f)

    phase4 = data.get("phase4", {})
    files = phase4.get("files", {})

    console.print("[yellow]Current Phase 4 files:[/yellow]")
    for file_id in files.keys():
        chunks = len(files[file_id].get("chunk_audio_paths", []))
        if "Gift" in file_id or "magi" in file_id.lower():
            console.print(f"  🎁 Gift of Magi: {file_id} ({chunks} chunks)")
        elif "Confucius" in file_id:
            console.print(f"  📚 Confucius: {file_id} ({chunks} chunks)")
        else:
            console.print(f"  ❓ {file_id} ({chunks} chunks)")

    # Find Gift of Magi
    magi_file_id = None
    magi_data = None

    for file_id, file_data in files.items():
        if "Gift" in file_id or "magi" in file_id.lower():
            magi_file_id = file_id
            magi_data = file_data
            break

    if not magi_file_id:
        console.print(
            "\n[red]❌ ERROR: Gift of Magi not found in Phase 4![/red]"
        )
        console.print("The pipeline may not have processed this book yet.")
        return False

    # Keep only Magi
    if len(files) == 1:
        console.print(
            "\n[green]✅ Only Gift of Magi is in JSON - nothing to clean[/green]"
        )
        return True
    else:
        console.print("\n[yellow]🔧 Removing other books...[/yellow]")

        removed_count = 0
        for file_id in list(files.keys()):
            if file_id != magi_file_id:
                console.print(f"  ✗ Removing: {file_id}")
                removed_count += 1

        # Update Phase 4
        phase4["files"] = {magi_file_id: magi_data}
        data["phase4"] = phase4

        # Clear Phase 5 so it re-runs
        if "phase5" in data:
            console.print("  🗑️  Clearing old Phase 5 data")
            data.pop("phase5")

        # Save
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)

        console.print("\n[bold green]✅ SUCCESS![/bold green]")
        console.print(f"  • Removed {removed_count} other book(s)")
        console.print(
            f"  • Kept Gift of Magi ({len(magi_data.get('chunk_audio_paths', []))} chunks)"
        )
        console.print("  • Cleared Phase 5 data")

        return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
