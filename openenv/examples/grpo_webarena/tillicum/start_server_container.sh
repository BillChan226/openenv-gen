#!/bin/bash
# =============================================================================
# Start OpenEnv BrowserGym Server (Inside Container)
# =============================================================================
# Run this INSIDE the container after running enter_container.sh
#
# Usage (inside container):
#   cd /workspace/training
#   ./start_server_container.sh
# =============================================================================

set -e

# Environment is set by enter_container.sh
# PYTHONPATH already includes OpenEnv and envs

BENCHMARK="${1:-miniwob}"
TASK_NAME="${2:-click-test}"
PORT="${3:-8005}"

export BROWSERGYM_BENCHMARK="$BENCHMARK"
export BROWSERGYM_TASK_NAME="$TASK_NAME"
export BROWSERGYM_HEADLESS="true"
export BROWSERGYM_VIEWPORT_WIDTH="1280"
export BROWSERGYM_VIEWPORT_HEIGHT="720"
export BROWSERGYM_TIMEOUT="10000"
export BROWSERGYM_PORT="$PORT"

# Ensure MiniWoB is set up
if [ "$BENCHMARK" = "miniwob" ]; then
    if [ ! -d "/scratch/miniwob-plusplus" ]; then
        echo "Setting up MiniWoB..."
        cd /scratch
        git clone https://github.com/Farama-Foundation/miniwob-plusplus.git
    fi
    export MINIWOB_URL="file:///scratch/miniwob-plusplus/miniwob/html/miniwob/"
    echo "MINIWOB_URL: $MINIWOB_URL"
fi

echo "============================================"
echo "OpenEnv BrowserGym Server (Container)"
echo "============================================"
echo "Benchmark: $BENCHMARK"
echo "Task: $TASK_NAME"
echo "Port: $PORT"
echo "============================================"
echo ""
echo "Starting server..."
echo "Training connects to: http://localhost:$PORT"
echo ""

cd /workspace/OpenEnv
python -m envs.browsergym_env.server.app
