#!/bin/bash

# =============================================================================
# Enter Apptainer Container
# =============================================================================
# Quick script to enter the container once you're on a GPU node.
# Run this after srun_interactive.sh gives you a node.
#
# Usage:
#   ./sbatch/srun_workflow/enter_container.sh
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENENV_DIR="$(realpath "${SCRIPT_DIR}/../../../../..")"   # OpenEnv root
WEBARENA_DIR="$(realpath "${SCRIPT_DIR}/../..")"           # grpo_webarena directory
TORCHFORGE_DIR="/gpfs/projects/socialrl/bo/work/projects/synthetic_env_generation/github_repo/torchforge"
TRAINING_DIR="${SCRIPT_DIR}/training"                       # Training scripts
SCRATCH_DIR="/gpfs/scrubbed/${USER}"
CONTAINER_PATH="/gpfs/projects/socialrl/bo/work/github_repo/spiral_0.0.2.sif"

# Create cache directories
mkdir -p $SCRATCH_DIR/.cache/huggingface/{datasets,transformers,hub} \
         $SCRATCH_DIR/.cache/torch \
         $SCRATCH_DIR/.cache/playwright \
         $SCRATCH_DIR/tmp \
         $SCRATCH_DIR/run

echo "Entering container: $CONTAINER_PATH"
echo "OpenEnv: /workspace/OpenEnv"
echo "TorchForge: /workspace/torchforge"
echo "WebArena: /workspace/webarena"
echo "Training: /workspace/training"
echo ""

apptainer exec --nv \
    --bind $OPENENV_DIR:/workspace/OpenEnv \
    --bind $TORCHFORGE_DIR:/workspace/torchforge \
    --bind $WEBARENA_DIR:/workspace/webarena \
    --bind $TRAINING_DIR:/workspace/training \
    --bind $SCRATCH_DIR:/scratch \
    --bind /gpfs/projects/socialrl/bo:/gpfs/projects/socialrl/bo \
    --bind /usr/lib64/libibverbs.so.1:/usr/lib/x86_64-linux-gnu/libibverbs.so.1:ro \
    --bind /usr/lib64/libibverbs:/usr/lib/x86_64-linux-gnu/libibverbs:ro \
    --bind /usr/lib64/libmlx5.so.1.24.47.0:/usr/lib/x86_64-linux-gnu/libmlx5.so.1:ro \
    --bind /usr/lib64/librdmacm.so.1.3.47.0:/usr/lib/x86_64-linux-gnu/librdmacm.so.1:ro \
    --bind /usr/lib64/libnl-3.so.200.26.0:/usr/lib/x86_64-linux-gnu/libnl-3.so.200:ro \
    --bind /usr/lib64/libnl-route-3.so.200.26.0:/usr/lib/x86_64-linux-gnu/libnl-route-3.so.200:ro \
    --bind /dev/shm:/dev/shm \
    --bind /dev/infiniband:/dev/infiniband \
    --ipc \
    --env HF_HOME=/scratch/.cache/huggingface \
    --env HF_DATASETS_CACHE=/scratch/.cache/huggingface/datasets \
    --env TRANSFORMERS_CACHE=/scratch/.cache/huggingface/transformers \
    --env HF_HUB_CACHE=/scratch/.cache/huggingface/hub \
    --env TORCH_HOME=/scratch/.cache/torch \
    --env PLAYWRIGHT_BROWSERS_PATH=/scratch/.cache/playwright \
    --env XDG_CACHE_HOME=/scratch/.cache \
    --env TMPDIR=/scratch/tmp \
    --env XDG_RUNTIME_DIR=/scratch/run \
    --env PYTHONPATH=/workspace/OpenEnv/OpenEnv/src:/workspace/OpenEnv/OpenEnv:/workspace/OpenEnv/OpenEnv/envs:/workspace/torchforge/src:/workspace/training \
    --env NCCL_CUMEM_ENABLE=0 \
    --env MINIWOB_URL="file:///scratch/miniwob-plusplus/miniwob/html/miniwob/" \
    --pwd /workspace/training \
    $CONTAINER_PATH \
    bash
