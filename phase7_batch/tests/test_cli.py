"""
Tests for Phase 7 Batch Processing CLI
"""

import pytest
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import yaml

from phase7_batch.models import BatchConfig, BatchMetadata, BatchSummary
from phase7_batch.cli import (
    load_config,
    get_project_root,
    find_orchestrator,
    load_existing_metadata,
    update_pipeline_json,
)


class TestBatchConfig:
    """Test BatchConfig model"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = BatchConfig()
        assert config.max_workers >= 1
        assert config.cpu_threshold > 0
        assert config.phases_to_run == [1, 2, 3, 4, 5]
        assert config.log_level == "INFO"
        assert config.resume_enabled is True
    
    def test_config_validation(self):
        """Test configuration field validation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = BatchConfig(
                input_dir=f"{temp_dir}/test_input",
                pipeline_json=f"{temp_dir}/test_pipeline.json"
            )
            
            # Should create directories
            assert Path(config.input_dir).exists()
            assert Path(config.pipeline_json).exists()
    
    def test_invalid_phases(self):
        """Test validation rejects invalid phase numbers"""
        with pytest.raises(Exception):  # Pydantic validation error
            BatchConfig(phases_to_run=[0, 1, 6])


class TestBatchMetadata:
    """Test BatchMetadata model"""
    
    def test_metadata_lifecycle(self):
        """Test metadata state transitions"""
        metadata = BatchMetadata(file_id="test.pdf")
        
        # Initial state
        assert metadata.status == "pending"
        assert metadata.phases_completed == []
        assert metadata.start_time is None
        
        # Mark as started
        metadata.mark_started()
        assert metadata.status == "running"
        assert metadata.start_time is not None
        
        # Add phase completion
        metadata.phases_completed.append(1)
        metadata.add_phase_metric(1, 10.5)
        assert len(metadata.phase_metrics) == 1
        assert metadata.phase_metrics[0].phase == 1
        
        # Mark as completed
        metadata.mark_completed()
        assert metadata.status == "success"
        assert metadata.duration is not None
    
    def test_metadata_with_error(self):
        """Test metadata with error conditions"""
        metadata = BatchMetadata(file_id="test.pdf")
        metadata.mark_started()
        metadata.error_message = "Test error"
        metadata.mark_completed()
        
        # Should be failed since no phases completed
        assert metadata.status == "failed"
        
        # With some phases completed, should be partial
        metadata.phases_completed.append(1)
        metadata.phases_completed.append(2)
        metadata.mark_completed()
        assert metadata.status == "partial"
    
    def test_phase_metrics(self):
        """Test adding phase metrics"""
        metadata = BatchMetadata(file_id="test.pdf")
        
        metadata.add_phase_metric(1, 15.5)
        metadata.add_phase_metric(2, 20.3, "Some error")
        
        assert len(metadata.phase_metrics) == 2
        assert metadata.phase_metrics[0].duration == 15.5
        assert metadata.phase_metrics[0].error is None
        assert metadata.phase_metrics[1].error == "Some error"


class TestBatchSummary:
    """Test BatchSummary model"""
    
    def test_summary_from_metadata(self):
        """Test creating summary from metadata list"""
        metadata_list = [
            BatchMetadata(file_id="file1.pdf", status="success"),
            BatchMetadata(file_id="file2.pdf", status="partial", error_message="Phase 3 failed"),
            BatchMetadata(file_id="file3.pdf", status="failed", error_message="Phase 1 failed")
        ]
        
        summary = BatchSummary.from_metadata_list(metadata_list, 120.5, 65.0)
        
        assert summary.total_files == 3
        assert summary.successful_files == 1
        assert summary.partial_files == 1
        assert summary.failed_files == 1
        assert summary.status == "partial"  # Mixed results
        assert summary.total_duration == 120.5
        assert summary.avg_cpu_usage == 65.0
        assert len(summary.errors) == 2
    
    def test_summary_all_success(self):
        """Test summary with all successful files"""
        metadata_list = [
            BatchMetadata(file_id=f"file{i}.pdf", status="success")
            for i in range(5)
        ]
        
        summary = BatchSummary.from_metadata_list(metadata_list, 300.0)
        
        assert summary.status == "success"
        assert summary.successful_files == 5
        assert summary.failed_files == 0
        assert len(summary.errors) == 0
    
    def test_summary_all_failed(self):
        """Test summary with all failed files"""
        metadata_list = [
            BatchMetadata(file_id=f"file{i}.pdf", status="failed", error_message="Error")
            for i in range(3)
        ]
        
        summary = BatchSummary.from_metadata_list(metadata_list, 60.0)
        
        assert summary.status == "failed"
        assert summary.successful_files == 0
        assert summary.failed_files == 3


class TestConfigLoading:
    """Test configuration loading"""
    
    def test_load_valid_config(self):
        """Test loading valid YAML config"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
max_workers: 8
cpu_threshold: 90
phases_to_run: [1, 2, 3]
log_level: DEBUG
input_dir: /tmp/input
pipeline_json: /tmp/pipeline.json
            """)
            f.flush()
            
            config = load_config(f.name)
            assert config.max_workers == 8
            assert config.cpu_threshold == 90
            assert config.phases_to_run == [1, 2, 3]
            assert config.log_level == "DEBUG"
    
    def test_load_missing_config(self):
        """Test loading missing config returns defaults"""
        config = load_config("nonexistent.yaml")
        assert isinstance(config, BatchConfig)
        assert config.max_workers >= 1
    
    def test_load_invalid_yaml(self):
        """Test loading invalid YAML returns defaults"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()
            
            config = load_config(f.name)
            assert isinstance(config, BatchConfig)


class TestOrchestratorFinding:
    """Test finding Phase 6 orchestrator"""
    
    def test_find_orchestrator_exists(self):
        """Test finding orchestrator when it exists"""
        with patch('pathlib.Path.exists', return_value=True):
            result = find_orchestrator()
            assert result is not None
            assert result.name == "orchestrator.py"
    
    def test_find_orchestrator_missing(self):
        """Test finding orchestrator when missing"""
        with patch('pathlib.Path.exists', return_value=False):
            result = find_orchestrator()
            assert result is None


class TestPipelineJsonHandling:
    """Test pipeline.json operations"""
    
    def test_update_pipeline_json(self):
        """Test updating pipeline.json with batch data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline_path = Path(temp_dir) / "pipeline.json"
            
            config = BatchConfig(
                pipeline_json=str(pipeline_path),
                input_dir=temp_dir
            )
            
            metadata_list = [
                BatchMetadata(file_id="test1.pdf", status="success"),
                BatchMetadata(file_id="test2.pdf", status="failed", error_message="Test error")
            ]
            
            summary = BatchSummary.from_metadata_list(metadata_list, 60.0)
            
            update_pipeline_json(config, summary, metadata_list)
            
            # Verify file was created
            assert pipeline_path.exists()
            
            # Verify contents
            with open(pipeline_path) as f:
                data = json.load(f)
            
            assert "batch" in data
            assert data["batch"]["status"] == "partial"
            assert len(data["batch"]["files"]) == 2
            assert data["batch"]["summary"]["total_files"] == 2
    
    def test_load_existing_metadata(self):
        """Test loading existing metadata for resume"""
        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline_path = Path(temp_dir) / "pipeline.json"
            
            # Create existing pipeline with completed phases
            existing_data = {
                "phase1": {"status": "success", "files": {"test.pdf": {"status": "success"}}},
                "phase2": {"status": "success", "files": {"test.pdf": {"status": "success"}}},
                "phase3": {"status": "success", "files": {"test.pdf": {"status": "success"}}},
                "phase4": {"status": "success", "files": {"test.pdf": {"status": "success"}}},
                "phase5": {"status": "success", "files": {"test.pdf": {"status": "success"}}}
            }
            
            with open(pipeline_path, 'w') as f:
                json.dump(existing_data, f)
            
            config = BatchConfig(
                pipeline_json=str(pipeline_path),
                phases_to_run=[1, 2, 3, 4, 5],
                input_dir=temp_dir
            )
            
            metadata = load_existing_metadata(config, "test.pdf")
            
            assert metadata is not None
            assert metadata.status == "success"
            assert metadata.phases_completed == [1, 2, 3, 4, 5]
    
    def test_load_existing_metadata_incomplete(self):
        """Test loading metadata when phases incomplete"""
        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline_path = Path(temp_dir) / "pipeline.json"
            
            # Only phases 1-3 completed
            existing_data = {
                "phase1": {"status": "success", "files": {"test.pdf": {"status": "success"}}},
                "phase2": {"status": "success", "files": {"test.pdf": {"status": "success"}}},
                "phase3": {"status": "success", "files": {"test.pdf": {"status": "success"}}},
                "phase4": {"status": "pending", "files": {}},
                "phase5": {"status": "pending", "files": {}}
            }
            
            with open(pipeline_path, 'w') as f:
                json.dump(existing_data, f)
            
            config = BatchConfig(
                pipeline_json=str(pipeline_path),
                phases_to_run=[1, 2, 3, 4, 5],
                input_dir=temp_dir
            )
            
            # Should return None since not all phases complete
            metadata = load_existing_metadata(config, "test.pdf")
            assert metadata is None


class TestIntegration:
    """Integration tests"""
    
    @patch('trio.run_process')
    async def test_process_single_file_success(self, mock_run_process):
        """Test successful file processing"""
        import trio
        
        # Mock successful subprocess
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.stdout = b"Success"
        mock_process.stderr = b""
        mock_run_process.return_value = mock_process
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup
            test_file = Path(temp_dir) / "test.pdf"
            test_file.touch()
            
            config = BatchConfig(
                input_dir=temp_dir,
                pipeline_json=f"{temp_dir}/pipeline.json",
                phases_to_run=[1, 2, 3],
                resume_enabled=False
            )
            
            semaphore = trio.Semaphore(1)
            
            # Import here to avoid issues
            from phase7_batch.cli import process_single_file
            
            # Process
            metadata = await process_single_file(test_file, config, semaphore)
            
            # Verify
            assert metadata.file_id == "test"
            assert metadata.status == "success"
            assert metadata.phases_completed == [1, 2, 3]
            assert metadata.error_message is None
    
    @patch('trio.run_process')
    async def test_process_single_file_failure(self, mock_run_process):
        """Test failed file processing"""
        import trio
        
        # Mock failed subprocess
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.stdout = b""
        mock_process.stderr = b"Phase 1 failed"
        mock_run_process.return_value = mock_process
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.pdf"
            test_file.touch()
            
            config = BatchConfig(
                input_dir=temp_dir,
                pipeline_json=f"{temp_dir}/pipeline.json",
                phases_to_run=[1, 2, 3],
                resume_enabled=False
            )
            
            semaphore = trio.Semaphore(1)
            
            from phase7_batch.cli import process_single_file
            
            metadata = await process_single_file(test_file, config, semaphore)
            
            assert metadata.status == "failed"
            assert metadata.error_message is not None
            assert len(metadata.phases_completed) == 0


# Fixtures
@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield BatchConfig(
            input_dir=f"{temp_dir}/inputs",
            pipeline_json=f"{temp_dir}/pipeline.json",
            log_file=f"{temp_dir}/batch.log",
            max_workers=2,
            phases_to_run=[1, 2, 3]
        )


@pytest.fixture
def sample_metadata_list():
    """Sample metadata list for testing"""
    return [
        BatchMetadata(
            file_id="doc1.pdf",
            status="success",
            phases_completed=[1, 2, 3],
            duration=45.2
        ),
        BatchMetadata(
            file_id="doc2.pdf", 
            status="partial",
            phases_completed=[1, 2],
            error_message="Phase 3 timeout",
            duration=78.1
        ),
        BatchMetadata(
            file_id="doc3.pdf",
            status="failed",
            error_message="Invalid PDF format",
            duration=5.3
        )
    ]


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    def test_mixed_results_batch(self, sample_metadata_list):
        """Test batch with mixed results"""
        summary = BatchSummary.from_metadata_list(
            sample_metadata_list, 
            150.0, 
            72.5
        )
        
        assert summary.total_files == 3
        assert summary.successful_files == 1
        assert summary.partial_files == 1
        assert summary.failed_files == 1
        assert summary.status == "partial"
        assert len(summary.errors) == 2
    
    def test_resume_skips_completed(self):
        """Test resume functionality skips completed files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline_path = Path(temp_dir) / "pipeline.json"
            
            # Create completed pipeline
            pipeline_data = {
                "phase1": {"status": "success", "files": {"completed.pdf": {"status": "success"}}},
                "phase2": {"status": "success", "files": {"completed.pdf": {"status": "success"}}},
                "phase3": {"status": "success", "files": {"completed.pdf": {"status": "success"}}},
            }
            
            with open(pipeline_path, 'w') as f:
                json.dump(pipeline_data, f)
            
            config = BatchConfig(
                pipeline_json=str(pipeline_path),
                phases_to_run=[1, 2, 3],
                resume_enabled=True,
                input_dir=temp_dir
            )
            
            metadata = load_existing_metadata(config, "completed.pdf")
            
            assert metadata is not None
            assert metadata.status == "success"
    
    def test_large_batch_summary(self):
        """Test summary with large number of files"""
        # Simulate 100 files
        metadata_list = []
        for i in range(100):
            status = "success" if i < 80 else "partial" if i < 95 else "failed"
            metadata_list.append(
                BatchMetadata(
                    file_id=f"file{i}.pdf",
                    status=status,
                    error_message=None if status == "success" else f"Error in file {i}"
                )
            )
        
        summary = BatchSummary.from_metadata_list(metadata_list, 3600.0)
        
        assert summary.total_files == 100
        assert summary.successful_files == 80
        assert summary.partial_files == 15
        assert summary.failed_files == 5
        assert summary.status == "partial"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=phase7_batch", "--cov-report=term-missing"])
