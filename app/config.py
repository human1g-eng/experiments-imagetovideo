from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    workspace_dir: Path = Path(os.getenv("WORKSPACE_DIR", "/workspace"))
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "/workspace/outputs"))
    jobs_dir: Path = Path(os.getenv("JOBS_DIR", "/workspace/jobs"))

    hunyuan_repo_dir: Path = Path(os.getenv("HUNYUAN_REPO_DIR", "/workspace/HunyuanVideo-I2V"))
    hunyuan_python: str = os.getenv("HUNYUAN_PYTHON", "python3")

    default_model: str = os.getenv("DEFAULT_MODEL", "HYVideo-T/2")
    default_resolution: str = os.getenv("DEFAULT_RESOLUTION", "720p")
    default_video_length: int = int(os.getenv("DEFAULT_VIDEO_LENGTH", "129"))
    default_infer_steps: int = int(os.getenv("DEFAULT_INFER_STEPS", "50"))
    default_embedded_cfg_scale: float = float(os.getenv("DEFAULT_EMBEDDED_CFG_SCALE", "6.0"))
    default_flow_shift_stable: float = float(os.getenv("DEFAULT_FLOW_SHIFT_STABLE", "7.0"))
    default_flow_shift_dynamic: float = float(os.getenv("DEFAULT_FLOW_SHIFT_DYNAMIC", "17.0"))

    mock_mode: bool = os.getenv("MOCK_MODE", "false").lower() in {"1", "true", "yes", "on"}


settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.jobs_dir.mkdir(parents=True, exist_ok=True)
