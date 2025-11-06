#!/usr/bin/env python3
"""
Fix Phase 5's pipeline.json path and verify Phase 4 data exists
"""

import json
import yaml
from pathlib import Path
from rich.console import Console

console = Console()

def main():
    console.print("\n[bold cyan]Pipeline.json Path Fixer[/bold cyan]\n")
    
    project_root = Path(__file__).parent.parent
    config_path = project_root / "phase5_enhancement" / "src" / "phase5_enhancement" / "config.yaml"
    pipeline_json = project_root / "pipeline.json"
    
    console.print(f"[cyan]Config:[/cyan] {config_path}")
    console.print(f"[cyan]Pipeline JSON:[/cyan] {pipeline_json}")
    
    # Check pipeline.json exists
    if not pipeline_json.exists():
        console.print(f"\n[red]❌ pipeline.json not found at: {pipeline_json}[/red]")
        return 1
    
    # Load pipeline.json and check Phase 4 data
    console.print("\n[yellow]Checking pipeline.json...[/yellow]")
    with open(pipeline_json, 'r') as f:
        pipeline_data = json.load(f)
    
    phase4_data = pipeline_data.get("phase4", {})
    phase4_files = phase4_data.get("files", {})
    
    if not phase4_files:
        console.print("[red]❌ No Phase 4 files found in pipeline.json![/red]")
        console.print("[yellow]Phase 4 may need to be re-run[/yellow]")
        return 1
    
    console.print(f"[green]✓[/green] Phase 4 has {len(phase4_files)} file(s)")
    
    # Check for audio paths
    total_audio_paths = 0
    for file_id, file_data in phase4_files.items():
        audio_paths = file_data.get("chunk_audio_paths", [])
        total_audio_paths += len(audio_paths)
        console.print(f"  - {file_id}: {len(audio_paths)} audio chunks")
    
    console.print(f"[green]✓[/green] Total audio chunks in pipeline.json: {total_audio_paths}")
    
    if total_audio_paths == 0:
        console.print("[red]❌ No audio paths found in Phase 4 data![/red]")
        console.print("[yellow]Phase 4 may need finalization[/yellow]")
        return 1
    
    # Load config and fix pipeline_json path
    console.print("\n[yellow]Updating config.yaml...[/yellow]")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}
    
    old_path = config.get('pipeline_json', 'not set')
    new_path = str(pipeline_json)
    
    config['pipeline_json'] = new_path
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    console.print(f"[green]✓[/green] pipeline_json path updated")
    console.print(f"  Old: {old_path}")
    console.print(f"  New: {new_path}")
    
    console.print("\n[bold green]✓ Pipeline path fixed![/bold green]\n")
    
    return 0

if __name__ == "__main__":
    exit(main())
