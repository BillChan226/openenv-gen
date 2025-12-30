"""
BlackJack GRPO Training Example

Train language models to play BlackJack using Group Relative Policy Optimization (GRPO).

Usage:
    # Run training
    python -m examples.grpo_blackjack.main --config examples/grpo_blackjack/blackjack.yaml

    # Run benchmark
    python -m examples.grpo_blackjack.main --config examples/grpo_blackjack/blackjack.yaml --benchmark

    # Explore environment
    python -m examples.grpo_blackjack.main --config examples/grpo_blackjack/blackjack.yaml --explore
"""

import sys
from pathlib import Path

# Add torchforge to path
_torchforge_path = Path(__file__).parent.parent.parent.parent / "torchforge" / "src"
if _torchforge_path.exists() and str(_torchforge_path) not in sys.path:
    sys.path.insert(0, str(_torchforge_path))

# Add src to path for envs imports
_src_path = Path(__file__).parent.parent.parent / "src"
if _src_path.exists() and str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Add openenv root to path for envs imports
_openenv_root = Path(__file__).parent.parent.parent
if str(_openenv_root) not in sys.path:
    sys.path.insert(0, str(_openenv_root))

from .grpo_utils import (
    # Data structures
    Episode,
    Group,
    # GRPO components
    collate,
    simple_grpo_loss,
    # Prompt formatting
    format_prompt,
    parse_action,
    # Forge actors
    BlackJackReward,
    ComputeAdvantages,
    EnvironmentActor,
    BlackJackEnvActor,
    # Game playing
    play_game,
    play_blackjack_game,
    play_random_policy,
    play_heuristic_policy,
    # Training
    GRPOTrainer,
    setup_forge_training,
    # Utilities
    setup_game_logger,
    drop_weights,
    show_openenv_observation,
)

__all__ = [
    # Data structures
    "Episode",
    "Group",
    # GRPO components
    "collate",
    "simple_grpo_loss",
    # Prompt formatting
    "format_prompt",
    "parse_action",
    # Forge actors
    "BlackJackReward",
    "ComputeAdvantages",
    "EnvironmentActor",
    "BlackJackEnvActor",
    # Game playing
    "play_game",
    "play_blackjack_game",
    "play_random_policy",
    "play_heuristic_policy",
    # Training
    "GRPOTrainer",
    "setup_forge_training",
    # Utilities
    "setup_game_logger",
    "drop_weights",
    "show_openenv_observation",
]
