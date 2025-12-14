"""
OpenEnv Generator Multi-Agent System

A multi-agent system for automatically generating OpenEnv-compatible
execution environments with web GUI support.

Phases:
    1. Design: Environment specification and schema design
    2. Backend: FastAPI + SQLAlchemy code generation
    3. Frontend: React UI generation
    4. Integration: Docker + OpenEnv adapter generation

Usage:
    from env_generator import EnvGeneratorOrchestrator
    from utils import AgentConfig, LLMConfig, LLMProvider
    
    config = AgentConfig(
        agent_id="env_generator",
        agent_name="EnvGenerator",
        llm=LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4",
            api_key="your-api-key",
        ),
    )
    
    orchestrator = EnvGeneratorOrchestrator(config)
    await orchestrator.initialize()
    
    result = await orchestrator.generate_environment(
        name="calendar",
        description="A Google Calendar-like application...",
        domain_type="calendar",
    )
"""

# Version
__version__ = "0.1.0"
__author__ = "OpenEnv Generator Team"

# Orchestrator
from .orchestrator import EnvGeneratorOrchestrator

# Context and types
from .context import (
    EnvGenerationContext,
    GenerationResult,
    Entity,
    EntityField,
    EntityRelationship,
    APIEndpoint,
    UIPage,
    UIComponent,
    UserRole,
    Feature,
)

# Phase agents
from .design import EnvDesignerAgent
from .backend import SchemaDesignerAgent, APIBuilderAgent
from .frontend import UIBuilderAgent
from .integration import OpenEnvAdapterAgent, DockerComposerAgent, ValidatorAgent

# TODO: Implement remaining agents
# from .design import RequirementDocAgent

__all__ = [
    # Orchestrator
    "EnvGeneratorOrchestrator",
    # Context
    "EnvGenerationContext",
    "GenerationResult",
    "Entity",
    "EntityField",
    "EntityRelationship",
    "APIEndpoint",
    "UIPage",
    "UIComponent",
    "UserRole",
    "Feature",
    # Design Phase
    "EnvDesignerAgent",
    # Backend Phase
    "SchemaDesignerAgent",
    "APIBuilderAgent",
    # Frontend Phase
    "UIBuilderAgent",
    # Integration Phase
    "OpenEnvAdapterAgent",
    "DockerComposerAgent",
    "ValidatorAgent",
    # TODO: Add remaining agents
    # "RequirementDocAgent",
]

