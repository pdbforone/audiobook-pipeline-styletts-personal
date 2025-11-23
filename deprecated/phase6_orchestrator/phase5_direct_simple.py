#!/usr/bin/env python3
"""
Phase 5 Direct Mode - Simple Version
This script creates a modified config and runs Phase 5 as a subprocess.
No complex imports needed!
"""

import sys
import json
import yaml
import shutil
import subprocess
import time
from pathlib import Path
from rich.console import Console

console = Console()


def main():
    """Run Phase 5 with modified config to process ALL chunks."""

    console.print("\n[bold cyan]" + "=" * 70 + "[/bold cyan]")
    console.print("[bold cyan]Phase 5 Direct Mode - Simplified[/bold cyan]")
    console.print("[bold cyan]" + "=" * 70 + "[/bold cyan]\n")

    # Paths
    project_root = Path(__file__).parent.parent
    phase4_audio_dir = project_root / "phase4_tts" / "audio_chunks"
    phase5_dir = project_root / "phase5_enhancement"
    config_path = phase5_dir / "config.yaml"
    pipeline_json = project_root / "pipeline.json"

    # Verify Phase 4 audio exists
    if not phase4_audio_dir.exists():
        console.print(
            f"[red]❌ Phase 4 audio directory not found: {phase4_audio_dir}[/red]"
        )
        return 1

    audio_files = list(phase4_audio_dir.glob("*.wav"))
    console.print(
        f"[green]✓[/green] Found {len(audio_files)} audio files in Phase 4\n"
    )

    # Load and modify config
    console.print("[yellow]📝 Modifying config.yaml...[/yellow]")

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        console.print(f"[red]❌ Failed to load config: {e}[/red]")
        return 1

    # CRITICAL SETTINGS to process ALL chunks:
    config["resume_on_failure"] = False  # Don't skip any chunks
    config["quality_validation_enabled"] = False  # Don't reject any chunks
    config["pipeline_json"] = str(pipeline_json)
    config["input_dir"] = str(phase4_audio_dir)

    # Relax quality thresholds (in case quality validation gets re-enabled)
    config["snr_threshold"] = 5.0  # Very low threshold
    config["noise_reduction_factor"] = 0.05  # Gentle noise reduction

    # Save modified config
    config_backup = phase5_dir / "config.yaml.backup"
    shutil.copy(config_path, config_backup)

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    console.print(
        "[green]✓[/green] Config updated (backup saved to config.yaml.backup)"
    )
    console.print(f"   - resume_on_failure: {config['resume_on_failure']}")
    console.print(
        f"   - quality_validation: {config['quality_validation_enabled']}"
    )
    console.print(f"   - input_dir: {config['input_dir']}\n")

    # Clear Phase 5 data from pipeline.json
    console.print(
        "[yellow]📝 Clearing old Phase 5 data from pipeline.json...[/yellow]"
    )

    try:
        with open(pipeline_json, "r") as f:
            pipeline_data = json.load(f)

        if "phase5" in pipeline_data:
            old_count = len(pipeline_data.get("phase5", {}).get("chunks", []))
            del pipeline_data["phase5"]

            with open(pipeline_json, "w") as f:
                json.dump(pipeline_data, f, indent=4)

            console.print(
                f"[green]✓[/green] Cleared {old_count} old Phase 5 entries\n"
            )
        else:
            console.print("[green]✓[/green] No old Phase 5 data to clear\n")
    except Exception as e:
        console.print(
            f"[yellow]⚠️[/yellow]  Could not clear Phase 5 data: {e}\n"
        )

    # Clear processed directory
    processed_dir = phase5_dir / "processed"
    if processed_dir.exists():
        old_files = list(processed_dir.glob("enhanced_*.wav"))
        if old_files:
            console.print(
                f"[yellow]📝 Clearing {len(old_files)} old files from processed/...[/yellow]"
            )
            shutil.rmtree(processed_dir)
            processed_dir.mkdir(parents=True, exist_ok=True)
            console.print("[green]✓[/green] Cleared processed directory\n")

    # Run Phase 5
    console.print("[bold yellow]▶ Running Phase 5...[/bold yellow]\n")

    main_script = phase5_dir / "src" / "phase5_enhancement" / "main.py"

    if not main_script.exists():
        console.print(f"[red]❌ Phase 5 script not found: {main_script}[/red]")
        return 1

    cmd = ["poetry", "run", "python", str(main_script), "--config=config.yaml"]

    start_time = time.perf_counter()

    try:
        result = subprocess.run(
            cmd,
            cwd=str(phase5_dir),
            capture_output=False,  # Show output in real-time
            text=True,
            timeout=3600,  # 1 hour max
        )

        duration = time.perf_counter() - start_time

        if result.returncode != 0:
            console.print(
                f"\n[red]❌ Phase 5 failed with exit code {result.returncode}[/red]"
            )
            console.print("[yellow]Check the logs above for errors[/yellow]")
            return 1

        # Check results
        processed_files = list(processed_dir.glob("enhanced_*.wav"))
        output_dir = phase5_dir / "output"
        audiobook = output_dir / "audiobook.mp3"

        console.print("\n[bold green]" + "=" * 70 + "[/bold green]")
        console.print("[bold green]Phase 5 Completed![/bold green]")
        console.print("[bold green]" + "=" * 70 + "[/bold green]\n")
        console.print(
            f"[green]Duration:[/green] {duration:.1f}s ({duration/60:.1f} minutes)"
        )
        console.print(
            f"[green]Processed files:[/green] {len(processed_files)}/{len(audio_files)}"
        )

        if audiobook.exists():
            size_mb = audiobook.stat().st_size / (1024 * 1024)
            console.print(
                f"[green]Final audiobook:[/green] {audiobook} ({size_mb:.1f} MB)"
            )
            console.print(
                f"\n[bold cyan]✓ Success! Listen to: {audiobook}[/bold cyan]\n"
            )
        else:
            console.print(
                "[yellow]⚠️  audiobook.mp3 not found (chunks may have failed)[/yellow]\n"
            )

        if len(processed_files) < len(audio_files):
            missing = len(audio_files) - len(processed_files)
            console.print(
                f"[yellow]⚠️  Warning: {missing} chunks may have failed[/yellow]"
            )
            console.print(
                "[yellow]   Run analyze_phase5_failures.py to diagnose[/yellow]\n"
            )

        return 0

    except subprocess.TimeoutExpired:
        console.print("\n[red]❌ Phase 5 timed out after 1 hour[/red]")
        return 1
    except Exception as e:
        console.print(f"\n[red]❌ Error running Phase 5: {e}[/red]")
        return 1
    finally:
        # Restore original config
        if config_backup.exists():
            shutil.copy(config_backup, config_path)
            console.print("[green]✓[/green] Restored original config.yaml")


if __name__ == "__main__":
    sys.exit(main())
