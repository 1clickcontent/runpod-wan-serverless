FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_INPUT=1
ENV PIP_PREFER_BINARY=1

# ----------------------------------------------------
# Install Python 3.12 + pip + system dependencies
# ----------------------------------------------------
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-distutils python3-venv \
    git wget curl ffmpeg \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Ensure python and pip point to Python 3.12
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

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