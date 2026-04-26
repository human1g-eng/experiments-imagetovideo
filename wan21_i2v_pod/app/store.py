from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

from .models import JobDetail, JobStatus


@dataclass
class JobRecord:
    job_id: str
    prompt: str
    image_path: Path
    status: JobStatus = JobStatus.queued
    output_path: Optional[Path] = None
    error: Optional[str] = None

    def to_detail(self) -> JobDetail:
        return JobDetail(
            job_id=self.job_id,
            status=self.status,
            prompt=self.prompt,
            image_path=str(self.image_path),
            output_path=str(self.output_path) if self.output_path else None,
            error=self.error,
        )


class JobStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: Dict[str, JobRecord] = {}

    def create(self, record: JobRecord) -> None:
        with self._lock:
            self._jobs[record.job_id] = record

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def set_status(self, job_id: str, status: JobStatus) -> None:
        with self._lock:
            self._jobs[job_id].status = status

    def set_success(self, job_id: str, output_path: Path) -> None:
        with self._lock:
            record = self._jobs[job_id]
            record.status = JobStatus.succeeded
            record.output_path = output_path
            record.error = None

    def set_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            record = self._jobs[job_id]
            record.status = JobStatus.failed
            record.error = error
