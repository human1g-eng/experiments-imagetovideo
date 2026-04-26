#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${APP_DIR:-/workspace/experiments-imagetovideo/wan21_i2v_pod}"
WAN_REPO_DIR="${WAN_REPO_DIR:-/workspace/Wan2.1}"
WAN_REPO_URL="${WAN_REPO_URL:-https://github.com/Wan-Video/Wan2.1.git}"

if ! command -v python3 >/dev/null 2>&1; then
  apt-get update && apt-get install -y python3 python3-pip python3-venv git ffmpeg
fi

if [[ ! -d "${WAN_REPO_DIR}" ]]; then
  git clone "${WAN_REPO_URL}" "${WAN_REPO_DIR}"
fi

cd "${APP_DIR}"
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

cd "${WAN_REPO_DIR}"
python3 -m pip install -r requirements.txt
python3 -m pip install "huggingface_hub[cli]"

cat <<EOT
Bootstrap done.
Download model checkpoints next:
huggingface-cli download Wan-AI/Wan2.1-I2V-14B-720P --local-dir ${WAN_REPO_DIR}/Wan2.1-I2V-14B-720P

Then start API:
cd ${APP_DIR}
WAN_REPO_DIR=${WAN_REPO_DIR} WAN_CKPT_DIR=${WAN_REPO_DIR}/Wan2.1-I2V-14B-720P HOST=0.0.0.0 PORT=8001 ./scripts/start.sh
EOT
