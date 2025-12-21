"""Reward functions for task definitions.

Provides reusable reward computation strategies.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple


def sparse_reward(success: bool, success_reward: float = 1.0) -> float:
    """Simple sparse reward: 1.0 on success, 0.0 otherwise."""
    return success_reward if success else 0.0


def step_penalty_reward(
    success: bool,
    steps: int,
    max_steps: int,
    success_reward: float = 1.0,
    penalty_per_step: float = 0.01,
) -> float:
    """Reward with penalty for each step taken.

    Encourages efficient task completion.
    """
    if not success:
        return 0.0
    penalty = steps * penalty_per_step
    return max(0.0, success_reward - penalty)


def progress_reward(
    completed_steps: int,
    total_steps: int,
    bonus_for_completion: float = 0.5,
) -> Tuple[float, bool]:
    """Reward based on progress through multi-step task.

    Returns partial reward for each completed step plus bonus for full completion.
    """
    progress = completed_steps / total_steps if total_steps > 0 else 0.0
    done = completed_steps >= total_steps

    reward = progress * (1.0 - bonus_for_completion)
    if done:
        reward += bonus_for_completion

    return reward, done


def distance_reward(
    current_value: float,
    target_value: float,
    initial_value: float,
    max_reward: float = 1.0,
) -> float:
    """Reward based on distance to target value.

    Useful for numeric goals (e.g., cart total, score).
    """
    if initial_value == target_value:
        return max_reward if current_value == target_value else 0.0

    initial_distance = abs(target_value - initial_value)
    current_distance = abs(target_value - current_value)

    progress = (initial_distance - current_distance) / initial_distance
    return max(0.0, min(max_reward, progress * max_reward))


class ShapedReward:
    """Builder for shaped reward functions with multiple components."""

    def __init__(self):
        self._components: List[Tuple[str, Callable[[], float], float]] = []

    def add_component(
        self,
        name: str,
        reward_fn: Callable[[], float],
        weight: float = 1.0,
    ) -> "ShapedReward":
        """Add a reward component.

        Args:
            name: Component name (for debugging)
            reward_fn: Function returning component reward
            weight: Weight for this component
        """
        self._components.append((name, reward_fn, weight))
        return self

    def compute(self) -> Tuple[float, Dict[str, float]]:
        """Compute total reward and breakdown.

        Returns:
            Tuple of (total_reward, component_breakdown)
        """
        total = 0.0
        breakdown = {}

        for name, reward_fn, weight in self._components:
            component_reward = reward_fn() * weight
            breakdown[name] = component_reward
            total += component_reward

        return total, breakdown
