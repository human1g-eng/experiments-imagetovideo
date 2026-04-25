from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .config import settings
from .models import InferenceParams, RunResult


class RunnerError(RuntimeError):
    pass


def _ensure_transformers_compat(python_bin: str) -> None:
    # HunyuanVideo-I2V + llava-i2v currently works reliably with a 4.46.x stack.
    code = (
        "import transformers, tokenizers; "
        "print(transformers.__version__); "
        "print(tokenizers.__version__)"
    )
    try:
        proc = subprocess.run([python_bin, "-c", code], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise RunnerError(
            "Could not verify transformers/tokenizers versions in HUNYUAN_PYTHON environment."
        ) from exc

    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    if len(lines) < 2:
        raise RunnerError("Could not parse transformers/tokenizers versions from runtime.")

    transformers_ver, tokenizers_ver = lines[-2], lines[-1]
    if not transformers_ver.startswith("4.46.") or not tokenizers_ver.startswith("0.20."):
        raise RunnerError(
            "Incompatible HF stack detected. "
            f"Found transformers={transformers_ver}, tokenizers={tokenizers_ver}. "
            "Install transformers==4.46.3 tokenizers==0.20.3 huggingface_hub==0.25.2."
        )


def _ensure_llava_processor_config(repo_dir: Path) -> None:
    base = repo_dir / "ckpts" / "text_encoder_i2v"
    pre = base / "preprocessor_config.json"
    proc = base / "processor_config.json"
    if not pre.exists():
        return

    if not proc.exists():
        proc.write_text(pre.read_text())

    for config_path in (pre, proc):
        data = json.loads(config_path.read_text())
        data["processor_class"] = "LlavaProcessor"
        data["patch_size"] = 14
        data["vision_feature_select_strategy"] = "default"
        data["num_additional_image_tokens"] = 0
        data["image_seq_length"] = 576
        config_path.write_text(json.dumps(data, indent=2))


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

    _ensure_transformers_compat(settings.hunyuan_python)
    _ensure_attention_mode(settings.hunyuan_repo_dir, settings.attn_mode)
    _ensure_llava_processor_config(settings.hunyuan_repo_dir)

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
