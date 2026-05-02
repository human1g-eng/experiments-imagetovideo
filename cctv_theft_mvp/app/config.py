from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8020"))

    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "/workspace/outputs_theft"))
    jobs_dir: Path = Path(os.getenv("JOBS_DIR", "/workspace/jobs_theft"))

    # Optional detector defaults.
    detector_engine: str = os.getenv("DETECTOR_ENGINE", "auto")  # auto|yolo|hog
    detector_model: str = os.getenv("DETECTOR_MODEL", "yolo11s.pt")
    detector_conf: float = float(os.getenv("DETECTOR_CONF", "0.35"))


settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.jobs_dir.mkdir(parents=True, exist_ok=True)

