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

proc = None
proc_lock = Lock()

# Polling interval and max wait time for long workflows
COMFY_POLLING_INTERVAL_MS = 5000        # check every 5 seconds
COMFY_MAX_WAIT_SECONDS = 20 * 60        # 20 minutes

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
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1
    )
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

def queue_comfyui_deploy(workflow):
    try:
        # Only parse JSON if it's a string
        if isinstance(workflow, str):
            try:
                workflow = json.loads(workflow)
            except:
                pass  # Already a dict or invalid, leave it

        # Wrap workflow if necessary
        if "prompt" not in workflow:
            workflow = {"prompt": workflow}

        req = requests.post(
            f"{COMFY_BASE}/prompt",
            json=workflow
        )
        return req.json()

    except Exception as e:
        return {"status": "error", "message": f"Failed to queue workflow: {str(e)}"}

def check_status(prompt_id):
    try:
        req = requests.get(f"{COMFY_BASE}/history/{prompt_id}")
        return req.json()
    except Exception as e:
        return {"status": "error", "message": f"Status check failed: {str(e)}"}

# ------------------ HANDLER ------------------
def handler(job):
    job_input = job.get("input")
    if not job_input:
        return {"error": "No input provided"}

    workflow = job_input.get("workflow")
    if not workflow:
        return {"error": "No workflow provided"}

    # Ensure workflow is a dict
    if isinstance(workflow, str):
        try:
            workflow = json.loads(workflow)
        except Exception as e:
            return {"status": "error", "message": f"Invalid JSON workflow: {str(e)}"}

    # Queue the workflow
    queued = queue_comfyui_deploy(workflow)
    prompt_id = queued.get("prompt_id")

    if not prompt_id:
        print(f"[serverless] Failed to queue workflow: {queued}")
        return {"status": "error", "response": queued, "refresh_worker": REFRESH_WORKER}

    # Poll for completion (up to 20 minutes)
    deadline = time.time() + COMFY_MAX_WAIT_SECONDS
    print(f"[serverless] Waiting up to 20 minutes for workflow result...")

    while time.time() < deadline:
        try:
            status_result = check_status(prompt_id)
            print(f"[serverless] Status check result: {json.dumps(status_result)}")  # <-- log the full result

            status = str(status_result.get("status", "")).lower()

            if status in ["success", "failed", "completed"]:
                print(f"[serverless] Workflow completed with status: {status}")
                return {
                    "status": status,
                    "prompt_id": prompt_id,
                    "response": status_result,
                    "refresh_worker": REFRESH_WORKER
                }

        except Exception as e:
            print(f"[ERROR] Checking status failed: {e}")

        time.sleep(COMFY_POLLING_INTERVAL_MS / 1000)

    # Timeout fallback
    return {
        "status": "timeout",
        "prompt_id": prompt_id,
        "message": "Workflow exceeded 20 minute limit",
        "refresh_worker": REFRESH_WORKER
    }

# ------------------ MAIN ------------------
if __name__ == "__main__":
    start_comfy()
    if not wait_for_comfy():
        sys.exit(1)
    runpod.serverless.start({"handler": handler})
