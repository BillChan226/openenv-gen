"""Task definitions for {{ENV_NAME}} environment.

This module provides the task registry and base classes for defining
training/evaluation tasks.
"""

from .base import BaseTask
from .registry import register_task, get_task_class, list_tasks

__all__ = ["BaseTask", "register_task", "get_task_class", "list_tasks"]

# Import task definitions to register them
from . import definitions  # noqa: F401
