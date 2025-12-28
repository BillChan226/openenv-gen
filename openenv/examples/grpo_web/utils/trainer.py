import asyncio
import random
import time
import uuid
from typing import Any, Dict, List, Optional

import torch
import torchstore as ts
from omegaconf import DictConfig, OmegaConf

from forge.actors._torchstore_utils import (
    get_dcp_whole_state_dict_key,
    get_param_prefix,
)
from forge.actors.generator import Generator
from forge.actors.reference_model import ReferenceModel
from forge.actors.replay_buffer import ReplayBuffer
from forge.actors.trainer import RLTrainer
from forge.controller.provisioner import init_provisioner, shutdown
from forge.observability.metric_actors import get_or_create_metric_logger
from forge.observability.metrics import Reduce, record_metric
from forge.types import LauncherConfig, ProvisionerConfig

from .data import Episode, collate
from .loss import simple_grpo_loss
from .actors import WebReward, ComputeAdvantages, WebEnvActor
from .rollout import play_web_task, play_web_task_parallel, setup_task_logger
from .env_pool import EnvironmentPool, create_pool_from_config
from .tasks import get_tasks_by_category, MINIWOB_ALL_TASKS_UNIQUE


async def drop_weights(version: int) -> None:
    """
    Drop old model weights from torchstore to free memory.

    Args:
        version: Weight version to drop
    """
    print(f"Dropping weights @ version {version}")
    start_time = time.perf_counter()

    prefix = get_param_prefix(version)
    matching_keys = await ts.keys(prefix)
    dcp_key = get_dcp_whole_state_dict_key(version)

    if dcp_key in matching_keys:
        dcp_handle = await ts.get(dcp_key)
        dcp_handle.drop()

    for key in matching_keys:
        await ts.delete(key)

    elapsed = time.perf_counter() - start_time
    print(f"Dropped weights @ version {version}, took {elapsed:.2f}s")


class GRPOWebTrainer:
    """
    High-level interface for GRPO training on web navigation tasks.

    This class wraps all Forge infrastructure (provisioner, services, actors)
    and provides a simple interface for training web agents.

    Example usage:
        trainer = await setup_forge_training("web.yaml")
        metrics = await trainer.run(steps=1000)
        await trainer.shutdown()
    """

    def __init__(self, services: Dict[str, Any], cfg: DictConfig, env_pool: EnvironmentPool):
        """
        Initialize trainer with Forge services.

        Args:
            services: Dict of initialized Forge services/actors
            cfg: Training configuration
            env_pool: Shared environment pool for all server connections
        """
        self._services = services
        self._cfg = cfg
        self._env_pool = env_pool
        self._shutdown_event = asyncio.Event()
        self._training_step = 0
        self._rollout_count = 0

    @property
    def policy(self):
        """Access the trained policy for inference."""
        return self._services["policy"]

    @property
    def training_step(self) -> int:
        """Current training step."""
        return self._training_step

    @property
    def rollout_count(self) -> int:
        """Number of completed rollouts."""
        return self._rollout_count

    async def run(
        self,
        steps: int,
        log_interval: int = 10,
        checkpoint_interval: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run GRPO training for specified number of steps.

        This runs two concurrent loops:
        1. Rollout loop: Plays web tasks and collects episodes
        2. Training loop: Samples from replay buffer and updates policy

        Args:
            steps: Number of training steps to run
            log_interval: How often to log progress
            checkpoint_interval: How often to save checkpoints (None = use config)

        Returns:
            Dict of training metrics
        """
        # Unpack services
        policy = self._services["policy"]
        trainer = self._services["trainer"]
        replay_buffer = self._services["replay_buffer"]
        compute_advantages = self._services["compute_advantages"]
        ref_model = self._services["ref_model"]
        reward_actor = self._services["reward_actor"]
        tokenizer = self._services["tokenizer"]
        pad_id = self._services["pad_id"]
        mlogger = self._services["mlogger"]

        # Training parameters
        group_size = self._cfg.group_size
        max_req_tokens = self._cfg.max_req_tokens
        max_res_tokens = self._cfg.max_res_tokens

        web_env_cfg = self._cfg.get("web_env", {})
        benchmark = web_env_cfg.get("benchmark", "miniwob")
        default_task_name = web_env_cfg.get("task_name", "click-test")
        max_steps = web_env_cfg.get("max_steps", 15)

        # Use the shared environment pool
        env_pool = self._env_pool
        print(f"Environment pool: {env_pool.capacity} server(s) available")

        # Build task pool for random sampling during training
        task_pool_cfg = web_env_cfg.get("task_pool", None)
        if task_pool_cfg is None:
            # No task pool specified, use single task
            task_pool = [default_task_name]
        elif isinstance(task_pool_cfg, str):
            # String like "easy", "medium", "hard", "all", or combined like "easy+medium"
            if "+" in task_pool_cfg:
                # Combined categories: "easy+medium" -> easy tasks + medium tasks
                task_pool = []
                for category in task_pool_cfg.split("+"):
                    category = category.strip()
                    tasks = get_tasks_by_category(category)
                    if tasks:
                        task_pool.extend(tasks)
                # Deduplicate while preserving order
                task_pool = list(dict.fromkeys(task_pool))
            else:
                task_pool = get_tasks_by_category(task_pool_cfg)
            if not task_pool:
                print(f"Warning: Unknown task_pool '{task_pool_cfg}', using default task")
                task_pool = [default_task_name]
        elif hasattr(task_pool_cfg, '__iter__') and not isinstance(task_pool_cfg, str):
            # Direct list of task names (handles both list and OmegaConf ListConfig)
            task_pool = list(task_pool_cfg)
        else:
            task_pool = [default_task_name]

        print(f"Task pool: {len(task_pool)} tasks")
        if len(task_pool) <= 10:
            print(f"  Tasks: {task_pool}")
        else:
            print(f"  First 10: {task_pool[:10]}...")

        task_log = setup_task_logger()

        # Metrics tracking
        metrics = {
            "training_steps": [],
            "success_rates": [],
            "avg_rewards": [],
            "rollout_counts": [],
        }

        async def continuous_rollouts():
            """Rollout loop: play tasks and collect episodes."""
            while not self._shutdown_event.is_set():
                # GRPO: Sample ONE task and run group_size rollouts on it
                current_task = random.choice(task_pool)
                # Create list with same task repeated for all rollouts in the group
                rollout_tasks = [current_task] * group_size

                # The pool automatically limits concurrency to available servers
                all_step_results = await play_web_task_parallel(
                    num_tasks=group_size,
                    env_pool=env_pool,
                    policy=policy,
                    tokenizer=tokenizer,
                    task_log=task_log,
                    task_names=rollout_tasks,
                    rollout_count=self._rollout_count,
                    max_steps=max_steps,
                    benchmark=benchmark,
                )

                # Create episodes from step results
                # Generate a unique group ID (uid) for this rollout batch
                # All episodes in this batch share the same uid for GRPO grouping
                group_uid = str(uuid.uuid4())

                # print(f"[TRAINER DEBUG] Creating {len(all_step_results)} episodes...")
                episodes = []
                input_ids = torch.ones(
                    (len(all_step_results), max_req_tokens + max_res_tokens),
                    dtype=torch.long,
                )

                for i, step_result in enumerate(all_step_results):
                    # Extract old_logprobs from completion (log probs at generation time)
                    completion = step_result["response"]
                    old_logprobs = completion.logprobs if completion.logprobs is not None else None

                    episode = Episode(
                        episode_id=str(uuid.uuid4()),
                        pad_id=pad_id,
                        request_len=max_req_tokens,
                        response_len=max_res_tokens,
                        task_id=step_result["task_id"],
                        traj_uid=step_result["traj_uid"],  # Trajectory ID (shared by all steps in same trajectory)
                        uid=group_uid,  # Group ID (shared by all episodes in this GRPO batch)
                        step_in_task=step_result["step_num"],
                        completion=completion,
                        old_logprobs=old_logprobs,  # Log probs from policy at rollout time
                    )

                    # Compute shaped reward
                    print(f"[TRAINER DEBUG] Computing reward for episode {i+1}/{len(all_step_results)}...")
                    episode.reward = await reward_actor.evaluate_response.route(
                        prompt=step_result["prompt"],
                        response=step_result["response"].text,
                        task_reward=step_result["final_reward"],
                        step_count=step_result["step_count"],
                        max_steps=step_result["max_steps"],
                        had_error=step_result.get("had_error", False),
                    )
                    print(f"[TRAINER DEBUG] Episode {i+1} reward: {episode.reward}")

                    episodes.append(episode)
                    input_ids[i, :max_req_tokens] = episode.request_tensor
                    input_ids[i, max_req_tokens:] = episode.response_tensor

                # Get reference model log probabilities
                print(f"[TRAINER DEBUG] Getting ref model logprobs for {len(episodes)} episodes...")
                ref_logprobs = await ref_model.forward.route(
                    input_ids, max_req_tokens, return_logprobs=True
                )
                print(f"[TRAINER DEBUG] Got ref logprobs")
                for i, episode in enumerate(episodes):
                    episode.ref_logprobs = ref_logprobs[i]

                # Compute group-relative advantages
                print(f"[TRAINER DEBUG] Computing advantages...")
                advantages = await compute_advantages.compute.call_one(episodes)

                # CRITICAL FIX: Skip groups with zero variance (no learning signal)
                if advantages is None:
                    print(f"[TRAINER] Skipping rollout {self._rollout_count + 1}: zero-variance group")
                    self._rollout_count += 1
                    continue

                # print(f"[TRAINER DEBUG] Adding episodes to replay buffer...")
                for episode, advantage in zip(episodes, advantages):
                    episode.advantage = advantage
                    await replay_buffer.add.call_one(episode)
                # print(f"[TRAINER DEBUG] Episodes added to replay buffer")

                self._rollout_count += 1

                traj_rewards = {}
                for e in episodes:
                    if e.traj_uid not in traj_rewards:
                        traj_rewards[e.traj_uid] = e.reward

                num_trajectories = len(traj_rewards)
                successes = sum(1 for r in traj_rewards.values() if r > 0)
                success_rate = successes / num_trajectories if num_trajectories else 0
                avg_reward = sum(traj_rewards.values()) / num_trajectories if num_trajectories else 0

                print(
                    f"Rollout {self._rollout_count}: "
                    f"{num_trajectories} trajectories ({len(episodes)} episodes), "
                    f"success rate: {success_rate:.1%}, "
                    f"avg reward: {avg_reward:.2f}"
                )

                # Log to wandb
                record_metric("train/success_rate", success_rate, Reduce.MEAN)
                record_metric("train/avg_reward", avg_reward, Reduce.MEAN)
                record_metric("train/episodes_per_rollout", len(episodes), Reduce.MEAN)
                record_metric("train/trajectories_per_rollout", num_trajectories, Reduce.MEAN)

        # Get evaluation config
        eval_cfg = self._cfg.get("evaluation", {})
        eval_interval = eval_cfg.get("eval_interval", 0)  # 0 means no eval
        eval_tasks = eval_cfg.get("eval_tasks", 64)
        eval_quiet = eval_cfg.get("quiet", True)

        if eval_interval > 0:
            print(f"Evaluation: every {eval_interval} steps, {eval_tasks} tasks")
            # Run initial evaluation before training starts
            print(f"\n[Step 0] Running initial evaluation (before training)...")
            await self.evaluate(
                num_tasks=eval_tasks,
                quiet=eval_quiet,
                log_to_wandb=True,
            )

        async def continuous_training():
            """Training loop: sample and update policy."""
            while self._training_step < steps:
                # Sample batch from replay buffer
                batch = await replay_buffer.sample.call_one(
                    curr_policy_version=self._training_step
                )
                if batch is None:
                    await asyncio.sleep(0.1)
                    continue

                # Training step
                inputs, targets = batch
                await trainer.train_step.call(inputs, targets)
                self._training_step += 1

                # Push updated weights
                await trainer.push_weights.call(self._training_step)
                await policy.update_weights.fanout(self._training_step)

                # Drop old weights to free memory
                if self._training_step >= 2:
                    await drop_weights(self._training_step - 1)

                # Flush metrics
                await mlogger.flush.call_one(self._training_step)

                # Log progress
                if self._training_step % log_interval == 0:
                    print(f"Training step {self._training_step}/{steps}")

                # Periodic evaluation
                if eval_interval > 0 and self._training_step % eval_interval == 0:
                    print(f"\n[Step {self._training_step}] Running evaluation...")
                    await self.evaluate(
                        num_tasks=eval_tasks,
                        quiet=eval_quiet,
                        log_to_wandb=True,
                    )

            print(f"\nTraining complete! {steps} steps finished.")

        # Run both loops concurrently
        rollout_task = asyncio.create_task(continuous_rollouts())
        training_task = asyncio.create_task(continuous_training())

        try:
            await training_task
        finally:
            self._shutdown_event.set()
            try:
                await asyncio.wait_for(rollout_task, timeout=5)
            except asyncio.TimeoutError:
                rollout_task.cancel()

        return metrics

    async def evaluate(
        self,
        num_tasks: int = 64,
        task_name: Optional[str] = None,
        use_task_pool: bool = True,
        quiet: bool = False,
        log_to_wandb: bool = True,
    ) -> Dict[str, Any]:
        """
        Evaluate current policy on web tasks.

        This is a held-out evaluation that runs a fixed number of tasks
        and computes success rate with num_tasks as the denominator.

        Uses the shared environment pool to avoid conflicts with training rollouts.

        Args:
            num_tasks: Number of tasks to evaluate on (denominator for success rate)
            task_name: Specific task to evaluate (if None, samples from task_pool)
            use_task_pool: If True and task_name is None, sample from task_pool
            quiet: If True, suppress per-task logging
            log_to_wandb: If True, record metrics to wandb

        Returns:
            Evaluation metrics dict with success_rate, avg_reward, etc.
        """
        policy = self._services["policy"]
        tokenizer = self._services["tokenizer"]
        env_pool = self._env_pool

        web_env_cfg = self._cfg.get("web_env", {})
        benchmark = web_env_cfg.get("benchmark", "miniwob")
        max_steps = web_env_cfg.get("max_steps", 15)

        # Build task pool for evaluation
        if task_name:
            eval_task_pool = [task_name]
        elif use_task_pool:
            task_pool_cfg = web_env_cfg.get("task_pool", None)
            if task_pool_cfg is None:
                eval_task_pool = [web_env_cfg.get("task_name")]
            elif isinstance(task_pool_cfg, str):
                if "+" in task_pool_cfg:
                    eval_task_pool = []
                    for category in task_pool_cfg.split("+"):
                        tasks = get_tasks_by_category(category.strip())
                        if tasks:
                            eval_task_pool.extend(tasks)
                    eval_task_pool = list(dict.fromkeys(eval_task_pool))
                else:
                    eval_task_pool = get_tasks_by_category(task_pool_cfg)
                if not eval_task_pool:
                    eval_task_pool = [web_env_cfg.get("task_name")]
            elif hasattr(task_pool_cfg, '__iter__') and not isinstance(task_pool_cfg, str):
                eval_task_pool = list(task_pool_cfg)
            else:
                eval_task_pool = [web_env_cfg.get("task_name")]
        else:
            eval_task_pool = [web_env_cfg.get("task_name")]

        task_log = (lambda msg: None) if quiet else (lambda msg: print(msg))

        print(f"\n{'='*60}")
        print(f"EVALUATION: {num_tasks} tasks (from {len(eval_task_pool)} task types)")
        print(f"Using shared pool with {env_pool.capacity} server(s)")
        print(f"Task pool sample: {eval_task_pool[:5]}..." if len(eval_task_pool) > 5 else f"Task pool: {eval_task_pool}")
        print(f"{'='*60}")

        # Deterministic task selection: use first N tasks from pool (cycling if needed)
        # This ensures consistent evaluation across training runs
        eval_task_names = []
        for i in range(num_tasks):
            eval_task_names.append(eval_task_pool[i % len(eval_task_pool)])

        # Run all evaluation tasks using the shared pool
        # The pool limits concurrency and prevents conflicts with training
        all_results = await play_web_task_parallel(
            num_tasks=num_tasks,
            env_pool=env_pool,
            policy=policy,
            tokenizer=tokenizer,
            task_log=task_log,
            rollout_count=-1,  # Mark as evaluation
            max_steps=max_steps,
            benchmark=benchmark,
            task_names=eval_task_names,
        )

        # Process results - group by task_id to get per-task outcomes
        task_results_map: Dict[str, Dict[str, Any]] = {}
        for result in all_results:
            task_id = result["task_id"]
            if task_id not in task_results_map:
                task_results_map[task_id] = {
                    "task": eval_task_names[len(task_results_map) % len(eval_task_names)],
                    "final_reward": result["final_reward"],
                    "step_count": result["step_count"],
                    "success": result["final_reward"] > 0,
                }

        # Calculate metrics
        task_results = list(task_results_map.values())
        successes = sum(1 for r in task_results if r["success"])
        total_reward = sum(r["final_reward"] for r in task_results)
        total_steps = sum(r["step_count"] for r in task_results)

        # Handle case where we have fewer results than expected
        actual_num_tasks = len(task_results)
        if actual_num_tasks < num_tasks:
            print(f"  Warning: Only {actual_num_tasks}/{num_tasks} tasks completed")

        success_rate = successes / actual_num_tasks if actual_num_tasks > 0 else 0
        avg_reward = total_reward / actual_num_tasks if actual_num_tasks > 0 else 0
        avg_steps = total_steps / actual_num_tasks if actual_num_tasks > 0 else 0

        # Log per-task results if not quiet
        if not quiet:
            for i, result in enumerate(task_results):
                if result["success"]:
                    print(f"  [EVAL] Task {i} ({result['task']}): SUCCESS in {result['step_count']} steps")
                else:
                    print(f"  [EVAL] Task {i} ({result['task']}): FAILED, reward={result['final_reward']}")

        print(f"\n{'='*60}")
        print(f"EVAL RESULTS: {successes}/{actual_num_tasks} = {success_rate:.1%} success rate")
        print(f"Avg reward: {avg_reward:.3f}, Avg steps: {avg_steps:.1f}")
        print(f"{'='*60}\n")

        # Log to wandb
        if log_to_wandb:
            record_metric("eval/success_rate", success_rate, Reduce.MEAN)
            record_metric("eval/avg_reward", avg_reward, Reduce.MEAN)
            record_metric("eval/successes", successes, Reduce.SUM)
            record_metric("eval/num_tasks", actual_num_tasks, Reduce.MEAN)

        return {
            "num_tasks": actual_num_tasks,
            "successes": successes,
            "success_rate": success_rate,
            "avg_reward": avg_reward,
            "avg_steps": avg_steps,
            "task_results": task_results,
        }

    async def shutdown(self):
        """Shutdown all Forge services."""
        self._shutdown_event.set()
        await shutdown()


async def setup_forge_training(config_path: str) -> GRPOWebTrainer:
    """
    Setup Forge GRPO training infrastructure for web navigation.

    This function initializes all Forge services and actors needed
    for training.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        GRPOWebTrainer instance ready for training
    """

    # Load configuration
    cfg = OmegaConf.load(config_path)

    print("Initializing Forge infrastructure...")
    print("")

    # Initialize provisioner (manages distributed resources)
    if cfg.get("provisioner", None) is not None:
        provisioner = await init_provisioner(
            ProvisionerConfig(launcher_config=LauncherConfig(**cfg.provisioner))
        )
    else:
        provisioner = await init_provisioner()
    print("  [OK] Provisioner")

    # Initialize metric logging
    metric_logging_cfg = cfg.get("metric_logging", {"console": {"log_per_rank": False}})
    mlogger = await get_or_create_metric_logger()
    await mlogger.init_backends.call_one(metric_logging_cfg)
    print("  [OK] Metric Logger")

    # Initialize services in parallel for faster startup
    print("")
    print("  Initializing services...")

    # Filter web_env config for WebEnvActor (remove task_pool which is only used in trainer)
    web_env_cfg = dict(cfg.get("web_env", {}))
    web_env_cfg.pop("task_pool", None)  # task_pool is handled in GRPOWebTrainer.run()

    # Create environment pool from config (shared by training and evaluation)
    env_pool = create_pool_from_config(cfg.get("web_env", {}))
    print(f"  [OK] Environment pool: {env_pool.capacity} server(s)")

    # Start all services concurrently
    (
        env_actor,
        policy,
        trainer,
        replay_buffer,
        compute_advantages,
        ref_model,
        reward_actor,
    ) = await asyncio.gather(
        WebEnvActor.options(
            **cfg.actors.get("web_env", cfg.actors.get("env_actor", {}))
        ).as_actor(**web_env_cfg),
        Generator.options(**cfg.services.policy).as_service(**cfg.policy),
        RLTrainer.options(**cfg.actors.trainer).as_actor(
            **cfg.trainer, loss=simple_grpo_loss
        ),
        ReplayBuffer.options(**cfg.actors.replay_buffer).as_actor(
            **cfg.replay_buffer, collate=collate
        ),
        ComputeAdvantages.options(**cfg.actors.compute_advantages).as_actor(),
        ReferenceModel.options(**cfg.services.ref_model).as_service(**cfg.ref_model),
        WebReward.options(**cfg.services.reward_actor).as_service(),
    )

    print("  [OK] All services initialized")

    # Initialize torchstore (distributed weight storage)
    trainer_num_procs = cfg.actors.trainer["procs"]
    trainer_host_mesh_name = cfg.actors.trainer["mesh_name"]
    trainer_hosts = provisioner.get_host_mesh(trainer_host_mesh_name)
    await ts.initialize(
        mesh=trainer_hosts.spawn_procs(per_host={"procs": trainer_num_procs}),
        strategy=ts.LocalRankStrategy(),
    )
    print("  [OK] Torchstore")

    # Get tokenizer from environment actor
    tokenizer = await env_actor.get_tokenizer.call_one()
    pad_id = await env_actor.pad_token.call_one()

    print("")
    print("Forge ready for training!")
    print("")

    # Package all services
    services = {
        "provisioner": provisioner,
        "mlogger": mlogger,
        "env_actor": env_actor,
        "policy": policy,
        "trainer": trainer,
        "replay_buffer": replay_buffer,
        "compute_advantages": compute_advantages,
        "ref_model": ref_model,
        "reward_actor": reward_actor,
        "tokenizer": tokenizer,
        "pad_id": pad_id,
    }

    return GRPOWebTrainer(services, cfg, env_pool)
