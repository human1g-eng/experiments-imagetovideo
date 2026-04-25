FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv git ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt /workspace/requirements.txt
RUN python3 -m pip install --upgrade pip && pip3 install -r /workspace/requirements.txt

COPY app /workspace/app
COPY scripts /workspace/scripts

RUN chmod +x /workspace/scripts/*.sh

EXPOSE 8000
CMD ["/workspace/scripts/start.sh"]
