"""
Runtime Events - Action and Observation dataclasses for runtime operations

These are simplified versions of the OpenHands event system, providing
just the necessary structure for command execution.
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List
from enum import Enum, auto


# ============================================================================
# Action Types
# ============================================================================

class ActionType(Enum):
    """Types of actions that can be executed."""
    CMD_RUN = auto()
    IPYTHON = auto()
    FILE_READ = auto()
    FILE_EDIT = auto()
    THINK = auto()
    FINISH = auto()


# ============================================================================
# Base Action
# ============================================================================

@dataclass
class Action:
    """Base class for all actions."""
    action_type: ActionType = ActionType.CMD_RUN
    
    @property
    def type(self) -> ActionType:
        return self.action_type


# ============================================================================
# Specific Actions
# ============================================================================

@dataclass
class CmdRunAction(Action):
    """Action to run a bash command."""
    command: str = ""
    timeout: int = 120
    keep_prompt: bool = True
    blocking: bool = True
    hidden: bool = False
    action_type: ActionType = field(default=ActionType.CMD_RUN, init=False)


@dataclass
class IPythonRunCellAction(Action):
    """Action to run Python code in IPython."""
    code: str = ""
    timeout: int = 120
    action_type: ActionType = field(default=ActionType.IPYTHON, init=False)


@dataclass
class FileReadAction(Action):
    """Action to read a file."""
    path: str = ""
    start_line: int = 0
    end_line: int = -1
    action_type: ActionType = field(default=ActionType.FILE_READ, init=False)


@dataclass
class FileEditAction(Action):
    """Action to edit a file."""
    path: str = ""
    content: str = ""
    start_line: int = 0
    end_line: int = -1
    action_type: ActionType = field(default=ActionType.FILE_EDIT, init=False)


@dataclass
class ThinkAction(Action):
    """Action for agent thinking/reasoning."""
    thought: str = ""
    action_type: ActionType = field(default=ActionType.THINK, init=False)


@dataclass
class FinishAction(Action):
    """Action to finish/complete task."""
    message: str = ""
    outputs: Dict = field(default_factory=dict)
    action_type: ActionType = field(default=ActionType.FINISH, init=False)


# ============================================================================
# Base Observation
# ============================================================================

@dataclass
class Observation:
    """Base class for all observations."""
    pass


# ============================================================================
# Specific Observations
# ============================================================================

@dataclass
class CmdOutputObservation(Observation):
    """Output from a bash command."""
    output: str = ""
    command: str = ""
    exit_code: int = 0
    hidden: bool = False
    
    @property
    def success(self) -> bool:
        return self.exit_code == 0


@dataclass
class IPythonOutputObservation(Observation):
    """Output from IPython execution."""
    output: str = ""
    code: str = ""


@dataclass
class FileReadObservation(Observation):
    """Result of reading a file."""
    path: str = ""
    content: str = ""


@dataclass
class FileEditObservation(Observation):
    """Result of editing a file."""
    path: str = ""
    old_content: str = ""
    new_content: str = ""


@dataclass
class ErrorObservation(Observation):
    """Error during execution."""
    error: str = ""
    details: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return False


@dataclass
class AgentMessageObservation(Observation):
    """Message from agent (thinking, etc.)."""
    message: str = ""
    role: str = "assistant"


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Enums
    "ActionType",
    
    # Actions
    "Action",
    "CmdRunAction",
    "IPythonRunCellAction",
    "FileReadAction",
    "FileEditAction",
    "ThinkAction",
    "FinishAction",
    
    # Observations
    "Observation",
    "CmdOutputObservation",
    "IPythonOutputObservation",
    "FileReadObservation",
    "FileEditObservation",
    "ErrorObservation",
    "AgentMessageObservation",
]

