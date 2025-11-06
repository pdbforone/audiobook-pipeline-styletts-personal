#!/usr/bin/env python3
"""
Example: How to integrate PipelineState into existing phases

Shows before/after comparison for common patterns.
"""

import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline_common import PipelineState


# ============================================================================
# PATTERN 1: Simple Phase Update
# ============================================================================

def pattern1_before(pipeline_json):
    """❌ OLD WAY - Unsafe"""
    import json

    # Load
    with open(pipeline_json, 'r') as f:
        pipeline = json.load(f)

    # Modify
    pipeline['phase1'] = {
        'status': 'success',
        'metrics': {'duration': 42.0}
    }

    # Write (NOT ATOMIC!)
    with open(pipeline_json, 'w') as f:
        json.dump(pipeline, f, indent=4)


def pattern1_after(pipeline_json):
    """✅ NEW WAY - Safe"""
    state = PipelineState(pipeline_json)

    with state.transaction() as txn:
        txn.data['phase1'] = {
            'status': 'success',
            'metrics': {'duration': 42.0}
        }


# ============================================================================
# PATTERN 2: Error Handling with Rollback
# ============================================================================

def pattern2_before(pipeline_json):
    """❌ OLD WAY - State corrupted on error"""
    import json

    with open(pipeline_json, 'r') as f:
        pipeline = json.load(f)

    # Modify
    pipeline['phase2']['status'] = 'running'

    # Write partial state
    with open(pipeline_json, 'w') as f:
        json.dump(pipeline, f, indent=4)

    # If this fails, state says "running" but phase actually failed!
    run_extraction()

    # Update to success
    with open(pipeline_json, 'r') as f:
        pipeline = json.load(f)
    pipeline['phase2']['status'] = 'success'
    with open(pipeline_json, 'w') as f:
        json.dump(pipeline, f, indent=4)


def pattern2_after(pipeline_json):
    """✅ NEW WAY - Atomic commit or rollback"""
    state = PipelineState(pipeline_json)

    try:
        with state.transaction() as txn:
            txn.data['phase2']['status'] = 'running'

            # If this fails, transaction rolls back automatically
            run_extraction()

            txn.data['phase2']['status'] = 'success'
    except Exception as e:
        # State unchanged - still shows previous status
        print(f"Extraction failed: {e}")


def run_extraction():
    """Dummy function"""
    pass


# ============================================================================
# PATTERN 3: Reading and Updating Multiple Phases
# ============================================================================

def pattern3_before(pipeline_json):
    """❌ OLD WAY - Multiple read/write cycles"""
    import json

    # Read phase 2 output
    with open(pipeline_json, 'r') as f:
        pipeline = json.load(f)
    text_path = pipeline['phase2']['files']['book.pdf']['extracted_text_path']

    # Process chunks
    chunks = create_chunks(text_path)

    # Update phase 3
    with open(pipeline_json, 'r') as f:
        pipeline = json.load(f)

    pipeline['phase3'] = {
        'status': 'success',
        'chunks': chunks
    }

    with open(pipeline_json, 'w') as f:
        json.dump(pipeline, f, indent=4)


def pattern3_after(pipeline_json):
    """✅ NEW WAY - Single transaction"""
    state = PipelineState(pipeline_json)

    # Read current state
    data = state.read()
    text_path = data['phase2']['files']['book.pdf']['extracted_text_path']

    # Process
    chunks = create_chunks(text_path)

    # Update atomically
    with state.transaction() as txn:
        txn.data['phase3'] = {
            'status': 'success',
            'chunks': chunks
        }


def create_chunks(text_path):
    """Dummy function"""
    return []


# ============================================================================
# PATTERN 4: Orchestrator Loop
# ============================================================================

def pattern4_before(pipeline_json, input_file):
    """❌ OLD WAY - Manual state management"""
    import json

    phases = ['phase1', 'phase2', 'phase3', 'phase4', 'phase5']

    for phase_name in phases:
        print(f"Running {phase_name}...")

        # Read state
        with open(pipeline_json, 'r') as f:
            pipeline = json.load(f)

        # Run phase
        try:
            result = run_phase(phase_name, pipeline, input_file)

            # Update state
            pipeline[phase_name] = result

            with open(pipeline_json, 'w') as f:
                json.dump(pipeline, f, indent=4)

            print(f"✓ {phase_name} complete")
        except Exception as e:
            print(f"✗ {phase_name} failed: {e}")
            break


def pattern4_after(pipeline_json, input_file):
    """✅ NEW WAY - Clean transaction handling"""
    state = PipelineState(pipeline_json)
    phases = ['phase1', 'phase2', 'phase3', 'phase4', 'phase5']

    for phase_name in phases:
        print(f"Running {phase_name}...")

        try:
            # Read current state
            data = state.read()

            # Run phase
            result = run_phase(phase_name, data, input_file)

            # Update atomically
            with state.transaction() as txn:
                txn.data[phase_name] = result

            print(f"✓ {phase_name} complete")
        except Exception as e:
            print(f"✗ {phase_name} failed: {e}")
            # State unchanged - can resume from this point
            break


def run_phase(phase_name, pipeline, input_file):
    """Dummy function"""
    return {'status': 'success'}


# ============================================================================
# PATTERN 5: Crash Recovery
# ============================================================================

def pattern5_recovery(pipeline_json):
    """✅ Recover from corruption"""
    state = PipelineState(pipeline_json)

    # Try to read state
    try:
        data = state.read()
        print(f"State is valid: {data.get('file_id')}")
    except Exception as e:
        print(f"State corrupted: {e}")

        # Restore from backup
        backups = state.list_backups()
        if backups:
            print(f"Found {len(backups)} backups")
            success = state.restore_backup(backups[0])

            if success:
                print("✓ Restored from backup")
                data = state.read()
                print(f"  Restored state: {data.get('file_id')}")
        else:
            print("✗ No backups available")


# ============================================================================
# PATTERN 6: Debugging with Transaction Log
# ============================================================================

def pattern6_debug(pipeline_json):
    """✅ Use transaction log to debug issues"""
    state = PipelineState(pipeline_json)

    # View recent operations
    history = state.get_transaction_history(limit=20)

    print("Recent operations:")
    for record in history[:5]:
        status = "✓" if record['success'] else "✗"
        print(f"{status} {record['operation']:10s} at {record['timestamp']}")

        if not record['success']:
            print(f"  Error: {record['details']}")


# ============================================================================
# MAIN DEMO
# ============================================================================

def main():
    """Show all patterns"""
    import tempfile
    import os

    print("="*60)
    print("PIPELINE STATE INTEGRATION PATTERNS")
    print("="*60)

    # Create temp file
    fd, temp_json = tempfile.mkstemp(suffix='.json')
    os.close(fd)

    try:
        # Initialize state
        state = PipelineState(temp_json)
        state.write({
            'file_id': 'example_book',
            'phase1': {'status': 'pending'},
            'phase2': {
                'files': {
                    'book.pdf': {
                        'extracted_text_path': '/tmp/text.txt'
                    }
                }
            }
        }, validate=False)

        print("\n1. Simple phase update...")
        pattern1_after(temp_json)
        print("   ✓ Phase 1 updated atomically")

        print("\n2. Error handling with rollback...")
        pattern2_after(temp_json)
        print("   ✓ Transaction rolled back on error")

        print("\n3. Multiple phase coordination...")
        pattern3_after(temp_json)
        print("   ✓ Read and write in single transaction")

        print("\n4. Orchestrator loop...")
        pattern4_after(temp_json, 'dummy.pdf')
        print("   ✓ All phases coordinated safely")

        print("\n5. Crash recovery...")
        pattern5_recovery(temp_json)
        print("   ✓ Can restore from backups")

        print("\n6. Debugging with transaction log...")
        pattern6_debug(temp_json)
        print("   ✓ Full audit trail available")

        print("\n" + "="*60)
        print("ALL PATTERNS DEMONSTRATED SUCCESSFULLY")
        print("="*60)

    finally:
        # Cleanup
        if os.path.exists(temp_json):
            os.unlink(temp_json)


if __name__ == '__main__':
    main()
