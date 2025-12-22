#!/usr/bin/env python3
"""
Download Llama-3.1-8B-Instruct to a local directory for TorchTitan.

TorchTitan requires local paths for checkpoint loading (not hf:// URLs).
This script downloads the model to /scratch/models/ which is accessible
in the container.

Usage (inside container):
    python download_model.py
"""

import os
from huggingface_hub import snapshot_download

MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
LOCAL_DIR = "/scratch/models/meta-llama/Llama-3.1-8B-Instruct"

def main():
    print(f"Downloading {MODEL_ID} to {LOCAL_DIR}...")

    # Create parent directory
    os.makedirs(os.path.dirname(LOCAL_DIR), exist_ok=True)

    # Download with snapshot_download (uses same auth as transformers)
    path = snapshot_download(
        repo_id=MODEL_ID,
        local_dir=LOCAL_DIR,
        local_dir_use_symlinks=False,  # Copy files directly, no symlinks
    )

    print(f"\nModel downloaded to: {path}")
    print(f"\nUpdate your config to use:")
    print(f'  model_path: "{LOCAL_DIR}"')
    print(f"\nVerifying files exist:")

    for f in os.listdir(path):
        print(f"  - {f}")

    return path

if __name__ == "__main__":
    main()
