#!/usr/bin/env python3
"""
Improved serverless.py for RunPod + ComfyUI
- Starts ComfyUI with real-time logs
- Detects startup failures quickly
- Returns clear error messages
"""

import json
import os
import requests
import subprocess
import time
import sys
import runpod
from threading import Thread, Lock

COMFY_HOST = os.environ.get("COMFY_HOST", "127.0.0.1")
COMFY_PORT = int(os.environ.get("COMFY_PORT", 8188))
COMFY_BASE = f"http://{COMFY_HOST}:{COMFY_PORT}"
BOOT_TIMEOUT = int(os.environ.get("COMFY_BOOT_WAIT", 180))

proc = None        # global ComfyUI process
proc_lock = Lock() # for thread-safe reading

# -------------------------------------------------------------------
# Utils
# -------------------------------------------------------------------

def stream_logs(pipe, name):
    """Stream ComfyUI logs into container output."""
    for line in iter(pipe.readline, b''):
        print(f"[ComfyUI:{name}] {line.decode().rstrip()}", flush=True)
    pipe.close()

# -------------------------------------------------------------------
# Start ComfyUI
# -------------------------------------------------------------------

def start_comfy():
    global proc

    main_path = os.path.abspath("main.py")
    print(f"[serverless] Using Python: {sys.executable}")
    print(f"[serverless] Expected ComfyUI main.py at: {main_path}")

    if not os.path.exists(main_path):
        print("[ERROR] main.py not found! ComfyUI directory not correct!")
        sys.exit(1)

    cmd = [
        sys.executable, main_path, 
        "--port", str(COMFY_PORT), 
        "--listen", COMFY_HOST,
        "--output-directory", "/runpod-volume/serverless-output",
        "--disable-auto-launch"
    ]

    print("[serverless] Launching ComfyUI...")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1
    )

    # Start log threads
    Thread(target=stream_logs, args=(proc.stdout, "stdout"), daemon=True).start()
    Thread(target=stream_logs, args=(proc.stderr, "stderr"), daemon=True).start()

    print(f"[serverless] ComfyUI started with PID {proc.pid}")

# -------------------------------------------------------------------
# Wait for ComfyUI
# -------------------------------------------------------------------

def wait_for_comfy(timeout=BOOT_TIMEOUT):
    print(f"[serverless] Waiting for ComfyUI @ {COMFY_BASE}/system_stats (max {timeout}s)...")

    deadline = time.time() + timeout
    while time.time() < deadline:

        # Detect crash early
        if proc.poll() is not None:
            print("[ERROR] ComfyUI process exited prematurely.")
            return False

        try:
            r = requests.get(f"{COMFY_BASE}/system_stats", timeout=3)
            if r.status_code == 200:
                print("[serverless] ComfyUI is READY.")
                return True
        except:
            pass

        time.sleep(1)

    print("[ERROR] ComfyUI did NOT start before timeout.")
    return False

# -------------------------------------------------------------------
# Workflow helpers
# -------------------------------------------------------------------

def comfy_list_nodes():
    try:
        r = requests.get(f"{COMFY_BASE}/nodes", timeout=5)
        if r.ok:
            return r.json()
    except Exception as e:
        print("[serverless] Node list error:", e)
    return []

def extract_node_class_types(workflow):
    class_set = set()
    if not workflow:
        return class_set

    nodes = (
        workflow.get("nodes") or
        workflow.get("nodes_info") or
        workflow.get("graph") or
        workflow.get("node_list")
    )

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

    return [c for c in required_classes if c not in available_classes]

# -------------------------------------------------------------------
# Run workflow
# -------------------------------------------------------------------

def run_workflow_on_comfy(workflow):
    payload = {"prompt": workflow}
    endpoints = ["/prompt", "/run"]

    for ep in endpoints:
        try:
            print(f"[serverless] Sending workflow → {ep}")
            r = requests.post(f"{COMFY_BASE}{ep}", json=payload, timeout=3600)

            try:
                return r.status_code, r.json()
            except:
                return r.status_code, {"raw": r.text}

        except Exception as e:
            print(f"[serverless] Error sending to {ep}: {e}")

    raise RuntimeError("All ComfyUI endpoints failed")

# -------------------------------------------------------------------
# RunPod handler
# -------------------------------------------------------------------

def handler(job):
    print("[serverless] Received job:", job.get("id"))

    input_data = job.get("input") or {}
    workflow = input_data.get("workflow")

    if not workflow:
        return {"ok": False, "error": "No workflow provided"}

    required = extract_node_class_types(workflow)
    print("[serverless] Workflow needs:", required)

    missing = check_nodes_exist(required)
    if missing:
        return {"ok": False, "error": "Missing nodes", "missing": missing}

    status, body = run_workflow_on_comfy(workflow)
    print("[serverless] Job completed, status:", status)

    return {"ok": True, "status": status, "body": body}

# -------------------------------------------------------------------
# Main entry
# -------------------------------------------------------------------

if __name__ == "__main__":
    start_comfy()

    if not wait_for_comfy():
        print("[serverless] FATAL: ComfyUI failed to start.")
        sys.exit(1)

    print("[serverless] Starting RunPod handler...")
    runpod.serverless.start({"handler": handler})
