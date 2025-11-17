FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04 AS base

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
ARG COMFYUI_VERSION="v0.3.68"
WORKDIR /comfyui

RUN git clone --branch "${COMFYUI_VERSION}" --single-branch https://github.com/comfyanonymous/ComfyUI.git .

RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128 \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir runpod requests websocket-client

RUN mkdir -p /runpod-volume/models

WORKDIR /runpod-volume/models

RUN mkdir -p checkpoints vae unet clip diffusion_models detection clip_vision configs controlnet embeddings loras upscale_models sam2 text_encoders

WORKDIR /runpod-volume

RUN mkdir -p serverless-input serverless-output

WORKDIR /comfyui

ADD scripts/comfy-node-install.sh ./comfy-node-install.sh
# RUN chmod +x comfy-node-install.sh && ./comfy-node-install.sh

# ADD src/extra_model_paths.yaml ./extra_model_paths.yaml
ADD serverless.py test_input.json .

CMD ["python", "serverless.py"]