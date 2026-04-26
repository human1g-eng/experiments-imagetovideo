from __future__ import annotations

import shlex
import shutil
import subprocess
import time
from pathlib import Path

from .config import settings
from .models import InferenceParams, RunResult


class RunnerError(RuntimeError):
    pass


def _run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    try:
        subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)
    except subprocess.CalledProcessError as exc:
        raise RunnerError(f"Command failed: {' '.join(cmd)}") from exc


def _run_mock(image_path: Path, output_path: Path) -> RunResult:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RunnerError("MOCK_MODE is enabled but ffmpeg is not installed.")

    cmd = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-vf",
        "zoompan=z='min(zoom+0.002,1.1)':d=180:s=1280x720,framerate=24",
        "-t",
        "8",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    _run_cmd(cmd)
    return RunResult(output_path=output_path)


def _latest_mp4_after(repo_dir: Path, start_time: float) -> Path | None:
    candidates = [p for p in repo_dir.rglob("*.mp4") if p.is_file() and p.stat().st_mtime >= start_time]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def run_wan_i2v(image_path: Path, output_path: Path, params: InferenceParams) -> RunResult:
    if settings.mock_mode:
        return _run_mock(image_path, output_path)

    script = settings.wan_repo_dir / "generate.py"
    if not script.exists():
        raise RunnerError(f"Could not find {script}. Clone Wan-Video/Wan2.1 in WAN_REPO_DIR.")

    cmd = [
        settings.wan_python,
        str(script),
        "--task",
        settings.wan_task,
        "--size",
        params.size,
        "--ckpt_dir",
        str(settings.wan_ckpt_dir),
        "--image",
        str(image_path),
        "--prompt",
        params.prompt,
        "--base_seed",
        str(params.seed),
    ]
    if settings.wan_extra_args.strip():
        cmd.extend(shlex.split(settings.wan_extra_args.strip()))

    started = time.time() - 1
    _run_cmd(cmd, cwd=settings.wan_repo_dir)

    generated = _latest_mp4_after(settings.wan_repo_dir, started)
    if generated is None:
        generated = _latest_mp4_after(settings.output_dir, started)
    if generated is None:
        raise RunnerError("Generation completed but no output mp4 was found.")

    generated.rename(output_path)
    return RunResult(output_path=output_path)
