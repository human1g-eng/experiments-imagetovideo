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
    size: str = "1280*720"
    seed: int = 0


class RunResult(BaseModel):
    output_path: Path
