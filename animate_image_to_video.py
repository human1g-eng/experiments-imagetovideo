#!/usr/bin/env python3
"""Create a simple animated MP4 (Ken Burns style) from a still image using ffmpeg."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Turn a single image into an animated MP4 using ffmpeg zoompan."
    )
    parser.add_argument("--input", required=True, help="Path to input image (jpg/png/webp).")
    parser.add_argument("--output", required=True, help="Path to output mp4.")
    parser.add_argument("--duration", type=float, default=8.0, help="Duration in seconds. Default: 8")
    parser.add_argument("--fps", type=int, default=24, help="Frames per second. Default: 24")
    parser.add_argument("--width", type=int, default=1280, help="Output width. Default: 1280")
    parser.add_argument("--height", type=int, default=720, help="Output height. Default: 720")
    parser.add_argument("--zoom-start", type=float, default=1.0, help="Starting zoom. Default: 1.0")
    parser.add_argument("--zoom-end", type=float, default=1.12, help="Ending zoom. Default: 1.12")
    parser.add_argument(
        "--pan",
        choices=["center", "left-to-right", "right-to-left", "top-to-bottom", "bottom-to-top"],
        default="center",
        help="Pan direction while zooming.",
    )
    return parser.parse_args()


def pan_expr(direction: str) -> tuple[str, str]:
    if direction == "left-to-right":
        return "x='iw/2-(iw/zoom/2)+(on*0.5)'", "y='ih/2-(ih/zoom/2)'"
    if direction == "right-to-left":
        return "x='iw/2-(iw/zoom/2)-(on*0.5)'", "y='ih/2-(ih/zoom/2)'"
    if direction == "top-to-bottom":
        return "x='iw/2-(iw/zoom/2)'", "y='ih/2-(ih/zoom/2)+(on*0.5)'"
    if direction == "bottom-to-top":
        return "x='iw/2-(iw/zoom/2)'", "y='ih/2-(ih/zoom/2)-(on*0.5)'"
    return "x='iw/2-(iw/zoom/2)'", "y='ih/2-(ih/zoom/2)'"


def main() -> int:
    args = parse_args()

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("Error: ffmpeg not found in PATH.")

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not input_path.exists():
        raise SystemExit(f"Error: input image does not exist: {input_path}")

    if args.duration <= 0:
        raise SystemExit("Error: --duration must be > 0")
    if args.fps <= 0:
        raise SystemExit("Error: --fps must be > 0")
    if args.width <= 0 or args.height <= 0:
        raise SystemExit("Error: --width and --height must be > 0")
    if args.zoom_end < args.zoom_start:
        raise SystemExit("Error: --zoom-end must be >= --zoom-start")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_frames = max(1, int(round(args.duration * args.fps)))
    zoom_step = (args.zoom_end - args.zoom_start) / total_frames
    x_expr, y_expr = pan_expr(args.pan)

    vf = (
        f"zoompan=z='min(zoom+{zoom_step:.8f},{args.zoom_end})':"
        f"d={total_frames}:"
        f"s={args.width}x{args.height}:"
        f"fps={args.fps}:"
        f"{x_expr}:"
        f"{y_expr},"
        f"framerate={args.fps},format=yuv420p"
    )

    cmd = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        str(input_path),
        "-t",
        str(args.duration),
        "-vf",
        vf,
        "-an",
        "-movflags",
        "+faststart",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]

    subprocess.run(cmd, check=True)
    print(f"Saved animated video: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
