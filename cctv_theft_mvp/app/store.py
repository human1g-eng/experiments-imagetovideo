from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from .models import JobDetail, JobStatus


@dataclass
class JobRecord:
    job_id: str
    video_path: Path
    status: JobStatus = JobStatus.queued
    output_video_path: Optional[Path] = None
    report_path: Optional[Path] = None
    events: list[dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_detail(self) -> JobDetail:
        return JobDetail(
            job_id=self.job_id,
            status=self.status,
            video_path=str(self.video_path),
            output_video_path=str(self.output_video_path) if self.output_video_path else None,
            report_path=str(self.report_path) if self.report_path else None,
            events_count=len(self.events),
            events_preview=self.events[:20],
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

    def set_success(self, job_id: str, output_video_path: Path, report_path: Path, events: list[dict[str, Any]]) -> None:
        with self._lock:
            record = self._jobs[job_id]
            record.status = JobStatus.succeeded
            record.output_video_path = output_video_path
            record.report_path = report_path
            record.events = events
            record.error = None

    def set_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            record = self._jobs[job_id]
            record.status = JobStatus.failed
            record.error = error

