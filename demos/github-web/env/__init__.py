"""github-web OpenEnv Environment.

This module provides access to the BrowserGym-registered environment.

Usage:
    from env import make_env, list_tasks

    # Create environment for a specific task
    env = make_env("login")
    obs, info = env.reset()
    obs, reward, terminated, truncated, info = env.step("click('submit-btn')")
    env.close()

    # Or use gymnasium directly
    import gymnasium as gym
    env = gym.make("browsergym/github-web.login")
"""

from .client import (
    make_env,
    list_tasks,
    BrowserGymAction,
    BrowserGymObservation,
    BrowserGymState,
)

__all__ = [
    "make_env",
    "list_tasks",
    "BrowserGymAction",
    "BrowserGymObservation",
    "BrowserGymState",
]
