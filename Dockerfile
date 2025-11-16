FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04 AS basee

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_INPUT=1
ENV PIP_PREFER_BINARY=1

# Install Python + pip + deps
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    git \
    wget \
    ffmpeg \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip inside venv
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Clone ComfyUI
ARG COMFYUI_VERSION=latest
WORKDIR /comfyui

RUN if [ "${COMFYUI_VERSION}" = "latest" ]; then \
        git clone https://github.com/comfyanonymous/ComfyUI.git . ; \
    else \
        git clone --branch "${COMFYUI_VERSION}" --single-branch https://github.com/comfyanonymous/ComfyUI.git . ; \
    fi

# Install ComfyUI requirements
RUN pip install --no-cache-dir -r requirements.txt

# Serverless deps
RUN pip install --no-cache-dir runpod requests websocket-client

ADD src/extra_model_paths.yaml ./extra_model_paths.yaml
ADD serverless.py test_input.json .

COPY scripts/comfy-node-install.sh /usr/local/bin/comfy-node-install
RUN chmod +x /usr/local/bin/comfy-node-install

RUN mkdir -p models/checkpoints models/vae models/unet models/clip /runpod-volume/serverless-output

# ---- Run custom node installer ----
# RUN comfy-node-install

CMD ["python", "serverless.py"]