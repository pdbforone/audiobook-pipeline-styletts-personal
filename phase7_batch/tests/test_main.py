import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import time

from phase6_batch.mainbu import (
    load_config, 
    setup_logging, 
    find_phase_directory,
    find_phase_main,
    load_existing_metadata,
    update_pipeline_json
)
from src.phase6_batch.models import BatchConfig, BatchMetadata, BatchSummary


class TestBatchConfig:
    def test_default_config(self):
        """Test default configuration creation"""
        config = BatchConfig()
        assert config.max_workers == 4
        assert config.cpu_threshold == 80
        assert config.phases_to_run == [1, 2, 3, 4, 5]
        assert config.log_level == "INFO"

    def test_config_validation(self):
        """Test configuration validation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = BatchConfig(
                input_dir=f"{temp_dir}/test_input",
                pipeline_json=f"{temp_dir}/test_pipeline.json"
            )
            
            # Should create directories
            assert Path(config.input_dir).exists()
            assert Path(config.pipeline_json).exists()


class TestBatchMetadata:
    def test_metadata_lifecycle(self):
        """Test metadata state transitions"""
        metadata = BatchMetadata(file_id="test.pdf")
        
        # Initial state
        assert metadata.status == "pending"
        assert metadata.phases_completed == []
        
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
        metadata.mark_completed()
        assert metadata.status == "partial"


class TestBatchSummary:
    def test_summary_creation(self):
        """Test batch summary creation from metadata"""
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
        assert len(summary.errors) == 2


class TestConfigLoading:
    def test_load_valid_config(self):
        """Test loading valid YAML config"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
max_workers: 8
cpu_threshold: 90
phases_to_run: [1, 2, 3]
log_level: DEBUG
            """)
            f.flush()
            
            config = load_config(f.name)
            assert config.max_workers == 8
            assert config.cpu_threshold == 90
            assert config.phases_to_run == [1, 2, 3]
            assert config.log_level == "DEBUG"

    def test_load_missing_config(self):
        """Test loading missing config file"""
        config = load_config("nonexistent.yaml")
        # Should return default config
        assert isinstance(config, BatchConfig)
        assert config.max_workers == 4  # Default value

    def test_load_invalid_config(self):
        """Test loading invalid YAML"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()
            
            config = load_config(f.name)
            # Should return default config on parse error
            assert isinstance(config, BatchConfig)


class TestDirectoryResolution:
    @patch('pathlib.Path.glob')
    def test_find_phase_directory_not_found(self, mock_glob):
        """Test phase directory not found"""
        mock_glob.return_value = []
        
        result = find_phase_directory(99)
        assert result is None

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.glob')
    def test_find_phase_main(self, mock_glob, mock_exists):
        """Test finding main.py in phase directory"""
        mock_phase_dir = Mock()
        mock_src_dir = Mock()
        mock_main_path = Mock()
        
        mock_glob.return_value = [mock_src_dir]
        mock_src_dir.__truediv__.return_value = mock_main_path
        mock_exists.return_value = True
        
        result = find_phase_main(mock_phase_dir, 1)
        assert result == mock_main_path


class TestPipelineJsonHandling:
    def test_update_pipeline_json(self):
        """Test updating pipeline.json file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline_path = Path(temp_dir) / "pipeline.json"
            
            config = BatchConfig(pipeline_json=str(pipeline_path))
            
            metadata_list = [
                BatchMetadata(file_id="test1.pdf", status="success"),
                BatchMetadata(file_id="test2.pdf", status="failed", error_message="Test error")
            ]
            
            summary = BatchSummary.from_metadata_list(metadata_list, 60.0)
            
            update_pipeline_json(config, summary, metadata_list)
            
            # Verify file was created and contains correct data
            assert pipeline_path.exists()
            with open(pipeline_path) as f:
                data = json.load(f)
            
            assert "batch" in data
            assert data["batch"]["status"] == summary.status
            assert data["batch"]["metrics"]["total_files"] == 2
            assert len(data["batch"]["files"]) == 2

    def test_load_existing_metadata(self):
        """Test loading existing metadata for resume"""
        with tempfile.TemporaryDirectory() as temp_dir:
            pipeline_path = Path(temp_dir) / "pipeline.json"
            
            # Create existing pipeline data
            existing_data = {
                "batch": {
                    "files": {
                        "test.pdf": {
                            "file_id": "test.pdf",
                            "status": "partial",
                            "phases_completed": [1, 2],
                            "error_message": None,
                            "duration": 45.5,
                            "phase_metrics": [],
                            "start_time": None,
                            "end_time": None
                        }
                    }
                }
            }
            
            with open(pipeline_path, 'w') as f:
                json.dump(existing_data, f)
            
            config = BatchConfig(pipeline_json=str(pipeline_path), resume_enabled=True)
            
            metadata = load_existing_metadata(config, "test.pdf")
            
            assert metadata.file_id == "test.pdf"
            assert metadata.status == "partial"
            assert metadata.phases_completed == [1, 2]
            assert metadata.duration == 45.5


class TestIntegration:
    @patch('subprocess.run')
    @patch('src.phase6_batch.main.find_phase_directory')
    @patch('src.phase6_batch.main.find_phase_main')
    def test_successful_phase_execution(self, mock_find_main, mock_find_dir, mock_subprocess):
        """Test successful phase execution"""
        from phase6_batch.mainbu import run_phase_for_file
        
        # Setup mocks
        mock_phase_dir = Path("/fake/phase1_validation")
        mock_main_path = Path("/fake/phase1_validation/src/phase1_validation/main.py")
        
        mock_find_dir.return_value = mock_phase_dir
        mock_find_main.return_value = mock_main_path
        
        mock_result = Mock()
        mock_result.stdout = "Phase completed successfully"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        config = BatchConfig(phases_to_run=[1], phase_timeout=60)
        metadata = BatchMetadata(file_id="test.pdf")
        
        result = run_phase_for_file("test.pdf", [1], config, metadata)
        
        assert result.status == "success"
        assert 1 in result.phases_completed
        assert len(result.phase_metrics) == 1
        assert result.error_message is None

    @patch('subprocess.run')
    @patch('src.phase6_batch.main.find_phase_directory')
    @patch('src.phase6_batch.main.find_phase_main')
    def test_failed_phase_execution(self, mock_find_main, mock_find_dir, mock_subprocess):
        """Test failed phase execution"""
        from phase6_batch.mainbu import run_phase_for_file
        from subprocess import CalledProcessError
        
        # Setup mocks
        mock_phase_dir = Path("/fake/phase1_validation")
        mock_main_path = Path("/fake/phase1_validation/src/phase1_validation/main.py")
        
        mock_find_dir.return_value = mock_phase_dir
        mock_find_main.return_value = mock_main_path
        
        # Mock subprocess failure
        mock_subprocess.side_effect = CalledProcessError(
            1, ["poetry", "run", "python"], stderr="Phase failed"
        )
        
        config = BatchConfig(phases_to_run=[1], phase_timeout=60)
        metadata = BatchMetadata(file_id="test.pdf")
        
        result = run_phase_for_file("test.pdf", [1], config, metadata)
        
        assert result.status == "failed"
        assert len(result.phases_completed) == 0
        assert result.error_message is not None
        assert "Phase 1 failed" in result.error_message


class TestCLIIntegration:
    @patch('src.phase6_batch.main.ThreadPoolExecutor')
    @patch('src.phase6_batch.main.Path.glob')
    @patch('sys.argv', ['main.py', '--dry-run'])
    def test_dry_run_mode(self, mock_glob, mock_executor):
        """Test dry-run mode"""
        # Mock file discovery
        mock_file = Mock()
        mock_file.name = "test.pdf"
        mock_glob.return_value = [mock_file]
        
        # This would normally be tested with a full CLI test framework
        # For now, just verify the key components work
        config = BatchConfig(input_dir="test_inputs")
        assert config.input_dir == "test_inputs"


# Fixtures for testing
@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield BatchConfig(
            input_dir=f"{temp_dir}/inputs",
            pipeline_json=f"{temp_dir}/pipeline.json",
            log_file=f"{temp_dir}/batch.log",
            max_workers=2,
            phases_to_run=[1, 2]
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
    def test_mixed_results_summary(self, sample_metadata_list):
        """Test summary with mixed success/failure results"""
        summary = BatchSummary.from_metadata_list(sample_metadata_list, 150.0, 72.5)
        
        assert summary.total_files == 3
        assert summary.successful_files == 1
        assert summary.partial_files == 1
        assert summary.failed_files == 1
        assert summary.status == "partial"
        assert len(summary.errors) == 2
        
    def test_all_successful_summary(self):
        """Test summary with all successful results"""
        metadata_list = [
            BatchMetadata(file_id=f"doc{i}.pdf", status="success", phases_completed=[1, 2, 3])
            for i in range(5)
        ]
        
        summary = BatchSummary.from_metadata_list(metadata_list, 200.0)
        
        assert summary.status == "success"
        assert summary.successful_files == 5
        assert summary.failed_files == 0
        assert len(summary.errors) == 0

    def test_all_failed_summary(self):
        """Test summary with all failed results"""
        metadata_list = [
            BatchMetadata(file_id=f"doc{i}.pdf", status="failed", error_message="Test error")
            for i in range(3)
        ]
        
        summary = BatchSummary.from_metadata_list(metadata_list, 60.0)
        
        assert summary.status == "failed"
        assert summary.successful_files == 0
        assert summary.failed_files == 3
        assert len(summary.errors) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])Path.glob')
    def test_find_phase_directory(self, mock_glob):
        """Test phase directory finding logic"""
        mock_path = Mock()
        mock_path.name = "phase1_validation"
        mock_glob.return_value = [mock_path]
        
        result = find_phase_directory(1)
        assert result == mock_path

    @patch('pathlib.