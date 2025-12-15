"""Data models for the {{ENV_NAME}} environment.

Defines Action, Observation, and State dataclasses compatible with OpenEnv.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass(kw_only=True)
class WebAction:
    """Action for web environment interaction.

    Supports both natural language actions (BrowserGym style) and structured actions.

    Attributes:
        action_str: Natural language action string (e.g., "click('submit-btn')")
        action_type: Structured action type (click, type, scroll, etc.)
        selector: CSS selector or element ID for structured actions
        value: Value for type/fill actions
        metadata: Additional action metadata
    """

    # Natural language action (BrowserGym compatible)
    action_str: str = ""

    # Structured action fields (alternative to action_str)
    action_type: Optional[str] = None  # click, type, scroll, select, etc.
    selector: Optional[str] = None
    value: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_action_str(self) -> str:
        """Convert structured action to action string."""
        if self.action_str:
            return self.action_str

        if self.action_type == "click":
            return f"click('{self.selector}')"
        elif self.action_type == "type":
            return f"type('{self.selector}', '{self.value}')"
        elif self.action_type == "fill":
            return f"fill('{self.selector}', '{self.value}')"
        elif self.action_type == "scroll":
            return f"scroll('{self.value or 'down'}')"
        elif self.action_type == "goto":
            return f"goto('{self.value}')"
        elif self.action_type == "press":
            return f"press('{self.value}')"

        return "noop()"


@dataclass(kw_only=True)
class WebObservation:
    """Observation from the web environment.

    Attributes:
        text: Text representation of the page (accessibility tree or DOM)
        url: Current page URL
        screenshot: Screenshot as nested list [height, width, channels]
        goal: Current task goal/instruction
        html: Page HTML content
        axtree_txt: Accessibility tree as text
        error: Error message if last action failed
        last_action_error: Whether the last action resulted in an error
        done: Whether the episode is complete
        reward: Reward for the last action
        metadata: Additional observation metadata
    """

    text: str = ""
    url: str = ""
    screenshot: Optional[List[List[List[int]]]] = None
    goal: str = ""
    html: str = ""
    axtree_txt: str = ""
    error: str = ""
    last_action_error: bool = False
    done: bool = False
    reward: Union[bool, int, float, None] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebState:
    """Environment state for tracking episode progress.

    Attributes:
        episode_id: Unique identifier for the current episode
        step_count: Number of steps taken in the episode
        task_id: Identifier for the current task
        task_name: Human-readable task name
        goal: Current task goal
        current_url: Current page URL
        max_steps: Maximum allowed steps
        cum_reward: Cumulative reward for the episode
        db_state: Snapshot of relevant database state
    """

    episode_id: Optional[str] = None
    step_count: int = 0
    task_id: Optional[str] = None
    task_name: str = ""
    goal: str = ""
    current_url: str = ""
    max_steps: Optional[int] = None
    cum_reward: float = 0.0
    db_state: Dict[str, Any] = field(default_factory=dict)
