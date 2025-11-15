ARG BASE_IMAGE=runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404
FROM ${BASE_IMAGE} AS base

ARG COMFYUI_VERSION=latest
ARG CUDA_VERSION_FOR_COMFY

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_PREFER_BINARY=1

# Install system tools (NOTE: includes git)
RUN apt-get update && apt-get install -y \
    git wget ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv
RUN wget -qO- https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

# Install comfy-cli into system Python
RUN uv pip install --system comfy-cli

# Install ComfyUI
RUN if [ -n "${CUDA_VERSION_FOR_COMFY}" ]; then \
      yes | comfy --workspace /comfyui install --version "${COMFYUI_VERSION}" --cuda-version "${CUDA_VERSION_FOR_COMFY}" --nvidia; \
    else \
      yes | comfy --workspace /comfyui install --version "${COMFYUI_VERSION}" --nvidia; \
    fi

WORKDIR /comfyui

ADD src/extra_model_paths.yaml ./

WORKDIR /

# Runtime dependencies
RUN uv pip install runpod requests websocket-client

ADD src/start.sh handler.py test_input.json .
RUN chmod +x /start.sh

COPY scripts/comfy-node-install.sh /usr/local/bin/comfy-node-install
RUN chmod +x /usr/local/bin/comfy-node-install

ENV PIP_NO_INPUT=1

CMD ["/start.sh"]

FROM base AS downloader
WORKDIR /comfyui
RUN mkdir -p models/checkpoints models/vae models/unet models/clip

FROM base AS final
COPY --from=downloader /comfyui/models /comfyui/models