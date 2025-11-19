#!/usr/bin/env python3
import os
import sys
import time
import json
import requests
import subprocess
from threading import Thread, Lock
import runpod

COMFY_HOST = os.environ.get("COMFY_HOST", "127.0.0.1")
COMFY_PORT = int(os.environ.get("COMFY_PORT", 8188))
COMFY_BASE = f"http://{COMFY_HOST}:{COMFY_PORT}"
COMFY_OUTPUT_PATH = os.environ.get("COMFY_OUTPUT_PATH", "/runpod-volume/serverless-output")
COMFY_INPUT_PATH = os.environ.get("COMFY_INPUT_PATH", "/runpod-volume/serverless-input")
BOOT_TIMEOUT = int(os.environ.get("COMFY_BOOT_WAIT", 180))
REFRESH_WORKER = os.environ.get("REFRESH_WORKER", "false").lower() == "true"

proc = None
proc_lock = Lock()
COMFY_POLLING_INTERVAL_MS = 250
COMFY_POLLING_MAX_RETRIES = 500

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

def queue_prompt(workflow):
    """Implements /prompt"""
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = requests.post(f"{COMFY_BASE}/prompt", data=data, headers={"Content-Type": "application/json"})
    return req.json()

def queue_comfyui_deploy(workflow):
    """Implements /comfyui-deploy/run"""
    data = json.dumps(workflow).encode("utf-8")
    req = requests.post(f"{COMFY_BASE}/comfyui-deploy/run", data=data, headers={"Content-Type": "application/json"})
    return req.json()

def check_status(prompt_id):
    """Implements /comfyui-deploy/check-status"""
    req = requests.get(f"{COMFY_BASE}/comfyui-deploy/check-status?prompt_id={prompt_id}")
    return req.json()

# ------------------ HANDLER ------------------

def handler(job):
    job_input = job.get("input")
    if not job_input:
        return {"error": "No input provided"}

    endpoint = job_input.get("endpoint", "/prompt")  # default endpoint
    workflow = job_input.get("workflow")
    if not workflow:
        return {"error": "No workflow provided"}

    # Queue workflow depending on the endpoint
    if endpoint == "/prompt":
        queued = queue_prompt(workflow)
        return {"status": "queued", "response": queued}
    elif endpoint == "/comfyui-deploy/run":
        queued = queue_comfyui_deploy(workflow)
        prompt_id = queued.get("prompt_id")
        if not prompt_id:
            return {"status": "error", "response": queued}
        # Poll for completion
        retries = 0
        while retries < COMFY_POLLING_MAX_RETRIES:
            st = check_status(prompt_id)
            if st.get("status") in ["success", "failed"]:
                return {"status": st.get("status"), "prompt_id": prompt_id, "response": st}
            retries += 1
            time.sleep(COMFY_POLLING_INTERVAL_MS / 1000)
        return {"status": "error", "message": "Max retries reached"}
    elif endpoint == "/comfyui-deploy/check-status":
        prompt_id = job_input.get("prompt_id")
        if not prompt_id:
            return {"error": "prompt_id is required for check-status"}
        st = check_status(prompt_id)
        return {"status": st.get("status"), "prompt_id": prompt_id, "response": st}
    else:
        return {"error": f"Unknown endpoint: {endpoint}"}

# ------------------ MAIN ------------------

if __name__ == "__main__":
    start_comfy()
    if not wait_for_comfy():
        sys.exit(1)
    runpod.serverless.start({"handler": handler})
