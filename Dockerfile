FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_INPUT=1
ENV PIP_PREFER_BINARY=1

# Install system deps
RUN apt-get update && apt-get install -y \
    python3.12 python3.12-venv python3-pip \
    git wget ffmpeg \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Python virtualenv
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# ────────────────────────────────────────────
# Install ComfyUI
# ────────────────────────────────────────────
ARG COMFYUI_VERSION="v0.3.68"

WORKDIR /comfyui
RUN git clone --branch "${COMFYUI_VERSION}" --single-branch \
    https://github.com/comfyanonymous/ComfyUI.git .

RUN pip install --no-cache-dir torch torchvision torchaudio \
        --index-url https://download.pytorch.org/whl/cu128 \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir runpod requests websocket-client

# ────────────────────────────────────────────
# Install Custom Nodes (Wan, SAM2, VHS, etc.)
# ────────────────────────────────────────────
WORKDIR /comfyui/custom_nodes

# Wan Video Wrapper
RUN git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git \
    && pip install --no-cache-dir -r ComfyUI-WanVideoWrapper/requirements.txt

# Controlnet AUX
RUN git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git \
    && pip install --no-cache-dir -r comfyui_controlnet_aux/requirements.txt

# Video Helper Suite (VHS)
RUN git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git \
    && pip install --no-cache-dir -r ComfyUI-VideoHelperSuite/requirements.txt

# SAM2
RUN git clone https://github.com/kijai/ComfyUI-segment-anything-2.git

# Frame Interpolation
RUN git clone https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git \
    && pip install --no-cache-dir -r ComfyUI-Frame-Interpolation/requirements-no-cupy.txt

# TensorOps
RUN git clone https://github.com/un-seen/comfyui-tensorops.git \
    && pip install --no-cache-dir -r comfyui-tensorops/requirements.txt

# WanAnimate Preprocess
RUN git clone https://github.com/kijai/ComfyUI-WanAnimatePreprocess.git \
    && pip install --no-cache-dir -r ComfyUI-WanAnimatePreprocess/requirements.txt

# KJ Nodes
RUN git clone https://github.com/kijai/ComfyUI-KJNodes.git \
    && pip install --no-cache-dir -r ComfyUI-KJNodes/requirements.txt

# ────────────────────────────────────────────
# Custom model path config (pointing to /runpod-volume)
# ────────────────────────────────────────────
WORKDIR /comfyui
ADD src/extra_model_paths.yaml ./extra_model_paths.yaml

# Serverless entrypoint + optional test
ADD serverless.py test_input.json .

# ────────────────────────────────────────────
# CMD for serverless
# ────────────────────────────────────────────
CMD ["python", "serverless.py"]