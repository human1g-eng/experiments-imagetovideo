from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import settings
from .models import InferenceParams, RunResult


class RunnerError(RuntimeError):
    pass


def _ensure_attention_mode(repo_dir: Path, mode: str) -> None:
    # HunyuanVideo-I2V may fail when flash-attn is unavailable on some pods.
    # For "torch" mode we patch the default in-source attention mode.
    if mode not in {"flash", "torch"}:
        raise RunnerError(f"Invalid ATTN_MODE: {mode}. Use 'flash' or 'torch'.")
    if mode != "torch":
        return

    attn_file = repo_dir / "hyvideo" / "modules" / "attenion.py"
    if not attn_file.exists():
        raise RunnerError(f"Could not find attention module: {attn_file}")

    text = attn_file.read_text()
    if 'mode="torch"' in text:
        return
    updated = text.replace('mode="flash"', 'mode="torch"', 1)
    if updated == text:
        raise RunnerError("Could not patch attention mode in attenion.py")
    attn_file.write_text(updated)


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
        "zoompan=z='min(zoom+0.0015,1.12)':d=240:s=1280x720,framerate=24",
        "-t",
        "10",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    _run_cmd(cmd)
    return RunResult(output_path=output_path)


def run_hunyuan_i2v(image_path: Path, output_path: Path, params: InferenceParams) -> RunResult:
    if settings.mock_mode:
        return _run_mock(image_path, output_path)

    sample_script = settings.hunyuan_repo_dir / "sample_image2video.py"
    if not sample_script.exists():
        raise RunnerError(
            f"Could not find {sample_script}. Clone Tencent-Hunyuan/HunyuanVideo-I2V in HUNYUAN_REPO_DIR."
        )

    _ensure_attention_mode(settings.hunyuan_repo_dir, settings.attn_mode)

    cmd = [
        settings.hunyuan_python,
        str(sample_script),
        "--model",
        params.model,
        "--prompt",
        params.prompt,
        "--i2v-mode",
        "--i2v-image-path",
        str(image_path),
        "--i2v-resolution",
        params.resolution,
        "--infer-steps",
        str(params.infer_steps),
        "--video-length",
        str(params.video_length),
        "--flow-shift",
        str(params.flow_shift(settings.default_flow_shift_stable, settings.default_flow_shift_dynamic)),
        "--embedded-cfg-scale",
        str(params.embedded_cfg_scale),
        "--seed",
        str(params.seed),
        "--save-path",
        str(output_path.parent),
    ]

    if params.flow_reverse:
        cmd.append("--flow-reverse")
    if params.cpu_offload:
        cmd.append("--use-cpu-offload")
    if params.stable_mode:
        cmd.append("--i2v-stability")

    _run_cmd(cmd, cwd=settings.hunyuan_repo_dir)

    if not output_path.exists():
        candidates = sorted(output_path.parent.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise RunnerError("Inference completed but no output mp4 was found.")
        candidates[0].rename(output_path)

    return RunResult(output_path=output_path)
