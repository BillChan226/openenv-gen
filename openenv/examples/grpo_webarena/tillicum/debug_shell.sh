#!/bin/bash

# =============================================================================
# WebArena Debug Shell
# =============================================================================
# Opens an interactive shell inside the Apptainer container with GPU access.
# Use this for debugging and development.
#
# Usage:
#   ./sbatch/debug_shell.sh
# =============================================================================

# Configuration - adjust these paths as needed
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/../../../.."  # OpenEnv root
OPENENV_EXAMPLES="${SCRIPT_DIR}/.."      # grpo_webarena directory
SCRATCH_DIR="/gpfs/scrubbed/${USER}"
CONTAINER_PATH="${SCRATCH_DIR}/containers/webarena_training.sif"

# Container image to pull if not exists
CONTAINER_IMAGE="docker://python:3.12-slim"  # Base image, we'll install deps

echo "============================================"
echo "WebArena Debug Shell"
echo "============================================"
echo ""
echo "Project Dir: $PROJECT_DIR"
echo "Scratch Dir: $SCRATCH_DIR"
echo "Container: $CONTAINER_PATH"
echo ""

# Create cache directories
mkdir -p $SCRATCH_DIR/.cache/huggingface/{datasets,transformers,hub} \
         $SCRATCH_DIR/.cache/torch \
         $SCRATCH_DIR/.cache/playwright \
         $SCRATCH_DIR/tmp \
         $SCRATCH_DIR/containers

# Check if container exists, if not provide instructions
if [ ! -f "$CONTAINER_PATH" ]; then
    echo "WARNING: Container not found at $CONTAINER_PATH"
    echo ""
    echo "Option 1: Use the base spiral container (if available):"
    echo "  export CONTAINER_PATH=/gpfs/projects/socialrl/bo/work/github_repo/spiral_0.0.2.sif"
    echo ""
    echo "Option 2: Build a custom container:"
    echo "  See sbatch/build_container.def for Apptainer definition"
    echo ""
    echo "Option 3: Use module-based Python (no container):"
    echo "  module load conda"
    echo "  conda activate webarena"
    echo ""

    # Try to use existing spiral container as fallback
    if [ -f "/gpfs/projects/socialrl/bo/work/github_repo/spiral_0.0.2.sif" ]; then
        echo "Found spiral container, using as fallback..."
        CONTAINER_PATH="/gpfs/projects/socialrl/bo/work/github_repo/spiral_0.0.2.sif"
    else
        echo "No container found. Please set up a container or use conda."
        exit 1
    fi
fi

echo "Launching container shell..."
echo ""

# Launch interactive shell with GPU support
apptainer exec --nv \
    --bind $PROJECT_DIR:/workspace/OpenEnv \
    --bind $OPENENV_EXAMPLES:/workspace/webarena \
    --bind $SCRATCH_DIR:/scratch \
    --bind /gpfs/projects/socialrl/bo:/gpfs/projects/socialrl/bo \
    --bind /dev/shm:/dev/shm \
    --ipc \
    --env HF_HOME=/scratch/.cache/huggingface \
    --env HF_DATASETS_CACHE=/scratch/.cache/huggingface/datasets \
    --env TRANSFORMERS_CACHE=/scratch/.cache/huggingface/transformers \
    --env HF_HUB_CACHE=/scratch/.cache/huggingface/hub \
    --env TORCH_HOME=/scratch/.cache/torch \
    --env PLAYWRIGHT_BROWSERS_PATH=/scratch/.cache/playwright \
    --env XDG_CACHE_HOME=/scratch/.cache \
    --env TMPDIR=/scratch/tmp \
    --env PYTHONPATH=/workspace/OpenEnv:/workspace/webarena \
    --pwd /workspace/webarena \
    $CONTAINER_PATH \
    bash
