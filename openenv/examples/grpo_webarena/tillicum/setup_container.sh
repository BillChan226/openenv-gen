#!/bin/bash
# =============================================================================
# Setup Dependencies Inside Container
# =============================================================================
# Run this ONCE inside the container to install all dependencies.
# PYTHONPATH is already set by enter_container.sh - no need to pip install OpenEnv/TorchForge
#
# Usage (inside container):
#   cd /workspace/training
#   ./setup_container.sh
# =============================================================================

set -e

echo "============================================"
echo "Setting Up Container Dependencies"
echo "============================================"
echo ""

# Use scratch for pip cache
export PIP_CACHE_DIR=/scratch/.cache/pip
mkdir -p $PIP_CACHE_DIR

echo "1. Installing TorchForge dependencies..."
echo "   NOTE: Using container's pre-installed torchmonarch (patched TorchForge for compatibility)"
pip install --user omegaconf wandb

echo ""
echo "2. Installing OpenEnv dependencies..."
pip install --user fastapi uvicorn pydantic httpx websockets aiohttp

echo ""
echo "3. Installing BrowserGym..."
pip install --user browsergym browsergym-miniwob

echo ""
echo "4. Installing Playwright..."
pip install --user playwright
python -m playwright install chromium 2>/dev/null || echo "   (playwright browser - may already be installed)"

echo ""
echo "5. Setting up MiniWoB..."
if [ ! -d "/scratch/miniwob-plusplus" ]; then
    cd /scratch
    git clone https://github.com/Farama-Foundation/miniwob-plusplus.git
    echo "   Cloned MiniWoB to /scratch/miniwob-plusplus"
else
    echo "   MiniWoB already at /scratch/miniwob-plusplus"
fi

echo ""
echo "6. Verifying imports..."
cd /workspace/training
python -c "
import sys
print('Python:', sys.executable)
print('Checking imports...')

# Check core
try:
    import torch; print(f'  torch: {torch.__version__}')
except: print('  torch: MISSING')

try:
    import vllm; print('  vllm: OK')
except: print('  vllm: MISSING')

try:
    import omegaconf; print('  omegaconf: OK')
except: print('  omegaconf: MISSING')

try:
    import fastapi; print('  fastapi: OK')
except: print('  fastapi: MISSING')

try:
    import browsergym; print('  browsergym: OK')
except: print('  browsergym: MISSING')

# Check OpenEnv (via PYTHONPATH)
try:
    from openenv.core.env_client import EnvClient; print('  openenv: OK')
except Exception as e: print(f'  openenv: ERROR - {e}')

# Check TorchForge (via PYTHONPATH)
try:
    from forge.actors.generator import Generator; print('  forge: OK')
except Exception as e: print(f'  forge: ERROR - {e}')
"

echo ""
echo "============================================"
echo "Setup Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  Pane 1: ./start_server_container.sh"
echo "  Pane 2: ./run_training_container.sh --steps 100"
echo ""
