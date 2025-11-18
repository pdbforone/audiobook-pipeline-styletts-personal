#!/usr/bin/env python3
"""
Comprehensive test suite for PipelineState manager.

Tests:
- Atomic write operations
- Concurrent access safety
- Transaction commit/rollback
- Backup creation and rotation
- Schema validation
- Crash recovery simulation
- Lock acquisition/release
"""

import json
import os
import pytest
import shutil
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

from pipeline_common.state_manager import (
    PipelineState,
    StateError,
    StateLockError,
    StateValidationError,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir)


@pytest.fixture
def state_path(temp_dir):
    """Standard pipeline.json path"""
    return temp_dir / "pipeline.json"


@pytest.fixture
def state_manager(state_path):
    """Fresh PipelineState instance"""
    return PipelineState(state_path, validate_on_read=False)


class TestBasicOperations:
    """Test basic read/write operations"""

    def test_read_nonexistent_file(self, state_manager):
        """Reading nonexistent file returns empty dict"""
        data = state_manager.read()
        assert data == {}

    def test_write_and_read(self, state_manager):
        """Write data and read it back"""
        test_data = {
            "pipeline_version": "1.0",
            "file_id": "test_file",
            "phase1": {"status": "success"}
        }

        state_manager.write(test_data, validate=False)
        read_data = state_manager.read()

        assert read_data == test_data

    def test_atomic_write_no_corruption(self, state_manager, state_path):
        """Write creates temp file and atomically renames"""
        test_data = {"phase1": {"status": "success"}}

        state_manager.write(test_data, validate=False)

        # Verify temp file is gone
        temp_path = state_path.with_suffix('.json.tmp')
        assert not temp_path.exists()

        # Verify actual file exists and is valid JSON
        assert state_path.exists()
        with open(state_path) as f:
            data = json.load(f)
        assert data == test_data


class TestTransactions:
    """Test transaction-based updates"""

    def test_transaction_commit(self, state_manager):
        """Successful transaction commits changes"""
        with state_manager.transaction() as txn:
            txn.data['phase1'] = {'status': 'success', 'duration': 42.0}
            txn.data['file_id'] = 'test'

        # Verify changes persisted
        data = state_manager.read()
        assert data['phase1']['status'] == 'success'
        assert data['file_id'] == 'test'

    def test_transaction_rollback_on_exception(self, state_manager):
        """Transaction rolls back on exception"""
        # Write initial state
        state_manager.write({'phase1': {'status': 'pending'}}, validate=False)

        # Attempt transaction that raises exception
        with pytest.raises(ValueError):
            with state_manager.transaction() as txn:
                txn.data['phase1']['status'] = 'success'
                raise ValueError("Simulated error")

        # Verify state unchanged
        data = state_manager.read()
        assert data['phase1']['status'] == 'pending'

    def test_transaction_isolation(self, state_manager):
        """Changes not visible until commit"""
        state_manager.write({'phase1': {'status': 'pending'}}, validate=False)

        with state_manager.transaction() as txn:
            txn.data['phase1']['status'] = 'success'

            # Read outside transaction - should see old value
            outside_data = state_manager.read()
            assert outside_data['phase1']['status'] == 'pending'

        # After commit, see new value
        data = state_manager.read()
        assert data['phase1']['status'] == 'success'

    def test_nested_updates_in_transaction(self, state_manager):
        """Complex nested updates work correctly"""
        with state_manager.transaction() as txn:
            txn.data['phase1'] = {'status': 'success'}
            txn.data['phase2'] = {'status': 'success'}
            txn.data['phase3'] = {
                'status': 'success',
                'chunks': [
                    {'id': 1, 'path': '/path/1'},
                    {'id': 2, 'path': '/path/2'}
                ]
            }

        data = state_manager.read()
        assert len(data['phase3']['chunks']) == 2
        assert data['phase3']['chunks'][0]['id'] == 1


class TestBackups:
    """Test automatic backup system"""

    def test_backup_created_before_write(self, state_manager):
        """Backup is created before overwriting state"""
        # Write initial state
        state_manager.write({'version': 1}, validate=False)

        # Write new state - should create backup
        state_manager.write({'version': 2}, validate=False)

        # Verify backup exists
        backups = state_manager.list_backups()
        assert len(backups) >= 1

        # Verify backup contains old data
        with open(backups[0]) as f:
            backup_data = json.load(f)
        assert backup_data['version'] == 1

    def test_backup_rotation(self, temp_dir):
        """Old backups are rotated when limit exceeded"""
        state_path = temp_dir / "pipeline.json"
        state = PipelineState(state_path, max_backups=5)

        # Create 10 backups
        for i in range(10):
            state.write({'version': i}, validate=False)
            time.sleep(0.01)  # Ensure unique timestamps

        # Should only have 5 backups
        backups = state.list_backups(limit=100)
        assert len(backups) <= 5

    def test_restore_backup(self, state_manager):
        """Can restore from backup"""
        # Write initial state
        state_manager.write({'version': 1, 'data': 'original'}, validate=False)

        # Write new state
        state_manager.write({'version': 2, 'data': 'modified'}, validate=False)

        # Restore backup
        backups = state_manager.list_backups()
        assert len(backups) > 0
        success = state_manager.restore_backup(backups[0])
        assert success

        # Verify restored data
        data = state_manager.read()
        assert data['data'] == 'original'

    def test_no_backup_for_nonexistent_file(self, state_manager):
        """No backup created if file doesn't exist yet"""
        state_manager.write({'first': 'write'}, validate=False)

        # Should not have created backup for first write
        backups = state_manager.list_backups(limit=100)
        assert len(backups) == 0


class TestValidation:
    """Test schema validation"""

    def test_validation_on_write(self, state_manager):
        """Invalid data rejected on write"""
        invalid_data = {
            "phase1": "this should be a dict"  # Wrong type
        }

        with pytest.raises(StateValidationError):
            state_manager.write(invalid_data, validate=True)

    def test_validation_disabled(self, state_manager):
        """Can disable validation if needed"""
        invalid_data = {"phase1": "wrong type"}

        # Should not raise with validate=False
        state_manager.write(invalid_data, validate=False)

        # Verify data was written
        data = state_manager.read()
        assert data['phase1'] == "wrong type"

    def test_valid_schema_accepted(self, state_manager):
        """Correct schema passes validation"""
        valid_data = {
            "pipeline_version": "1.0",
            "file_id": "test",
            "phase1": {
                "status": "success",
                "files": {},
                "metrics": {"duration": 42.0}
            }
        }

        # Should not raise
        state_manager.write(valid_data, validate=True)

    def test_validation_allows_extra_fields(self, state_manager):
        """Extra fields are allowed (forward compatibility)"""
        data_with_extras = {
            "pipeline_version": "1.0",
            "custom_field": "allowed",
            "phase1": {
                "status": "success",
                "custom_metric": 123
            }
        }

        # Should not raise
        state_manager.write(data_with_extras, validate=True)


class TestConcurrency:
    """Test concurrent access safety"""

    def test_file_locking_prevents_concurrent_writes(self, state_manager, state_path):
        """File lock prevents simultaneous writes"""
        errors = []
        write_order = []

        def write_worker(worker_id, delay=0):
            try:
                time.sleep(delay)
                with state_manager._file_lock(timeout=1.0):
                    # Read current state
                    if state_path.exists():
                        with open(state_path) as f:
                            data = json.load(f)
                    else:
                        data = {}

                    # Modify
                    data[f'worker_{worker_id}'] = time.time()
                    write_order.append(worker_id)

                    # Write with delay to increase contention
                    time.sleep(0.1)
                    with open(state_path, 'w') as f:
                        json.dump(data, f)
            except Exception as e:
                errors.append((worker_id, e))

        # Start multiple threads
        threads = [
            threading.Thread(target=write_worker, args=(i,))
            for i in range(3)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All writes should succeed (no lock errors with sufficient timeout)
        assert len(errors) == 0

        # All workers should have written
        assert len(write_order) == 3

        # Data should be consistent
        with open(state_path) as f:
            data = json.load(f)
        assert len(data) == 3

    def test_lock_timeout(self, state_manager):
        """Lock acquisition times out if held too long"""
        acquired = False

        def hold_lock():
            nonlocal acquired
            with state_manager._file_lock(timeout=5.0):
                acquired = True
                time.sleep(2.0)  # Hold lock

        # Start thread that holds lock
        thread = threading.Thread(target=hold_lock)
        thread.start()

        # Wait for lock to be acquired
        while not acquired:
            time.sleep(0.1)

        # Try to acquire with short timeout - should fail
        with pytest.raises(StateLockError):
            with state_manager._file_lock(timeout=0.5):
                pass

        thread.join()


class TestTransactionLog:
    """Test audit logging"""

    def test_transaction_log_created(self, state_manager, temp_dir):
        """Transaction log file is created"""
        state_manager.write({'test': 'data'}, validate=False)

        log_path = temp_dir / ".pipeline" / "transactions.log"
        assert log_path.exists()

    def test_log_records_operations(self, state_manager):
        """Operations are logged"""
        state_manager.write({'v': 1}, validate=False)
        state_manager.read()

        history = state_manager.get_transaction_history()
        assert len(history) > 0

        # Check log structure
        record = history[0]
        assert 'timestamp' in record
        assert 'operation' in record
        assert 'success' in record

    def test_log_records_transaction_commits(self, state_manager):
        """Transaction commits are logged"""
        with state_manager.transaction() as txn:
            txn.data['test'] = 'value'

        history = state_manager.get_transaction_history()
        commit_records = [r for r in history if r['operation'] == 'commit']
        assert len(commit_records) > 0

    def test_log_records_rollbacks(self, state_manager):
        """Transaction rollbacks are logged"""
        try:
            with state_manager.transaction() as txn:
                txn.data['test'] = 'value'
                raise ValueError("Test error")
        except ValueError:
            pass

        history = state_manager.get_transaction_history()
        rollback_records = [r for r in history if r['operation'] == 'rollback']
        assert len(rollback_records) > 0


class TestErrorRecovery:
    """Test crash recovery and error scenarios"""

    def test_corrupted_json_raises_error(self, state_path, state_manager):
        """Corrupted JSON file raises StateError"""
        # Write corrupted JSON
        with open(state_path, 'w') as f:
            f.write("{invalid json")

        with pytest.raises(StateError):
            state_manager.read()

    def test_atomic_write_cleanup_on_error(self, state_manager, state_path):
        """Temp file is cleaned up if write fails"""
        # Patch json.dump to raise error
        with patch('json.dump', side_effect=IOError("Simulated error")):
            with pytest.raises(IOError):
                state_manager.write({'test': 'data'}, validate=False)

        # Verify temp file doesn't exist
        temp_path = state_path.with_suffix('.json.tmp')
        assert not temp_path.exists()

    def test_partial_write_recovery(self, state_manager, state_path):
        """Can recover from partial writes using backup"""
        # Write initial state
        state_manager.write({'version': 1}, validate=False)

        # Simulate crash during write by writing corrupted data directly
        with open(state_path, 'w') as f:
            f.write("{corrupt")

        # Should be able to restore from backup
        backups = state_manager.list_backups()
        if backups:
            success = state_manager.restore_backup(backups[0])
            assert success

            data = state_manager.read()
            assert data['version'] == 1


class TestRealWorldScenarios:
    """Test realistic usage patterns"""

    def test_orchestrator_pattern(self, state_manager):
        """Simulate orchestrator updating multiple phases"""
        # Phase 1
        with state_manager.transaction() as txn:
            txn.data['phase1'] = {
                'status': 'success',
                'files': {'test.pdf': {'hash': 'abc123'}}
            }

        # Phase 2
        with state_manager.transaction() as txn:
            txn.data['phase2'] = {
                'status': 'success',
                'files': {'test.pdf': {'extracted_text_path': '/path/text.txt'}}
            }

        # Phase 3
        with state_manager.transaction() as txn:
            txn.data['phase3'] = {
                'status': 'success',
                'files': {'test.pdf': {'chunk_paths': ['/path/chunk1.txt']}}
            }

        # Verify all phases persisted
        data = state_manager.read()
        assert data['phase1']['status'] == 'success'
        assert data['phase2']['status'] == 'success'
        assert data['phase3']['status'] == 'success'

    def test_error_handling_pattern(self, state_manager):
        """Simulate error handling with rollback"""
        # Initial state
        state_manager.write({'phase1': {'status': 'pending'}}, validate=False)

        # Simulate phase that fails mid-execution
        try:
            with state_manager.transaction() as txn:
                txn.data['phase1']['status'] = 'running'
                txn.data['phase1']['start_time'] = time.time()

                # Simulate error
                raise RuntimeError("TTS engine crashed")
        except RuntimeError:
            pass

        # State should be unchanged
        data = state_manager.read()
        assert data['phase1']['status'] == 'pending'
        assert 'start_time' not in data['phase1']

    def test_concurrent_batch_processing(self, temp_dir):
        """Simulate multiple files being processed concurrently"""
        errors = []

        def process_file(file_id):
            try:
                state_path = temp_dir / "pipeline.json"
                state = PipelineState(state_path, validate_on_read=False)

                with state.transaction() as txn:
                    if 'files' not in txn.data:
                        txn.data['files'] = {}

                    txn.data['files'][file_id] = {
                        'status': 'success',
                        'timestamp': time.time()
                    }

                    # Simulate processing time
                    time.sleep(0.05)
            except Exception as e:
                errors.append((file_id, e))

        # Process multiple files concurrently
        threads = [
            threading.Thread(target=process_file, args=(f'file_{i}',))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No errors
        assert len(errors) == 0

        # All files processed
        state = PipelineState(temp_dir / "pipeline.json")
        data = state.read()
        assert len(data['files']) == 5


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
