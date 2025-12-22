#!/bin/bash

# =============================================================================
# Conda Environment Setup for WebArena Training
# =============================================================================
# Sets up a conda environment with all dependencies for WebArena training.
# Use this as an alternative to the Apptainer container.
#
# Usage:
#   ./sbatch/setup_conda_env.sh
#
# After setup:
#   conda activate webarena
# =============================================================================

set -e

ENV_NAME="webarena"
SCRATCH_DIR="/gpfs/scrubbed/${USER}"

echo "============================================"
echo "Setting up Conda Environment: $ENV_NAME"
echo "============================================"
echo ""

# Load conda module on Tillicum
module load conda 2>/dev/null || {
    echo "Warning: Could not load conda module"
    echo "Trying to use existing conda installation..."
}

# Configure conda directories to use scratch
mkdir -p $SCRATCH_DIR/conda/{envs,pkgs}

# Create or update .condarc
cat > ~/.condarc << EOF
envs_dirs:
  - $SCRATCH_DIR/conda/envs
pkgs_dirs:
  - $SCRATCH_DIR/conda/pkgs
EOF

echo "Conda configured to use scratch directory"
echo ""

# Check if environment already exists
if conda env list | grep -q "^$ENV_NAME "; then
    echo "Environment '$ENV_NAME' already exists."
    read -p "Do you want to recreate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing environment..."
        conda env remove -n $ENV_NAME -y
    else
        echo "Keeping existing environment. Run 'conda activate $ENV_NAME' to use it."
        exit 0
    fi
fi

echo "Creating conda environment..."
conda create -n $ENV_NAME python=3.12 -y

echo ""
echo "Activating environment..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate $ENV_NAME

echo ""
echo "Installing PyTorch with CUDA support..."
# Install PyTorch - use appropriate CUDA version for Tillicum
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo ""
echo "Installing vLLM..."
pip install vllm

echo ""
echo "Installing HuggingFace libraries..."
pip install transformers accelerate datasets tokenizers

echo ""
echo "Installing BrowserGym..."
pip install browsergym browsergym-miniwob

# Note: browsergym-webarena requires additional setup
# pip install browsergym-webarena

echo ""
echo "Installing Playwright..."
pip install playwright
playwright install chromium

echo ""
echo "Installing OpenEnv dependencies..."
pip install fastapi uvicorn pydantic requests httpx aiohttp

echo ""
echo "Installing training dependencies..."
pip install omegaconf wandb tqdm numpy scipy

echo ""
echo "============================================"
echo "Environment Setup Complete!"
echo "============================================"
echo ""
echo "To activate the environment:"
echo "  module load conda"
echo "  conda activate $ENV_NAME"
echo ""
echo "To verify GPU access:"
echo "  python -c \"import torch; print(f'CUDA available: {torch.cuda.is_available()}')\""
echo ""
echo "To install Playwright browsers (run on GPU node):"
echo "  playwright install chromium"
echo ""

# Display installed packages
echo "Installed packages:"
pip list | grep -E "^(torch|vllm|transformers|browsergym|playwright)"
