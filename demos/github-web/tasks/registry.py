"""Task registry for github-web environment.

Manages registration and retrieval of task definitions.
"""

from typing import Dict, List, Optional, Type

from .base import BaseTask

# Global task registry
_TASK_REGISTRY: Dict[str, Type[BaseTask]] = {}


def register_task(task_id: Optional[str] = None):
    """Decorator to register a task class.

    Usage:
        @register_task()
        class MyTask(BaseTask):
            config = TaskConfig(task_id="my-task", ...)

        # Or with explicit ID
        @register_task("custom-id")
        class MyTask(BaseTask):
            ...
    """

    def decorator(cls: Type[BaseTask]) -> Type[BaseTask]:
        nonlocal task_id
        if task_id is None:
            task_id = cls.config.task_id

        if task_id in _TASK_REGISTRY:
            raise ValueError(f"Task '{task_id}' is already registered")

        _TASK_REGISTRY[task_id] = cls
        return cls

    return decorator


def get_task_class(task_id: str) -> Type[BaseTask]:
    """Get a task class by ID.

    Args:
        task_id: Task identifier

    Returns:
        Task class

    Raises:
        KeyError: If task not found
    """
    if task_id not in _TASK_REGISTRY:
        available = ", ".join(_TASK_REGISTRY.keys())
        raise KeyError(f"Task '{task_id}' not found. Available: {available}")
    return _TASK_REGISTRY[task_id]


def list_tasks() -> List[Dict[str, str]]:
    """List all registered tasks.

    Returns:
        List of task info dicts with id, name, goal, difficulty
    """
    tasks = []
    for task_id, task_cls in _TASK_REGISTRY.items():
        config = task_cls.config
        tasks.append({
            "id": task_id,
            "name": config.task_name,
            "goal": config.goal,
            "difficulty": config.difficulty,
            "tags": config.tags,
        })
    return tasks
