# Base image
ARG BASE_IMAGE=runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04
FROM ${BASE_IMAGE} AS base

ARG COMFYUI_VERSION=latest

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_PREFER_BINARY=1
ENV PIP_NO_INPUT=1

# Install system tools (git, wget, ffmpeg, libraries)
RUN apt-get update && apt-get install -y \
        git wget ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Clone ComfyUI from GitHub directly
WORKDIR /comfyui
RUN if [ "${COMFYUI_VERSION}" = "latest" ]; then \
        git clone https://github.com/comfyanonymous/ComfyUI.git . ; \
    else \
        git clone --branch "${COMFYUI_VERSION}" --single-branch https://github.com/comfyanonymous/ComfyUI.git . ; \
    fi

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Runtime dependencies
RUN pip install --no-cache-dir runpod requests websocket-client

# Add extra model paths
ADD src/extra_model_paths.yaml ./extra_model_paths.yaml

# Add scripts and test input
ADD serverless.py test_input.json .

COPY scripts/comfy-node-install.sh /usr/local/bin/comfy-node-install
RUN chmod +x /usr/local/bin/comfy-node-install

RUN mkdir -p models/checkpoints models/vae models/unet models/clip

# Default command
CMD ["python", "serverless.py"]