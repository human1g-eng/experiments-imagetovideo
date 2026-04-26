from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class CreateJobResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobDetail(BaseModel):
    job_id: str
    status: JobStatus
    prompt: str
    image_path: str
    output_path: Optional[str] = None
    error: Optional[str] = None


class InferenceParams(BaseModel):
    prompt: str = Field(default="", min_length=0, max_length=2000)
    model: str = "HYVideo-T/2"
    resolution: str = "720p"
    infer_steps: int = Field(default=50, ge=1, le=200)
    video_length: int = Field(default=129, ge=17, le=257)
    seed: int = 0
    embedded_cfg_scale: float = Field(default=6.0, ge=1.0, le=20.0)
    flow_reverse: bool = True
    cpu_offload: bool = True
    stable_mode: bool = True

    def flow_shift(self, stable_shift: float, dynamic_shift: float) -> float:
        return stable_shift if self.stable_mode else dynamic_shift


class RunResult(BaseModel):
    output_path: Path
