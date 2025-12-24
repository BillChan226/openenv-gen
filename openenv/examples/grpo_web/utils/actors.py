"""
Forge Actors for Web Agent Training

This module defines the Forge actors used in GRPO training:
- WebReward: Computes shaped rewards for web navigation tasks
- ComputeAdvantages: Calculates group-relative advantages
- WebEnvActor: Manages environment connections and tokenizer
"""

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

    Computes shaped rewards that encourage:
    - Task completion
    - Efficient completion (fewer steps)
    - Valid actions (penalize errors)
    """

    # Reward shaping parameters
    success_reward: float = 2.0
    failure_reward: float = -0.5
    efficiency_bonus_scale: float = 0.5
    error_penalty: float = 0.1

    @endpoint
    async def evaluate_response(
        self,
        prompt: str,
        response: str,
        task_reward: float,
        step_count: int,
        max_steps: int,
        had_error: bool = False,
    ) -> float:
        """
        Evaluate episode reward with shaping for web tasks.

        Reward shaping strategy:
        1. Base reward from task outcome (success/failure)
        2. Efficiency bonus for completing faster
        3. Penalty for action errors

        Args:
            prompt: Page state prompt (unused, for logging)
            response: Model's action string
            task_reward: Raw task outcome (1.0 for success, 0.0 for failure)
            step_count: Steps taken to complete
            max_steps: Maximum allowed steps
            had_error: Whether the action caused an error

        Returns:
            Shaped reward value
        """
        # Base reward from task outcome
        if task_reward > 0:
            # Success: base reward + efficiency bonus
            efficiency = 1.0 - (step_count / max_steps)
            reward = self.success_reward + (self.efficiency_bonus_scale * efficiency)
        else:
            # Failure
            reward = self.failure_reward

        # Penalty for action errors
        if had_error or response == "noop()":
            reward -= self.error_penalty

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
    Extended reward actor that also penalizes malformed actions.

    This variant adds penalties for:
    - Invalid action syntax
    - Referencing non-existent elements
    - Repetitive actions
    """

    success_reward: float = 2.0
    failure_reward: float = -0.5
    format_penalty: float = 0.2
    repetition_penalty: float = 0.1

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
        Evaluate with format and repetition penalties.
        """
        # Base reward
        if task_reward > 0:
            efficiency = 1.0 - (step_count / max_steps)
            reward = self.success_reward + (0.5 * efficiency)
        else:
            reward = self.failure_reward

        # Format penalty for noop (often means parsing failed)
        if response == "noop()":
            reward -= self.format_penalty

        # Repetition penalty
        if action_history and len(action_history) >= 2:
            if response == action_history[-1]:
                reward -= self.repetition_penalty

        # Invalid BID penalty
        if valid_bids and "click(" in response:
            # Extract BID from action
            import re
            match = re.search(r"click\(['\"]?(\d+)['\"]?\)", response)
            if match:
                bid = match.group(1)
                if bid not in valid_bids:
                    reward -= self.format_penalty

        record_metric("reward/avg_reward", reward, Reduce.MEAN)
        return reward


@dataclass
class ComputeAdvantages(ForgeActor):
    """
    Actor for computing group-relative advantages.

    GRPO uses group-relative normalization instead of absolute baselines.
    For each group of episodes, we normalize rewards by the group's
    mean and standard deviation.
    """

    eps: float = 1e-4  # Numerical stability constant

    @endpoint
    async def compute(self, group: Group) -> List[float]:
        """
        Compute advantages normalized by group statistics.

        Formula: advantage_i = (reward_i - mean) / (std + eps)

        Args:
            group: List of episodes from same rollout group

        Returns:
            List of advantage values (same order as input)
        """
        rewards = torch.tensor([[e.reward for e in group]])

        mean = rewards.mean(1, keepdim=True)
        std = rewards.std(1, keepdim=True)

        advantages = (rewards - mean) / (std + self.eps)

        return advantages.squeeze(0).tolist()

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
