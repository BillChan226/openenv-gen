"""
GRPO Web Agent Training

Train web navigation agents using GRPO (Group Relative Policy Optimization)
with OpenEnv's BrowserGym integration.

Example usage:
    from examples.grpo_web import setup_forge_training

    trainer = await setup_forge_training("examples/grpo_web/web.yaml")
    await trainer.run(steps=1000)
    await trainer.shutdown()

Or run directly:
    python -m examples.grpo_web.train --config examples/grpo_web/web.yaml
"""

# Re-export from utils for convenience
from .utils import (
    # Data structures
    Episode,
    Group,
    collate,
    create_episode,
    # Loss
    simple_grpo_loss,
    grpo_loss_with_entropy,
    compute_advantages_from_rewards,
    # Prompts
    format_web_prompt,
    format_web_prompt_with_cot,
    parse_web_action,
    parse_web_action_with_reasoning,
    extract_element_ids,
    BROWSERGYM_ACTIONS,
    BROWSERGYM_ACTIONS_COMPACT,
    # Actors
    WebReward,
    WebRewardWithFormatPenalty,
    ComputeAdvantages,
    WebEnvActor,
    CurriculumManager,
    # Rollout
    play_web_task,
    play_web_task_parallel,
    play_random_web_policy,
    play_heuristic_web_policy,
    show_web_observation,
    setup_task_logger,
    # Trainer
    GRPOWebTrainer,
    setup_forge_training,
    drop_weights,
    # Tasks
    MINIWOB_EASY_TASKS,
    MINIWOB_MEDIUM_TASKS,
    MINIWOB_HARD_TASKS,
    MINIWOB_ALL_TASKS,
    TASK_METADATA,
    WEBARENA_CATEGORIES,
    get_curriculum,
    get_task_difficulty,
    get_tasks_by_skill,
    suggest_next_tasks,
    get_webarena_tasks,
)

__all__ = [
    # Data structures
    "Episode",
    "Group",
    "collate",
    "create_episode",
    # Loss
    "simple_grpo_loss",
    "grpo_loss_with_entropy",
    "compute_advantages_from_rewards",
    # Prompts
    "format_web_prompt",
    "format_web_prompt_with_cot",
    "parse_web_action",
    "parse_web_action_with_reasoning",
    "extract_element_ids",
    "BROWSERGYM_ACTIONS",
    "BROWSERGYM_ACTIONS_COMPACT",
    # Actors
    "WebReward",
    "WebRewardWithFormatPenalty",
    "ComputeAdvantages",
    "WebEnvActor",
    "CurriculumManager",
    # Rollout
    "play_web_task",
    "play_web_task_parallel",
    "play_random_web_policy",
    "play_heuristic_web_policy",
    "show_web_observation",
    "setup_task_logger",
    # Trainer
    "GRPOWebTrainer",
    "setup_forge_training",
    "drop_weights",
    # Tasks
    "MINIWOB_EASY_TASKS",
    "MINIWOB_MEDIUM_TASKS",
    "MINIWOB_HARD_TASKS",
    "MINIWOB_ALL_TASKS",
    "TASK_METADATA",
    "WEBARENA_CATEGORIES",
    "get_curriculum",
    "get_task_difficulty",
    "get_tasks_by_skill",
    "suggest_next_tasks",
    "get_webarena_tasks",
]
