#!/usr/bin/env bash
set -euo pipefail

# One-shot bootstrap for a fresh GPU VM.
WORKSPACE_DIR="${WORKSPACE_DIR:-/workspace}"
APP_DIR="${APP_DIR:-/workspace/hunyuan_i2v_pod}"
HUNYUAN_REPO_DIR="${HUNYUAN_REPO_DIR:-/workspace/HunyuanVideo-I2V}"
HUNYUAN_REPO_URL="${HUNYUAN_REPO_URL:-https://github.com/Tencent-Hunyuan/HunyuanVideo-I2V.git}"

if ! command -v python3 >/dev/null 2>&1; then
  apt-get update && apt-get install -y python3 python3-pip python3-venv git ffmpeg
fi

if [[ ! -d "${HUNYUAN_REPO_DIR}" ]]; then
  git clone "${HUNYUAN_REPO_URL}" "${HUNYUAN_REPO_DIR}"
fi

cd "${APP_DIR}"
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

cd "${HUNYUAN_REPO_DIR}"
python3 -m pip install -r requirements.txt

cat <<EOT
Bootstrap done.

Next step: place model checkpoints under ${HUNYUAN_REPO_DIR}/ckpts per official instructions,
then run:

cd ${APP_DIR}
HOST=0.0.0.0 PORT=8000 ./scripts/start.sh
EOT
