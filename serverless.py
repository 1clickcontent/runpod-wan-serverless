#!/usr/bin/env python3
"""
RunPod Serverless WAN 2.2 LoRA Training Handler (Low Noise Only)
Uses Musubi training for WAN 2.2 models
"""
import os
import sys
import shutil
import subprocess
import tempfile
import requests
from pathlib import Path
from typing import Dict, Any, List
import runpod


# ------------------ CONFIG ------------------
WORKING_DIR = os.environ.get("WORKING_DIR", "/workspace")
NETWORK_VOLUME = os.environ.get("NETWORK_VOLUME", "/runpod-volume")
OUTPUT_DIR = os.path.join(NETWORK_VOLUME, "wan22_lora_outputs")
WAN22_TRAINING_DIR = os.path.join(NETWORK_VOLUME, "wan2.2_lora_training")
JOY_CAPTION_SCRIPT = os.path.join(WORKING_DIR, "joy_caption_batch.py")

# Set Hugging Face cache to network volume to save container disk space
HF_CACHE_DIR = os.path.join(NETWORK_VOLUME, "huggingface_cache")
os.environ["HF_HOME"] = HF_CACHE_DIR
os.environ["TRANSFORMERS_CACHE"] = HF_CACHE_DIR
os.environ["HF_HUB_CACHE"] = HF_CACHE_DIR

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HF_CACHE_DIR, exist_ok=True)


# ------------------ UTILS ------------------
def log(message: str):
    """Log message with timestamp"""
    print(f"[WAN22-LoRA] {message}", flush=True)


def download_images(image_urls: List[str], target_dir: Path) -> int:
    """
    Download images from URLs to target directory

    Args:
        image_urls: List of image URLs to download
        target_dir: Directory to save images

    Returns:
        Number of successfully downloaded images
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    success_count = 0

    for idx, url in enumerate(image_urls):
        try:
            log(f"Downloading image {idx + 1}/{len(image_urls)}: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Determine file extension
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'webp' in content_type:
                ext = '.webp'
            else:
                ext = Path(url).suffix or '.jpg'

            # Save image
            image_path = target_dir / f"image_{idx:05d}{ext}"
            with open(image_path, 'wb') as f:
                f.write(response.content)

            success_count += 1
            log(f"Saved: {image_path.name}")

        except Exception as e:
            log(f"Failed to download {url}: {e}")
            continue

    return success_count


def run_joy_caption(image_dir: Path, trigger_word: str) -> bool:
    """
    Run JoyCaption on images in directory

    Args:
        image_dir: Directory containing images
        trigger_word: Trigger word to prepend to captions

    Returns:
        True if captioning succeeded, False otherwise
    """
    try:
        log(f"Starting JoyCaption on {image_dir} with trigger word: {trigger_word}")

        cmd = [
            sys.executable,
            JOY_CAPTION_SCRIPT,
            str(image_dir),
            "--trigger-word", trigger_word
        ]

        log(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        log("JoyCaption STDOUT:")
        log(result.stdout)

        if result.stderr:
            log("JoyCaption STDERR:")
            log(result.stderr)

        log("JoyCaption completed successfully")
        return True

    except subprocess.CalledProcessError as e:
        log(f"JoyCaption failed with exit code {e.returncode}")
        log(f"STDOUT: {e.stdout}")
        log(f"STDERR: {e.stderr}")
        return False
    except Exception as e:
        log(f"JoyCaption error: {e}")
        return False


def create_musubi_config(
    dataset_dir: Path,
    lora_rank: int = 16,
    learning_rate: float = 3e-4,
    max_epochs: int = 100,
    save_every: int = 20,
    batch_size: int = 1,
    num_repeats: int = 1,
    resolution: List[int] = None,
    dataset_type: str = "image",
    seed_low: int = 42,
    lora_name: str = "WAN22_LowNoise_LoRA"
) -> Path:
    """
    Create Musubi configuration file for WAN 2.2 training

    Args:
        dataset_dir: Path to dataset directory
        lora_rank: LoRA rank
        learning_rate: Learning rate
        max_epochs: Maximum epochs
        save_every: Save checkpoint every N epochs
        batch_size: Batch size
        num_repeats: Number of repeats
        resolution: Resolution [width, height]
        dataset_type: 'image' or 'video'
        seed_low: Random seed for low noise model
        lora_name: Name for the LoRA

    Returns:
        Path to created config file
    """
    if resolution is None:
        resolution = [1024, 1024]

    resolution_str = ", ".join(map(str, resolution))

    config_content = f"""# WAN 2.2 Musubi Config - Auto-generated
# LoRA rank drives both network_dim and network_alpha
LORA_RANK={lora_rank}

# training schedule
MAX_EPOCHS={max_epochs}
SAVE_EVERY={save_every}

# seed for low noise model
SEED_LOW={seed_low}

# optimizer
LEARNING_RATE={learning_rate}

# dataset type
DATASET_TYPE={dataset_type}

# resolution list for bucketed training
RESOLUTION_LIST="{resolution_str}"

# dataset path
DATASET_DIR="{dataset_dir}"

# LoRA Name (low noise only)
TITLE_LOW="{lora_name}"

# ---- IMAGE options ----
BATCH_SIZE={batch_size}
NUM_REPEATS={num_repeats}

# Optional caption extension
CAPTION_EXT=".txt"
"""

    config_path = Path(tempfile.mktemp(suffix="_musubi_config.sh"))
    with open(config_path, 'w') as f:
        f.write(config_content)

    log(f"Created Musubi config at {config_path}")
    return config_path


def run_wan22_training(
    config_path: Path,
    dataset_dir: Path
) -> Dict[str, Any]:
    """
    Run WAN 2.2 LoRA training with Musubi (low noise only)

    Args:
        config_path: Path to Musubi config file
        dataset_dir: Path to dataset directory

    Returns:
        Dict with training results
    """
    try:
        log("Starting WAN 2.2 LoRA training (Low Noise)...")

        # Set environment variables
        env = os.environ.copy()
        env.update({
            "CONFIG_FILE": str(config_path),
            "NETWORK_VOLUME": NETWORK_VOLUME,
            "WORKDIR": WAN22_TRAINING_DIR,
            "DATASET_DIR": str(dataset_dir),
            "TRAIN_MODE": "low"  # Always train low-noise model in serverless
        })

        # Path to the training script
        training_script = os.path.join(WAN22_TRAINING_DIR, "setup_and_train_musubi.sh")

        if not os.path.exists(training_script):
            return {
                "success": False,
                "error": f"Training script not found: {training_script}"
            }

        cmd = ["bash", training_script]

        log(f"Running command: {' '.join(cmd)}")
        log(f"Config file: {config_path}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=WAN22_TRAINING_DIR
        )

        # Log output (truncate if too long)
        log("Training STDOUT:")
        stdout_lines = result.stdout.split('\n')
        if len(stdout_lines) > 100:
            log("...(showing last 100 lines)...")
            log('\n'.join(stdout_lines[-100:]))
        else:
            log(result.stdout)

        if result.stderr:
            log("Training STDERR:")
            stderr_lines = result.stderr.split('\n')
            if len(stderr_lines) > 50:
                log("...(showing last 50 lines)...")
                log('\n'.join(stderr_lines[-50:]))
            else:
                log(result.stderr)

        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Training failed with exit code {result.returncode}",
                "stderr": '\n'.join(stderr_lines[-50:]) if len(stderr_lines) > 50 else result.stderr
            }

        log("Training completed successfully")
        return {"success": True}

    except Exception as e:
        log(f"Training error: {e}")
        return {"success": False, "error": str(e)}


def find_latest_lora_low(output_base_dir: Path) -> Path:
    """
    Find the latest low noise LoRA output directory

    Args:
        output_base_dir: Base output directory

    Returns:
        Path to latest low noise LoRA directory
    """
    low_dir = output_base_dir / "low"

    if not low_dir.exists():
        raise ValueError(f"Low noise output directory not found: {low_dir}")

    # Find the most recent .safetensors file
    lora_files = list(low_dir.glob("*.safetensors"))

    if not lora_files:
        raise ValueError("No LoRA files found in output directory")

    latest_lora = max(lora_files, key=lambda f: f.stat().st_mtime)

    return latest_lora.parent


# ------------------ HANDLER ------------------
def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main job handler for serverless WAN 2.2 LoRA training

    Expected input format:
    {
        "input": {
            "image_urls": ["url1", "url2", ...],
            "trigger_word": "mychar",
            "model_type": "wan22",
            "training_params": {
                "lora_rank": 16,
                "learning_rate": 0.0003,
                "max_epochs": 100,
                "save_every": 20,
                "batch_size": 1,
                "num_repeats": 1,
                "resolution": [1024, 1024],
                "dataset_type": "image",
                "seed_low": 42,
                "lora_name": "My WAN22 Low Noise LoRA"
            }
        }
    }

    Returns:
    {
        "status": "success" or "error",
        "lora_path": "/path/to/trained/lora",
        "message": "...",
        "error": "..." (if status is error)
    }
    """
    job_input = job.get("input", {})

    # Validate input
    if not job_input:
        return {"status": "error", "error": "No input provided"}

    image_urls = job_input.get("image_urls", [])
    if not image_urls:
        return {"status": "error", "error": "No image URLs provided"}

    trigger_word = job_input.get("trigger_word", "")
    if not trigger_word:
        return {"status": "error", "error": "No trigger word provided"}

    model_type = job_input.get("model_type", "wan22")
    if model_type != "wan22":
        return {"status": "error", "error": f"Invalid model_type: {model_type}. Must be 'wan22'"}

    # Get training parameters
    training_params = job_input.get("training_params", {})
    lora_rank = training_params.get("lora_rank", 16)
    lr = training_params.get("learning_rate", 3e-4)
    max_epochs = training_params.get("max_epochs", 100)
    save_every = training_params.get("save_every", 20)
    batch_size = training_params.get("batch_size", 1)
    num_repeats = training_params.get("num_repeats", 1)
    resolution = training_params.get("resolution", [1024, 1024])
    dataset_type = training_params.get("dataset_type", "image")
    seed_low = training_params.get("seed_low", 42)
    lora_name = training_params.get("lora_name", f"{trigger_word}_wan22_low")

    # Create dataset directory on network volume (persistent)
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    datasets_base = Path(NETWORK_VOLUME) / "datasets"
    datasets_base.mkdir(parents=True, exist_ok=True)

    dataset_dir = datasets_base / f"{trigger_word}_{timestamp}"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    # Create temporary directory for config files only
    temp_dir = Path(tempfile.mkdtemp(prefix="wan22_config_"))

    try:
        # Step 1: Download images to network volume
        log(f"Downloading {len(image_urls)} images...")
        log(f"Dataset directory: {dataset_dir}")
        downloaded = download_images(image_urls, dataset_dir)

        if downloaded == 0:
            return {
                "status": "error",
                "error": "Failed to download any images"
            }

        log(f"Successfully downloaded {downloaded}/{len(image_urls)} images")
        log(f"Dataset saved to network volume: {dataset_dir}")

        # Step 2: Run JoyCaption
        caption_success = run_joy_caption(dataset_dir, trigger_word)
        if not caption_success:
            return {
                "status": "error",
                "error": "JoyCaption failed"
            }

        # Step 3: Create Musubi config
        config_path = create_musubi_config(
            dataset_dir=dataset_dir,
            lora_rank=lora_rank,
            learning_rate=lr,
            max_epochs=max_epochs,
            save_every=save_every,
            batch_size=batch_size,
            num_repeats=num_repeats,
            resolution=resolution,
            dataset_type=dataset_type,
            seed_low=seed_low,
            lora_name=lora_name
        )

        # Step 4: Run training
        training_result = run_wan22_training(config_path, dataset_dir)

        if not training_result.get("success"):
            return {
                "status": "error",
                "error": training_result.get("error", "Unknown training error"),
                "details": training_result.get("stderr", "")
            }

        # Step 5: Find and copy the trained LoRA
        try:
            output_base = Path(WAN22_TRAINING_DIR) / "output"
            lora_dir = find_latest_lora_low(output_base)

            # Copy to permanent storage
            final_output_dir = Path(OUTPUT_DIR) / f"lora_{trigger_word}_wan22_low"
            if final_output_dir.exists():
                shutil.rmtree(final_output_dir)
            shutil.copytree(lora_dir, final_output_dir)

            log(f"LoRA saved to: {final_output_dir}")

            return {
                "status": "success",
                "lora_path": str(final_output_dir),
                "message": f"WAN 2.2 Low Noise LoRA training completed successfully for trigger word '{trigger_word}'",
                "model_type": "wan22_low_noise",
                "epochs": max_epochs,
                "rank": lora_rank,
                "trigger_word": trigger_word
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to locate or copy trained LoRA: {e}"
            }

    except Exception as e:
        log(f"Unexpected error: {e}")
        return {
            "status": "error",
            "error": f"Unexpected error: {e}"
        }

    finally:
        # Cleanup temporary config directory (dataset remains on network volume)
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                log(f"Cleaned up temporary config directory: {temp_dir}")
        except Exception as e:
            log(f"Failed to cleanup temp directory: {e}")

        log(f"Dataset preserved on network volume at: {dataset_dir}")


# ------------------ MAIN ------------------
if __name__ == "__main__":
    log("Starting RunPod Serverless WAN 2.2 LoRA Training Handler (Low Noise Only)")
    log(f"Working Directory: {WORKING_DIR}")
    log(f"Network Volume: {NETWORK_VOLUME}")
    log(f"Output Directory: {OUTPUT_DIR}")
    log(f"WAN 2.2 Training Directory: {WAN22_TRAINING_DIR}")

    runpod.serverless.start({"handler": handler})
