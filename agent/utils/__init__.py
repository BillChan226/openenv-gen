"""
AgentForge Utils - Agent Infrastructure Module

Provides core components for building intelligent Multi-Agent systems:

Core Modules:
- message: Message protocol definitions
- config: Configuration management
- state: State and lifecycle management
- tool: Tool interface and registry (LiteLLM compatible)
- base_agent: Agent base class
- communication: Communication mechanisms (message bus, event system)

Intelligence Modules:
- llm: LLM client for various providers (OpenAI, Anthropic, etc.)
- prompt: Jinja2-based prompt template management
- memory: Memory systems with LLM-based condensation
- planner: Task planning and decomposition
- reasoning: ReAct and other reasoning patterns

New Modules (inspired by OpenHands):
- stuck_detector: Detect when agent is stuck in loops
- retry: Robust retry mechanism with exponential backoff
- debug: Enhanced logging and debugging

Usage example:
    from utils import BaseAgent, AgentConfig, TaskMessage, LLM, Planner, ReActEngine
    from utils import StuckDetector, RetryMixin, DebugMixin
    
    class SmartAgent(BaseAgent, RetryMixin, DebugMixin):
        def __init__(self, config):
            super().__init__(config)
            self.llm = LLM(config.llm)
            self.planner = Planner(config.llm)
            self.reasoner = ReActEngine(config.llm, self.tools)
            self.stuck_detector = StuckDetector()
        
        async def process_task(self, task: TaskMessage) -> ResultMessage:
            # Use planning + reasoning with stuck detection
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

# Tool module (refactored with LiteLLM support)
from .tool import (
    # Enums
    ToolCategory,
    SecurityRisk,
    # Data classes
    ToolResult,
    # Base class
    BaseTool,
    # Registry
    ToolRegistry,
    global_registry,
    # Decorator
    tool,
    # Helper function
    create_tool_param,
    # Built-in tools
    ThinkTool,
    FinishTool,
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

# Prompt module (refactored with Jinja2)
from .prompt import (
    # Classes
    PromptManager,
    RuntimeInfo,
    ProjectInfo,
    # Helper functions
    format_tools_for_prompt,
    format_history_for_prompt,
    refine_prompt,
    get_template,
    # Templates library
    TEMPLATE_LIBRARY,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT,
)

# Memory module (with LLM condenser)
from .memory import (
    # Data classes
    MemoryItem,
    # Memory types
    ShortTermMemory,
    WorkingMemory,
    LongTermMemory,
    # LLM Condenser
    LLMSummarizingCondenser,
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

# ===== New Modules (OpenHands-inspired) =====

# Stuck Detection
from .stuck_detector import (
    StuckAnalysis,
    HistoryEvent,
    StuckDetector,
    create_stuck_detector,
)

# Retry Mechanism (now integrated in BaseAgent, but available for standalone use)
from .retry import (
    RetryConfig,
    LLMNoResponseError,
    LLMRateLimitError,
    LLMContextWindowError,
    create_retry_decorator,
    retry_on_exception,
    retry_llm_call,
    DEFAULT_CONFIG as RETRY_DEFAULT_CONFIG,
    LLM_CONFIG as RETRY_LLM_CONFIG,
    API_CONFIG as RETRY_API_CONFIG,
)

# Debug/Logging (now integrated in BaseAgent, but available for standalone use)
from .debug import (
    # Loggers
    agent_logger,
    llm_prompt_logger,
    llm_response_logger,
    tool_logger,
    event_logger,
    # Config
    LogConfig,
    setup_logging,
    truncate_content,
    # Structured Logger
    LoggedEvent,
    StructuredLogger,
    # Convenience functions
    log_action,
    log_observation,
    log_error,
    log_phase,
)


# Version info
__version__ = "0.3.0"  # Updated version
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
    
    # Tool (LiteLLM compatible)
    "ToolCategory",
    "SecurityRisk",
    "ToolResult",
    "BaseTool",
    "ToolRegistry",
    "global_registry",
    "tool",
    "create_tool_param",
    "ThinkTool",
    "FinishTool",
    
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
    
    # Prompt (Jinja2)
    "PromptManager",
    "RuntimeInfo",
    "ProjectInfo",
    "format_tools_for_prompt",
    "format_history_for_prompt",
    "refine_prompt",
    "get_template",
    "TEMPLATE_LIBRARY",
    "DEFAULT_SYSTEM_PROMPT",
    "DEFAULT_USER_PROMPT",
    
    # Memory (with condenser)
    "MemoryItem",
    "ShortTermMemory",
    "WorkingMemory",
    "LongTermMemory",
    "LLMSummarizingCondenser",
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
    
    # ===== New (OpenHands-inspired) =====
    # Stuck Detection
    "StuckAnalysis",
    "HistoryEvent",
    "StuckDetector",
    "create_stuck_detector",
    
    # Retry (standalone utilities)
    "RetryConfig",
    "LLMNoResponseError",
    "LLMRateLimitError",
    "LLMContextWindowError",
    "create_retry_decorator",
    "retry_on_exception",
    "retry_llm_call",
    "RETRY_DEFAULT_CONFIG",
    "RETRY_LLM_CONFIG",
    "RETRY_API_CONFIG",
    
    # Debug (standalone utilities)
    "agent_logger",
    "llm_prompt_logger",
    "llm_response_logger",
    "tool_logger",
    "event_logger",
    "LogConfig",
    "setup_logging",
    "truncate_content",
    "LoggedEvent",
    "StructuredLogger",
    "log_action",
    "log_observation",
    "log_error",
    "log_phase",
]
