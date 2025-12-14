"""
LLM-Powered Environment Generator

A multi-agent system for generating OpenEnv-compatible environments.

Architecture:
- CodeGeneratorAgent: Base agent with code generation capabilities
- BackendAgent: Generates FastAPI backend
- FrontendAgent: Generates React frontend
- OpenEnvAgent: Generates OpenEnv adapter
- GeneratorOrchestrator: Coordinates all agents

Based on the AgentForge framework from utils/
"""

from .agents.orchestrator import GeneratorOrchestrator
from .agents.code_agent import CodeGeneratorAgent
from .context import GenerationContext
from .events import EventEmitter, EventType, ConsoleListener, FileLogger
from .checkpoint import CheckpointManager
from .parallel import ParallelGenerator, analyze_parallelism
from .runtime_verify import RuntimeVerifier, verify_environment

__all__ = [
    # Core
    "GeneratorOrchestrator",
    "CodeGeneratorAgent", 
    "GenerationContext",
    # Events
    "EventEmitter",
    "EventType",
    "ConsoleListener",
    "FileLogger",
    # Checkpoint
    "CheckpointManager",
    # Parallel
    "ParallelGenerator",
    "analyze_parallelism",
    # Runtime Verification
    "RuntimeVerifier",
    "verify_environment",
]

