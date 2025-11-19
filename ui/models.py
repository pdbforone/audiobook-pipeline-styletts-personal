from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class UISettings:
    sample_rate: int = 48000
    lufs_target: int = -23
    max_workers: int = 4
    enable_gpu: bool = False
    input_dir: str = ""
    output_dir: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any], project_root: Optional[Path] = None) -> "UISettings":
        project_root = Path(project_root) if project_root else None
        return cls(
            sample_rate=int(data.get("sample_rate", cls.sample_rate)),
            lufs_target=int(data.get("lufs_target", cls.lufs_target)),
            max_workers=int(data.get("max_workers", cls.max_workers)),
            enable_gpu=bool(data.get("enable_gpu", cls.enable_gpu)),
            input_dir=str(data.get("input_dir", project_root / "input" if project_root else "")),
            output_dir=str(data.get("output_dir", project_root / "phase5_enhancement" / "processed" if project_root else "")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_rate": self.sample_rate,
            "lufs_target": self.lufs_target,
            "max_workers": self.max_workers,
            "enable_gpu": self.enable_gpu,
            "input_dir": self.input_dir,
            "output_dir": self.output_dir,
        }


@dataclass
class VoiceMetadata:
    voice_id: str
    narrator_name: str
    preferred_profiles: List[str] = field(default_factory=list)
    description: str = ""
    notes: str = ""
    local_path: Optional[str] = None

    @classmethod
    def from_dict(cls, voice_id: str, data: Dict[str, Any]) -> "VoiceMetadata":
        return cls(
            voice_id=voice_id,
            narrator_name=data.get("narrator_name") or voice_id.replace("_", " ").title(),
            preferred_profiles=list(data.get("preferred_profiles", [])),
            description=data.get("description") or "",
            notes=data.get("notes") or "",
            local_path=data.get("local_path"),
        )

    def to_dropdown_label(self) -> str:
        profiles = ", ".join(self.preferred_profiles)
        profile_part = f" ({profiles})" if profiles else ""
        return f"{self.voice_id}: {self.narrator_name}{profile_part}"


@dataclass
class PhaseStatusSummary:
    key: str
    label: str
    status: str
    errors: List[str] = field(default_factory=list)


@dataclass
class FileSystemProgress:
    chunk_txt: int = 0
    phase4_wav: int = 0
    phase5_wav: int = 0
    mp3_exists: bool = False


@dataclass
class PipelineStatus:
    file_id: str
    phases: List[PhaseStatusSummary] = field(default_factory=list)
    fs_progress: FileSystemProgress = field(default_factory=FileSystemProgress)
    processes: List[str] = field(default_factory=list)


@dataclass
class Phase4ChunkSummary:
    chunk_id: str
    status: str
    engine: str
    rt_factor: Optional[float]
    audio_path: str


@dataclass
class Phase4Summary:
    file_id: str
    requested_engine: str
    total_chunks: int
    completed: int
    failed: int
    duration_seconds: Optional[float]
    page: int
    total_pages: int
    chunks: List[Phase4ChunkSummary] = field(default_factory=list)


@dataclass
class IncompleteWork:
    file_id: str
    phases_complete: List[float]
    phases_incomplete: List[float]
    last_phase: float
