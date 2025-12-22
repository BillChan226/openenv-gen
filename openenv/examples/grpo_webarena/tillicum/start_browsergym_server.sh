#!/bin/bash

# =============================================================================
# Start BrowserGym Server
# =============================================================================
# Starts the BrowserGym OpenEnv server for WebArena/MiniWoB tasks.
# Run this before starting training.
#
# Usage:
#   ./sbatch/start_browsergym_server.sh [benchmark] [task_name] [port]
#
# Examples:
#   ./sbatch/start_browsergym_server.sh miniwob click-test 8005
#   ./sbatch/start_browsergym_server.sh webarena 0 8005
# =============================================================================

set -e

# Configuration
BENCHMARK="${1:-miniwob}"
TASK_NAME="${2:-click-test}"
PORT="${3:-8005}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/../../../.."  # OpenEnv root
SCRATCH_DIR="/gpfs/scrubbed/${USER}"
CONTAINER_PATH="${CONTAINER_PATH:-/gpfs/projects/socialrl/bo/work/github_repo/spiral_0.0.2.sif}"

echo "============================================"
echo "Starting BrowserGym Server"
echo "============================================"
echo ""
echo "Configuration:"
echo "  Benchmark: $BENCHMARK"
echo "  Task: $TASK_NAME"
echo "  Port: $PORT"
echo ""

# Create cache directories
mkdir -p $SCRATCH_DIR/.cache/playwright $SCRATCH_DIR/tmp

# Export environment for server
export BROWSERGYM_BENCHMARK=$BENCHMARK
export BROWSERGYM_TASK_NAME=$TASK_NAME

# Check if running inside container or need to launch container
if [ -n "$APPTAINER_CONTAINER" ]; then
    # Already inside container
    echo "Running inside container..."
    cd $PROJECT_DIR
    python -m envs.browsergym_env.server.app --port $PORT
else
    # Launch container
    echo "Launching container..."

    if [ ! -f "$CONTAINER_PATH" ]; then
        echo "ERROR: Container not found at $CONTAINER_PATH"
        echo "Trying module-based approach..."

        # Fall back to module-based Python
        module load conda 2>/dev/null || true
        conda activate webarena 2>/dev/null || true

        cd $PROJECT_DIR
        PYTHONPATH=$PROJECT_DIR python -m envs.browsergym_env.server.app --port $PORT
    else
        apptainer exec --nv \
            --bind $PROJECT_DIR:/workspace/OpenEnv \
            --bind $SCRATCH_DIR:/scratch \
            --bind /gpfs/projects/socialrl/bo:/gpfs/projects/socialrl/bo \
            --bind /dev/shm:/dev/shm \
            --ipc \
            --env PLAYWRIGHT_BROWSERS_PATH=/scratch/.cache/playwright \
            --env XDG_CACHE_HOME=/scratch/.cache \
            --env TMPDIR=/scratch/tmp \
            --env PYTHONPATH=/workspace/OpenEnv \
            --env BROWSERGYM_BENCHMARK=$BENCHMARK \
            --env BROWSERGYM_TASK_NAME=$TASK_NAME \
            --pwd /workspace/OpenEnv \
            $CONTAINER_PATH \
            python -m envs.browsergym_env.server.app --port $PORT
    fi
fi
