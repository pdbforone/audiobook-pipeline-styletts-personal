#!/usr/bin/env python3
"""
Patch Phase 5's models.py to remove Pydantic validators
This allows us to set snr_threshold=0.0 and noise_reduction_factor=0.02
"""

import shutil
from pathlib import Path
from rich.console import Console

console = Console()

def main():
    console.print("\n[bold cyan]Phase 5 Models Patcher[/bold cyan]\n")
    
    project_root = Path(__file__).parent.parent
    models_py = project_root / "phase5_enhancement" / "src" / "phase5_enhancement" / "models.py"
    
    if not models_py.exists():
        console.print(f"[red]❌ models.py not found: {models_py}[/red]")
        return 1
    
    console.print(f"[cyan]Target file:[/cyan] {models_py}")
    
    # Backup
    backup_path = models_py.parent / "models.py.backup"
    shutil.copy(models_py, backup_path)
    console.print(f"[green]✓[/green] Backed up to: {backup_path.name}\n")
    
    # Read
    with open(models_py, 'r', encoding='utf-8') as f:
        content = f.read()
    
    patches_applied = 0
    
    # PATCH 1: Remove snr_threshold minimum validator
    # Look for: snr_threshold: float = Field(default=15.0, ge=5.0)
    # Replace with: snr_threshold: float = Field(default=15.0, ge=0.0)
    
    if "ge=5" in content and "snr_threshold" in content:
        content = content.replace(
            "snr_threshold: float = Field(default=15.0, ge=5.0",
            "snr_threshold: float = Field(default=15.0, ge=0.0"
        )
        console.print("[green]✓[/green] Patch 1: Allow snr_threshold >= 0.0 (was >= 5.0)")
        patches_applied += 1
    
    # PATCH 2: Remove noise_reduction_factor minimum validator
    # Look for: noise_reduction_factor: float = Field(default=0.3, ge=0.1, le=1.0)
    # Replace with: noise_reduction_factor: float = Field(default=0.3, ge=0.0, le=1.0)
    
    if "ge=0.1" in content and "noise_reduction_factor" in content:
        content = content.replace(
            "noise_reduction_factor: float = Field(default=0.3, ge=0.1, le=1.0",
            "noise_reduction_factor: float = Field(default=0.3, ge=0.0, le=1.0"
        )
        console.print("[green]✓[/green] Patch 2: Allow noise_reduction_factor >= 0.0 (was >= 0.1)")
        patches_applied += 1
    
    if patches_applied == 0:
        console.print("[yellow]⚠[/yellow]  No validators found to patch (may already be patched)")
    
    # Write
    with open(models_py, 'w', encoding='utf-8') as f:
        f.write(content)
    
    console.print(f"\n[bold green]✓ Models patched successfully![/bold green]")
    console.print(f"[cyan]Backup saved as:[/cyan] {backup_path.name}\n")
    
    return 0

if __name__ == "__main__":
    exit(main())
