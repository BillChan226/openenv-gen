# Interactive Development Workflow with srun + tmux

This guide covers the recommended workflow for interactive development and debugging on Tillicum using `srun` and `tmux`.

## Quick Start

```bash
# 0. cd to grpo_webarena directory
cd /path/to/OpenEnv/examples/grpo_webarena

# 1. Start a tmux session (so you don't lose work if SSH disconnects)
tmux new -s webarena

# 2. Reserve a GPU node
./sbatch/srun_workflow/srun_interactive.sh 4 8:00:00

# 3. Once on the node, enter the container
./sbatch/srun_workflow/enter_container.sh

# 4. Inside container, start the BrowserGym server (keep this running)
cd /workspace/OpenEnv
BROWSERGYM_BENCHMARK=miniwob BROWSERGYM_TASK_NAME=click-test \
    python -m envs.browsergym_env.server.app --port 8005

# 5. Open another tmux pane (Ctrl+b, %) and run training
cd /workspace/webarena
python webarena_main.py --config webarena_miniwob.yaml --steps 100
```

## Detailed Workflow

### Step 1: Start tmux Session

tmux keeps your session alive even if SSH disconnects.

```bash
# Create new session
tmux new -s webarena

# Or attach to existing session
tmux attach -t webarena

# Useful tmux commands:
#   Ctrl+b, d     - Detach (leave session running)
#   Ctrl+b, %     - Split pane vertically
#   Ctrl+b, "     - Split pane horizontally
#   Ctrl+b, arrow - Switch between panes
#   Ctrl+b, c     - Create new window
#   Ctrl+b, n     - Next window
#   Ctrl+b, p     - Previous window
```

### Step 2: Reserve GPU Node with srun

```bash
# Default: 4 GPUs, 8 hours
./sbatch/srun_workflow/srun_interactive.sh

# Custom configurations:
./sbatch/srun_workflow/srun_interactive.sh 2 4:00:00      # 2 GPUs, 4 hours
./sbatch/srun_workflow/srun_interactive.sh 8 24:00:00     # Full node (8 GPUs), 24 hours
./sbatch/srun_workflow/srun_interactive.sh 1 0:30:00 debug  # Quick test, debug QOS

# Or use srun directly:
srun --qos=normal --gpus=4 --cpus-per-task=32 --mem=800G --time=8:00:00 --pty bash
```

### Step 3: Enter Container

Once you have a node, enter the Apptainer container:

```bash
./sbatch/srun_workflow/enter_container.sh
```

This sets up:
- GPU access (`--nv`)
- OpenEnv at `/workspace/OpenEnv`
- WebArena example at `/workspace/webarena`
- Cache directories in `/scratch`
- All required environment variables

### Step 4: Run Training (Two-Pane Setup)

**Pane 1: BrowserGym Server**
```bash
# Inside container
cd /workspace/OpenEnv

# Start server for MiniWoB
BROWSERGYM_BENCHMARK=miniwob \
BROWSERGYM_TASK_NAME=click-test \
    python -m envs.browsergym_env.server.app --port 8005

# Or for WebArena (requires backend setup)
BROWSERGYM_BENCHMARK=webarena \
BROWSERGYM_TASK_NAME=0 \
    python -m envs.browsergym_env.server.app --port 8005
```

**Pane 2: Training**
```bash
# Open new pane: Ctrl+b, %
# Enter container again
./sbatch/srun_workflow/enter_container.sh

# Run training
cd /workspace/webarena
python webarena_main.py --config webarena_miniwob.yaml --steps 100
```

## Alternative: Without Container (Conda)

If you prefer not to use the container:

```bash
# On the GPU node
module load conda
conda activate webarena  # Run setup_conda_env.sh first if needed

# Set environment variables
export PYTHONPATH=/path/to/OpenEnv:/path/to/grpo_webarena
export HF_HOME=/gpfs/scrubbed/$USER/.cache/huggingface
export TORCH_HOME=/gpfs/scrubbed/$USER/.cache/torch

# Run commands directly
cd /path/to/grpo_webarena
python webarena_main.py --config webarena_miniwob.yaml
```

## Common srun Options

| Option | Description | Example |
|--------|-------------|---------|
| `--gpus=N` | Number of GPUs | `--gpus=4` |
| `--cpus-per-task=N` | Number of CPUs | `--cpus-per-task=32` |
| `--mem=SIZE` | Memory | `--mem=800G` |
| `--time=HH:MM:SS` | Max runtime | `--time=8:00:00` |
| `--qos=QOS` | Quality of service | `--qos=normal` |
| `--pty` | Allocate pseudo-terminal | Required for interactive |
| `--job-name=NAME` | Job name | `--job-name=webarena` |

## QOS Options

| QOS | Max Time | Max GPUs | Use Case |
|-----|----------|----------|----------|
| `debug` | 30 min | 1 | Quick tests |
| `interactive` | 8 hours | 2 | Development |
| `normal` | 24 hours | 16 | Training |

## Monitoring

```bash
# Check your jobs
squeue -u $USER

# Check GPU usage (on node)
nvidia-smi
watch -n 1 nvidia-smi

# Check node resources
sinfo -N -l

# Cancel a job
scancel JOB_ID
```

## Troubleshooting

**srun hangs waiting for resources:**
```bash
# Check queue
squeue -u $USER

# Try fewer GPUs or debug QOS
./sbatch/srun_workflow/srun_interactive.sh 1 0:30:00 debug
```

**Container not found:**
```bash
# Verify container exists
ls -la /gpfs/projects/socialrl/bo/work/github_repo/spiral_0.0.2.sif

# Use conda instead
module load conda
conda activate webarena
```

**Lost SSH connection:**
```bash
# Reattach to tmux
tmux attach -t webarena

# Your srun job and processes should still be running
```

**GPU not visible:**
```bash
# Inside container
nvidia-smi

# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"
```
