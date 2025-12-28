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
    old_logprobs: torch.Tensor,
    ref_logprobs: torch.Tensor,
    advantages: torch.Tensor,
    padding_mask: torch.Tensor,
    beta: float = 0.01,  # KL penalty coefficient (reduced from 0.1 to match verl-agent)
    clip_range: float = 0.2,  # PPO-style clipping (0 to disable)
    clip_ratio_c: float = 3.0,  # Dual-clip lower bound for negative advantages
) -> torch.Tensor:
    """
    Compute GRPO loss with proper importance sampling, KL penalty, and dual-clip PPO.

    The loss combines:
    1. Policy gradient term with importance sampling ratio
    2. KL penalty: Prevents the policy from diverging too far from reference
    3. Dual-clip PPO: Standard clipping + additional clipping for negative advantages

    Args:
        logits: Model output logits, shape (batch, seq_len, vocab_size)
        response: Response token IDs, shape (batch, response_len)
        old_logprobs: Log probs from policy at rollout time, shape (batch, response_len)
        ref_logprobs: Reference model log probabilities, shape (batch, response_len)
        advantages: Group-relative advantages, shape (batch, 1)
        padding_mask: Boolean mask for valid tokens, shape (batch, response_len)
        beta: KL penalty coefficient (default 0.01, matching verl-agent)
        clip_range: PPO-style clipping range (0 to disable clipping)
        clip_ratio_c: Dual-clip lower bound for negative advantages (default 3.0)
                      Prevents overly large updates when advantages are negative.

    Returns:
        Scalar loss value to minimize

    Notes:
        - The importance ratio is: ratio = exp(new_logprobs - old_logprobs)
          This enables proper off-policy correction when the policy has updated
          since the rollout was collected.

        - The KL divergence is computed using low-variance estimator (k3):
          KL = exp(ref_lp - policy_lp) - (ref_lp - policy_lp) - 1
          This is clamped to [-10, 10] for numerical stability.

        - Dual-clip PPO (https://arxiv.org/pdf/1912.09729):
          For positive advantages: standard PPO clip
          For negative advantages: additional lower bound clip_ratio_c
          This prevents destabilizing large updates for negative advantages.

        - Final loss averages over valid (non-padded) tokens per sequence,
          then averages over the batch
    """
    # Compute log probabilities for the response tokens under current policy
    logprobs: torch.Tensor = compute_logprobs(logits, response)

    # KL divergence using low-variance estimator (k3 from verl-agent)
    # This is more stable than the simple approximation
    kl_raw = ref_logprobs - logprobs
    kl_ratio = torch.exp(kl_raw)
    kl = torch.clamp(kl_ratio - kl_raw - 1, min=-10.0, max=10.0)

    # Importance sampling ratio: pi(a|s) / pi_old(a|s)
    log_ratio = logprobs - old_logprobs
    ratio = torch.exp(log_ratio)

    # Policy gradient term with dual-clip PPO
    if clip_range > 0:
        # Standard PPO clipping
        ratio_clipped = torch.clamp(ratio, 1.0 - clip_range, 1.0 + clip_range)
        pg_loss1 = -advantages * ratio
        pg_loss2 = -advantages * ratio_clipped
        clip_pg_loss1 = torch.max(pg_loss1, pg_loss2)

        # Dual-clip: additional lower bound for negative advantages
        # This prevents overly aggressive updates when advantages are negative
        pg_loss3 = -advantages * clip_ratio_c
        clip_pg_loss2 = torch.min(pg_loss3, clip_pg_loss1)

        # Apply dual-clip only for negative advantages
        per_token_policy_loss = torch.where(
            advantages < 0,
            clip_pg_loss2,
            clip_pg_loss1
        )
    else:
        # Standard REINFORCE with importance sampling
        per_token_policy_loss = -advantages * ratio

    # Combined loss: policy gradient + KL penalty
    per_token_loss = per_token_policy_loss + beta * kl

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
    old_logprobs: torch.Tensor,
    ref_logprobs: torch.Tensor,
    advantages: torch.Tensor,
    padding_mask: torch.Tensor,
    beta: float = 0.1,
    entropy_coef: float = 0.01,
    clip_range: float = 0.2,
) -> tuple[torch.Tensor, dict]:
    """
    GRPO loss with entropy bonus for exploration.

    Adding an entropy bonus encourages the policy to maintain diversity
    in its action distribution, which can help with exploration.

    Args:
        logits: Model output logits
        response: Response token IDs
        old_logprobs: Log probs from policy at rollout time
        ref_logprobs: Reference model log probabilities
        advantages: Group-relative advantages
        padding_mask: Boolean mask for valid tokens
        beta: KL penalty coefficient
        entropy_coef: Entropy bonus coefficient
        clip_range: PPO-style clipping range (0 to disable)

    Returns:
        Tuple of (loss, metrics_dict) where metrics_dict contains:
        - policy_loss: The policy gradient component
        - kl_loss: The KL divergence component
        - entropy: The entropy of the policy distribution
        - approx_kl: Approximate KL divergence between old and new policy
    """
    logprobs = compute_logprobs(logits, response)

    # Compute entropy: -sum(p * log(p))
    probs = torch.softmax(logits, dim=-1)
    log_probs_all = torch.log_softmax(logits, dim=-1)
    entropy = -(probs * log_probs_all).sum(dim=-1)

    # KL divergence from reference model
    kl = torch.exp(ref_logprobs - logprobs) - (ref_logprobs - logprobs) - 1

    # Importance sampling ratio: pi(a|s) / pi_old(a|s)
    log_ratio = logprobs - old_logprobs
    ratio = torch.exp(log_ratio)

    # Policy gradient term with importance sampling
    if clip_range > 0:
        ratio_clipped = torch.clamp(ratio, 1.0 - clip_range, 1.0 + clip_range)
        pg_loss1 = -advantages * ratio
        pg_loss2 = -advantages * ratio_clipped
        per_token_policy_loss = torch.max(pg_loss1, pg_loss2)
    else:
        per_token_policy_loss = -advantages * ratio

    # Combined loss with entropy bonus (entropy is subtracted because we want to maximize it)
    per_token_loss = per_token_policy_loss + beta * kl - entropy_coef * entropy

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
        "approx_kl": (log_ratio * padding_mask).sum() / padding_mask.sum(),  # Approx KL(old || new)
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
