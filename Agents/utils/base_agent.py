"""
Agent Base Module - Defines core structure and behavior of Agents

Provides:
- BaseAgent: Base class for all Agents
- AgentCapability: Agent capability definition
- AgentRole: Agent role definition
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, TypeVar
from uuid import uuid4
import asyncio
import logging

from .config import AgentConfig, LogLevel
from .state import AgentState, StateManager, TaskContext, TaskState, AgentContext
from .message import (
    BaseMessage, 
    TaskMessage, 
    ResultMessage, 
    StatusMessage,
    ErrorMessage,
    ControlMessage,
    ControlAction,
    MessageType,
    MessagePriority,
    create_result_message,
    create_error_message,
)
from .tool import BaseTool, ToolRegistry, ToolResult


class AgentRole(Enum):
    """Agent role types"""
    COORDINATOR = "coordinator"   # Coordinator - manages other agents
    WORKER = "worker"             # Worker - executes specific tasks
    SUPERVISOR = "supervisor"     # Supervisor - monitors and validates
    SPECIALIST = "specialist"     # Specialist - specific domain
    ASSISTANT = "assistant"       # Assistant - auxiliary work


@dataclass
class AgentCapability:
    """Agent capability definition"""
    name: str
    description: str = ""
    enabled: bool = True
    config: dict = field(default_factory=dict)


@dataclass
class AgentMetrics:
    """Agent metrics statistics"""
    tasks_received: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time: float = 0.0  # seconds
    average_execution_time: float = 0.0
    last_active: Optional[datetime] = None
    errors_count: int = 0
    
    def record_task_completion(self, execution_time: float, success: bool) -> None:
        """Record task completion"""
        self.last_active = datetime.now()
        if success:
            self.tasks_completed += 1
        else:
            self.tasks_failed += 1
        
        self.total_execution_time += execution_time
        total_tasks = self.tasks_completed + self.tasks_failed
        if total_tasks > 0:
            self.average_execution_time = self.total_execution_time / total_tasks
    
    def to_dict(self) -> dict:
        return {
            "tasks_received": self.tasks_received,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": self.average_execution_time,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "errors_count": self.errors_count,
            "success_rate": self.tasks_completed / max(1, self.tasks_completed + self.tasks_failed),
        }


class BaseAgent(ABC):
    """
    Agent Base Class
    
    All Agents must inherit this class and implement the process_task method
    
    Lifecycle:
    1. __init__: Create instance
    2. initialize: Initialize resources
    3. start: Start running
    4. process_task: Process tasks (loop)
    5. stop: Stop running
    6. cleanup: Clean up resources
    
    Usage example:
        class MyAgent(BaseAgent):
            async def process_task(self, task: TaskMessage) -> ResultMessage:
                # Process task
                result = do_something(task.payload)
                return create_result_message(
                    self.agent_id, task.header.source_agent_id,
                    task.task_id, True, result
                )
    """
    
    def __init__(
        self,
        config: AgentConfig,
        role: AgentRole = AgentRole.WORKER,
    ):
        # Basic attributes
        self._config = config
        self._role = role
        self._agent_id = config.agent_id or str(uuid4())
        self._name = config.agent_name or f"Agent-{self._agent_id[:8]}"
        
        # State management
        self._context = AgentContext(self._agent_id)
        self._state_manager = self._context.state_manager
        
        # Tool registry
        self._tools = ToolRegistry()
        
        # Capability list
        self._capabilities: list[AgentCapability] = []
        
        # Metrics
        self._metrics = AgentMetrics()
        
        # Message queue
        self._message_queue: asyncio.Queue[BaseMessage] = asyncio.Queue(
            maxsize=config.execution.queue_size
        )
        
        # Callbacks
        self._on_message_callbacks: list[Callable[[BaseMessage], None]] = []
        self._on_state_change_callbacks: list[Callable[[AgentState, AgentState], None]] = []
        
        # Internal control
        self._running = False
        self._main_task: Optional[asyncio.Task] = None
        self._worker_tasks: list[asyncio.Task] = []
        
        # Logger
        self._logger = self._setup_logger()
    
    # ===== Properties =====
    
    @property
    def agent_id(self) -> str:
        return self._agent_id
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def role(self) -> AgentRole:
        return self._role
    
    @property
    def config(self) -> AgentConfig:
        return self._config
    
    @property
    def state(self) -> AgentState:
        return self._state_manager.state
    
    @property
    def is_running(self) -> bool:
        return self._running and self._state_manager.is_running
    
    @property
    def context(self) -> AgentContext:
        return self._context
    
    @property
    def tools(self) -> ToolRegistry:
        return self._tools
    
    @property
    def metrics(self) -> AgentMetrics:
        return self._metrics
    
    @property
    def capabilities(self) -> list[AgentCapability]:
        return self._capabilities
    
    # ===== Lifecycle Methods =====
    
    async def initialize(self) -> bool:
        """
        Initialize Agent
        
        Subclasses can override this method to perform custom initialization
        """
        self._logger.info(f"Initializing agent: {self._name}")
        
        try:
            # Register built-in tools
            await self._register_builtin_tools()
            
            # Subclass custom initialization
            await self.on_initialize()
            
            # Transition to IDLE state
            self._state_manager.transition_to(AgentState.IDLE, "initialization_complete")
            
            self._logger.info(f"Agent {self._name} initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize agent: {e}")
            self._state_manager.transition_to(AgentState.ERROR, f"init_error: {e}")
            return False
    
    async def start(self) -> bool:
        """Start Agent"""
        if self._running:
            self._logger.warning("Agent is already running")
            return False
        
        if self.state != AgentState.IDLE:
            self._logger.warning(f"Cannot start agent in state: {self.state}")
            return False
        
        self._logger.info(f"Starting agent: {self._name}")
        
        try:
            self._running = True
            self._state_manager.transition_to(AgentState.RUNNING, "start_command")
            
            # Start main loop
            self._main_task = asyncio.create_task(self._main_loop())
            
            # Start worker threads
            for i in range(self._config.execution.max_concurrent_tasks):
                task = asyncio.create_task(self._worker_loop(i))
                self._worker_tasks.append(task)
            
            await self.on_start()
            
            self._logger.info(f"Agent {self._name} started successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to start agent: {e}")
            self._running = False
            self._state_manager.transition_to(AgentState.ERROR, f"start_error: {e}")
            return False
    
    async def stop(self, force: bool = False) -> bool:
        """Stop Agent"""
        if not self._running:
            return True
        
        self._logger.info(f"Stopping agent: {self._name}")
        self._state_manager.transition_to(AgentState.STOPPING, "stop_command")
        
        self._running = False
        
        # Wait for tasks to complete
        if not force:
            # Give running tasks some time to complete
            await asyncio.sleep(0.5)
        
        # Cancel all worker tasks
        for task in self._worker_tasks:
            if not task.done():
                task.cancel()
        
        if self._main_task and not self._main_task.done():
            self._main_task.cancel()
        
        # Wait for task cancellation to complete
        await asyncio.gather(*self._worker_tasks, self._main_task, return_exceptions=True)
        
        self._worker_tasks.clear()
        self._main_task = None
        
        await self.on_stop()
        
        self._state_manager.transition_to(AgentState.STOPPED, "stop_complete")
        self._logger.info(f"Agent {self._name} stopped")
        
        return True
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        self._logger.info(f"Cleaning up agent: {self._name}")
        
        # Ensure stopped
        if self._running:
            await self.stop(force=True)
        
        # Subclass cleanup
        await self.on_cleanup()
        
        # Clear context
        self._context.clear_variables()
        
        self._logger.info(f"Agent {self._name} cleaned up")
    
    # ===== Message Processing =====
    
    async def send_message(self, message: BaseMessage) -> None:
        """Send message to queue"""
        message.header.source_agent_id = self._agent_id
        await self._message_queue.put(message)
        self._logger.debug(f"Message queued: {message.message_type.value}")
    
    async def receive_message(self, message: BaseMessage) -> None:
        """Receive external message"""
        self._logger.debug(f"Received message: {message.message_type.value}")
        
        # Trigger callbacks
        for callback in self._on_message_callbacks:
            try:
                callback(message)
            except Exception as e:
                self._logger.error(f"Message callback error: {e}")
        
        # Handle control messages
        if isinstance(message, ControlMessage):
            await self._handle_control_message(message)
        else:
            await self._message_queue.put(message)
    
    async def _handle_control_message(self, message: ControlMessage) -> None:
        """Handle control message"""
        action = message.action
        
        if action == ControlAction.START:
            await self.start()
        elif action == ControlAction.STOP:
            await self.stop(force=message.force)
        elif action == ControlAction.PAUSE:
            self._state_manager.transition_to(AgentState.PAUSED, "pause_command")
        elif action == ControlAction.RESUME:
            self._state_manager.transition_to(AgentState.RUNNING, "resume_command")
        elif action == ControlAction.SHUTDOWN:
            await self.cleanup()
    
    # ===== Core Processing Logic =====
    
    async def _main_loop(self) -> None:
        """Main message loop"""
        while self._running:
            try:
                # Check if paused
                if self.state == AgentState.PAUSED:
                    await asyncio.sleep(0.1)
                    continue
                
                # Get message from queue
                try:
                    message = await asyncio.wait_for(
                        self._message_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process message
                await self._dispatch_message(message)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in main loop: {e}")
                self._metrics.errors_count += 1
    
    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop"""
        self._logger.debug(f"Worker {worker_id} started")
        
        while self._running:
            try:
                await asyncio.sleep(0.1)  # Prevent busy loop
            except asyncio.CancelledError:
                break
        
        self._logger.debug(f"Worker {worker_id} stopped")
    
    async def _dispatch_message(self, message: BaseMessage) -> None:
        """Dispatch message"""
        if isinstance(message, TaskMessage):
            await self._handle_task_message(message)
        elif isinstance(message, ResultMessage):
            await self.on_result_received(message)
        elif isinstance(message, StatusMessage):
            await self.on_status_received(message)
        elif isinstance(message, ErrorMessage):
            await self.on_error_received(message)
    
    async def _handle_task_message(self, task: TaskMessage) -> None:
        """Handle task message"""
        self._metrics.tasks_received += 1
        task_id = task.task_id
        
        # Create task context
        task_context = self._state_manager.create_task(
            task_id,
            max_retries=self._config.execution.max_retries,
        )
        
        self._logger.info(f"Processing task: {task.task_name} ({task_id})")
        
        start_time = datetime.now()
        self._state_manager.update_task_state(task_id, TaskState.RUNNING)
        
        try:
            # Call subclass implementation
            result = await asyncio.wait_for(
                self.process_task(task),
                timeout=self._config.execution.task_timeout
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Update state and metrics
            self._state_manager.update_task_state(
                task_id, 
                TaskState.COMPLETED,
                result=result.result_data if result else None
            )
            self._metrics.record_task_completion(execution_time, True)
            
            self._logger.info(f"Task completed: {task_id} ({execution_time:.2f}s)")
            
            # Send result
            if result:
                result.execution_time = execution_time
                await self.on_task_completed(task, result)
            
        except asyncio.TimeoutError:
            self._state_manager.update_task_state(
                task_id,
                TaskState.TIMEOUT,
                error_message="Task execution timeout"
            )
            self._metrics.record_task_completion(
                (datetime.now() - start_time).total_seconds(), 
                False
            )
            self._logger.warning(f"Task timeout: {task_id}")
            
            # Check if retry
            await self._handle_task_failure(task, task_context, "Timeout")
            
        except Exception as e:
            self._state_manager.update_task_state(
                task_id,
                TaskState.FAILED,
                error_message=str(e)
            )
            self._metrics.record_task_completion(
                (datetime.now() - start_time).total_seconds(),
                False
            )
            self._logger.error(f"Task failed: {task_id} - {e}")
            
            await self._handle_task_failure(task, task_context, str(e))
    
    async def _handle_task_failure(
        self,
        task: TaskMessage,
        task_context: TaskContext,
        error_message: str,
    ) -> None:
        """Handle task failure"""
        if task_context.can_retry() and self._config.execution.retry_on_failure:
            self._logger.info(f"Retrying task: {task.task_id} (attempt {task_context.retry_count + 1})")
            self._state_manager.update_task_state(task.task_id, TaskState.RETRYING)
            
            # Backoff delay
            delay = self._config.execution.retry_backoff ** task_context.retry_count
            await asyncio.sleep(delay)
            
            # Re-queue
            await self._message_queue.put(task)
        else:
            # Send error message
            await self.on_task_failed(task, error_message)
    
    # ===== Tool Management =====
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register tool"""
        self._tools.register(tool)
        self._logger.debug(f"Tool registered: {tool.name}")
    
    def unregister_tool(self, name: str) -> bool:
        """Unregister tool"""
        result = self._tools.unregister(name)
        if result:
            self._logger.debug(f"Tool unregistered: {name}")
        return result
    
    async def call_tool(self, name: str, **kwargs) -> ToolResult:
        """Call tool"""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult.fail(f"Tool not found: {name}")
        
        self._logger.debug(f"Calling tool: {name}")
        return await tool(**kwargs)
    
    async def _register_builtin_tools(self) -> None:
        """Register built-in tools - subclasses can override"""
        pass
    
    # ===== Capability Management =====
    
    def add_capability(self, capability: AgentCapability) -> None:
        """Add capability"""
        self._capabilities.append(capability)
    
    def has_capability(self, name: str) -> bool:
        """Check if has capability"""
        return any(c.name == name and c.enabled for c in self._capabilities)
    
    # ===== Callback Management =====
    
    def on_message(self, callback: Callable[[BaseMessage], None]) -> None:
        """Register message callback"""
        self._on_message_callbacks.append(callback)
    
    def on_state_change(self, callback: Callable[[AgentState, AgentState], None]) -> None:
        """Register state change callback"""
        self._on_state_change_callbacks.append(callback)
        self._state_manager.add_callback(callback)
    
    # ===== Hook Methods (subclasses can override) =====
    
    async def on_initialize(self) -> None:
        """Initialization hook"""
        pass
    
    async def on_start(self) -> None:
        """Start hook"""
        pass
    
    async def on_stop(self) -> None:
        """Stop hook"""
        pass
    
    async def on_cleanup(self) -> None:
        """Cleanup hook"""
        pass
    
    async def on_task_completed(self, task: TaskMessage, result: ResultMessage) -> None:
        """Task completed hook"""
        pass
    
    async def on_task_failed(self, task: TaskMessage, error: str) -> None:
        """Task failed hook"""
        pass
    
    async def on_result_received(self, result: ResultMessage) -> None:
        """Result received hook"""
        pass
    
    async def on_status_received(self, status: StatusMessage) -> None:
        """Status received hook"""
        pass
    
    async def on_error_received(self, error: ErrorMessage) -> None:
        """Error received hook"""
        pass
    
    # ===== Abstract Methods (subclasses must implement) =====
    
    @abstractmethod
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """
        Process task
        
        This is the core method of Agent, subclasses must implement
        
        Args:
            task: Task message
            
        Returns:
            Result message
        """
        pass
    
    # ===== Helper Methods =====
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger"""
        logger = logging.getLogger(f"Agent.{self._name}")
        
        level_map = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }
        logger.setLevel(level_map.get(self._config.logging.level, logging.INFO))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(self._config.logging.log_format))
            logger.addHandler(handler)
        
        return logger
    
    def get_status(self) -> dict:
        """Get Agent status information"""
        return {
            "agent_id": self._agent_id,
            "name": self._name,
            "role": self._role.value,
            "state": self.state.value,
            "is_running": self.is_running,
            "queue_size": self._message_queue.qsize(),
            "metrics": self._metrics.to_dict(),
            "capabilities": [c.name for c in self._capabilities if c.enabled],
            "tools": [t.name for t in self._tools.get_all()],
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self._agent_id}, name={self._name}, state={self.state.value})>"
