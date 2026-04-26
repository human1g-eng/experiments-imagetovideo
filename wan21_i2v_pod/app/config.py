from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8001"))

    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "/workspace/outputs_wan"))
    jobs_dir: Path = Path(os.getenv("JOBS_DIR", "/workspace/jobs_wan"))

    wan_repo_dir: Path = Path(os.getenv("WAN_REPO_DIR", "/workspace/Wan2.1"))
    wan_python: str = os.getenv("WAN_PYTHON", "python3")
    wan_task: str = os.getenv("WAN_TASK", "i2v-14B")
    wan_ckpt_dir: Path = Path(os.getenv("WAN_CKPT_DIR", "/workspace/Wan2.1/Wan2.1-I2V-14B-720P"))
    wan_extra_args: str = os.getenv("WAN_EXTRA_ARGS", "")

    default_size: str = os.getenv("DEFAULT_SIZE", "1280*720")
    default_seed: int = int(os.getenv("DEFAULT_SEED", "0"))

    mock_mode: bool = os.getenv("MOCK_MODE", "false").lower() in {"1", "true", "yes", "on"}


settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.jobs_dir.mkdir(parents=True, exist_ok=True)
