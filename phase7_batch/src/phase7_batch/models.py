from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


def _default_max_workers() -> int:
    """Choose a conservative default that keeps one core free."""
    return max(1, (os.cpu_count() or 2) - 1)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BatchConfig(BaseModel):
    """Configuration for the Phase 7 batch runner."""

    model_config = ConfigDict(validate_assignment=True, extra="ignore", populate_by_name=True)

    pipeline_json: str = Field(default="../pipeline.json")
    input_dir: str = Field(default="../input")
    log_file: str = Field(default="batch.log")
    log_level: str = Field(default="INFO")
    max_workers: int = Field(default_factory=_default_max_workers, ge=1)
    cpu_threshold: float = Field(default=85.0, ge=0, le=100)
    throttle_delay: float = Field(default=1.0, ge=0)
    resume: bool = Field(default=True, validation_alias=AliasChoices("resume", "resume_enabled"))
    phases: List[int] = Field(default_factory=list, validation_alias=AliasChoices("phases", "phases_to_run"))
    batch_size: Optional[int] = Field(default=None, ge=1)
    phase_timeout: int = Field(default=600, ge=1)
    dry_run: bool = Field(default=False)

    @field_validator("pipeline_json", "input_dir", "log_file", mode="before")
    @classmethod
    def _normalize_path(cls, value: str) -> str:
        return Path(value).as_posix()

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        return value.upper()

    @field_validator("phases", mode="before")
    @classmethod
    def _normalize_phases(cls, value: Any) -> List[int]:
        if value is None:
            return []
        if isinstance(value, (str, int)):
            return [int(value)]
        return [int(v) for v in value]

    @property
    def phases_argument(self) -> List[str]:
        return [str(p) for p in self.phases]


class Phase6Result(BaseModel):
    """Structured capture of the Phase 6 subprocess output."""

    exit_code: Optional[int] = None
    stdout_tail: Optional[str] = None
    stderr_tail: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


class BatchMetadata(BaseModel):
    """Metadata captured per input file."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    file_id: str
    status: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_sec: Optional[float] = None
    was_skipped: bool = False
    error_message: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    source_path: Optional[str] = None
    phase6: Phase6Result = Field(default_factory=Phase6Result)
    cpu_avg: Optional[float] = None

    def to_pipeline_dict(self) -> Dict[str, Any]:
        """Serialize with noise removed for pipeline.json."""
        return self.model_dump(exclude_none=True, exclude={"file_id"})


class BatchSummary(BaseModel):
    """Summary of the batch run."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    status: str
    total_files: int
    successful_files: int
    failed_files: int
    skipped_files: int
    duration_sec: float
    avg_cpu_usage: Optional[float] = None
    errors: List[str] = Field(default_factory=list)
    artifacts: List[str] = Field(default_factory=list)
    started_at: str
    completed_at: str

    @classmethod
    def from_metadata_list(
        cls,
        metadata_list: List[BatchMetadata],
        started_at: datetime,
        completed_at: datetime,
        avg_cpu: Optional[float] = None,
        status_override: Optional[str] = None,
    ) -> "BatchSummary":
        successes = sum(1 for m in metadata_list if m.status == "success")
        failed = sum(1 for m in metadata_list if m.status == "failed")
        skipped = sum(1 for m in metadata_list if m.status == "skipped")
        total = len(metadata_list)

        if status_override:
            status = status_override
        elif failed > 0 and successes > 0:
            status = "partial"
        elif failed > 0:
            status = "failed"
        elif successes > 0 and skipped > 0:
            status = "partial"
        elif successes > 0 and failed == 0:
            status = "success"
        elif skipped == total:
            status = "skipped"
        else:
            status = "failed"

        errors: List[str] = []
        for m in metadata_list:
            if m.error_message:
                errors.append(m.error_message)
            errors.extend(m.errors)

        duration_sec = max(0.0, (completed_at - started_at).total_seconds())

        return cls(
            status=status,
            total_files=total,
            successful_files=successes,
            failed_files=failed,
            skipped_files=skipped,
            duration_sec=duration_sec,
            avg_cpu_usage=avg_cpu,
            errors=errors,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
        )
