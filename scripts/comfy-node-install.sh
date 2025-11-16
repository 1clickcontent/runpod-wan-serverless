#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -e

CUSTOM_NODES_DIR="/comfyui/custom_nodes"

mkdir -p $CUSTOM_NODES_DIR

echo "Cloning ComfyUI-WanVideoWrapper..."
git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git "$CUSTOM_NODES_DIR/ComfyUI-WanVideoWrapper"
pip install --no-cache-dir -r "$CUSTOM_NODES_DIR/ComfyUI-WanVideoWrapper/requirements.txt"

echo "Cloning comfyui_controlnet_aux..."
git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git "$CUSTOM_NODES_DIR/comfyui_controlnet_aux"
pip install --no-cache-dir -r "$CUSTOM_NODES_DIR/comfyui_controlnet_aux/requirements.txt"

echo "Cloning ComfyUI-VideoHelperSuite..."
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git "$CUSTOM_NODES_DIR/ComfyUI-VideoHelperSuite"
pip install --no-cache-dir -r "$CUSTOM_NODES_DIR/ComfyUI-VideoHelperSuite/requirements.txt"

echo "Cloning ComfyUI-segment-anything-2..."
git clone https://github.com/kijai/ComfyUI-segment-anything-2.git "$CUSTOM_NODES_DIR/ComfyUI-segment-anything-2"

echo "Cloning ComfyUI-Frame-Interpolation..."
git clone https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git "$CUSTOM_NODES_DIR/ComfyUI-Frame-Interpolation"
pip install --no-cache-dir -r "$CUSTOM_NODES_DIR/ComfyUI-Frame-Interpolation/requirements-no-cupy.txt"

echo "Cloning comfyui-tensorops..."
git clone https://github.com/un-seen/comfyui-tensorops.git "$CUSTOM_NODES_DIR/comfyui-tensorops"
pip install --no-cache-dir -r "$CUSTOM_NODES_DIR/comfyui-tensorops/requirements.txt"

echo "Cloning ComfyUI-WanAnimatePreprocess..."
git clone https://github.com/kijai/ComfyUI-WanAnimatePreprocess.git "$CUSTOM_NODES_DIR/ComfyUI-WanAnimatePreprocess"
pip install --no-cache-dir -r "$CUSTOM_NODES_DIR/ComfyUI-WanAnimatePreprocess/requirements.txt"

echo "Cloning ComfyUI-KJNodes..."
git clone https://github.com/kijai/ComfyUI-KJNodes.git "$CUSTOM_NODES_DIR/ComfyUI-KJNodes"
pip install --no-cache-dir -r "$CUSTOM_NODES_DIR/ComfyUI-KJNodes/requirements.txt"

echo "Cloning rgthree-comfy..."
git clone https://github.com/rgthree/rgthree-comfy.git "$CUSTOM_NODES_DIR/rgthree-comfy"
pip install --no-cache-dir -r "$CUSTOM_NODES_DIR/rgthree-comfy/requirements.txt"