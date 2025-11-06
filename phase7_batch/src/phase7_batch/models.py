from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import time


class BatchConfig(BaseModel):
    """Configuration for batch processing"""

    pipeline_json: str = Field(
        default="../pipeline.json", description="Path to pipeline.json"
    )
    input_dir: str = Field(
        default="inputs", description="Input directory for batch files"
    )
    log_file: str = Field(default="batch.log", description="Log file path")
    max_workers: int = Field(default=4, ge=1, le=16, description="Max parallel workers")
    cpu_threshold: int = Field(
        default=80, ge=50, le=100, description="CPU utilization threshold %"
    )
    throttle_delay: float = Field(
        default=1.0, ge=0.1, le=5.0, description="Throttle sleep seconds"
    )
    resume_enabled: bool = Field(
        default=True, description="Enable resume from checkpoints"
    )
    phases_to_run: List[int] = Field(
        default=[1, 2, 3, 4, 5], description="Phases to execute"
    )
    batch_size: Optional[int] = Field(
        default=None, ge=1, description="Max files per batch"
    )
    log_level: str = Field(
        default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"
    )
    phase_timeout: int = Field(
        default=300, ge=30, le=3600, description="Timeout per phase in seconds"
    )

    @field_validator("input_dir")
    @classmethod
    def validate_directories(cls, v: str) -> str:
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @field_validator("pipeline_json")
    @classmethod
    def validate_json(cls, v: str) -> str:
        path = Path(v)
        if not path.exists():
            # Create initial structure
            initial_data = {
                "version": "1.0",
                "created": time.time(),
                "batch": {"status": "initialized", "files": {}, "metrics": {}},
            }
            with open(path, "w") as f:
                json.dump(initial_data, f, indent=2)
        return str(path)


class PhaseMetric(BaseModel):
    """Metrics for a single phase execution"""

    phase: int
    duration: float
    error: Optional[str] = None
    start_time: float
    end_time: float


class BatchMetadata(BaseModel):
    """Metadata for individual file processing"""

    file_id: str
    status: str = "pending"  # pending|running|success|failed|partial
    phases_completed: List[int] = []
    chunks_ids: List[int] = []
    error_message: Optional[str] = None
    errors: List[str] = []  # List of error messages
    duration: Optional[float] = None
    phase_metrics: List[PhaseMetric] = []
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def add_phase_metric(
        self, phase: int, duration: float, error: Optional[str] = None
    ):
        """Add a phase execution metric"""
        now = time.time()
        metric = PhaseMetric(
            phase=phase,
            duration=duration,
            error=error,
            start_time=now - duration,
            end_time=now,
        )
        self.phase_metrics.append(metric)

    def mark_started(self):
        """Mark processing as started"""
        self.status = "running"
        self.start_time = time.time()

    def mark_completed(self):
        """Mark processing as completed"""
        if self.start_time:
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time

        # Determine final status
        total_phases = len(set(self.phases_completed))
        if self.error_message:
            self.status = "partial" if total_phases > 0 else "failed"
        else:
            self.status = "success"


class BatchSummary(BaseModel):
    """Summary of entire batch processing"""

    status: str  # success|partial|failed
    total_files: int
    successful_files: int
    partial_files: int
    failed_files: int
    total_duration: float
    avg_cpu_usage: Optional[float] = None
    errors: List[str] = []
    artifacts: List[str] = []
    timestamps: Dict[str, float] = {}

    @classmethod
    def from_metadata_list(
        cls,
        metadata_list: List[BatchMetadata],
        total_duration: float,
        avg_cpu: Optional[float] = None,
    ):
        """Create summary from list of metadata"""
        successful = sum(1 for m in metadata_list if m.status == "success")
        partial = sum(1 for m in metadata_list if m.status == "partial")
        failed = len(metadata_list) - successful - partial

        errors = [m.error_message for m in metadata_list if m.error_message]

        # Overall status determination
        if failed == 0 and partial == 0:
            status = "success"
        elif successful > 0:
            status = "partial"
        else:
            status = "failed"

        return cls(
            status=status,
            total_files=len(metadata_list),
            successful_files=successful,
            partial_files=partial,
            failed_files=failed,
            total_duration=total_duration,
            avg_cpu_usage=avg_cpu,
            errors=errors,
            timestamps={
                "start": time.time() - total_duration,
                "end": time.time(),
                "duration": total_duration,
            },
        )
