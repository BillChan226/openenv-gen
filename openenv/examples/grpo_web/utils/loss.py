"""
GRPO Loss Functions

This module implements the Group Relative Policy Optimization (GRPO) loss
function used for training web navigation agents.

GRPO is more efficient than PPO as it only requires 2 models (policy + reference)
instead of 3 (policy + reference + value function).

Reference: https://arxiv.org/abs/2402.03300
"""

import torch
from forge.util.ops import compute_logprobs


def simple_grpo_loss(
    logits: torch.Tensor,
    response: torch.Tensor,
    ref_logprobs: torch.Tensor,
    advantages: torch.Tensor,
    padding_mask: torch.Tensor,
    beta: float = 0.1,
) -> torch.Tensor:
    """
    Compute GRPO loss with KL penalty.

    The loss combines:
    1. Policy gradient term: Encourages actions with positive advantages
    2. KL penalty: Prevents the policy from diverging too far from reference

    Args:
        logits: Model output logits, shape (batch, seq_len, vocab_size)
        response: Response token IDs, shape (batch, response_len)
        ref_logprobs: Reference model log probabilities, shape (batch, response_len)
        advantages: Group-relative advantages, shape (batch, 1)
        padding_mask: Boolean mask for valid tokens, shape (batch, response_len)
        beta: KL penalty coefficient (higher = more conservative updates)

    Returns:
        Scalar loss value to minimize

    Notes:
        - The KL divergence is computed in closed form as:
          KL(ref || policy) = exp(ref_lp - policy_lp) - (ref_lp - policy_lp) - 1

        - The importance weight exp(lp - lp.detach()) equals 1 at the start,
          but allows gradients to flow through the policy

        - Final loss averages over valid (non-padded) tokens per sequence,
          then averages over the batch
    """
    # Compute log probabilities for the response tokens
    logprobs: torch.Tensor = compute_logprobs(logits, response)

    # KL divergence in closed form (Schulman's approximation)
    # This is equivalent to: E[log(ref/policy)] when ref ≈ policy
    kl = torch.exp(ref_logprobs - logprobs) - (ref_logprobs - logprobs) - 1

    # Policy gradient term with importance sampling
    # The exp(lp - lp.detach()) term allows gradients while being 1 at evaluation
    per_token_policy_loss = torch.exp(logprobs - logprobs.detach()) * advantages

    # Combined loss: maximize policy gradient, minimize KL divergence
    # Negative sign because we want to maximize rewards
    per_token_loss = -(per_token_policy_loss - beta * kl)

    # Average over valid tokens in each sequence
    # Clamp denominator to avoid division by zero for fully padded sequences
    per_sequence_loss = (per_token_loss * padding_mask).sum(dim=1) / (
        padding_mask.sum(dim=1).clamp(min=1.0)
    )

    # Average over batch
    loss = per_sequence_loss.mean()

    return loss


def grpo_loss_with_entropy(
    logits: torch.Tensor,
    response: torch.Tensor,
    ref_logprobs: torch.Tensor,
    advantages: torch.Tensor,
    padding_mask: torch.Tensor,
    beta: float = 0.1,
    entropy_coef: float = 0.01,
) -> tuple[torch.Tensor, dict]:
    """
    GRPO loss with entropy bonus for exploration.

    Adding an entropy bonus encourages the policy to maintain diversity
    in its action distribution, which can help with exploration.

    Args:
        logits: Model output logits
        response: Response token IDs
        ref_logprobs: Reference model log probabilities
        advantages: Group-relative advantages
        padding_mask: Boolean mask for valid tokens
        beta: KL penalty coefficient
        entropy_coef: Entropy bonus coefficient

    Returns:
        Tuple of (loss, metrics_dict) where metrics_dict contains:
        - policy_loss: The policy gradient component
        - kl_loss: The KL divergence component
        - entropy: The entropy of the policy distribution
    """
    logprobs = compute_logprobs(logits, response)

    # Compute entropy: -sum(p * log(p))
    probs = torch.softmax(logits, dim=-1)
    log_probs_all = torch.log_softmax(logits, dim=-1)
    entropy = -(probs * log_probs_all).sum(dim=-1)

    # KL divergence
    kl = torch.exp(ref_logprobs - logprobs) - (ref_logprobs - logprobs) - 1

    # Policy gradient term
    per_token_policy_loss = torch.exp(logprobs - logprobs.detach()) * advantages

    # Combined loss with entropy bonus
    per_token_loss = -(per_token_policy_loss - beta * kl + entropy_coef * entropy)

    # Average over valid tokens
    per_sequence_loss = (per_token_loss * padding_mask).sum(dim=1) / (
        padding_mask.sum(dim=1).clamp(min=1.0)
    )
    loss = per_sequence_loss.mean()

    # Compute metrics for logging
    metrics = {
        "policy_loss": (per_token_policy_loss * padding_mask).sum() / padding_mask.sum(),
        "kl_loss": (kl * padding_mask).sum() / padding_mask.sum(),
        "entropy": (entropy * padding_mask).sum() / padding_mask.sum(),
    }

    return loss, metrics


def compute_advantages_from_rewards(
    rewards: torch.Tensor,
    normalize: bool = True,
    eps: float = 1e-8,
) -> torch.Tensor:
    """
    Compute group-relative advantages from rewards.

    GRPO uses group-relative advantages instead of absolute baselines.
    For each group, we normalize rewards by the group's mean and std.

    Args:
        rewards: Tensor of rewards, shape (group_size,) or (batch, group_size)
        normalize: Whether to normalize by mean and std
        eps: Small constant for numerical stability

    Returns:
        Tensor of advantages with same shape as rewards

    Example:
        >>> rewards = torch.tensor([1.0, 0.5, -0.5, -1.0])
        >>> advantages = compute_advantages_from_rewards(rewards)
        >>> # Positive rewards get positive advantages, scaled by group stats
    """
    if not normalize:
        return rewards

    if rewards.dim() == 1:
        rewards = rewards.unsqueeze(0)

    mean = rewards.mean(dim=-1, keepdim=True)
    std = rewards.std(dim=-1, keepdim=True)
    advantages = (rewards - mean) / (std + eps)

    return advantages.squeeze(0) if advantages.shape[0] == 1 else advantages
