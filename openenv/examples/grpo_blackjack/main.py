"""
BlackJack GRPO Training Main Script

Train language models to play BlackJack using Group Relative Policy Optimization (GRPO).

Prerequisites:
    1. Start the BlackJack server:
        cd /path/to/openenv
        export PYTHONPATH="src:${PYTHONPATH}"
        OPENSPIEL_GAME=blackjack python -m envs.openspiel_env.server.app --port 8004

    2. Run training:
        python -m examples.grpo_blackjack.main --config examples/grpo_blackjack/blackjack.yaml

Usage Examples:
    # Basic training
    python -m examples.grpo_blackjack.main --config examples/grpo_blackjack/blackjack.yaml

    # Training with custom steps
    python -m examples.grpo_blackjack.main --config examples/grpo_blackjack/blackjack.yaml --steps 100

    # Run benchmark before training
    python -m examples.grpo_blackjack.main --config examples/grpo_blackjack/blackjack.yaml --benchmark

    # Evaluation after training
    python -m examples.grpo_blackjack.main --config examples/grpo_blackjack/blackjack.yaml --eval
"""

import argparse
import asyncio
import sys
from pathlib import Path

from omegaconf import OmegaConf

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

# Import from grpo_utils
from .grpo_utils import (
    play_random_policy,
    play_heuristic_policy,
    setup_forge_training,
    show_openenv_observation,
)
from envs.openspiel_env import OpenSpielEnv


async def run_benchmark(server_url: str, num_games: int = 100):
    """
    Run baseline policy benchmarks.

    Args:
        server_url: OpenEnv server URL
        num_games: Number of games to play

    Returns:
        Tuple of (random_stats, heuristic_stats)
    """
    print("\n" + "=" * 60)
    print("BASELINE BENCHMARK")
    print("=" * 60)

    print(f"\nRunning {num_games} games with random policy...")
    random_stats = play_random_policy(server_url, num_games=num_games)
    print(f"  Wins: {random_stats['wins']}")
    print(f"  Losses: {random_stats['losses']}")
    print(f"  Pushes: {random_stats['pushes']}")
    print(f"  Win rate: {random_stats['win_rate']:.1%}")

    print(f"\nRunning {num_games} games with heuristic policy...")
    heuristic_stats = play_heuristic_policy(server_url, num_games=num_games)
    print(f"  Win rate: {heuristic_stats['win_rate']:.1%}")

    print("\nNote: Optimal BlackJack strategy achieves ~43% win rate")

    return random_stats, heuristic_stats


async def run_exploration(server_url: str):
    """
    Explore the OpenEnv BlackJack environment.

    Args:
        server_url: OpenEnv server URL
    """
    print("\n" + "=" * 60)
    print("OPENENV EXPLORATION")
    print("=" * 60)

    print("\nConnecting to BlackJack environment...")
    env = OpenSpielEnv(base_url=server_url)

    print("Resetting environment...")
    result = env.reset()

    print("\nEnvironment observation:")
    show_openenv_observation(result.observation)

    env.close()
    print("\nExploration complete!")


async def run_training(config_path: str, steps: int = None):
    """
    Run GRPO training.

    Args:
        config_path: Path to YAML config file
        steps: Number of training steps (overrides config)

    Returns:
        Tuple of (trainer, metrics)
    """
    print("\n" + "=" * 60)
    print("GRPO BLACKJACK TRAINING")
    print("=" * 60)

    # Load and optionally modify config
    cfg = OmegaConf.load(config_path)

    if steps is not None:
        cfg.trainer.training.steps = steps
        print(f"Overriding training steps: {steps}")

    # Save modified config temporarily
    temp_config = Path(config_path).parent / ".temp_config.yaml"
    OmegaConf.save(cfg, temp_config)

    try:
        # Setup and run training
        trainer = await setup_forge_training(str(temp_config))

        training_steps = cfg.trainer.training.get("steps", 1000)
        print(f"\nStarting training for {training_steps} steps...")
        print(f"Model: {cfg.model}")
        print(f"Group size: {cfg.group_size}")
        print(f"Server: {cfg.blackjack_env.get('server_url', 'http://localhost:8004')}")
        print("")

        metrics = await trainer.run(steps=training_steps)

        return trainer, metrics

    finally:
        # Cleanup temp config
        if temp_config.exists():
            temp_config.unlink()


async def run_evaluation(trainer, num_games: int = 100):
    """
    Evaluate trained policy.

    Args:
        trainer: GRPOTrainer instance
        num_games: Number of games to evaluate

    Returns:
        Evaluation results dict
    """
    print("\n" + "=" * 60)
    print("EVALUATION")
    print("=" * 60)

    # Use the trainer's policy to play games
    # This is a simplified evaluation - in production you'd use the full evaluation loop
    from .grpo_utils import play_random_policy

    server_url = trainer._cfg.get("blackjack_env", {}).get("server_url", "http://localhost:8004")

    print(f"\nEvaluating on {num_games} games...")
    print("Note: This uses random policy as placeholder - trained policy evaluation requires full loop")

    stats = play_random_policy(server_url, num_games=num_games)

    print(f"\nGames evaluated: {stats['total_games']}")
    print(f"Wins: {stats['wins']}")
    print(f"Losses: {stats['losses']}")
    print(f"Pushes: {stats['pushes']}")
    print(f"Win rate: {stats['win_rate']:.1%}")

    return stats


async def main():
    parser = argparse.ArgumentParser(
        description="Train BlackJack agents with GRPO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Number of training steps (overrides config)",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run evaluation after training",
    )
    parser.add_argument(
        "--eval-only",
        action="store_true",
        help="Only run evaluation (requires pre-trained model)",
    )
    parser.add_argument(
        "--eval-games",
        type=int,
        default=100,
        help="Number of games for evaluation (default: 100)",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run random policy benchmark before training",
    )
    parser.add_argument(
        "--benchmark-games",
        type=int,
        default=100,
        help="Number of games for benchmark (default: 100)",
    )
    parser.add_argument(
        "--explore",
        action="store_true",
        help="Explore the OpenEnv environment (no training)",
    )
    parser.add_argument(
        "--server-url",
        type=str,
        default=None,
        help="BlackJack server URL (overrides config)",
    )

    args = parser.parse_args()

    # Validate config exists
    config_path = Path(args.config)
    if not config_path.is_absolute():
        # Try relative to current directory first
        if not config_path.exists():
            # Try relative to script directory
            config_path = Path(__file__).parent / args.config

    if not config_path.exists():
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    # Load config to get server URL
    cfg = OmegaConf.load(str(config_path))
    server_url = args.server_url or cfg.blackjack_env.get("server_url", "http://localhost:8004")

    trainer = None

    try:
        # Run exploration if requested
        if args.explore:
            await run_exploration(server_url)
            return

        # Run benchmark if requested
        if args.benchmark:
            await run_benchmark(server_url, num_games=args.benchmark_games)

        # Run training
        if not args.eval_only:
            trainer, metrics = await run_training(
                str(config_path),
                steps=args.steps,
            )

        # Run evaluation if requested
        if args.eval or args.eval_only:
            if trainer is None:
                print("Error: --eval-only requires a pre-trained model")
                print("Run training first or provide a checkpoint")
                sys.exit(1)

            await run_evaluation(
                trainer,
                num_games=args.eval_games,
            )

        print("\n" + "=" * 60)
        print("DONE")
        print("=" * 60)

    finally:
        if trainer is not None:
            await trainer.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
