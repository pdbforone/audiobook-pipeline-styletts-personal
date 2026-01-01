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
    # UI preferences
    enable_audio_feedback: bool = True
    audio_volume: float = 0.5
    show_detailed_progress: bool = True
    theme_mode: str = "dark"  # "dark" or "light"
    # LLM/Ollama settings
    llm_enable: bool = True
    llm_model: str = "llama3.1:8b-instruct-q4_K_M"
    llm_auto_start_server: bool = True
    llm_auto_pull_model: bool = True

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], project_root: Optional[Path] = None
    ) -> "UISettings":
        project_root = Path(project_root) if project_root else None
        defaults = cls()
        return cls(
            sample_rate=int(data.get("sample_rate", defaults.sample_rate)),
            lufs_target=int(data.get("lufs_target", defaults.lufs_target)),
            max_workers=int(data.get("max_workers", defaults.max_workers)),
            enable_gpu=bool(data.get("enable_gpu", defaults.enable_gpu)),
            input_dir=str(
                data.get(
                    "input_dir", project_root / "input" if project_root else ""
                )
            ),
            output_dir=str(
                data.get(
                    "output_dir",
                    (
                        project_root / "phase5_enhancement" / "processed"
                        if project_root
                        else ""
                    ),
                )
            ),
            enable_audio_feedback=bool(data.get("enable_audio_feedback", defaults.enable_audio_feedback)),
            audio_volume=float(data.get("audio_volume", defaults.audio_volume)),
            show_detailed_progress=bool(data.get("show_detailed_progress", defaults.show_detailed_progress)),
            theme_mode=str(data.get("theme_mode", defaults.theme_mode)),
            llm_enable=bool(data.get("llm_enable", defaults.llm_enable)),
            llm_model=str(data.get("llm_model", defaults.llm_model)),
            llm_auto_start_server=bool(data.get("llm_auto_start_server", defaults.llm_auto_start_server)),
            llm_auto_pull_model=bool(data.get("llm_auto_pull_model", defaults.llm_auto_pull_model)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_rate": self.sample_rate,
            "lufs_target": self.lufs_target,
            "max_workers": self.max_workers,
            "enable_gpu": self.enable_gpu,
            "input_dir": self.input_dir,
            "output_dir": self.output_dir,
            "enable_audio_feedback": self.enable_audio_feedback,
            "audio_volume": self.audio_volume,
            "show_detailed_progress": self.show_detailed_progress,
            "theme_mode": self.theme_mode,
            "llm_enable": self.llm_enable,
            "llm_model": self.llm_model,
            "llm_auto_start_server": self.llm_auto_start_server,
            "llm_auto_pull_model": self.llm_auto_pull_model,
        }


@dataclass
class VoiceMetadata:
    voice_id: str
    narrator_name: str
    preferred_profiles: List[str] = field(default_factory=list)
    description: str = ""
    notes: str = ""
    local_path: Optional[str] = None
    built_in: bool = False
    engine: Optional[str] = None
    gender: Optional[str] = None
    accent: Optional[str] = None

    @classmethod
    def from_dict(cls, voice_id: str, data: Dict[str, Any]) -> "VoiceMetadata":
        return cls(
            voice_id=voice_id,
            narrator_name=data.get("narrator_name")
            or voice_id.replace("_", " ").title(),
            preferred_profiles=list(data.get("preferred_profiles", [])),
            description=data.get("description") or "",
            notes=data.get("notes") or "",
            local_path=data.get("local_path"),
            built_in=bool(data.get("built_in", False)),
            engine=data.get("engine"),
            gender=data.get("gender"),
            accent=data.get("accent"),
        )

    def to_dropdown_label(self) -> str:
        profiles = ", ".join(self.preferred_profiles)
        profile_part = f" ({profiles})" if profiles else ""
        # Add engine tag for built-in voices
        if self.built_in and self.engine:
            engine_tag = f"[{self.engine.upper()}] "
        else:
            engine_tag = ""
        return f"{self.voice_id}: {engine_tag}{self.narrator_name}{profile_part}"


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


@dataclass
class DetailedProgress:
    """Detailed progress tracking for chunk-level operations"""
    phase: str  # "phase4" or "phase5"
    current_chunk: Optional[str] = None
    total_chunks: int = 0
    completed_chunks: int = 0
    failed_chunks: int = 0
    current_operation: str = ""  # "Synthesizing", "Enhancing", etc.
    estimated_time_remaining: Optional[float] = None  # seconds
    last_updated: Optional[str] = None

    @property
    def progress_percent(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return (self.completed_chunks / self.total_chunks) * 100

    @property
    def status_text(self) -> str:
        if self.current_chunk:
            return f"{self.current_operation} {self.current_chunk} ({self.completed_chunks}/{self.total_chunks})"
        return f"{self.phase}: {self.completed_chunks}/{self.total_chunks} complete"
