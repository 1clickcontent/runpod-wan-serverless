FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_INPUT=1
ENV PIP_PREFER_BINARY=1

# ----------------------------------------------------
# Install Python 3.12 + pip + system dependencies
# ----------------------------------------------------
# Install Python, git and other necessary tools
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    git \
    wget \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    && ln -sf /usr/bin/python3.12 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip

# Clean up to reduce image size
RUN apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Upgrade pip to latest
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# ----------------------------------------------------
# Clone ComfyUI repo
# ----------------------------------------------------
ARG COMFYUI_VERSION=latest
WORKDIR /comfyui

RUN if [ "${COMFYUI_VERSION}" = "latest" ]; then \
        git clone https://github.com/comfyanonymous/ComfyUI.git . ; \
    else \
        git clone --branch "${COMFYUI_VERSION}" --single-branch https://github.com/comfyanonymous/ComfyUI.git . ; \
    fi

# ----------------------------------------------------
# Install ComfyUI dependencies
# ----------------------------------------------------
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------------------------------
# Runtime packages for serverless
# ----------------------------------------------------
RUN pip install --no-cache-dir runpod requests websocket-client

# ----------------------------------------------------
# Extra paths + scripts
# ----------------------------------------------------
ADD src/extra_model_paths.yaml ./extra_model_paths.yaml
ADD serverless.py test_input.json .

COPY scripts/comfy-node-install.sh /usr/local/bin/comfy-node-install
RUN chmod +x /usr/local/bin/comfy-node-install

RUN mkdir -p models/checkpoints models/vae models/unet models/clip

# ----------------------------------------------------
# RunPod entrypoint
# ----------------------------------------------------
CMD ["python", "serverless.py"]