"""Client for the {{ENV_NAME}} environment.

This module provides access to the BrowserGym-registered environment.

Usage:
    from env.client import make_env, list_tasks

    # Create environment for a specific task
    env = make_env("login")  # Creates browsergym/{{ENV_NAME}}.login
    obs, info = env.reset()

    # Take actions
    obs, reward, terminated, truncated, info = env.step("click('submit-btn')")

    env.close()

    # Or use gymnasium directly
    import gymnasium as gym
    env = gym.make("browsergym/{{ENV_NAME}}.login")
"""

import gymnasium as gym

# Re-export BrowserGym types for convenience
from envs.browsergym_env import (
    BrowserGymAction,
    BrowserGymObservation,
    BrowserGymState,
)


def make_env(
    task_id: str,
    headless: bool = True,
    **kwargs,
) -> gym.Env:
    """Create a BrowserGym environment for a {{ENV_NAME}} task.

    Args:
        task_id: Task identifier (e.g., "login", "create-repo")
        headless: Run browser in headless mode
        **kwargs: Additional arguments passed to gym.make()

    Returns:
        Gymnasium environment

    Example:
        env = make_env("login")
        obs, info = env.reset()
        obs, reward, terminated, truncated, info = env.step("click('login-btn')")
        env.close()
    """
    # Ensure tasks are registered
    from env.server.environment import register_all_tasks
    try:
        register_all_tasks()
    except Exception:
        pass  # Already registered or tasks not available

    env_id = f"browsergym/{{ENV_NAME}}.{task_id}"
    return gym.make(env_id, headless=headless, **kwargs)


def list_tasks() -> list[dict]:
    """List all available tasks for {{ENV_NAME}}.

    Returns:
        List of task info dicts with id, name, goal, difficulty
    """
    from tasks import list_tasks as _list_tasks
    return _list_tasks()


__all__ = [
    "make_env",
    "list_tasks",
    "BrowserGymAction",
    "BrowserGymObservation",
    "BrowserGymState",
]
