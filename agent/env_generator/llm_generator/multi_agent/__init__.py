"""
Multi-Agent Environment Generation System

Event-driven architecture where agents communicate in real-time via MessageBus.

Components:
- Orchestrator: Coordinates the workflow
- WorkspaceManager: File access control
- Agents:
  - UserAgent: Requirements & Testing
  - DesignAgent: Architecture & Design
  - DatabaseAgent: Database code
  - BackendAgent: API code  
  - FrontendAgent: UI code
"""

from .orchestrator import Orchestrator, GenerationResult
from .workspace_manager import WorkspaceManager
from .agents import (
    EnvGenAgent,
    UserAgent,
    DesignAgent,
    DatabaseAgent,
    BackendAgent,
    FrontendAgent,
)

__all__ = [
    "Orchestrator",
    "GenerationResult",
    "WorkspaceManager",
    "EnvGenAgent",
    "UserAgent",
    "DesignAgent",
    "DatabaseAgent",
    "BackendAgent",
    "FrontendAgent",
]
