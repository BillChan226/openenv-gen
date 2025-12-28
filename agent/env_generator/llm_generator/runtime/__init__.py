"""
Runtime Module - Code execution environment

Provides:
- BashSession: Persistent bash shell with timeout handling
- IPythonSession: Python code execution with Jupyter-like environment
- RuntimeManager: Manages all runtime sessions
- Events: Action and Observation dataclasses
"""

from .bash import BashSession
from .ipython import IPythonSession
from .manager import RuntimeManager

# Event types for external use
from ._events import (
    ActionType,
    Action,
    CmdRunAction,
    IPythonRunCellAction,
    FileReadAction,
    FileEditAction,
    ThinkAction,
    FinishAction,
    Observation,
    CmdOutputObservation,
    IPythonOutputObservation,
    FileReadObservation,
    FileEditObservation,
    ErrorObservation,
    AgentMessageObservation,
)

__all__ = [
    # Sessions
    "BashSession",
    "IPythonSession",
    "RuntimeManager",
    
    # Events
    "ActionType",
    "Action",
    "CmdRunAction",
    "IPythonRunCellAction",
    "FileReadAction",
    "FileEditAction",
    "ThinkAction",
    "FinishAction",
    "Observation",
    "CmdOutputObservation",
    "IPythonOutputObservation",
    "FileReadObservation",
    "FileEditObservation",
    "ErrorObservation",
    "AgentMessageObservation",
]
