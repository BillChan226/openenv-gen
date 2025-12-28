"""
Agents - Dual agent system for environment generation

Uses utils.base_agent.BaseAgent as foundation.

UserAgent: Simulated user/PM/QA - plans, delegates, verifies
CodeAgent: Developer - generates code, fixes issues
Coordinator: Orchestrates the interaction
"""

from .user_agent import UserAgent
from .code_agent import CodeAgent
from .coordinator import Coordinator

__all__ = [
    "UserAgent",
    "CodeAgent",
    "Coordinator",
]
