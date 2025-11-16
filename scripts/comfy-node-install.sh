#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -e

CUSTOM_NODES_DIR=" /comfyui/custom_nodes"

mkdir -p $CUSTOM_NODES_DIR

if [ ! -d "$CUSTOM_NODES_DIR/ComfyUI-WanVideoWrapper" ]; then
  echo "Cloning ComfyUI-WanVideoWrapper..."
  git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git "$CUSTOM_NODES_DIR/ComfyUI-WanVideoWrapper"
  pip install -r "$CUSTOM_NODES_DIR/ComfyUI-WanVideoWrapper/requirements.txt"
fi