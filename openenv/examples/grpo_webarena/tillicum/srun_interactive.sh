#!/bin/bash

# =============================================================================
# Interactive GPU Node Reservation with srun
# =============================================================================
# Reserves a GPU node interactively for development and debugging.
# Use with tmux for persistent sessions.
#
# Usage:
#   ./sbatch/srun_workflow/srun_interactive.sh [num_gpus] [time] [qos]
#
# Examples:
#   ./sbatch/srun_workflow/srun_interactive.sh              # Default: 4 GPUs, 8 hours, normal
#   ./sbatch/srun_workflow/srun_interactive.sh 2 4:00:00    # 2 GPUs, 4 hours
#   ./sbatch/srun_workflow/srun_interactive.sh 1 0:30:00 debug  # 1 GPU, 30 min, debug QOS
#   ./sbatch/srun_workflow/srun_interactive.sh 8 24:00:00   # Full node, 24 hours
#
# Recommended Workflow:
#   1. Start tmux session: tmux new -s webarena
#   2. Run this script to get a GPU node
#   3. Inside the node, run your training commands
#   4. Detach tmux (Ctrl+b, d) to keep session running
#   5. Reattach later: tmux attach -t webarena
# =============================================================================

# Configuration with defaults
NUM_GPUS="${1:-4}"
TIME="${2:-8:00:00}"
QOS="${3:-normal}"

# Calculate resources based on GPU count
# Tillicum: 8 CPUs per GPU, ~200GB memory per GPU
CPUS=$((NUM_GPUS * 8))
MEM=$((NUM_GPUS * 200))G

echo "============================================"
echo "Reserving Interactive GPU Node"
echo "============================================"
echo ""
echo "Resources:"
echo "  GPUs: $NUM_GPUS"
echo "  CPUs: $CPUS"
echo "  Memory: $MEM"
echo "  Time: $TIME"
echo "  QOS: $QOS"
echo ""
echo "Tips:"
echo "  - Use tmux to keep your session alive"
echo "  - Run ./sbatch/srun_workflow/enter_container.sh to enter Apptainer"
echo "  - Or use conda: module load conda && conda activate webarena"
echo ""
echo "Starting srun..."
echo "============================================"
echo ""

# Reserve node with srun
srun --job-name=synthetic_env_generation_webarena \
     --qos=$QOS \
     --gpus=$NUM_GPUS \
     --cpus-per-task=$CPUS \
     --mem=$MEM \
     --time=$TIME \
     --pty bash
