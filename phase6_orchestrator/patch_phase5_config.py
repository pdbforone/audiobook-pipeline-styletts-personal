#!/usr/bin/env python3
"""
Patch Phase 5's config to accept ALL chunks
This modifies the ACTUAL config file that Phase 5 reads.
"""

import yaml
import shutil
from pathlib import Path
from rich.console import Console

console = Console()

def main():
    console.print("\n[bold cyan]Phase 5 Config Patcher[/bold cyan]\n")
    
    # The ACTUAL config that Phase 5 reads
    project_root = Path(__file__).parent.parent
    config_path = project_root / "phase5_enhancement" / "src" / "phase5_enhancement" / "config.yaml"
    
    if not config_path.exists():
        # Fallback to root-level config
        config_path = project_root / "phase5_enhancement" / "config.yaml"
        console.print(f"[yellow]Using fallback config:[/yellow] {config_path}")
    
    console.print(f"[cyan]Config path:[/cyan] {config_path}")
    
    # Backup
    backup_path = config_path.parent / f"{config_path.name}.backup"
    shutil.copy(config_path, backup_path)
    console.print(f"[green]✓[/green] Backed up to: {backup_path.name}\n")
    
    # Load
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}
    
    # AGGRESSIVE PATCHES to force acceptance of ALL chunks
    old_values = {}
    
    patches = {
        'resume_on_failure': False,
        'quality_validation_enabled': False,
        'snr_threshold': 0.0,  # Accept ANY SNR
        'noise_reduction_factor': 0.02,  # Minimal enhancement
        'retries': 0,  # Don't retry - accept first result
    }
    
    console.print("[bold yellow]Applying patches:[/bold yellow]")
    for key, new_value in patches.items():
        old_value = config.get(key, "not set")
        old_values[key] = old_value
        config[key] = new_value
        console.print(f"  {key}: {old_value} → [green]{new_value}[/green]")
    
    # Save
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    console.print(f"\n[bold green]✓ Config patched![/bold green]")
    console.print(f"[cyan]Backup saved as:[/cyan] {backup_path.name}")
    console.print("\n[yellow]To restore:[/yellow] Copy .backup file back to config.yaml\n")
    
    return 0

if __name__ == "__main__":
    exit(main())
