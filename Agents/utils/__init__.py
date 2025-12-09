"""
AgentForge Utils - Agent Infrastructure Module

Provides core components for building intelligent Multi-Agent systems:

Core Modules:
- message: Message protocol definitions
- config: Configuration management
- state: State and lifecycle management
- tool: Tool interface and registry
- base_agent: Agent base class
- communication: Communication mechanisms (message bus, event system)

Intelligence Modules:
- llm: LLM client for various providers (OpenAI, Anthropic, etc.)
- prompt: Prompt template management
- memory: Memory systems (short-term, long-term, semantic)
- planner: Task planning and decomposition
- reasoning: ReAct and other reasoning patterns

Usage example:
    from utils import BaseAgent, AgentConfig, TaskMessage, LLM, Planner, ReActEngine
    
    class SmartAgent(BaseAgent):
        def __init__(self, config):
            super().__init__(config)
            self.llm = LLM(config.llm)
            self.planner = Planner(config.llm)
            self.reasoner = ReActEngine(config.llm, self.tools)
        
        async def process_task(self, task: TaskMessage) -> ResultMessage:
            # Use planning + reasoning
            plan = await self.planner.create_plan(task.task_description)
            result = await self.reasoner.run(task.task_description)
            ...
"""

# ===== Core Modules =====

# Message module
from .message import (
    # Enums
    MessageType,
    MessagePriority,
    ControlAction,
    # Data classes
    MessageHeader,
    BaseMessage,
    TaskMessage,
    ResultMessage,
    StatusMessage,
    ErrorMessage,
    ControlMessage,
    # Factory functions
    create_task_message,
    create_result_message,
    create_error_message,
)

# Config module
from .config import (
    # Enums
    LogLevel,
    LLMProvider,
    ExecutionMode,
    # Config classes
    LLMConfig,
    ExecutionConfig,
    LoggingConfig,
    NetworkConfig,
    MemoryConfig,
    AgentConfig,
)

# State module
from .state import (
    # Enums
    AgentState,
    TaskState,
    # Data classes
    StateTransition,
    TaskContext,
    # Managers
    StateManager,
    AgentContext,
    # Constants
    VALID_AGENT_TRANSITIONS,
    VALID_TASK_TRANSITIONS,
)

# Tool module
from .tool import (
    # Enums
    ToolCategory,
    ToolStatus,
    # Data classes
    ToolParameter,
    ToolResult,
    ToolDefinition,
    # Base class
    BaseTool,
    # Registry
    ToolRegistry,
    global_registry,
    # Decorator
    tool,
    # Example tools
    EchoTool,
    SleepTool,
)

# Agent base
from .base_agent import (
    AgentRole,
    AgentCapability,
    AgentMetrics,
    BaseAgent,
)

# Planning agent
from .planning_agent import (
    PlanRecord,
    PlanningAgent,
)

# Communication module
from .communication import (
    Subscription,
    MessageBus,
    EventEmitter,
    MessageRouter,
)

# ===== Intelligence Modules =====

# LLM module
from .llm import (
    # Data classes
    Message,
    LLMResponse,
    # Base class
    BaseLLMClient,
    # Clients
    OpenAIClient,
    AnthropicClient,
    LocalLLMClient,
    # Factory
    create_llm_client,
    # High-level interface
    LLM,
)

# Prompt module
from .prompt import (
    # Classes
    PromptTemplate,
    PromptBuilder,
    PromptRegistry,
    # Built-in templates
    PLANNER_SYSTEM_PROMPT,
    PLANNER_TEMPLATE,
    REACT_SYSTEM_PROMPT,
    REACT_TEMPLATE,
    SUMMARIZER_TEMPLATE,
    ANALYZER_TEMPLATE,
    CODE_GENERATOR_TEMPLATE,
    EVALUATOR_TEMPLATE,
    # Registry
    prompt_registry,
    # Helpers
    format_tools_for_prompt,
    format_history_for_prompt,
)

# Memory module
from .memory import (
    # Data classes
    MemoryItem,
    # Memory types
    BaseMemory,
    ShortTermMemory,
    WorkingMemory,
    LongTermMemory,
    SemanticMemory,
    # Unified memory
    AgentMemory,
)

# Planner module
from .planner import (
    # Enums
    StepStatus,
    # Data classes
    PlanStep,
    Plan,
    # Planner
    Planner,
    PlanExecutor,
    # Helpers
    create_planner_template,
)

# Reasoning module
from .reasoning import (
    # Enums
    ReasoningAction,
    # Data classes
    ReasoningStep,
    ReasoningResult,
    # Engines
    ReActEngine,
    ChainOfThought,
    SelfAsk,
    ReflectionEngine,
    # Helpers
    create_react_template,
)


# Version info
__version__ = "0.2.0"
__author__ = "AgentForge Team"


# Export list
__all__ = [
    # ===== Core =====
    # Message
    "MessageType",
    "MessagePriority",
    "ControlAction",
    "MessageHeader",
    "BaseMessage",
    "TaskMessage",
    "ResultMessage",
    "StatusMessage",
    "ErrorMessage",
    "ControlMessage",
    "create_task_message",
    "create_result_message",
    "create_error_message",
    
    # Config
    "LogLevel",
    "LLMProvider",
    "ExecutionMode",
    "LLMConfig",
    "ExecutionConfig",
    "LoggingConfig",
    "NetworkConfig",
    "MemoryConfig",
    "AgentConfig",
    
    # State
    "AgentState",
    "TaskState",
    "StateTransition",
    "TaskContext",
    "StateManager",
    "AgentContext",
    "VALID_AGENT_TRANSITIONS",
    "VALID_TASK_TRANSITIONS",
    
    # Tool
    "ToolCategory",
    "ToolStatus",
    "ToolParameter",
    "ToolResult",
    "ToolDefinition",
    "BaseTool",
    "ToolRegistry",
    "global_registry",
    "tool",
    "EchoTool",
    "SleepTool",
    
    # Agent
    "AgentRole",
    "AgentCapability",
    "AgentMetrics",
    "BaseAgent",
    "PlanRecord",
    "PlanningAgent",
    
    # Communication
    "Subscription",
    "MessageBus",
    "EventEmitter",
    "MessageRouter",
    
    # ===== Intelligence =====
    # LLM
    "Message",
    "LLMResponse",
    "BaseLLMClient",
    "OpenAIClient",
    "AnthropicClient",
    "LocalLLMClient",
    "create_llm_client",
    "LLM",
    
    # Prompt
    "PromptTemplate",
    "PromptBuilder",
    "PromptRegistry",
    "PLANNER_SYSTEM_PROMPT",
    "PLANNER_TEMPLATE",
    "REACT_SYSTEM_PROMPT",
    "REACT_TEMPLATE",
    "SUMMARIZER_TEMPLATE",
    "ANALYZER_TEMPLATE",
    "CODE_GENERATOR_TEMPLATE",
    "EVALUATOR_TEMPLATE",
    "prompt_registry",
    "format_tools_for_prompt",
    "format_history_for_prompt",
    
    # Memory
    "MemoryItem",
    "BaseMemory",
    "ShortTermMemory",
    "WorkingMemory",
    "LongTermMemory",
    "SemanticMemory",
    "AgentMemory",
    
    # Planner
    "StepStatus",
    "PlanStep",
    "Plan",
    "Planner",
    "PlanExecutor",
    "create_planner_template",
    
    # Reasoning
    "ReasoningAction",
    "ReasoningStep",
    "ReasoningResult",
    "ReActEngine",
    "ChainOfThought",
    "SelfAsk",
    "ReflectionEngine",
    "create_react_template",
]
