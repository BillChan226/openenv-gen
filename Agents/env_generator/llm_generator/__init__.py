"""
LLM Generator - Generate OpenEnv-compatible web environments using LLM

Architecture:
- UserAgent: Plans tasks, verifies results, reports issues
- CodeAgent: Generates code, fixes issues
- Coordinator: Orchestrates the interaction

Usage:
    from llm_generator import Coordinator
    from utils.config import LLMConfig
    
    coordinator = Coordinator(llm_config, output_dir)
    result = await coordinator.run(goal="Build a calendar app")
"""

from .agents import UserAgent, CodeAgent, Coordinator
from .messages import Task, TaskType, Issue, IssueSeverity, TaskResult, VerifyResult
from .specs import PROJECT_STRUCTURE, PHASES, get_phase_spec
from .context import GenerationContext
from .progress import EventEmitter, EventType

__all__ = [
    # Agents
    "UserAgent",
    "CodeAgent", 
    "Coordinator",
    
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
