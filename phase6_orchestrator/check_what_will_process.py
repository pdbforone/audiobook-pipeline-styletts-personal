#!/usr/bin/env python3
"""
Check which books will be processed by Phase 5
"""

import json
from pathlib import Path
from rich.console import Console

console = Console()


def main():
    console.print("\n[bold cyan]What Will Phase 5 Process?[/bold cyan]\n")

    json_path = Path("../pipeline_magi.json")

    if not json_path.exists():
        console.print("[red]❌ pipeline_magi.json not found[/red]")
        return

    with open(json_path, "r") as f:
        data = json.load(f)

    phase4 = data.get("phase4", {})
    files = phase4.get("files", {})

    console.print(f"[yellow]Phase 4 contains {len(files)} file(s):[/yellow]\n")

    for file_id, file_data in files.items():
        chunk_paths = file_data.get("chunk_audio_paths", [])

        # Identify which book
        if "Gift" in file_id or "magi" in file_id.lower():
            book_name = "🎁 Gift of the Magi"
            color = "green"
        elif "Confucius" in file_id or "Analects" in file_id:
            book_name = "📚 The Analects of Confucius"
            color = "yellow"
        else:
            book_name = "❓ Unknown Book"
            color = "white"

        console.print(f"[{color}]{book_name}[/{color}]")
        console.print(f"  File ID: {file_id}")
        console.print(f"  Chunks: {len(chunk_paths)}")
        console.print()

    # Check what Phase 5 will process
    if len(files) == 0:
        console.print(
            "[red]⚠️  No files in Phase 4 - Phase 5 has nothing to process![/red]"
        )
    elif len(files) == 1:
        file_id = list(files.keys())[0]
        chunks = len(files[file_id].get("chunk_audio_paths", []))

        if "Gift" in file_id or "magi" in file_id.lower():
            console.print(
                f"[bold green]✅ Phase 5 will process ONLY Gift of Magi ({chunks} chunks)[/bold green]"
            )
        elif "Confucius" in file_id:
            console.print(
                f"[bold yellow]⚠️  Phase 5 will process ONLY Confucius ({chunks} chunks)[/bold yellow]"
            )
            console.print(
                "\nIf you want Gift of Magi, run: .\\switch_to_magi.bat"
            )
        else:
            console.print(
                f"[bold white]Phase 5 will process: {file_id} ({chunks} chunks)[/bold white]"
            )
    else:
        console.print(
            f"[bold red]⚠️  WARNING: Phase 5 will process ALL {len(files)} books![/bold red]"
        )

        total_chunks = sum(
            len(f.get("chunk_audio_paths", [])) for f in files.values()
        )
        console.print(f"\nTotal chunks: {total_chunks}")
        console.print("\nThis means:")
        console.print("• Phase 5 will process BOTH books together")
        console.print("• The audiobook will have MIXED content")
        console.print("• Processing will take longer")

        console.print("\n[bold cyan]Recommended Action:[/bold cyan]")
        console.print("Clean the JSON to only include Gift of Magi:")
        console.print("  .\\switch_to_magi.bat")


if __name__ == "__main__":
    main()
