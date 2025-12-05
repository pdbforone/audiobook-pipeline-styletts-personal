#!/usr/bin/env python3
"""
Kill old stuck Phase 4 processes.
Only kills processes older than 10 minutes to avoid killing active runs.
"""

import psutil
import time
from datetime import datetime

def main():
    print("=" * 70)
    print("KILLING OLD PHASE 4 PROCESSES")
    print("=" * 70)
    print()

    current_time = time.time()
    killed = []
    kept = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])

            # Check if it's a Phase 4 process
            if any(keyword in cmdline.lower() for keyword in ['phase4', 'engine_runner', 'main_multi_engine']):
                # Skip the check script itself
                if 'kill_old_phase4' in cmdline:
                    continue

                create_time = proc.info['create_time']
                age_mins = (current_time - create_time) / 60
                started_at = datetime.fromtimestamp(create_time).strftime('%H:%M:%S')

                # Determine process type
                if 'main_multi_engine' in cmdline:
                    proc_type = 'main_multi_engine'
                elif 'engine_runner' in cmdline:
                    proc_type = 'engine_runner'
                else:
                    proc_type = 'phase4'

                # Kill if older than 10 minutes
                if age_mins > 10:
                    print(f"KILLING PID {proc.info['pid']}: {proc_type}")
                    print(f"  Started: {started_at} ({age_mins:.1f} min ago)")
                    try:
                        proc.terminate()
                        killed.append(proc.info['pid'])
                        print(f"  Status: Terminated")
                    except Exception as e:
                        print(f"  Status: Failed ({e})")
                    print()
                else:
                    print(f"KEEPING PID {proc.info['pid']}: {proc_type}")
                    print(f"  Started: {started_at} ({age_mins:.1f} min ago)")
                    print(f"  Status: Recent, keeping")
                    kept.append(proc.info['pid'])
                    print()

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Killed {len(killed)} old processes: {killed}")
    print(f"Kept {len(kept)} recent processes: {kept}")
    print()

    if len(kept) > 0:
        print("Recent processes are still running.")
        print("Check back in 1-2 minutes to see if they're making progress.")
    elif len(killed) > 0:
        print("All processes killed.")
        print("Restart Phase 4 from the UI.")
    else:
        print("No Phase 4 processes found.")

if __name__ == "__main__":
    main()
