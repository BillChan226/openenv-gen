import argparse
import asyncio
import sys
from pathlib import Path
from omegaconf import OmegaConf

# Add src to path for envs imports
_src_path = Path(__file__).parent.parent.parent / "src"
if _src_path.exists() and str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

# Import from utils subpackage
from .utils.rollout import play_random_web_policy, play_heuristic_web_policy
from .utils.trainer import setup_forge_training


async def run_benchmark(server_url: str, num_tasks: int = 50):
    """Run random policy benchmark."""

    print("\n" + "=" * 60)
    print("BASELINE BENCHMARK")
    print("=" * 60)

    print("\nRandom policy:")
    random_stats = play_random_web_policy(server_url, num_tasks=num_tasks)
    print(f"  Success rate: {random_stats['success_rate']:.1%}")
    print(f"  Avg steps: {random_stats['avg_steps']:.1f}")

    print("\nHeuristic policy:")
    heuristic_stats = play_heuristic_web_policy(server_url, num_tasks=num_tasks)
    print(f"  Success rate: {heuristic_stats['success_rate']:.1%}")

    return random_stats, heuristic_stats


async def run_training(config_path: str, steps: int = None, task_name: str = None):
    """Run GRPO training."""

    print("\n" + "=" * 60)
    print("GRPO WEB AGENT TRAINING")
    print("=" * 60)

    # Load and optionally modify config
    cfg = OmegaConf.load(config_path)

    if steps is not None:
        cfg.trainer.training.steps = steps
        print(f"Overriding training steps: {steps}")

    if task_name is not None:
        cfg.web_env.task_name = task_name
        print(f"Overriding task: {task_name}")

    # Save modified config temporarily
    temp_config = Path(config_path).parent / ".temp_config.yaml"
    OmegaConf.save(cfg, temp_config)

    try:
        # Setup and run training
        trainer = await setup_forge_training(str(temp_config))

        training_steps = cfg.trainer.training.get("steps", 1000)
        print(f"\nStarting training for {training_steps} steps...")
        print(f"Task: {cfg.web_env.get('task_name', 'click-test')}")
        print(f"Benchmark: {cfg.web_env.get('benchmark', 'miniwob')}")
        print("")

        metrics = await trainer.run(steps=training_steps)

        return trainer, metrics

    finally:
        # Cleanup temp config
        if temp_config.exists():
            temp_config.unlink()


async def run_evaluation(trainer, num_tasks: int = 50, task_name: str = None):
    """Run evaluation on trained policy."""
    print("\n" + "=" * 60)
    print("EVALUATION")
    print("=" * 60)

    results = await trainer.evaluate(num_tasks=num_tasks, task_name=task_name)

    print(f"\nTask: {results['task']}")
    print(f"Tasks evaluated: {results['num_tasks']}")
    print(f"Success rate: {results['success_rate']:.1%}")
    print(f"Avg reward: {results['avg_reward']:.2f}")
    print(f"Avg steps: {results['avg_steps']:.1f}")

    return results


async def main():
    parser = argparse.ArgumentParser(
        description="Train web navigation agents with GRPO",
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
        "--task",
        type=str,
        default=None,
        help="MiniWoB task name (overrides config)",
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
        "--eval-tasks",
        type=int,
        default=50,
        help="Number of tasks for evaluation (default: 50)",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run random policy benchmark before training",
    )
    parser.add_argument(
        "--server-url",
        type=str,
        default=None,
        help="BrowserGym server URL (overrides config)",
    )

    args = parser.parse_args()

    # Validate config exists
    if not Path(args.config).exists():
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    # Load config to get server URL
    from omegaconf import OmegaConf
    cfg = OmegaConf.load(args.config)
    server_url = args.server_url or cfg.web_env.get("server_url", "http://localhost:8005")

    trainer = None

    try:
        # Run benchmark if requested
        if args.benchmark:
            await run_benchmark(server_url)

        # Run training
        if not args.eval_only:
            trainer, metrics = await run_training(
                args.config,
                steps=args.steps,
                task_name=args.task,
            )

        # Run evaluation if requested
        if args.eval or args.eval_only:
            if trainer is None:
                print("Error: --eval-only requires a pre-trained model")
                print("Run training first or provide a checkpoint")
                sys.exit(1)

            await run_evaluation(
                trainer,
                num_tasks=args.eval_tasks,
                task_name=args.task,
            )

        print("\n" + "=" * 60)
        print("DONE")
        print("=" * 60)

    finally:
        if trainer is not None:
            await trainer.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
