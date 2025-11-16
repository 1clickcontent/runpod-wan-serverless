#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -e

CUSTOM_NODES_DIR=" /comfyui/custom_nodes"

mkdir -p $CUSTOM_NODES_DIR

echo "Cloning ComfyUI-WanVideoWrapper..."
git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git "$CUSTOM_NODES_DIR/ComfyUI-WanVideoWrapper"
pip install -r "$CUSTOM_NODES_DIR/ComfyUI-WanVideoWrapper/requirements.txt"

echo "Cloning comfyui_controlnet_aux..."
git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git "$CUSTOM_NODES_DIR/comfyui_controlnet_aux"
pip install -r "$CUSTOM_NODES_DIR/comfyui_controlnet_aux/requirements.txt"

echo "Cloning ComfyUI-VideoHelperSuite..."
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git "$CUSTOM_NODES_DIR/ComfyUI-VideoHelperSuite"
pip install -r "$CUSTOM_NODES_DIR/ComfyUI-VideoHelperSuite/requirements.txt"

echo "Cloning ComfyUI-segment-anything-2..."
git clone https://github.com/kijai/ComfyUI-segment-anything-2.git "$CUSTOM_NODES_DIR/ComfyUI-segment-anything-2"

echo "Cloning ComfyUI-Frame-Interpolation..."
git clone https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git "$CUSTOM_NODES_DIR/ComfyUI-Frame-Interpolation"
pip install -r "$CUSTOM_NODES_DIR/ComfyUI-Frame-Interpolation/requirements-with-cupy.txt"