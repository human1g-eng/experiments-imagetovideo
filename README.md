# HunyuanVideo-I2V Pod App

FastAPI app that accepts an image + prompt, runs `HunyuanVideo-I2V` inference, and returns an MP4.

## What This Gives You

- `POST /v1/jobs`: create generation job (image + prompt)
- `GET /v1/jobs/{job_id}`: check status
- `GET /v1/jobs/{job_id}/result`: download MP4
- `GET /health`: readiness check
- `GET /` or `GET /ui`: simple browser UI

## 1) Build and Run (Local Docker)

```bash
cd hunyuan_i2v_pod
docker build -t hunyuan-i2v-api .
docker run --gpus all --rm -p 8000:8000 \
  -e HUNYUAN_REPO_DIR=/workspace/HunyuanVideo-I2V \
  -v /absolute/path/to/HunyuanVideo-I2V:/workspace/HunyuanVideo-I2V \
  hunyuan-i2v-api
```

## 2) RunPod VM Setup (Recommended)

Use a template with CUDA + Python and attach a persistent volume so you do not redownload checkpoints every restart.

Recommended persistent paths:
- `/workspace/HunyuanVideo-I2V`
- `/workspace/outputs`
- `/workspace/jobs`

On first boot:

```bash
cd /workspace/hunyuan_i2v_pod
./scripts/runpod_bootstrap.sh
```

The bootstrap script applies compatibility pins for Hunyuan I2V:
- `transformers==4.46.3`
- `tokenizers==0.20.3`
- `huggingface_hub==0.25.2`

Then place model checkpoints in:

```bash
/workspace/HunyuanVideo-I2V/ckpts
```

Start API:

```bash
cd /workspace/hunyuan_i2v_pod
HOST=0.0.0.0 PORT=8000 ./scripts/start.sh
```

Optional pre-start API-only test (no model):

```bash
cd /workspace/hunyuan_i2v_pod
MOCK_MODE=true HOST=0.0.0.0 PORT=8000 ./scripts/start.sh
```

Recommended for most RunPod images (avoids flash-attn build dependency):

```bash
ATTN_MODE=torch HOST=0.0.0.0 PORT=8000 ./scripts/start.sh
```

If your pod has `/workspace` quota pressure, move caches out of `/workspace` before starting:

```bash
export HF_HOME=/dev/shm/hf-home
unset TRANSFORMERS_CACHE
unset HF_HUB_ENABLE_HF_TRANSFER
```

Open UI in browser:

```bash
http://<pod-ip>:8000/ui
```

## 3) API Usage

Create job:

```bash
curl -X POST "http://localhost:8000/v1/jobs" \
  -F "image=@/path/to/input.jpg" \
  -F "prompt=cinematic slow dolly shot of a tiger blinking" \
  -F 'params={"infer_steps":50,"video_length":129,"stable_mode":true}'
```

Check status:

```bash
curl "http://localhost:8000/v1/jobs/<job_id>"
```

Download result:

```bash
curl -L "http://localhost:8000/v1/jobs/<job_id>/result" -o out.mp4
```

## 4) Real Inference Command Used

The worker runs the official script:

```bash
python3 sample_image2video.py \
  --model HYVideo-T/2 \
  --prompt "..." \
  --i2v-mode \
  --i2v-image-path <input-image> \
  --i2v-resolution 720p \
  --i2v-stability \
  --infer-steps 50 \
  --video-length 129 \
  --flow-reverse \
  --flow-shift 7.0 \
  --seed 0 \
  --embedded-cfg-scale 6.0 \
  --use-cpu-offload \
  --save-path <output-dir>
```

If `stable_mode=false`, the app uses `--flow-shift 17.0` and skips `--i2v-stability`.

## 5) Smoke Test Without GPU/Weights

Set `MOCK_MODE=true` and run API. It will generate a short zoom video from the image via ffmpeg so you can test full request flow.
