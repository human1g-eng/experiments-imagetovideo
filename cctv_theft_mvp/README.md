# CCTV Theft MVP (Jewelry Shop Focus)

FastAPI app to test suspicious-behavior detection on CCTV clips:
- uploads a video
- detects/tracks people
- flags risk events (counter reach, loitering near counter, grab-and-exit risk)
- exports annotated video + JSON report

## Endpoints

- `GET /health`
- `POST /v1/jobs`
- `GET /v1/jobs/{job_id}`
- `GET /v1/jobs/{job_id}/result`
- `GET /v1/jobs/{job_id}/report`
- `GET /ui`

## Quick Start (RunPod / Linux VM)

```bash
cd /workspace/experiments-imagetovideo/cctv_theft_mvp
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# Optional but strongly recommended for better person detection:
python3 -m pip install ultralytics
```

Start:

```bash
cd /workspace/experiments-imagetovideo/cctv_theft_mvp
HOST=0.0.0.0 PORT=8020 ./scripts/start.sh
```

Open:

- `http://<pod-ip>:8020/ui`
- or SSH tunnel then `http://localhost:8020/ui`

## Params JSON (optional)

Example:

```json
{
  "detector_engine": "auto",
  "detector_model": "yolo11s.pt",
  "detector_conf": 0.35,
  "process_every_n_frames": 2,
  "counter_line_ratio": 0.45,
  "counter_band_ratio": 0.15,
  "dwell_seconds": 10,
  "exit_zone_width_ratio": 0.15,
  "min_speed_px_per_sec": 220
}
```

Notes:
- `detector_engine=auto` tries YOLO first; falls back to HOG if YOLO runtime is unavailable.
- Tune `counter_line_ratio` based on camera angle.
- This is an MVP risk scorer, not a final conviction engine.

