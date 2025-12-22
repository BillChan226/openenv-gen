"""
GRPO Training Infrastructure for BrowserGym Agents

This module provides the high-level training interface that wraps
all Forge infrastructure and exposes a simple API for training.
"""

import asyncio
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
from forge.types import LauncherConfig, ProvisionerConfig

from .data import Episode, collate
from .loss import simple_grpo_loss
from .actors import WebReward, ComputeAdvantages, WebEnvActor
from .rollout import play_web_task, setup_task_logger


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

    def __init__(self, services: Dict[str, Any], cfg: DictConfig):
        """
        Initialize trainer with Forge services.

        Args:
            services: Dict of initialized Forge services/actors
            cfg: Training configuration
        """
        self._services = services
        self._cfg = cfg
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
        server_url = web_env_cfg.get("server_url", "http://localhost:8005")
        benchmark = web_env_cfg.get("benchmark", "miniwob")
        task_name = web_env_cfg.get("task_name", "click-test")
        max_steps = web_env_cfg.get("max_steps", 15)

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
                all_step_results = []

                # Play a group of tasks
                for task_idx in range(group_size):
                    task_id = str(uuid.uuid4())[:8]
                    step_results = await play_web_task(
                        task_idx=task_idx,
                        task_id=task_id,
                        server_url=server_url,
                        policy=policy,
                        tokenizer=tokenizer,
                        task_log=task_log,
                        rollout_count=self._rollout_count,
                        max_steps=max_steps,
                        benchmark=benchmark,
                        task_name=task_name,
                    )
                    all_step_results.extend(step_results)

                # Create episodes from step results
                print(f"[TRAINER DEBUG] Creating {len(all_step_results)} episodes...")
                episodes = []
                input_ids = torch.ones(
                    (len(all_step_results), max_req_tokens + max_res_tokens),
                    dtype=torch.long,
                )

                for i, step_result in enumerate(all_step_results):
                    episode = Episode(
                        episode_id=str(uuid.uuid4()),
                        pad_id=pad_id,
                        request_len=max_req_tokens,
                        response_len=max_res_tokens,
                        task_id=step_result["task_id"],
                        step_in_task=step_result["step_num"],
                        completion=step_result["response"],
                    )

                    # Compute shaped reward
                    print(f"[TRAINER DEBUG] Computing reward for episode {i+1}/{len(all_step_results)}...")
                    episode.reward = await reward_actor.evaluate_response.route(
                        prompt=step_result["prompt"],
                        response=step_result["response"].text,
                        task_reward=step_result["final_reward"],
                        step_count=step_result["step_count"],
                        max_steps=step_result["max_steps"],
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
                print(f"[TRAINER DEBUG] Adding episodes to replay buffer...")
                for episode, advantage in zip(episodes, advantages):
                    episode.advantage = advantage
                    await replay_buffer.add.call_one(episode)
                print(f"[TRAINER DEBUG] Episodes added to replay buffer")

                self._rollout_count += 1

                # Log rollout stats
                successes = sum(1 for e in episodes if e.reward > 0)
                success_rate = successes / len(episodes) if episodes else 0
                avg_reward = sum(e.reward for e in episodes) / len(episodes) if episodes else 0

                print(
                    f"Rollout {self._rollout_count}: "
                    f"{len(episodes)} episodes, "
                    f"success rate: {success_rate:.1%}, "
                    f"avg reward: {avg_reward:.2f}"
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
        num_tasks: int = 50,
        task_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate current policy on web tasks.

        Args:
            num_tasks: Number of tasks to evaluate on
            task_name: Task to evaluate (default: from config)

        Returns:
            Evaluation metrics
        """
        from .rollout import play_web_task

        policy = self._services["policy"]
        tokenizer = self._services["tokenizer"]

        web_env_cfg = self._cfg.get("web_env", {})
        server_url = web_env_cfg.get("server_url", "http://localhost:8005")
        benchmark = web_env_cfg.get("benchmark", "miniwob")
        task = task_name or web_env_cfg.get("task_name", "click-test")
        max_steps = web_env_cfg.get("max_steps", 15)

        task_log = lambda msg: print(msg)  # Simple logging for eval

        successes = 0
        total_reward = 0
        total_steps = 0

        for i in range(num_tasks):
            task_id = str(uuid.uuid4())[:8]
            results = await play_web_task(
                task_idx=i,
                task_id=task_id,
                server_url=server_url,
                policy=policy,
                tokenizer=tokenizer,
                task_log=task_log,
                max_steps=max_steps,
                benchmark=benchmark,
                task_name=task,
            )

            if results:
                final_reward = results[0]["final_reward"]
                step_count = results[0]["step_count"]

                if final_reward > 0:
                    successes += 1
                total_reward += final_reward
                total_steps += step_count

        return {
            "task": task,
            "num_tasks": num_tasks,
            "successes": successes,
            "success_rate": successes / num_tasks,
            "avg_reward": total_reward / num_tasks,
            "avg_steps": total_steps / num_tasks,
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
        ).as_actor(**cfg.get("web_env", {})),
        Generator.options(**cfg.services.policy).as_service(**cfg.policy),
        RLTrainer.options(**cfg.actors.trainer).as_actor(
            **cfg.trainer, loss=simple_grpo_loss
        ),
        ReplayBuffer.options(**cfg.actors.replay_buffer).as_actor(
            **cfg.replay_buffer, collate=collate
        ),
        ComputeAdvantages.options(**cfg.actors.compute_advantages).as_actor(),
        ReferenceModel.options(**cfg.services.ref_model).as_service(**cfg.ref_model),
        WebReward.options(**cfg.actors.reward_actor).as_actor(),
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

    return GRPOWebTrainer(services, cfg)
