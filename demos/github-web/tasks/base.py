"""Base task class for {{ENV_NAME}} environment.

Defines the interface for all task definitions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TaskConfig:
    """Configuration for a task.

    Attributes:
        task_id: Unique task identifier
        task_name: Human-readable task name
        goal: Natural language goal description
        start_url: URL to navigate to at episode start
        max_steps: Maximum steps allowed
        difficulty: Task difficulty level (easy, medium, hard)
        tags: Task categories/tags
    """

    task_id: str
    task_name: str
    goal: str
    start_url: str = "/"
    max_steps: int = 20
    difficulty: str = "medium"
    tags: List[str] = field(default_factory=list)


class BaseTask(ABC):
    """Base class for all tasks.

    Subclasses must implement:
    - config: Task configuration
    - validate(): Check if task is completed and compute reward
    - setup(): Optional setup logic
    - teardown(): Optional cleanup logic

    Example:
        class LoginTask(BaseTask):
            config = TaskConfig(
                task_id="login",
                task_name="User Login",
                goal="Log in with email user@example.com and password user123",
                start_url="/login",
            )

            def validate(self, page, db_state) -> Tuple[float, bool, str]:
                # Check if logged in
                if "/dashboard" in page.url:
                    return 1.0, True, "Login successful"
                return 0.0, False, ""
    """

    config: TaskConfig

    def __init__(self):
        """Initialize the task."""
        pass

    @property
    def task_id(self) -> str:
        """Get task ID."""
        return self.config.task_id

    @property
    def task_name(self) -> str:
        """Get task name."""
        return self.config.task_name

    @property
    def goal(self) -> str:
        """Get task goal description."""
        return self.config.goal

    @property
    def start_url(self) -> str:
        """Get starting URL."""
        return self.config.start_url

    @property
    def max_steps(self) -> int:
        """Get maximum steps allowed."""
        return self.config.max_steps

    def setup(self, page: Any, db_state: Dict[str, Any]) -> None:
        """Optional setup before episode starts.

        Args:
            page: Playwright page object
            db_state: Current database state
        """
        pass

    @abstractmethod
    def validate(
        self,
        page: Any,
        db_state: Dict[str, Any],
    ) -> Tuple[float, bool, str]:
        """Validate task completion and compute reward.

        Args:
            page: Playwright page object
            db_state: Current database state

        Returns:
            Tuple of (reward, done, message)
            - reward: Float reward value (typically 0.0 or 1.0)
            - done: Whether task is complete
            - message: Optional status message
        """
        pass

    def teardown(self) -> None:
        """Optional cleanup after episode ends."""
        pass

    def get_hint(self, step: int) -> Optional[str]:
        """Get optional hint for the current step.

        Args:
            step: Current step number

        Returns:
            Hint string or None
        """
        return None


class MultiStepTask(BaseTask):
    """Base class for tasks with multiple subtasks/steps.

    Provides step-by-step validation with partial rewards.
    """

    subtasks: List[Dict[str, Any]] = []

    def __init__(self):
        super().__init__()
        self._completed_subtasks = set()

    def validate(
        self,
        page: Any,
        db_state: Dict[str, Any],
    ) -> Tuple[float, bool, str]:
        """Validate subtasks and compute cumulative reward."""
        total_reward = 0.0

        for i, subtask in enumerate(self.subtasks):
            if i in self._completed_subtasks:
                continue

            if self._check_subtask(i, page, db_state):
                self._completed_subtasks.add(i)
                total_reward += subtask.get("reward", 1.0 / len(self.subtasks))

        all_done = len(self._completed_subtasks) == len(self.subtasks)
        return total_reward, all_done, ""

    def _check_subtask(
        self,
        index: int,
        page: Any,
        db_state: Dict[str, Any],
    ) -> bool:
        """Check if a specific subtask is completed.

        Override in subclass to implement subtask validation.
        """
        return False
