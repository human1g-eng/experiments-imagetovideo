from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class CreateJobResponse(BaseModel):
    job_id: str
    status: JobStatus


class AnalyzeParams(BaseModel):
    detector_engine: str = Field(default="auto", pattern="^(auto|yolo|hog)$")
    detector_model: str = "yolo11s.pt"
    detector_conf: float = Field(default=0.35, ge=0.05, le=0.95)
    process_every_n_frames: int = Field(default=2, ge=1, le=10)

    counter_line_ratio: float = Field(default=0.45, ge=0.1, le=0.9)
    counter_band_ratio: float = Field(default=0.15, ge=0.05, le=0.4)
    dwell_seconds: float = Field(default=10.0, ge=2.0, le=120.0)

    exit_zone_width_ratio: float = Field(default=0.15, ge=0.05, le=0.35)
    min_speed_px_per_sec: float = Field(default=220.0, ge=40.0, le=2000.0)
    max_track_missed: int = Field(default=25, ge=3, le=200)
    match_distance_px: float = Field(default=90.0, ge=10.0, le=500.0)


class JobDetail(BaseModel):
    job_id: str
    status: JobStatus
    video_path: str
    output_video_path: Optional[str] = None
    report_path: Optional[str] = None
    events_count: int = 0
    events_preview: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class AnalysisResult(BaseModel):
    output_video_path: Path
    report_path: Path
    events: list[dict[str, Any]]

