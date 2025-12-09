"""
Message Protocol Module - Defines communication message formats between Agents

Supported message types:
- TaskMessage: Task assignment messages
- ResultMessage: Task result messages
- StatusMessage: Status update messages
- ErrorMessage: Error report messages
- ControlMessage: Control commands (start, stop, pause, etc.)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


class MessageType(Enum):
    """Message type enumeration"""
    TASK = "task"           # Task assignment
    RESULT = "result"       # Task result
    STATUS = "status"       # Status update
    ERROR = "error"         # Error report
    CONTROL = "control"     # Control command
    HEARTBEAT = "heartbeat" # Heartbeat detection
    LOG = "log"             # Log message


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class ControlAction(Enum):
    """Control action types"""
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    RESTART = "restart"
    SHUTDOWN = "shutdown"


@dataclass
class MessageHeader:
    """Message header - contains metadata"""
    message_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    source_agent_id: str = ""
    target_agent_id: str = ""  # Empty string means broadcast
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: Optional[str] = None  # Used to track related message chains
    reply_to: Optional[str] = None  # ID of message being replied to
    ttl: Optional[int] = None  # Message time-to-live (seconds)


@dataclass
class BaseMessage:
    """Base message class"""
    header: MessageHeader = field(default_factory=MessageHeader)
    message_type: MessageType = MessageType.STATUS
    payload: Any = None
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary format"""
        return {
            "header": {
                "message_id": self.header.message_id,
                "timestamp": self.header.timestamp.isoformat(),
                "source_agent_id": self.header.source_agent_id,
                "target_agent_id": self.header.target_agent_id,
                "priority": self.header.priority.value,
                "correlation_id": self.header.correlation_id,
                "reply_to": self.header.reply_to,
                "ttl": self.header.ttl,
            },
            "message_type": self.message_type.value,
            "payload": self.payload,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BaseMessage":
        """Create message from dictionary format"""
        header_data = data.get("header", {})
        header = MessageHeader(
            message_id=header_data.get("message_id", str(uuid4())),
            timestamp=datetime.fromisoformat(header_data.get("timestamp", datetime.now().isoformat())),
            source_agent_id=header_data.get("source_agent_id", ""),
            target_agent_id=header_data.get("target_agent_id", ""),
            priority=MessagePriority(header_data.get("priority", 1)),
            correlation_id=header_data.get("correlation_id"),
            reply_to=header_data.get("reply_to"),
            ttl=header_data.get("ttl"),
        )
        return cls(
            header=header,
            message_type=MessageType(data.get("message_type", "status")),
            payload=data.get("payload"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TaskMessage(BaseMessage):
    """Task message"""
    message_type: MessageType = field(default=MessageType.TASK, init=False)
    task_id: str = field(default_factory=lambda: str(uuid4()))
    task_name: str = ""
    task_description: str = ""
    task_params: dict = field(default_factory=dict)
    deadline: Optional[datetime] = None
    dependencies: list[str] = field(default_factory=list)  # List of dependent task IDs


@dataclass
class ResultMessage(BaseMessage):
    """Result message"""
    message_type: MessageType = field(default=MessageType.RESULT, init=False)
    task_id: str = ""
    success: bool = True
    result_data: Any = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None  # Execution time (seconds)


@dataclass
class StatusMessage(BaseMessage):
    """Status message"""
    message_type: MessageType = field(default=MessageType.STATUS, init=False)
    agent_status: str = ""
    progress: Optional[float] = None  # 0.0 - 1.0
    current_task_id: Optional[str] = None
    resource_usage: dict = field(default_factory=dict)


@dataclass
class ErrorMessage(BaseMessage):
    """Error message"""
    message_type: MessageType = field(default=MessageType.ERROR, init=False)
    error_code: str = ""
    error_message: str = ""
    error_details: dict = field(default_factory=dict)
    recoverable: bool = True
    stack_trace: Optional[str] = None


@dataclass
class ControlMessage(BaseMessage):
    """Control message"""
    message_type: MessageType = field(default=MessageType.CONTROL, init=False)
    action: ControlAction = ControlAction.START
    action_params: dict = field(default_factory=dict)
    force: bool = False  # Whether to force execution


# Message factory functions
def create_task_message(
    source_id: str,
    target_id: str,
    task_name: str,
    task_description: str = "",
    task_params: dict = None,
    priority: MessagePriority = MessagePriority.NORMAL,
) -> TaskMessage:
    """Shortcut method to create a task message"""
    header = MessageHeader(
        source_agent_id=source_id,
        target_agent_id=target_id,
        priority=priority,
    )
    return TaskMessage(
        header=header,
        task_name=task_name,
        task_description=task_description,
        task_params=task_params or {},
    )


def create_result_message(
    source_id: str,
    target_id: str,
    task_id: str,
    success: bool,
    result_data: Any = None,
    error_message: str = None,
    reply_to: str = None,
) -> ResultMessage:
    """Shortcut method to create a result message"""
    header = MessageHeader(
        source_agent_id=source_id,
        target_agent_id=target_id,
        reply_to=reply_to,
    )
    return ResultMessage(
        header=header,
        task_id=task_id,
        success=success,
        result_data=result_data,
        error_message=error_message,
    )


def create_error_message(
    source_id: str,
    error_code: str,
    error_message: str,
    target_id: str = "",
    recoverable: bool = True,
) -> ErrorMessage:
    """Shortcut method to create an error message"""
    header = MessageHeader(
        source_agent_id=source_id,
        target_agent_id=target_id,
        priority=MessagePriority.HIGH,
    )
    return ErrorMessage(
        header=header,
        error_code=error_code,
        error_message=error_message,
        recoverable=recoverable,
    )
