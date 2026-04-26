#!/usr/bin/env bash
set -euo pipefail
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8001}"
mkdir -p "${OUTPUT_DIR:-/workspace/outputs_wan}" "${JOBS_DIR:-/workspace/jobs_wan}"
exec python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT"
