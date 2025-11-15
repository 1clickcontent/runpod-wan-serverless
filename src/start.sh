#!/usr/bin/env bash

# Use libtcmalloc for better memory management
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"

echo "worker-comfyui: Starting ComfyUI"

# Default log level
: "${COMFY_LOG_LEVEL:=DEBUG}"

# Run ComfyUI API in foreground if serving locally, otherwise run main in foreground
if [ "$SERVE_API_LOCALLY" == "true" ]; then
    echo "worker-comfyui: Serving ComfyUI API locally"
    exec python -u /comfyui/main.py --disable-auto-launch --disable-metadata --listen \
        --verbose "${COMFY_LOG_LEVEL}" --log-stdout
else
    echo "worker-comfyui: Starting handler for RunPod"
    exec python -u /handler.py
fi