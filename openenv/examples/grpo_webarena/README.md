# WebArena GRPO Training

GRPO training for web navigation using BrowserGym (MiniWoB/WebArena).

## Usage

1. Start BrowserGym server:
```bash
export BROWSERGYM_BENCHMARK=miniwob
export BROWSERGYM_PORT=8005
python -m envs.browsergym_env.server.app
```

2. Run training:
```bash
python webarena_main.py --config webarena.yaml --steps 100
```

## Files

- `grpo_utils.py` - Core GRPO training logic
- `webarena_main.py` - Entry point
- `webarena.yaml` - Training config
