#!/bin/bash
# =============================================================================
# Start OpenEnv BrowserGym Server for WebArena/MiniWoB Training
# =============================================================================
#
# This script starts the OpenEnv BrowserGym server that the training code
# connects to. Run this in a separate tmux pane before starting training.
#
# Usage:
#   ./start_server.sh              # Default: MiniWoB click-test
#   ./start_server.sh miniwob click-button
#   ./start_server.sh webarena 0   # WebArena task 0
#
# =============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# training -> srun_workflow -> sbatch -> grpo_webarena -> examples -> OpenEnv
OPENENV_ROOT="$(realpath "$SCRIPT_DIR/../../../../..")"

# Default settings
BENCHMARK="${1:-miniwob}"
TASK_NAME="${2:-click-test}"
PORT="${3:-8005}"

# Environment setup - include src, root, and envs directories
export PYTHONPATH="$OPENENV_ROOT/src:$OPENENV_ROOT:$OPENENV_ROOT/envs:$PYTHONPATH"

# BrowserGym environment variables
export BROWSERGYM_BENCHMARK="$BENCHMARK"
export BROWSERGYM_TASK_NAME="$TASK_NAME"
export BROWSERGYM_HEADLESS="true"
export BROWSERGYM_VIEWPORT_WIDTH="1280"
export BROWSERGYM_VIEWPORT_HEIGHT="720"
export BROWSERGYM_TIMEOUT="10000"
export BROWSERGYM_PORT="$PORT"
# Disable screenshots for text-only LLMs (Llama, etc.) - saves ~20MB per observation
export BROWSERGYM_USE_SCREENSHOT="false"

# For MiniWoB, ensure MINIWOB_URL is set
if [ "$BENCHMARK" = "miniwob" ]; then
    if [ -z "$MINIWOB_URL" ]; then
        # Try common locations
        if [ -d "/gpfs/scrubbed/$USER/miniwob-plusplus" ]; then
            export MINIWOB_URL="file:///gpfs/scrubbed/$USER/miniwob-plusplus/miniwob/html/miniwob/"
        else
            echo "WARNING: MINIWOB_URL not set!"
            echo "Please run: export MINIWOB_URL='file:///path/to/miniwob-plusplus/miniwob/html/miniwob/'"
            echo ""
            echo "To set up MiniWoB:"
            echo "  cd /gpfs/scrubbed/\$USER"
            echo "  git clone https://github.com/Farama-Foundation/miniwob-plusplus.git"
            echo "  export MINIWOB_URL='file:///gpfs/scrubbed/\$USER/miniwob-plusplus/miniwob/html/miniwob/'"
        fi
    fi
    echo "MINIWOB_URL: $MINIWOB_URL"
fi

echo "============================================"
echo "OpenEnv BrowserGym Server"
echo "============================================"
echo "Benchmark: $BENCHMARK"
echo "Task: $TASK_NAME"
echo "Port: $PORT"
echo "Use Screenshot: $BROWSERGYM_USE_SCREENSHOT (disabled for text-only LLMs)"
echo "OpenEnv Root: $OPENENV_ROOT"
echo "============================================"
echo ""
echo "Starting server..."
echo "Connect training with: server_url='http://localhost:$PORT'"
echo ""

# Start the OpenEnv BrowserGym server
cd "$OPENENV_ROOT"
python -m envs.browsergym_env.server.app
