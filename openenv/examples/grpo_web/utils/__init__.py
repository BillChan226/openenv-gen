import sys
from pathlib import Path

# Setup paths for dependencies
_openenv_root = Path(__file__).parent.parent.parent.parent
_torchforge_src = _openenv_root.parent / "torchforge" / "src"
_openenv_src = _openenv_root / "src"

# Add torchforge to path (for forge imports)
if _torchforge_src.exists() and str(_torchforge_src) not in sys.path:
    sys.path.insert(0, str(_torchforge_src))

# Add openenv root to path (for envs imports)
if str(_openenv_root) not in sys.path:
    sys.path.insert(0, str(_openenv_root))

# Add openenv src to path (for openenv core imports)
if _openenv_src.exists() and str(_openenv_src) not in sys.path:
    sys.path.insert(0, str(_openenv_src))

from .data import Episode, Group, collate, create_episode
from .loss import simple_grpo_loss, grpo_loss_with_entropy, compute_advantages_from_rewards
from .prompts import (
    format_web_prompt,
    format_web_prompt_with_cot,
    parse_web_action,
    parse_web_action_with_reasoning,
    extract_element_ids,
    BROWSERGYM_ACTIONS,
    BROWSERGYM_ACTIONS_COMPACT,
)
from .actors import (
    WebReward,
    WebRewardWithFormatPenalty,
    ComputeAdvantages,
    WebEnvActor,
    CurriculumManager,
)
from .rollout import (
    play_web_task,
    play_web_task_parallel,
    play_random_web_policy,
    play_heuristic_web_policy,
    show_web_observation,
    setup_task_logger,
)
from .trainer import GRPOWebTrainer, setup_forge_training, drop_weights
from .tasks import (
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
