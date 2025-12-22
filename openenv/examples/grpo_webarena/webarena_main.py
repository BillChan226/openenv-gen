#!/usr/bin/env python3
"""WebArena GRPO Training - Entry Point"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from grpo_utils import setup_training


async def main(config_path: str, steps: int):
    print(f"WebArena GRPO Training\nConfig: {config_path}\n")
    trainer = await setup_training(config_path)
    await trainer.run(steps=steps)
    await trainer.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="webarena.yaml")
    parser.add_argument("--steps", type=int, default=100)
    args = parser.parse_args()

    config = Path(args.config)
    if not config.is_absolute():
        config = Path(__file__).parent / config

    asyncio.run(main(str(config), args.steps))
