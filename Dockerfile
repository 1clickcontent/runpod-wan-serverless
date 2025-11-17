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

ADD src/extra_model_paths.yaml ./extra_model_paths.yaml
ADD serverless.py test_input.json .

# Create all necessary model directories that match the extra_model_paths.yaml structure
RUN mkdir -p /runpod-volume/models/checkpoints \
    /runpod-volume/models/vae \
    /runpod-volume/models/unet \
    /runpod-volume/models/clip \
    /runpod-volume/models/diffusion_models \
    /runpod-volume/models/detection \
    /runpod-volume/models/clip_vision \
    /runpod-volume/models/configs \
    /runpod-volume/models/controlnet \
    /runpod-volume/models/embeddings \
    /runpod-volume/models/loras \
    /runpod-volume/models/upscale_models \
    /runpod-volume/models/sam2 \
    /runpod-volume/models/text_encoders \
    /runpod-volume/serverless-input \
    /runpod-volume/serverless-output \

# ---- Run custom node installer ----
ADD scripts/comfy-node-install.sh ./comfy-node-install.sh
RUN chmod +x comfy-node-install.sh && ./comfy-node-install.sh

CMD ["python", "serverless.py"]