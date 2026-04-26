# Wan2.1 I2V Pod App

Image-to-video API + simple UI for `Wan2.1`.

## Endpoints

- `GET /health`
- `POST /v1/jobs`
- `GET /v1/jobs/{job_id}`
- `GET /v1/jobs/{job_id}/result`
- `GET /ui`

## RunPod Quickstart

```bash
cd /workspace/experiments-imagetovideo/wan21_i2v_pod
./scripts/runpod_bootstrap.sh

huggingface-cli download Wan-AI/Wan2.1-I2V-14B-720P --local-dir /workspace/Wan2.1/Wan2.1-I2V-14B-720P

WAN_REPO_DIR=/workspace/Wan2.1 \
WAN_CKPT_DIR=/workspace/Wan2.1/Wan2.1-I2V-14B-720P \
HOST=0.0.0.0 PORT=8001 ./scripts/start.sh
```

Open:
- `http://<pod-ip>:8001/ui`
- or tunnel to localhost.

## Notes

- First run is slow due model load.
- Use size `832*480` for faster testing.
- If official CLI changes, set extra flags in `WAN_EXTRA_ARGS`.
