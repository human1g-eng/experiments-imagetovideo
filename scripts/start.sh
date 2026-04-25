#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace}"
OUTPUT_DIR="${OUTPUT_DIR:-/workspace/outputs}"
JOBS_DIR="${JOBS_DIR:-/workspace/jobs}"
HUNYUAN_REPO_DIR="${HUNYUAN_REPO_DIR:-/workspace/HunyuanVideo-I2V}"

mkdir -p "${OUTPUT_DIR}" "${JOBS_DIR}"

if [[ "${MOCK_MODE:-false}" != "true" && ! -f "${HUNYUAN_REPO_DIR}/sample_image2video.py" ]]; then
  echo "WARNING: sample_image2video.py not found at ${HUNYUAN_REPO_DIR}"
  echo "Set MOCK_MODE=true for API-only test, or clone HunyuanVideo-I2V before starting."
fi

exec python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT"
