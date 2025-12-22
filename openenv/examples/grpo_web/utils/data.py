"""
Data structures for GRPO web agent training.

This module defines the Episode dataclass and collation functions
for batching episodes during training.
"""

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

import torch
import torch.nn.functional as F

# Lazy import for forge dependency
if TYPE_CHECKING:
    from forge.data_models.completion import Completion
else:
    Completion = Any  # Runtime placeholder


@dataclass
class Episode:
    """
    Episode data for RL training.

    Each episode represents a single step in a web navigation task,
    containing the prompt, model response, and associated rewards.

    Attributes:
        episode_id: Unique identifier for this episode
        pad_id: Token ID used for padding
        request_len: Fixed length for request (prompt) tensors
        response_len: Fixed length for response tensors
        task_id: Identifier for the web task this episode belongs to
        step_in_task: Step number within the task (0-indexed)
        completion: Model completion containing generated tokens
        ref_logprobs: Log probabilities from reference model
        reward: Shaped reward value
        advantage: Group-relative advantage
    """

    episode_id: str
    pad_id: int
    request_len: int
    response_len: int
    task_id: str
    step_in_task: int
    completion: Completion | None = None
    ref_logprobs: torch.Tensor | None = None
    reward: float | None = None
    advantage: float | None = None

    @property
    def policy_version(self) -> int | None:
        """Get the policy version that generated this episode."""
        if self.completion is None:
            return None
        return self.completion.generator_version

    @property
    def request_tensor(self) -> torch.Tensor:
        """
        Get padded request (prompt) tensor.

        Left-pads the prompt tokens to request_len.

        Returns:
            Tensor of shape (request_len,)
        """
        request_tokens: torch.Tensor = self.completion.prompt_ids
        tensor = torch.tensor(request_tokens, dtype=torch.long)
        if tensor.shape[0] < self.request_len:
            diff = self.request_len - tensor.shape[0]
            tensor = F.pad(tensor, (diff, 0), value=self.pad_id)
        elif tensor.shape[0] > self.request_len:
            # Truncate from left if too long
            tensor = tensor[-self.request_len:]
        return tensor

    @property
    def response_tensor(self) -> torch.Tensor:
        """
        Get padded response tensor.

        Right-pads the response tokens to response_len.

        Returns:
            Tensor of shape (response_len,)
        """
        response_tokens: torch.Tensor = self.completion.token_ids
        tensor = torch.tensor(response_tokens, dtype=torch.long)
        if tensor.shape[0] < self.response_len:
            diff = self.response_len - tensor.shape[0]
            tensor = F.pad(tensor, (0, diff), value=self.pad_id)
        elif tensor.shape[0] > self.response_len:
            # Truncate if too long
            tensor = tensor[:self.response_len]
        return tensor

    def to_dict(self) -> dict:
        """Convert episode to dictionary for logging."""
        return {
            "episode_id": self.episode_id,
            "task_id": self.task_id,
            "step_in_task": self.step_in_task,
            "reward": self.reward,
            "advantage": self.advantage,
            "policy_version": self.policy_version,
        }


# Type alias for a group of episodes (used for advantage computation)
Group = list[Episode]


def collate(batches: list[Group]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Collate batches of episodes into model inputs and targets.

    This function prepares data for the GRPO training step by stacking
    episode tensors and creating the required input/target dictionaries.

    Args:
        batches: List of episode groups, where each group contains
                 episodes that will be compared for advantage computation

    Returns:
        Tuple of (inputs, targets) where:
        - inputs: List of dicts with "tokens" key (concatenated request+response)
        - targets: List of dicts with response, ref_logprobs, advantages, padding_mask
    """
    inputs = []
    targets = []

    for batch in batches:
        # Stack tensors from all episodes in batch
        request = torch.stack([e.request_tensor for e in batch])
        response = torch.stack([e.response_tensor for e in batch])
        ref_logprobs = torch.stack([e.ref_logprobs for e in batch]).squeeze()
        advantages = torch.tensor([e.advantage for e in batch]).unsqueeze(-1)

        # Create padding mask (True for non-pad tokens)
        pad_id = batch[0].pad_id
        mask = response != pad_id

        # Concatenate request and response for full sequence
        input_dict = {"tokens": torch.cat([request, response], dim=1)}

        target_dict = {
            "response": response,
            "ref_logprobs": ref_logprobs,
            "advantages": advantages,
            "padding_mask": mask,
        }

        inputs.append(input_dict)
        targets.append(target_dict)

    return inputs, targets


def create_episode(
    episode_id: str,
    pad_id: int,
    request_len: int,
    response_len: int,
    task_id: str,
    step_in_task: int,
    completion: Completion,
) -> Episode:
    """
    Factory function to create an Episode instance.

    Args:
        episode_id: Unique identifier
        pad_id: Padding token ID
        request_len: Fixed request length
        response_len: Fixed response length
        task_id: Task identifier
        step_in_task: Step number
        completion: Model completion

    Returns:
        New Episode instance
    """
    return Episode(
        episode_id=episode_id,
        pad_id=pad_id,
        request_len=request_len,
        response_len=response_len,
        task_id=task_id,
        step_in_task=step_in_task,
        completion=completion,
    )
