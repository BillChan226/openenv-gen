# Training Web Agents with GRPO + OpenEnv + BrowserGym

This example demonstrates how to train language models to navigate web pages using **GRPO (Group Relative Policy Optimization)** with **OpenEnv's BrowserGym** integration.

## What This Example Shows

- **OpenEnv + BrowserGym**: Unified interface for web navigation tasks
- **MiniWoB++**: 100+ training tasks (click buttons, fill forms, navigate menus)
- **GRPO**: Efficient RL algorithm for training web agents
- **Forge**: PyTorch-native distributed training infrastructure
- **End-to-End Training**: From random policy to trained web navigator

## Module Structure

```
grpo_web/
├── __init__.py          # Package exports (re-exports from utils/)
├── train.py             # Main training script (entry point)
├── web.yaml             # Training configuration
├── README.md            # This file
└── utils/               # Core utilities
    ├── __init__.py      # Utils package exports + automatic path setup
    ├── data.py          # Episode data structures and collation
    ├── loss.py          # GRPO loss function implementation
    ├── prompts.py       # Prompt formatting and action parsing
    ├── actors.py        # Forge actors (reward, advantages, env)
    ├── rollout.py       # Web task playing and episode collection
    ├── trainer.py       # High-level training interface
    └── tasks.py         # MiniWoB++ task lists and curriculum
```

### Module Overview

| Module | Purpose |
|--------|---------|
| `train.py` | Main entry point with CLI arguments |
| `utils/data.py` | Episode dataclass, collation for batching |
| `utils/loss.py` | GRPO loss with KL penalty, entropy bonus variant |
| `utils/prompts.py` | Convert observations to prompts, parse actions |
| `utils/actors.py` | WebReward, ComputeAdvantages, WebEnvActor |
| `utils/rollout.py` | play_web_task(), benchmarking utilities |
| `utils/trainer.py` | GRPOWebTrainer, setup_forge_training() |
| `utils/tasks.py` | Task lists by difficulty, curriculum utilities |

---

## Complete Installation Guide

This section documents all the fixes and version requirements needed to make this example work.

### System Requirements

- Linux (tested on Ubuntu 20.04+)
- CUDA-capable GPU(s) with 16GB+ VRAM (for 7B model)
- Docker (for BrowserGym server)
- Python 3.12

### Directory Structure

Ensure your project has this structure:
```
/scratch/czr/env-gen/          # or your project root
├── openenv/                   # This repository
│   ├── src/                   # OpenEnv core
│   ├── envs/                  # Environment implementations
│   └── examples/
│       └── grpo_web/          # This example
└── torchforge/                # TorchForge (cloned separately)
    └── src/
```

### Step 1: Create Conda Environment

```bash
conda create -n openenv python=3.12 -y
conda activate openenv
```

### Step 2: Install PyTorch

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### Step 3: Install TorchForge Dependencies

**IMPORTANT**: There are specific version requirements for compatibility between vLLM, torchmonarch, and torchforge.

```bash
# Install vLLM from the Forge index (special build with Forge support)
# This version includes vllm.executor module required by torchforge
pip install vllm --index-url https://download.pytorch.org/whl/preview/forge --force-reinstall --no-deps

# Install torchmonarch (MUST be this specific version)
pip install torchmonarch==0.1.2 --force-reinstall

# Install torchstore
pip install torchstore==0.1.2

# Install torchtitan
pip install torchtitan
```

### Step 4: Clone and Setup TorchForge

```bash
cd /scratch/czr/env-gen  # or your project root

# Clone TorchForge
git clone https://github.com/pytorch-labs/torchforge.git
cd torchforge

# CRITICAL: Checkout to the compatible commit (before monarch upgrade)
git checkout b628308

cd ..
```

**Why this specific commit?**
- Newer versions of TorchForge use `torchmonarch-nightly` which has breaking API changes
- For example, `RootClientActor` was renamed to `ClientActor`
- Commit `b628308` is compatible with `torchmonarch==0.1.2`

### Step 5: Install OpenEnv Dependencies

```bash
cd /scratch/czr/env-gen/openenv

# Install OpenEnv and its dependencies
pip install -e .

# Install additional dependencies
pip install omegaconf huggingface_hub transformers requests
```

### Step 6: Download the Model

The training uses Qwen2.5-7B-Instruct. Download it to a local path:

```bash
python -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='Qwen/Qwen2.5-7B-Instruct',
    local_dir='/scratch/czr/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28'
)
"
```

Or use the HuggingFace CLI:
```bash
huggingface-cli download Qwen/Qwen2.5-7B-Instruct \
    --local-dir /scratch/czr/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28
```

**Note**: Update `model_local_path` in `web.yaml` if you download to a different location.

### Step 7: Setup BrowserGym Docker Container

```bash
cd /scratch/czr/env-gen/openenv/envs/browsergym_env/server

# Build the Docker image
docker build -t browsergym-env:latest .

# Run the container (keep this running in a separate terminal)
docker run -p 8005:8000 \
    -e BROWSERGYM_BENCHMARK=miniwob \
    -e BROWSERGYM_TASK_NAME=click-test \
    browsergym-env:latest
```

---

## Configuration

The training is configured via `web.yaml`. Key settings:

```yaml
# Model configuration
model: "Qwen/Qwen2.5-7B-Instruct"
model_local_path: /scratch/czr/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28

# Training parameters
group_size: 4                # Number of parallel tasks per rollout
local_batch_size: 4          # Per-device batch size
max_req_tokens: 2048         # Max tokens for prompt
max_res_tokens: 64           # Max tokens for response

# Web environment
web_env:
  server_url: "http://localhost:8005"
  benchmark: "miniwob"
  task_name: "click-test"
  max_steps: 15

# Metric logging (required for console backend)
metric_logging:
  console:
    logging_mode: global_reduce
```

---

## Running Training

```bash
cd /scratch/czr/env-gen/openenv

# Run training with explicit PYTHONPATH
PYTHONPATH="/scratch/czr/env-gen/torchforge/src:/scratch/czr/env-gen/openenv/src:$PYTHONPATH" \
python -m examples.grpo_web.train --config examples/grpo_web/web.yaml
```

**Note**: The `PYTHONPATH` is needed to include TorchForge and OpenEnv source directories. The example also has automatic path setup in `utils/__init__.py`, but setting `PYTHONPATH` explicitly ensures all imports work correctly.

### CLI Options

```bash
python -m examples.grpo_web.train \
    --config examples/grpo_web/web.yaml \
    --steps 1000 \
    --task click-button \
    --benchmark \
    --eval
```

- `--config PATH` - Path to YAML config file (required)
- `--steps N` - Override training steps
- `--task NAME` - Override MiniWoB task name
- `--benchmark` - Run random policy benchmark first
- `--eval` - Run evaluation after training
- `--eval-only` - Only evaluate (skip training)
- `--eval-tasks N` - Number of evaluation tasks (default: 50)

### Programmatic Usage

```python
import asyncio
from examples.grpo_web import setup_forge_training

async def main():
    trainer = await setup_forge_training('examples/grpo_web/web.yaml')
    await trainer.run(steps=1000)

    # Evaluate
    results = await trainer.evaluate(num_tasks=50)
    print(f"Success rate: {results['success_rate']:.1%}")

    await trainer.shutdown()

asyncio.run(main())
```

---

## Troubleshooting

### 1. `ModuleNotFoundError: No module named 'vllm.executor'`

**Cause**: Wrong vLLM version installed. The standard PyPI vLLM doesn't include the `executor` module required by torchforge.

**Fix**: Install vLLM from the Forge index:
```bash
pip install vllm --index-url https://download.pytorch.org/whl/preview/forge --force-reinstall --no-deps
```

### 2. `pyo3_runtime.PanicException: RootClientActor not found in registry`

**Cause**: Version mismatch between `torchmonarch` and `torchforge`. The newer `torchmonarch-nightly` renamed `RootClientActor` to `ClientActor`.

**Fix**:
1. Checkout TorchForge to the compatible commit:
   ```bash
   cd torchforge && git checkout b628308
   ```
2. Reinstall the correct torchmonarch version:
   ```bash
   pip uninstall torchmonarch-nightly torchmonarch -y
   pip install torchmonarch==0.1.2 --force-reinstall
   ```

### 3. `ModuleNotFoundError: No module named 'openenv'`

**Cause**: OpenEnv paths not in Python path.

**Fix**: The `utils/__init__.py` should handle this automatically by adding paths:
```python
# Automatic path setup in utils/__init__.py
_openenv_root = Path(__file__).parent.parent.parent.parent
_torchforge_src = _openenv_root.parent / "torchforge" / "src"
_openenv_src = _openenv_root / "src"
```

If that doesn't work, set PYTHONPATH explicitly:
```bash
export PYTHONPATH="/scratch/czr/env-gen/openenv/src:/scratch/czr/env-gen/openenv:$PYTHONPATH"
```

### 4. `ValueError: logging_mode is required for backend 'console'`

**Cause**: Missing `logging_mode` in metric_logging configuration.

**Fix**: Ensure `web.yaml` has:
```yaml
metric_logging:
  console:
    logging_mode: global_reduce
```

### 5. `ValueError: checkpoint.initial_load_path is specified but the path is not valid`

**Cause**: The `hf://` prefix for HuggingFace models isn't being resolved properly.

**Fix**: Download the model locally and use an absolute path:
```yaml
model_local_path: /absolute/path/to/model/snapshot

trainer:
  checkpoint:
    initial_load_path: ${model_local_path}
    initial_load_in_hf: true
```

### 6. `TypeError: WebEnvActor.__init__() got an unexpected keyword argument 'max_steps'`

**Cause**: The `max_steps` field was missing from the `WebEnvActor` class.

**Fix**: Already fixed in `utils/actors.py`. Ensure you have:
```python
@dataclass
class WebEnvActor(ForgeActor):
    server_url: str = "http://localhost:8005"
    model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    benchmark: str = "miniwob"
    task_name: str = "click-test"
    max_steps: int = 15  # This field must exist
```

### 7. Docker Connection Issues

```bash
# Check if container is running
docker ps

# View container logs
docker logs <container_id>

# Test server is accessible
curl http://localhost:8005/health

# Rebuild if needed
docker build --no-cache -t browsergym-env:latest .
```

### 8. Out of Memory (OOM)

```yaml
# Reduce batch size in web.yaml
local_batch_size: 2

# Or use smaller model
model: "Qwen/Qwen2.5-1.5B-Instruct"
model_local_path: /path/to/smaller/model
```

### Verifying Installation

```python
# Test all critical imports
import torch
import vllm
from vllm.executor.uniproc_executor import UniProcExecutor  # Should work with forge vllm
import monarch
from monarch.actor import endpoint
print("All imports successful!")

# Check versions
print(f"PyTorch: {torch.__version__}")
print(f"vLLM: {vllm.__version__}")

# Check monarch version (should be 0.1.2)
import importlib.metadata
print(f"torchmonarch: {importlib.metadata.version('torchmonarch')}")
```

---

## Training Pipeline

### Stage 1: Train on MiniWoB++ (This Example)

MiniWoB++ provides 100+ synthetic web tasks perfect for training:

| Task Type | Examples | Difficulty |
|-----------|----------|------------|
| Click | click-button, click-link, click-dialog | Easy |
| Form | enter-text, focus-text, login-user | Medium |
| Navigation | click-tab, navigate-tree, search-engine | Hard |
| Multi-step | book-flight, email-inbox, social-media | Hard |

**Why MiniWoB++ for training:**
- Fast resets (no network latency)
- Dense rewards (immediate feedback)
- No external infrastructure needed
- Docker image bundles everything

### Stage 2: Evaluate on WebArena (Optional)

After training on MiniWoB++, evaluate on realistic web tasks:

```bash
# Start WebArena (requires backend setup)
docker run -p 8005:8000 \
  -e BROWSERGYM_BENCHMARK=webarena \
  -e BROWSERGYM_TASK_NAME=0 \
  -e SHOPPING="http://your-server:7770" \
  -e GITLAB="http://your-server:8023" \
  browsergym-env:latest
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GRPOWebTrainer                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐    │
│  │  Rollout    │  │  Training   │  │   Metrics Logger     │    │
│  │    Loop     │  │    Loop     │  │                      │    │
│  └──────┬──────┘  └──────┬──────┘  └──────────────────────┘    │
│         │                │                                      │
│  ┌──────▼──────┐  ┌──────▼──────┐                              │
│  │   Policy    │  │   Trainer   │                              │
│  │ (Generator) │  │ (RLTrainer) │                              │
│  └──────┬──────┘  └──────┬──────┘                              │
│         │                │                                      │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌───────────────────────┐   │
│  │ BrowserGym  │  │   Replay    │  │    Reference Model    │   │
│  │    Env      │  │   Buffer    │  │                       │   │
│  └─────────────┘  └─────────────┘  └───────────────────────┘   │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │  WebReward  │  │  Compute    │                              │
│  │   Actor     │  │ Advantages  │                              │
│  └─────────────┘  └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Differences from BlackJack GRPO

| Aspect | BlackJack | Web Navigation |
|--------|-----------|----------------|
| Observation | Game state (cards) | Web page (HTML/AXTree) |
| Action Space | 2 actions (HIT/STAND) | Natural language actions |
| Episode Length | 1-3 steps | 5-15+ steps |
| Prompt Size | ~300 tokens | ~2000 tokens |
| Reward | Dense (+1/-1/0) | Sparse (success/failure) |

---

## Reward Shaping

The `WebReward` actor shapes rewards for better learning:

```python
@endpoint
async def evaluate_response(self, prompt, response, task_reward, step_count, max_steps):
    reward = float(task_reward)

    if task_reward > 0:
        # Bonus for completing faster
        efficiency_bonus = 0.5 * (1.0 - step_count / max_steps)
        reward = 2.0 + efficiency_bonus
    elif task_reward == 0:
        # Small penalty for timeout
        reward = -0.5

    # Penalty for errors
    if "error" in response.lower():
        reward -= 0.1

    return reward
```

---

## MiniWoB++ Task Categories

### Easy (Start Here)
- `click-test` - Click a single button
- `click-button` - Click the specified button
- `click-link` - Click a hyperlink
- `focus-text` - Focus on a text input
- `enter-text` - Type text into a field

### Medium
- `click-checkboxes` - Select specific checkboxes
- `click-tab` - Navigate between tabs
- `login-user` - Complete login form
- `email-inbox` - Navigate email interface

### Hard
- `book-flight` - Multi-step booking form
- `choose-date` - Date picker interaction
- `navigate-tree` - Tree navigation
- `social-media` - Social media interactions

---

## Available Actions

The web agent can use these BrowserGym actions:

| Action | Description | Example |
|--------|-------------|---------|
| `click(bid)` | Click element by ID | `click('btn-submit')` |
| `fill(bid, text)` | Fill text field | `fill('input-email', 'test@example.com')` |
| `type(bid, text)` | Type into element | `type('search', 'query')` |
| `select(bid, value)` | Select dropdown option | `select('country', 'USA')` |
| `scroll(direction)` | Scroll page | `scroll('down')` |
| `goto(url)` | Navigate to URL | `goto('https://example.com')` |
| `send_keys(key)` | Send keyboard key | `send_keys('Enter')` |
| `hover(bid)` | Hover over element | `hover('menu-item')` |
| `noop()` | Do nothing | `noop()` |

---

## Expected Results

| Metric | Random Policy | Trained (1k steps) | Trained (10k steps) |
|--------|---------------|--------------------|--------------------|
| Success Rate | ~5% | ~30% | ~60%+ |
| Avg Steps | 10+ | 5-7 | 3-5 |

*Results vary by task difficulty and model size.*

---

## Version Compatibility Summary

| Package | Required Version | Notes |
|---------|-----------------|-------|
| Python | 3.12 | Tested version |
| PyTorch | 2.x | CUDA 12.4 |
| vLLM | forge build | Install from forge index |
| torchmonarch | 0.1.2 | NOT nightly |
| torchstore | 0.1.2 | |
| torchtitan | latest | |
| torchforge | commit b628308 | Before monarch upgrade |

---

## References

- **OpenEnv**: [GitHub](https://github.com/meta-pytorch/OpenEnv)
- **TorchForge**: [GitHub](https://github.com/pytorch-labs/torchforge)
- **BrowserGym**: [GitHub](https://github.com/ServiceNow/BrowserGym)
- **MiniWoB++**: [GitHub](https://github.com/Farama-Foundation/miniwob-plusplus)
- **GRPO Paper**: [arXiv:2402.03300](https://arxiv.org/abs/2402.03300)
- **Qwen2.5**: [HuggingFace](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct)

---

## License

This example follows the same license as the parent OpenEnv repository.
