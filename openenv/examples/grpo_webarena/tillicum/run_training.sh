#!/bin/bash
# =============================================================================
# Run WebArena GRPO Training (TorchForge)
# =============================================================================
#
# This script runs the GRPO training using TorchForge. The OpenEnv BrowserGym
# server must already be running (use start_server.sh in another tmux pane).
#
# Usage:
#   ./run_training.sh                    # Default config
#   ./run_training.sh --steps 100        # Override steps
#   ./run_training.sh --config my.yaml   # Custom config
#
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# training -> srun_workflow -> sbatch -> grpo_webarena -> examples -> OpenEnv
OPENENV_ROOT="$(realpath "$SCRIPT_DIR/../../../../..")"

# Environment setup
# Include src, root, envs, and training directories
export PYTHONPATH="$OPENENV_ROOT/src:$OPENENV_ROOT:$OPENENV_ROOT/envs:$SCRIPT_DIR:$PYTHONPATH"

# Cache directories (important for Tillicum)
export HF_HOME="${HF_HOME:-/gpfs/scrubbed/$USER/.cache/huggingface}"
export TORCH_HOME="${TORCH_HOME:-/gpfs/scrubbed/$USER/.cache/torch}"
export TRANSFORMERS_CACHE="$HF_HOME"

# NCCL settings for multi-GPU
export NCCL_DEBUG=INFO
export NCCL_CUMEM_ENABLE=0

# Create cache dirs
mkdir -p "$HF_HOME" "$TORCH_HOME"

echo "============================================"
echo "WebArena GRPO Training (TorchForge)"
echo "============================================"
echo "OpenEnv Root: $OPENENV_ROOT"
echo "Training Dir: $SCRIPT_DIR"
echo "HF_HOME: $HF_HOME"
echo "============================================"
echo ""

# Check if server is running
if ! curl -s http://localhost:8005/health > /dev/null 2>&1; then
    echo "WARNING: OpenEnv server not responding at localhost:8005"
    echo "Make sure to run ./start_server.sh in another tmux pane first!"
    echo ""
fi

# Run training
cd "$SCRIPT_DIR"
python webarena_main.py "$@"
