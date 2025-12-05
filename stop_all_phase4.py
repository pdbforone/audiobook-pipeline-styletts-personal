#!/usr/bin/env python3
"""
Force stop ALL Phase 4 processes.
This is more aggressive than the UI stop button.
"""

import psutil
import time
import sys

def main():
    print("=" * 70)
    print("FORCE STOPPING ALL PHASE 4 PROCESSES")
    print("=" * 70)
    print()

    # First pass: find and terminate all processes
    phase4_pids = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])

            # Match any Phase 4 related process
            keywords = ['phase4', 'engine_runner', 'main_multi_engine', 'xtts']
            if any(keyword in cmdline.lower() for keyword in keywords):
                # Skip this script itself
                if 'stop_all_phase4' in cmdline:
                    continue

                phase4_pids.append(proc.info['pid'])

                # Determine process type
                if 'main_multi_engine' in cmdline:
                    proc_type = 'main_multi_engine'
                elif 'engine_runner' in cmdline:
                    proc_type = 'engine_runner'
                elif 'xtts' in cmdline.lower():
                    proc_type = 'xtts_worker'
                else:
                    proc_type = 'phase4'

                print(f"Terminating PID {proc.info['pid']}: {proc_type}")
                try:
                    proc.terminate()
                except Exception as e:
                    print(f"  Warning: {e}")

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if not phase4_pids:
        print("No Phase 4 processes found.")
        return

    print()
    print(f"Sent terminate signal to {len(phase4_pids)} processes.")
    print("Waiting 3 seconds for graceful shutdown...")
    time.sleep(3)

    # Second pass: kill any that didn't terminate
    still_running = []

    for pid in phase4_pids:
        try:
            proc = psutil.Process(pid)
            if proc.is_running():
                print(f"Force killing PID {pid} (didn't terminate gracefully)")
                proc.kill()
                still_running.append(pid)
        except psutil.NoSuchProcess:
            # Already gone, good
            pass
        except Exception as e:
            print(f"  Warning: {e}")

    if still_running:
        print()
        print(f"Force killed {len(still_running)} stubborn processes.")
        time.sleep(1)

    # Third pass: verify all are gone
    print()
    print("Verifying cleanup...")
    remaining = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            keywords = ['phase4', 'engine_runner', 'main_multi_engine', 'xtts']

            if any(keyword in cmdline.lower() for keyword in keywords):
                if 'stop_all_phase4' not in cmdline:
                    remaining.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    print()
    print("=" * 70)
    print("CLEANUP COMPLETE")
    print("=" * 70)

    if remaining:
        print(f"WARNING: {len(remaining)} processes still running: {remaining}")
        print("You may need to manually kill them from Task Manager.")
        sys.exit(1)
    else:
        print("SUCCESS: All Phase 4 processes stopped.")
        print()
        print("You can now:")
        print("  1. Close and restart the UI (Ctrl+C in the UI terminal)")
        print("  2. Upload the book again")
        print("  3. Select 'Resume (skip completed phases)'")
        print("  4. Click 'Generate Audio'")
        print()
        print("This time it will:")
        print("  - Skip Phases 1-3 (already complete)")
        print("  - Skip 269 existing chunks in Phase 4")
        print("  - Generate only the 27 missing chunks")
        print("  - Take ~4 hours instead of ~48 hours")
        sys.exit(0)

if __name__ == "__main__":
    main()
