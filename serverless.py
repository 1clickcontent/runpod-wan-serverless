#!/usr/bin/env python3
import os
import sys
import time
import json
import requests
import subprocess
from threading import Thread, Lock
import runpod

# ------------------ CONFIG ------------------
COMFY_HOST = os.environ.get("COMFY_HOST", "127.0.0.1")
COMFY_PORT = int(os.environ.get("COMFY_PORT", 8188))
COMFY_BASE = f"http://{COMFY_HOST}:{COMFY_PORT}"
COMFY_OUTPUT_PATH = os.environ.get("COMFY_OUTPUT_PATH", "/runpod-volume/serverless-output")
COMFY_INPUT_PATH = os.environ.get("COMFY_INPUT_PATH", "/runpod-volume/serverless-input")
BOOT_TIMEOUT = int(os.environ.get("COMFY_BOOT_WAIT", 180))
REFRESH_WORKER = os.environ.get("REFRESH_WORKER", "false").lower() == "true"

COMFY_POLLING_INTERVAL_MS = 5000  # 5 seconds
COMFY_POLLING_MAX_RETRIES = 360   # ~30 minutes max wait

proc = None
proc_lock = Lock()

# ------------------ UTILS ------------------

def stream_logs(pipe, name):
    for line in iter(pipe.readline, b''):
        print(f"[ComfyUI:{name}] {line.decode().rstrip()}", flush=True)
    pipe.close()

def start_comfy():
    global proc
    main_path = "main.py"
    if not os.path.exists(main_path):
        print("[ERROR] main.py not found!")
        sys.exit(1)

    cmd = [
        sys.executable, main_path,
        "--port", str(COMFY_PORT),
        "--listen", COMFY_HOST,
        "--disable-auto-launch"
    ]

    if os.path.exists(COMFY_OUTPUT_PATH):
        cmd.extend(["--output-directory", COMFY_OUTPUT_PATH])
        print(f"[serverless] Using output: {COMFY_OUTPUT_PATH}")

    if os.path.exists(COMFY_INPUT_PATH):
        cmd.extend(["--input-directory", COMFY_INPUT_PATH])
        print(f"[serverless] Using input: {COMFY_INPUT_PATH}")

    print("[serverless] Launching ComfyUI...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1)
    Thread(target=stream_logs, args=(proc.stdout, "stdout"), daemon=True).start()
    Thread(target=stream_logs, args=(proc.stderr, "stderr"), daemon=True).start()

def wait_for_comfy(timeout=BOOT_TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            print("[ERROR] ComfyUI exited prematurely")
            return False
        try:
            r = requests.get(f"{COMFY_BASE}/system_stats", timeout=3)
            if r.status_code == 200:
                print("[serverless] ComfyUI is READY")
                return True
        except:
            pass
        time.sleep(1)
    print("[ERROR] ComfyUI did NOT start before timeout")
    return False

# ------------------ WORKFLOW ENDPOINTS ------------------

def queue_comfyui_deploy(workflow):
    """Implements /comfyui-deploy/run"""
    try:
        data = json.dumps(workflow).encode("utf-8")
        req = requests.post(f"{COMFY_BASE}/comfyui-deploy/run", data=data, headers={"Content-Type": "application/json"})
        return req.json()
    except Exception as e:
        return {"status": "error", "message": f"Failed to queue workflow: {str(e)}"}

def check_status(prompt_id):
    """Implements /comfyui-deploy/check-status"""
    try:
        req = requests.get(f"{COMFY_BASE}/comfyui-deploy/check-status?prompt_id={prompt_id}")
        return req.json()
    except Exception as e:
        return {"status": "error", "message": f"Failed to check status: {str(e)}"}

# ------------------ HANDLER ------------------

def handler(job):
    job_input = job.get("input")
    if not job_input:
        return {"error": "No input provided"}

    workflow = job_input.get("workflow")
    if not workflow:
        return {"error": "No workflow provided"}

    # Queue workflow
    queued = queue_comfyui_deploy(workflow)
    if queued.get("status") == "error" or not queued.get("prompt_id"):
        return {"status": "error", "response": queued}

    prompt_id = queued["prompt_id"]
    print(f"[serverless] Workflow queued with prompt_id: {prompt_id}")

    # Poll for completion
    retries = 0
    while retries < COMFY_POLLING_MAX_RETRIES:
        status_result = check_status(prompt_id)
        status = status_result.get("status", "").lower()
        if status in ["success", "failed", "completed"]:
            return {
                "status": status,
                "prompt_id": prompt_id,
                "response": status_result,
                "refresh_worker": REFRESH_WORKER
            }
        print(f"[serverless] Workflow in progress... retry {retries}")
        retries += 1
        time.sleep(COMFY_POLLING_INTERVAL_MS / 1000)

    return {
        "status": "error",
        "prompt_id": prompt_id,
        "message": "Max retries reached while waiting for workflow to complete",
        "refresh_worker": REFRESH_WORKER
    }

# ------------------ MAIN ------------------

if __name__ == "__main__":
    start_comfy()
    if not wait_for_comfy():
        sys.exit(1)
    runpod.serverless.start({"handler": handler})
