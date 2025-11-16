#!/usr/bin/env python3
"""
serverless.py
- starts ComfyUI main.py in background
- waits until /system_stats returns OK
- exposes RunPod serverless handler to receive jobs (via runpod.serverless.start)
- validates that workflow's nodes exist on ComfyUI before running
- sends workflow to /prompt and returns comfy response
"""

import json
import os
import requests
import subprocess
import time
import sys
import runpod

COMFY_HOST = os.environ.get("COMFY_HOST", "127.0.0.1")
COMFY_PORT = int(os.environ.get("COMFY_PORT", 8188))
COMFY_BASE = f"http://{COMFY_HOST}:{COMFY_PORT}"
BOOT_TIMEOUT = int(os.environ.get("COMFY_BOOT_WAIT", 180))  # seconds

def start_comfy():
    print("[serverless] Launching ComfyUI (background)...")
    cmd = [
        sys.executable,
        "main.py",
        "--listen", "0.0.0.0",
        "--output-directory", "/runpod-volume/serverless-output"
        "--port", str(COMFY_PORT),
        "--disable-auto-launch"
    ]
    # start in background
    subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
    print("[serverless] ComfyUI launched (pid).")

def wait_for_comfy(timeout=BOOT_TIMEOUT):
    print(f"[serverless] Waiting for ComfyUI at {COMFY_BASE}/system_stats (timeout {timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{COMFY_BASE}/system_stats", timeout=3)
            if r.status_code == 200:
                print("[serverless] ComfyUI is ready.")
                return True
        except Exception as e:
            pass
        time.sleep(1)
    print("[serverless] TIMEOUT waiting for ComfyUI.")
    return False

def comfy_list_nodes():
    try:
        r = requests.get(f"{COMFY_BASE}/nodes", timeout=5)
        if r.ok:
            return r.json()
    except Exception as e:
        print("[serverless] nodes list error:", e)
    return []

def extract_node_class_types(workflow):
    class_set = set()
    if not workflow:
        return class_set
    if isinstance(workflow, dict):
        nodes = workflow.get("nodes") or workflow.get("nodes_info") or workflow.get("graph") or workflow.get("node_list")
        if isinstance(nodes, list):
            for n in nodes:
                t = n.get("class_type") or n.get("type") or n.get("class")
                if isinstance(t, str):
                    class_set.add(t)
    return class_set

def check_nodes_exist(required_classes):
    available = comfy_list_nodes()
    available_classes = set()
    for a in available:
        name = a.get("type") or a.get("class_type") or a.get("class")
        if isinstance(name, str):
            available_classes.add(name)
    missing = [c for c in required_classes if c not in available_classes]
    return missing

def run_workflow_on_comfy(workflow):
    # Try /prompt then /run
    payload = {"prompt": workflow}
    endpoints = ["/prompt", "/run"]
    for ep in endpoints:
        try:
            r = requests.post(f"{COMFY_BASE}{ep}", json=payload, timeout=3600)
            try:
                return r.status_code, r.json()
            except:
                return r.status_code, {"raw": r.text}
        except Exception as e:
            print(f"[serverless] send to {ep} failed:", e)
    raise RuntimeError("All Comfy endpoints failed")

def handler(job):
    print("[serverless] Received job:", job.get("id"))
    input_data = job.get("input") or {}
    workflow = input_data.get("workflow")
    if not workflow:
        return {"ok": False, "error": "No workflow provided in input"}

    required = extract_node_class_types(workflow)
    print("[serverless] Required node classes:", required)

    missing = check_nodes_exist(required)
    if missing:
        return {"ok": False, "error": "Missing required nodes on this worker", "missing": missing}

    # send to comfy
    print("[serverless] Sending workflow to ComfyUI...")
    status, body = run_workflow_on_comfy(workflow)
    print("[serverless] Comfy responded:", status)
    return {"ok": True, "status": status, "body": body}

if __name__ == "__main__":
    start_comfy()
    ok = wait_for_comfy()
    if not ok:
        print("[serverless] ComfyUI failed to start - exiting")
        sys.exit(1)
    print("[serverless] Starting RunPod serverless handler ...")
    runpod.serverless.start({"handler": handler})
