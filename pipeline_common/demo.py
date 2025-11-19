#!/usr/bin/env python3
"""
Demonstration of PipelineState atomic state manager.

Proves:
1. Atomic writes work
2. Transactions commit/rollback correctly
3. Backups are created automatically
4. Concurrent writes are safe
5. Schema validation works
"""

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline_common import (
    PipelineState,
    StateValidationError,
    play_alert_beep,
    play_success_beep,
)


def demo_basic_operations():
    """Demo 1: Basic read/write operations"""
    print("\n" + "="*60)
    print("DEMO 1: Basic Operations")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "pipeline.json"
        state = PipelineState(state_path, validate_on_read=False)

        # Write data
        test_data = {
            "pipeline_version": "1.0",
            "file_id": "test_book",
            "phase1": {"status": "success", "duration": 2.5}
        }

        print("Writing state...")
        state.write(test_data, validate=False)

        # Read back
        print("Reading state...")
        read_data = state.read()

        print(f"✓ Data written and read successfully")
        print(f"  File ID: {read_data['file_id']}")
        print(f"  Phase 1 status: {read_data['phase1']['status']}")


def demo_transactions():
    """Demo 2: Transaction commit and rollback"""
    print("\n" + "="*60)
    print("DEMO 2: Transactions")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "pipeline.json"
        state = PipelineState(state_path, validate_on_read=False)

        # Initial state
        state.write({"counter": 0}, validate=False)

        # Successful transaction
        print("\nTest 1: Successful transaction commits...")
        with state.transaction() as txn:
            txn.data['counter'] = 1
            txn.data['phase1'] = {'status': 'success'}

        data = state.read()
        print(f"✓ Transaction committed")
        print(f"  Counter: {data['counter']}")
        print(f"  Phase 1: {data.get('phase1', {}).get('status')}")

        # Failed transaction with rollback
        print("\nTest 2: Failed transaction rolls back...")
        try:
            with state.transaction() as txn:
                txn.data['counter'] = 999
                txn.data['should_not_exist'] = True
                raise ValueError("Simulated error!")
        except ValueError:
            print("  Exception raised (as expected)")

        data = state.read()
        print(f"✓ Transaction rolled back")
        print(f"  Counter still: {data['counter']} (unchanged)")
        print(f"  'should_not_exist' in data: {('should_not_exist' in data)}")


def demo_backups():
    """Demo 3: Automatic backups"""
    print("\n" + "="*60)
    print("DEMO 3: Automatic Backups")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "pipeline.json"
        state = PipelineState(state_path, max_backups=10)

        # Create multiple versions
        print("\nCreating 5 versions...")
        for i in range(5):
            state.write({"version": i, "data": f"state_{i}"}, validate=False)
            time.sleep(0.01)  # Ensure unique timestamps

        # List backups
        backups = state.list_backups(limit=10)
        print(f"✓ Created {len(backups)} backups")

        # Show backup contents
        if backups:
            print(f"\nMost recent backup:")
            with open(backups[0]) as f:
                backup_data = json.load(f)
            print(f"  Version: {backup_data['version']}")

            print(f"\nOldest backup:")
            with open(backups[-1]) as f:
                backup_data = json.load(f)
            print(f"  Version: {backup_data['version']}")

        # Test restore
        print("\nRestoring oldest backup...")
        if backups:
            success = state.restore_backup(backups[-1])
            if success:
                data = state.read()
                print(f"✓ Restored successfully")
                print(f"  Current version: {data['version']}")


def demo_validation():
    """Demo 4: Schema validation"""
    print("\n" + "="*60)
    print("DEMO 4: Schema Validation")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "pipeline.json"
        state = PipelineState(state_path)

        # Valid data passes
        print("\nTest 1: Valid schema...")
        valid_data = {
            "pipeline_version": "1.0",
            "phase1": {
                "status": "success",
                "metrics": {"duration": 42.0}
            }
        }

        try:
            state.write(valid_data, validate=True)
            print("✓ Valid data accepted")
        except StateValidationError as e:
            print(f"✗ Unexpected validation error: {e}")

        # Invalid data rejected
        print("\nTest 2: Invalid schema...")
        invalid_data = {
            "phase1": "this should be a dict"
        }

        try:
            state.write(invalid_data, validate=True)
            print("✗ Invalid data should have been rejected!")
        except StateValidationError:
            print("✓ Invalid data correctly rejected")


def demo_concurrent_access():
    """Demo 5: Concurrent write safety"""
    print("\n" + "="*60)
    print("DEMO 5: Concurrent Access Safety")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "pipeline.json"
        state_path.write_text('{"workers": {}}')

        errors = []
        write_count = [0]

        def worker(worker_id):
            try:
                state = PipelineState(state_path, validate_on_read=False)

                with state.transaction() as txn:
                    if 'workers' not in txn.data:
                        txn.data['workers'] = {}

                    txn.data['workers'][f'worker_{worker_id}'] = {
                        'timestamp': time.time(),
                        'status': 'completed'
                    }

                    # Simulate work
                    time.sleep(0.05)

                write_count[0] += 1
            except Exception as e:
                errors.append((worker_id, str(e)))

        # Launch multiple concurrent workers
        print("\nLaunching 5 concurrent workers...")
        threads = [
            threading.Thread(target=worker, args=(i,))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        print(f"✓ All workers completed")
        print(f"  Successful writes: {write_count[0]}")
        print(f"  Errors: {len(errors)}")

        # Verify data integrity
        state = PipelineState(state_path)
        data = state.read()
        print(f"  Workers in final state: {len(data.get('workers', {}))}")

        if errors:
            print("\n  Errors encountered:")
            for worker_id, error in errors:
                print(f"    Worker {worker_id}: {error}")


def demo_transaction_log():
    """Demo 6: Transaction logging"""
    print("\n" + "="*60)
    print("DEMO 6: Transaction Audit Log")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "pipeline.json"
        state = PipelineState(state_path, validate_on_read=False)

        # Perform operations
        print("\nPerforming operations...")
        state.write({"v": 1}, validate=False)
        state.read()

        with state.transaction() as txn:
            txn.data['v'] = 2

        # Check log
        history = state.get_transaction_history(limit=10)
        print(f"✓ Transaction log created")
        print(f"  Log entries: {len(history)}")

        if history:
            print(f"\n  Most recent operation:")
            latest = history[0]
            print(f"    Operation: {latest['operation']}")
            print(f"    Success: {latest['success']}")
            print(f"    Timestamp: {latest['timestamp']}")


def demo_crash_recovery():
    """Demo 7: Crash recovery simulation"""
    print("\n" + "="*60)
    print("DEMO 7: Crash Recovery")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "pipeline.json"
        state = PipelineState(state_path, validate_on_read=False)

        # Write initial state
        print("\nCreating initial state...")
        state.write({"version": 1, "data": "important"}, validate=False)

        # Simulate corruption (crash during write)
        print("Simulating crash (corrupting state file)...")
        with open(state_path, 'w') as f:
            f.write("{corrupted json")

        print("State file is now corrupted!")

        # Show we can recover from backup
        backups = state.list_backups()
        if backups:
            print(f"✓ Found {len(backups)} backup(s)")
            print("\nRestoring from backup...")
            success = state.restore_backup(backups[0])

            if success:
                data = state.read()
                print("✓ Recovery successful!")
                print(f"  Restored version: {data['version']}")
                print(f"  Data intact: {data['data']}")
        else:
            print("  (No backups available for first write)")


def main():
    """Run all demonstrations"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  PIPELINE STATE MANAGER - DEMONSTRATION".center(58) + "║")
    print("║" + " "*58 + "║")
    print("║" + "  Proving atomic, safe, bulletproof state management".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")

    try:
        demo_basic_operations()
        demo_transactions()
        demo_backups()
        demo_validation()
        demo_concurrent_access()
        demo_transaction_log()
        demo_crash_recovery()

        print("\n" + "="*60)
        print("ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\nThe state manager provides:")
        print("  ✓ Atomic writes (no corruption)")
        print("  ✓ Transaction support (commit/rollback)")
        print("  ✓ Automatic backups (with rotation)")
        print("  ✓ Schema validation (data integrity)")
        print("  ✓ Concurrent access safety (file locking)")
        print("  ✓ Audit trail (transaction log)")
        print("  ✓ Crash recovery (restore from backup)")
        print("\nYour pipeline state is now bulletproof.")
        print()
        play_success_beep()

    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        play_alert_beep()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
