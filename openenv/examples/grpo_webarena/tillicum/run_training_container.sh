#!/bin/bash
# =============================================================================
# Run GRPO Training (Inside Container)
# =============================================================================
# Run this INSIDE the container after:
# 1. Running enter_container.sh
# 2. Starting the server with start_server_container.sh (in another pane)
#
# Usage (inside container):
#   cd /workspace/training
#   ./run_training_container.sh --config webarena_miniwob.yaml --steps 100
# =============================================================================

set -e

cd /workspace/training

# Check dependencies
echo "Checking dependencies..."

check_import() {
    python -c "import $1" 2>/dev/null && echo "  $1: OK" || echo "  $1: MISSING - run: pip install $2"
}

check_import "torch" "torch"
check_import "vllm" "vllm"
check_import "omegaconf" "omegaconf"
check_import "torchstore" "torchstore (from torchforge)"
check_import "forge" "forge (pip install -e /workspace/torchforge)"

echo ""

# Check if server is running
if ! curl -s http://localhost:8005/health > /dev/null 2>&1; then
    echo "WARNING: OpenEnv server not responding at localhost:8005"
    echo "Run ./start_server_container.sh in another tmux pane first!"
    echo ""
fi

echo "============================================"
echo "WebArena GRPO Training (Container)"
echo "============================================"
echo ""

# Run training
python webarena_main.py "$@"
