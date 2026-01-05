"""
LLM Generator - Generate OpenEnv-compatible web environments using LLM

Architecture (Multi-Agent):
- UserAgent: Plans tasks, verifies results, reports issues, tracks progress
- DesignAgent: Creates design specifications (API, UI, Database)
- DatabaseAgent: Generates database code
- BackendAgent: Generates backend code
- FrontendAgent: Generates frontend code
- Orchestrator: Coordinates multi-agent interaction

Usage:
    from llm_generator import Orchestrator
    from utils.config import LLMConfig
    
    orchestrator = Orchestrator(llm_config, output_dir, project_name)
    result = await orchestrator.run(requirements="Build a calendar app")
"""

from .agents import (
    Orchestrator,
    UserAgent,
    DesignAgent,
    DatabaseAgent,
    BackendAgent,
    FrontendAgent,
)
from .messages import Task, TaskType, Issue, IssueSeverity, TaskResult, VerifyResult
from .specs import PROJECT_STRUCTURE, PHASES, get_phase_spec
from .context import GenerationContext
from .progress import EventEmitter, EventType

__all__ = [
    # Multi-Agent System
    "Orchestrator",
    "UserAgent",
    "DesignAgent",
    "DatabaseAgent",
    "BackendAgent",
    "FrontendAgent",
    
    # Messages
    "Task",
    "TaskType",
    "Issue",
    "IssueSeverity",
    "TaskResult",
    "VerifyResult",
    
    # Specs
    "PROJECT_STRUCTURE",
    "PHASES",
    "get_phase_spec",
    
    # Context
    "GenerationContext",
    
    # Events
    "EventEmitter",
    "EventType",
]
