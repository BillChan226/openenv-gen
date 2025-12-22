#!/bin/bash

# =============================================================================
# WebArena Training Script (runs inside container)
# =============================================================================
# Main training script for WebArena GRPO training.
# This is called by the Slurm sbatch script or can be run manually.
#
# Usage:
#   ./sbatch/train_webarena.sh [config_file] [steps]
#
# Examples:
#   ./sbatch/train_webarena.sh webarena_miniwob.yaml 200
#   ./sbatch/train_webarena.sh webarena.yaml 500
# =============================================================================

set -e

# Configuration
CONFIG="${1:-webarena_miniwob.yaml}"
STEPS="${2:-200}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBARENA_DIR="${SCRIPT_DIR}/.."

# Environment setup
export LD_LIBRARY_PATH=$(python -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))"):$LD_LIBRARY_PATH
export NCCL_CUMEM_ENABLE=0
export PYTHONUNBUFFERED=1

echo "============================================"
echo "WebArena GRPO Training"
echo "============================================"
echo ""
echo "Config: $CONFIG"
echo "Steps: $STEPS"
echo "GPU Count: $(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)"
echo ""

# Check BrowserGym server
BROWSERGYM_URL="${BROWSERGYM_URL:-http://localhost:8005}"
echo "Checking BrowserGym server at $BROWSERGYM_URL..."

for i in {1..30}; do
    if curl -s "${BROWSERGYM_URL}/health" > /dev/null 2>&1; then
        echo "  Server is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "ERROR: BrowserGym server not responding at $BROWSERGYM_URL"
        echo "Please start the server first with: ./sbatch/start_browsergym_server.sh"
        exit 1
    fi
    echo "  Waiting for server... ($i/30)"
    sleep 2
done

echo ""

# Run training
cd $WEBARENA_DIR

echo "Starting training..."
echo ""

python webarena_main.py \
    --config "$CONFIG" \
    --steps "$STEPS"

echo ""
echo "============================================"
echo "Training Complete!"
echo "============================================"
