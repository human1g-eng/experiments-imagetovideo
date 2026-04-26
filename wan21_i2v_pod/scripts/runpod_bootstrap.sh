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
if [[ -f requirements.txt ]]; then
  # flash-attn frequently fails to build on generic pod images (Py3.12 / CUDA mismatch).
  # Wan can run with the SDPA fallback, so we install requirements without flash-attn.
  if grep -qiE "flash[-_]?attn" requirements.txt; then
    grep -viE "flash[-_]?attn" requirements.txt > /tmp/wan_requirements_no_flash.txt
    python3 -m pip install -r /tmp/wan_requirements_no_flash.txt
  else
    python3 -m pip install -r requirements.txt
  fi
else
  echo "WARNING: ${WAN_REPO_DIR}/requirements.txt not found, skipping Wan repo requirements install."
fi
python3 -m pip install "huggingface_hub[cli]"

patch_attention_fallback() {
  local target_file="$1"
  if [[ ! -f "${target_file}" ]]; then
    return 0
  fi

  # Replace hard flash_attention calls with wrapper attention() so PyTorch SDPA fallback works.
  sed -i "s/from \\.attention import flash_attention/from .attention import attention/" "${target_file}" || true
  sed -i "s/flash_attention(/attention(/g" "${target_file}" || true
  sed -i "s/version=/fa_version=/g" "${target_file}" || true
}

patch_attention_fallback "wan/modules/clip.py"
patch_attention_fallback "wan/modules/model.py"

cat <<EOT
Bootstrap done.
Download model checkpoints next:
hf download Wan-AI/Wan2.1-I2V-14B-720P --local-dir ${WAN_REPO_DIR}/Wan2.1-I2V-14B-720P

Then start API:
cd ${APP_DIR}
WAN_REPO_DIR=${WAN_REPO_DIR} WAN_CKPT_DIR=${WAN_REPO_DIR}/Wan2.1-I2V-14B-720P HOST=0.0.0.0 PORT=8001 ./scripts/start.sh
EOT
