"""
Multi-Agent Environment Generation Agents

Architecture:
- EnvGenAgent: Extends utils.base_agent.BaseAgent with j2 prompts, LLM agentic loop
- Each agent: Subclass that overrides _get_system_prompt() and _build_task_prompt()
- Prompts: Use j2 templates from prompts/ directory

Inherited from utils:
- BaseAgent: State management, message queue, stuck detection, retry, metrics
- MessageBus: Agent communication
- ToolRegistry: Tool management

Agents:
- DatabaseAgent: PostgreSQL schema, seed data
- BackendAgent: Express.js API
- FrontendAgent: React + Vite + Tailwind
- DesignAgent: Architecture, specs
- UserAgent: PM/QA, requirements, testing
- TaskAgent: Benchmark tasks, trajectories, judges
"""

# Re-export utils base classes for convenience
from utils.base_agent import BaseAgent, AgentRole, AgentCapability, AgentMetrics
from utils.state import AgentState
from utils.communication import MessageBus, EventEmitter

# Environment generation specific
from .base import EnvGenAgent, safe_json_dumps
from .database_agent import DatabaseAgent
from .backend_agent import BackendAgent
from .frontend_agent import FrontendAgent
from .design_agent import DesignAgent
from .user_agent import UserAgent
from .task_agent import TaskAgent

__all__ = [
    # Utils base classes
    "BaseAgent",
    "AgentRole",
    "AgentCapability",
    "AgentMetrics",
    "AgentState",
    "MessageBus",
    "EventEmitter",
    # EnvGen specific
    "EnvGenAgent",
    "safe_json_dumps",
    "DatabaseAgent",
    "BackendAgent",
    "FrontendAgent",
    "DesignAgent",
    "UserAgent",
    "TaskAgent",
]
