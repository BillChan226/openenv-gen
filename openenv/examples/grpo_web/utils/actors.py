from dataclasses import dataclass
from typing import List, Optional

import torch
from forge.controller.actor import ForgeActor
from forge.observability.metrics import Reduce, record_metric
from monarch.actor import endpoint
from vllm.transformers_utils.tokenizer import get_tokenizer

from .data import Episode, Group


@dataclass
class WebReward(ForgeActor):
    """
    Reward actor for evaluating web navigation outcomes.

    Computes shaped rewards based on TRAJECTORY OUTCOME ONLY.

    IMPORTANT: All steps in a trajectory MUST receive the same reward
    for GRPO advantage computation to work correctly. This means:
    - NO per-step penalties (errors, noop)
    - Only final outcome (success/failure) + efficiency bonus

    The efficiency bonus is based on total trajectory length, so all
    steps in the same trajectory get the identical reward.
    """

    # Reward shaping parameters
    success_reward: float = 2.0
    failure_reward: float = -0.5
    efficiency_bonus_scale: float = 0.5
    # NOTE: error_penalty removed - was causing reward inconsistency within trajectories

    @endpoint
    async def evaluate_response(
        self,
        prompt: str,
        response: str,
        task_reward: float,
        step_count: int,
        max_steps: int,
        had_error: bool = False,  # Kept for API compatibility but NOT used
    ) -> float:
        """
        Evaluate trajectory reward (same for ALL steps in trajectory).

        Reward is computed based on:
        1. Task outcome (success/failure)
        2. Efficiency bonus (for success only)

        CRITICAL: This returns the SAME reward for all steps in a trajectory.
        The had_error and response parameters are kept for API compatibility
        but are NOT used in reward computation to ensure consistency.

        Args:
            prompt: Page state prompt (unused)
            response: Model's action string (unused for reward)
            task_reward: Raw task outcome (1.0 for success, 0.0 for failure)
            step_count: Total steps taken in trajectory
            max_steps: Maximum allowed steps
            had_error: Whether action caused error (unused - for API compat)

        Returns:
            Shaped reward value (identical for all steps in same trajectory)
        """
        # Base reward from task outcome
        if task_reward > 0:
            # Success: base reward + efficiency bonus
            efficiency = 1.0 - (step_count / max_steps)
            reward = self.success_reward + (self.efficiency_bonus_scale * efficiency)
        else:
            # Failure: flat penalty (no per-step penalties!)
            reward = self.failure_reward

        # NOTE: We intentionally do NOT penalize per-step errors or noops here.
        # Doing so would create inconsistent rewards within a trajectory,
        # which breaks the GRPO advantage computation.
        # The model learns to avoid errors through the relative advantage:
        # trajectories with fewer errors are more likely to succeed.

        # Record metrics for monitoring
        record_metric("reward/avg_reward", reward, Reduce.MEAN)
        record_metric("reward/sum_reward", reward, Reduce.SUM)
        record_metric("reward/success_rate", 1.0 if task_reward > 0 else 0.0, Reduce.MEAN)

        return reward

    @endpoint
    async def evaluate_batch(
        self,
        episodes: List[dict],
    ) -> List[float]:
        """
        Evaluate rewards for a batch of episodes.

        Args:
            episodes: List of episode dicts with task_reward, step_count, etc.

        Returns:
            List of shaped rewards
        """
        rewards = []
        for ep in episodes:
            reward = await self.evaluate_response(
                prompt=ep.get("prompt", ""),
                response=ep.get("response", ""),
                task_reward=ep.get("task_reward", 0.0),
                step_count=ep.get("step_count", 1),
                max_steps=ep.get("max_steps", 15),
                had_error=ep.get("had_error", False),
            )
            rewards.append(reward)
        return rewards


@dataclass
class WebRewardWithFormatPenalty(ForgeActor):
    """
    Extended reward actor - DEPRECATED, use WebReward instead.

    WARNING: Per-step penalties break GRPO advantage computation.
    This class is kept for backwards compatibility but should NOT be used.
    All steps in a trajectory MUST have the same reward.
    """

    success_reward: float = 2.0
    failure_reward: float = -0.5
    efficiency_bonus_scale: float = 0.5

    @endpoint
    async def evaluate_response(
        self,
        prompt: str,
        response: str,
        task_reward: float,
        step_count: int,
        max_steps: int,
        action_history: Optional[List[str]] = None,
        valid_bids: Optional[List[str]] = None,
    ) -> float:
        """
        Evaluate trajectory reward (same for ALL steps).

        NOTE: action_history and valid_bids are kept for API compatibility
        but are NOT used. Per-step penalties break GRPO.
        """
        # Base reward from task outcome ONLY
        if task_reward > 0:
            efficiency = 1.0 - (step_count / max_steps)
            reward = self.success_reward + (self.efficiency_bonus_scale * efficiency)
        else:
            reward = self.failure_reward

        # NOTE: All per-step penalties removed to ensure consistent
        # rewards within a trajectory for GRPO

        record_metric("reward/avg_reward", reward, Reduce.MEAN)
        return reward


@dataclass
class ComputeAdvantages(ForgeActor):
    """
    Actor for computing group-relative advantages at the TRAJECTORY level.

    GRPO uses group-relative normalization instead of absolute baselines.

    IMPORTANT: This computes advantages per TRAJECTORY (not per step).
    - Episodes are grouped by their `traj_uid` (trajectory identifier)
    - One reward per trajectory is used for normalization
    - The resulting advantage is broadcast to ALL steps in that trajectory

    This is the correct implementation matching verl-agent's approach,
    avoiding the bias toward longer trajectories that occurs when
    treating steps as independent samples.

    CRITICAL FIX: Returns None when all trajectories have the same reward
    (zero variance), as there's no learning signal in this case.
    """

    eps: float = 1e-4  # Numerical stability constant
    min_std_threshold: float = 1e-6  # Minimum std to consider group valid

    @endpoint
    async def compute(self, group: Group) -> Optional[List[float]]:
        """
        Compute trajectory-level advantages and broadcast to steps.

        Algorithm:
        1. Group episodes by traj_uid (trajectory identifier)
        2. Get ONE reward per trajectory (all steps have same final reward)
        3. Compute mean and std over trajectories (not steps)
        4. If std < threshold, return None (skip this batch - no learning signal)
        5. Compute advantage per trajectory
        6. Broadcast each trajectory's advantage to all its steps

        Formula (per trajectory): advantage_traj = (reward_traj - mean) / (std + eps)

        Args:
            group: List of episodes from same rollout group (may contain
                   multiple steps from multiple trajectories)

        Returns:
            List of advantage values (same order as input episodes),
            or None if group should be skipped (zero variance)
        """
        from collections import defaultdict

        # Step 1: Group episodes by trajectory
        traj_to_episodes: dict[str, List[Episode]] = defaultdict(list)
        for ep in group:
            traj_to_episodes[ep.traj_uid].append(ep)

        # Step 2: Get ONE reward per trajectory
        # All steps in a trajectory have the same reward (final outcome)
        traj_rewards: dict[str, float] = {}
        for traj_uid, episodes in traj_to_episodes.items():
            # Use the first episode's reward (should all be the same)
            traj_rewards[traj_uid] = episodes[0].reward

        # Step 3: Compute mean and std over TRAJECTORIES
        reward_values = list(traj_rewards.values())
        rewards_tensor = torch.tensor(reward_values, dtype=torch.float32)

        mean = rewards_tensor.mean()

        # Handle edge cases:
        # - Single trajectory: no relative signal, skip
        # - All same rewards (std ~= 0): no relative signal, skip
        if len(reward_values) <= 1:
            print(f"[ADVANTAGES] Skipping group with only {len(reward_values)} trajectory(ies)")
            return None

        std = rewards_tensor.std()

        # CRITICAL FIX: Skip groups with zero/near-zero variance
        # When all trajectories have the same reward, there's no learning signal
        if std < self.min_std_threshold:
            print(f"[ADVANTAGES] Skipping zero-variance group: all rewards = {reward_values[0]:.3f}")
            return None

        # Step 4: Compute advantage per trajectory
        traj_advantages: dict[str, float] = {}
        for traj_uid, reward in traj_rewards.items():
            traj_advantages[traj_uid] = ((reward - mean) / (std + self.eps)).item()

        # Step 5: Broadcast to all episodes (steps)
        advantages = [traj_advantages[ep.traj_uid] for ep in group]

        # DEBUG: Print statistics
        print(f"[ADVANTAGES] num_trajectories={len(traj_rewards)}, num_episodes={len(group)}")
        print(f"[ADVANTAGES] traj_rewards: {[round(r, 2) for r in reward_values]}")
        print(f"[ADVANTAGES] mean={mean.item():.3f}, std={std.item():.3f}")
        print(f"[ADVANTAGES] traj_advantages: {[round(a, 2) for a in traj_advantages.values()]}")

        return advantages

    @endpoint
    async def compute_batch(self, groups: List[Group]) -> List[List[float]]:
        """
        Compute advantages for multiple groups.

        Args:
            groups: List of episode groups

        Returns:
            List of advantage lists
        """
        all_advantages = []
        for group in groups:
            advantages = await self.compute(group)
            all_advantages.append(advantages)
        return all_advantages


@dataclass
class WebEnvActor(ForgeActor):
    """
    Actor that manages BrowserGym environment connections and tokenizer.

    This actor is responsible for:
    - Initializing and caching the tokenizer
    - Providing tokenizer access to other components
    - Managing environment configuration
    """

    server_url: str = "http://localhost:8005"
    model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    benchmark: str = "miniwob"
    task_name: str = "click-test"
    max_steps: int = 15  # Max steps per episode

    _tokenizer = None  # Cached tokenizer

    @endpoint
    def setup(self):
        """Initialize tokenizer and log configuration."""
        self._tokenizer = get_tokenizer(self.model)
        print(f"WebEnvActor initialized:")
        print(f"  Server: {self.server_url}")
        print(f"  Model: {self.model}")
        print(f"  Benchmark: {self.benchmark}")
        print(f"  (Task selection handled by trainer task_pool)")

    def _get_tokenizer(self):
        """Get the cached tokenizer instance (internal helper)."""
        if self._tokenizer is None:
            self._tokenizer = get_tokenizer(self.model)
        return self._tokenizer

    @endpoint
    async def get_tokenizer(self):
        """Get the cached tokenizer instance."""
        return self._get_tokenizer()

    @endpoint
    async def pad_token(self) -> int:
        """Get padding token ID."""
        tokenizer = self._get_tokenizer()
        return tokenizer.pad_token_id or tokenizer.eos_token_id

    @endpoint
    async def get_config(self) -> dict:
        """Get environment configuration."""
        return {
            "server_url": self.server_url,
            "model": self.model,
            "benchmark": self.benchmark,
            "task_name": self.task_name,
        }

    @endpoint
    async def tokenize(self, text: str) -> List[int]:
        """Tokenize text string."""
        tokenizer = self._get_tokenizer()
        return tokenizer.encode(text)

    @endpoint
    async def decode(self, token_ids: List[int]) -> str:
        """Decode token IDs to string."""
        tokenizer = self._get_tokenizer()
        return tokenizer.decode(token_ids)


@dataclass
class CurriculumManager(ForgeActor):
    """
    Actor for managing curriculum learning across tasks.

    Tracks performance on different tasks and suggests
    which tasks to train on next.
    """

    easy_threshold: float = 0.7  # Success rate to consider task "mastered"
    medium_threshold: float = 0.5

    _task_stats: dict = None

    @endpoint
    def setup(self):
        """Initialize task statistics."""
        self._task_stats = {}

    @endpoint
    async def record_result(self, task_name: str, success: bool):
        """Record a task attempt result."""
        if task_name not in self._task_stats:
            self._task_stats[task_name] = {"attempts": 0, "successes": 0}

        self._task_stats[task_name]["attempts"] += 1
        if success:
            self._task_stats[task_name]["successes"] += 1

    @endpoint
    async def get_success_rate(self, task_name: str) -> float:
        """Get success rate for a task."""
        if task_name not in self._task_stats:
            return 0.0
        stats = self._task_stats[task_name]
        if stats["attempts"] == 0:
            return 0.0
        return stats["successes"] / stats["attempts"]

    @endpoint
    async def suggest_next_task(self, available_tasks: List[str]) -> str:
        """
        Suggest which task to train on next.

        Strategy: Focus on tasks with medium success rate
        (not too easy, not too hard).
        """
        candidates = []
        for task in available_tasks:
            rate = await self.get_success_rate(task)
            # Prioritize tasks in the "learning zone"
            if self.medium_threshold <= rate < self.easy_threshold:
                candidates.append((task, rate, 2))  # High priority
            elif rate < self.medium_threshold:
                candidates.append((task, rate, 1))  # Medium priority
            else:
                candidates.append((task, rate, 0))  # Low priority (mastered)

        # Sort by priority, then by success rate (ascending)
        candidates.sort(key=lambda x: (-x[2], x[1]))

        return candidates[0][0] if candidates else available_tasks[0]
