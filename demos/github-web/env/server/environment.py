"""Environment implementation for github-web.

This module provides BrowserGym-compatible task wrappers and registration
for the generated web environment.
"""

from typing import Any, Dict, Optional, Tuple, Type
from functools import partial

import gymnasium as gym
import numpy as np
import requests

from browsergym.core.task import AbstractBrowserTask
from browsergym.core.env import BrowserEnv
BROWSERGYM_AVAILABLE = True


import playwright.sync_api


# Environment configuration (set via environment variables or defaults)
APP_URL = "http://frontend:3000"
API_URL = "http://backend:5000"


class frozen_partial:
    """Freeze some keyword arguments of a function."""

    def __init__(self, func, **frozen_kwargs):
        self.func = func
        self.frozen_kwargs = frozen_kwargs

    def __call__(self, *args, **kwargs):
        clashing_kwargs = set(self.frozen_kwargs) & set(kwargs)
        if clashing_kwargs:
            raise ValueError(f"Illegal attempt to override frozen parameters {clashing_kwargs}.")
        kwargs = kwargs | self.frozen_kwargs
        return self.func(*args, **kwargs)


class WebTask(AbstractBrowserTask):
    """BrowserGym-compatible wrapper for github-web tasks.

    Wraps tasks from the task registry to work with BrowserGym's BrowserEnv.
    """

    def __init__(
        self,
        seed: int,
        task_id: str,
        app_url: str = APP_URL,
        api_url: str = API_URL,
    ):
        """Initialize the task wrapper.

        Args:
            seed: Random seed for reproducibility
            task_id: ID of the task from the task registry
            app_url: Frontend application URL
            api_url: Backend API URL
        """
        super().__init__(seed)

        self.task_id = task_id
        self.app_url = app_url
        self.api_url = api_url

        # Import and instantiate the task
        from tasks import get_task_class
        task_class = get_task_class(task_id)
        self._task = task_class()

        # Set viewport and timeout from task config
        self.viewport = {"width": 1280, "height": 720}
        self.timeout = 10000
        self.slow_mo = 100

    @classmethod
    def get_task_id(cls) -> str:
        """Get the task ID (overridden per-task via partial)."""
        return "github-web"

    def setup(self, page: playwright.sync_api.Page) -> Tuple[str, dict]:
        """Set up the task environment.

        Args:
            page: Playwright page object

        Returns:
            Tuple of (goal, info)
        """
        # Reset database state
        self._reset_database()

        # Run task-specific setup
        db_state = self._get_db_state()
        self._task.setup(page, db_state)

        # Navigate to start URL
        start_url = self._task.start_url
        if start_url.startswith("/"):
            start_url = f"{self.app_url}{start_url}"
        page.goto(start_url, timeout=self.timeout)

        return self._task.goal, {"task_id": self.task_id}

    def validate(
        self,
        page: playwright.sync_api.Page,
        chat_messages: list[str],
    ) -> Tuple[float, bool, str, dict]:
        """Validate task completion.

        Args:
            page: Playwright page object
            chat_messages: Chat messages (not used for web tasks)

        Returns:
            Tuple of (reward, done, message, info)
        """
        db_state = self._get_db_state()
        reward, done, message = self._task.validate(page, db_state)
        return reward, done, message, {"db_state": db_state}

    def teardown(self) -> None:
        """Clean up after task completion."""
        self._task.teardown()

    def _reset_database(self) -> None:
        """Reset database to initial state via API."""
        try:
            response = requests.post(f"{self.api_url}/api/admin/reset", timeout=5)
            response.raise_for_status()
        except Exception:
            pass  # API might not have reset endpoint

    def _get_db_state(self) -> Dict[str, Any]:
        """Get current database state for validation."""
        try:
            response = requests.get(f"{self.api_url}/api/admin/state", timeout=5)
            if response.ok:
                return response.json()
        except Exception:
            pass
        return {}


def register_task(
    task_id: str,
    task_class: Type[AbstractBrowserTask] = WebTask,
    task_kwargs: dict = None,
    default_task_kwargs: dict = None,
    nondeterministic: bool = True,
    **kwargs,
) -> None:
    """Register a task as a BrowserGym environment.

    Args:
        task_id: Task identifier (will be registered as browsergym/github-web.{task_id})
        task_class: Task class (default: WebTask)
        task_kwargs: Frozen task arguments
        default_task_kwargs: Default task arguments (can be overridden)
        nondeterministic: Whether task is non-deterministic
        **kwargs: Additional gym.register arguments
    """
    if not BROWSERGYM_AVAILABLE:
        raise ImportError("browsergym is required for environment registration")

    task_kwargs = task_kwargs or {}
    default_task_kwargs = default_task_kwargs or {}

    if task_kwargs and default_task_kwargs:
        clashing = set(task_kwargs) & set(default_task_kwargs)
        if clashing:
            raise ValueError(f"Clashing task kwargs: {clashing}")

    # Create task entry point with frozen kwargs
    task_entrypoint = task_class
    task_entrypoint = frozen_partial(task_class, **task_kwargs)
    task_entrypoint = partial(task_entrypoint, **default_task_kwargs)

    # Register with BrowserGym naming convention
    env_id = f"browsergym/github-web.{task_id}"

    gym.register(
        id=env_id,
        entry_point=lambda *args, **kw: BrowserEnv(task_entrypoint, *args, **kw),
        nondeterministic=nondeterministic,
        **kwargs,
    )


def register_all_tasks(
    app_url: str = APP_URL,
    api_url: str = API_URL,
) -> None:
    """Register all tasks from the task registry into BrowserGym.

    Args:
        app_url: Frontend application URL
        api_url: Backend API URL
    """
    if not BROWSERGYM_AVAILABLE:
        raise ImportError("browsergym is required for environment registration")

    from tasks import list_tasks

    for task_info in list_tasks():
        task_id = task_info["id"]
        register_task(
            task_id=task_id,
            task_kwargs={"task_id": task_id},
            default_task_kwargs={
                "app_url": app_url,
                "api_url": api_url,
            },
        )


# Auto-register tasks when module is imported
def _auto_register():
    """Automatically register all tasks on module import."""
    import os
    if BROWSERGYM_AVAILABLE and os.environ.get("AUTO_REGISTER_TASKS", "true").lower() == "true":
        try:
            register_all_tasks(
                app_url=os.environ.get("APP_URL", APP_URL),
                api_url=os.environ.get("API_URL", API_URL),
            )
        except Exception:
            pass  # Tasks might not be available yet


_auto_register()
