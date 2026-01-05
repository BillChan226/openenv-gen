"""
Debug Module - Enhanced logging and debugging for LLM agents

Inspired by OpenHands DebugMixin, this module provides:
- Separated loggers for prompts and responses
- Structured logging with metadata
- Token usage tracking
- Configurable log levels and formats
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path


# ===== Separate Loggers =====

# Main logger for general agent operations
agent_logger = logging.getLogger("agent")

# Dedicated logger for LLM prompts (can be enabled/disabled separately)
llm_prompt_logger = logging.getLogger("agent.llm.prompt")

# Dedicated logger for LLM responses (can be enabled/disabled separately)
llm_response_logger = logging.getLogger("agent.llm.response")

# Logger for tool calls
tool_logger = logging.getLogger("agent.tool")

# Logger for events (actions, observations)
event_logger = logging.getLogger("agent.event")


@dataclass
class LogConfig:
    """Configuration for logging."""
    level: int = logging.INFO
    format: str = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    log_file: Optional[str] = None
    log_prompts: bool = False  # Enable to log full prompts (verbose)
    log_responses: bool = False  # Enable to log full responses (verbose)
    max_content_length: int = 1000  # Truncate long content in logs


def setup_logging(config: LogConfig = None) -> None:
    """
    Setup logging with the given configuration.
    
    Args:
        config: Logging configuration
    """
    config = config or LogConfig()
    
    # Create formatter
    formatter = logging.Formatter(config.format)
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(config.level)
    
    # Setup root agent logger
    agent_logger.setLevel(config.level)
    agent_logger.addHandler(console_handler)
    
    # Setup file handler if specified
    if config.log_file:
        file_handler = logging.FileHandler(config.log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(config.level)
        agent_logger.addHandler(file_handler)
    
    # Configure sub-loggers based on settings
    if config.log_prompts:
        llm_prompt_logger.setLevel(logging.DEBUG)
    else:
        llm_prompt_logger.setLevel(logging.WARNING)
    
    if config.log_responses:
        llm_response_logger.setLevel(logging.DEBUG)
    else:
        llm_response_logger.setLevel(logging.WARNING)


def truncate_content(content: str, max_length: int = 1000) -> str:
    """Truncate content for logging."""
    if len(content) <= max_length:
        return content
    return content[:max_length] + f"... [truncated, total {len(content)} chars]"


# ===== Debug Mixin =====

class DebugMixin:
    """
    Mixin that adds debugging capabilities to LLM classes.
    
    Usage:
        class MyLLM(DebugMixin):
            def __init__(self):
                self._debug_config = LogConfig()
                
            async def completion(self, messages):
                self.log_prompt(messages)
                response = await self._call_api(messages)
                self.log_response(response)
                return response
    """
    
    MESSAGE_SEPARATOR = "\n\n" + "=" * 50 + "\n\n"
    
    def __init__(self):
        self._debug_config = LogConfig()
        self._call_count = 0
        self._total_tokens = 0
    
    def log_prompt(self, messages: List[Dict[str, Any]]) -> None:
        """
        Log LLM prompt messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
        """
        if not llm_prompt_logger.isEnabledFor(logging.DEBUG):
            return
        
        if not messages:
            llm_prompt_logger.debug("No messages to send")
            return
        
        formatted_parts = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            if isinstance(content, list):
                # Handle multimodal content
                content = self._format_multimodal_content(content)
            
            formatted_parts.append(f"[{role.upper()}]\n{content}")
        
        debug_message = self.MESSAGE_SEPARATOR.join(formatted_parts)
        llm_prompt_logger.debug(f"LLM Prompt:\n{debug_message}")
    
    def log_response(self, response: Any) -> None:
        """
        Log LLM response.
        
        Args:
            response: Response from LLM API
        """
        if not llm_response_logger.isEnabledFor(logging.DEBUG):
            return
        
        # Handle different response formats
        if hasattr(response, 'choices') and response.choices:
            choice = response.choices[0]
            message = choice.message if hasattr(choice, 'message') else choice
            
            content = getattr(message, 'content', '') or ''
            tool_calls = getattr(message, 'tool_calls', []) or []
            
            log_parts = [f"Content: {content}"]
            
            if tool_calls:
                for tc in tool_calls:
                    func = tc.function if hasattr(tc, 'function') else tc
                    name = getattr(func, 'name', 'unknown')
                    args = getattr(func, 'arguments', '{}')
                    log_parts.append(f"Tool Call: {name}({args})")
            
            llm_response_logger.debug(f"LLM Response:\n" + "\n".join(log_parts))
        else:
            llm_response_logger.debug(f"LLM Response: {response}")
    
    def log_tool_call(self, tool_name: str, arguments: Dict[str, Any], result: Any) -> None:
        """
        Log a tool call and its result.
        
        Args:
            tool_name: Name of the tool called
            arguments: Arguments passed to the tool
            result: Result from the tool
        """
        args_str = json.dumps(arguments, default=str)[:500]
        result_str = str(result)[:500]
        
        tool_logger.info(f"Tool: {tool_name}")
        tool_logger.debug(f"  Args: {args_str}")
        tool_logger.debug(f"  Result: {result_str}")
    
    def log_event(self, event_type: str, content: Any, metadata: Dict = None) -> None:
        """
        Log an agent event (action or observation).
        
        Args:
            event_type: Type of event (e.g., "action", "observation")
            content: Event content
            metadata: Additional metadata
        """
        content_str = truncate_content(str(content), 500)
        
        if metadata:
            event_logger.info(f"[{event_type.upper()}] {content_str} | meta: {metadata}")
        else:
            event_logger.info(f"[{event_type.upper()}] {content_str}")
    
    def _format_multimodal_content(self, content: List[Dict]) -> str:
        """Format multimodal content (text + images) for logging."""
        parts = []
        for item in content:
            if item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif item.get("type") == "image_url":
                url = item.get("image_url", {}).get("url", "")
                if url.startswith("data:"):
                    parts.append("[IMAGE: base64 data]")
                else:
                    parts.append(f"[IMAGE: {url[:100]}]")
        return "\n".join(parts)
    
    def update_token_usage(self, usage: Dict[str, int]) -> None:
        """
        Update token usage statistics.
        
        Args:
            usage: Dict with 'prompt_tokens', 'completion_tokens', etc.
        """
        self._call_count += 1
        
        if 'total_tokens' in usage:
            self._total_tokens += usage['total_tokens']
        else:
            self._total_tokens += usage.get('prompt_tokens', 0) + usage.get('completion_tokens', 0)
    
    @property
    def debug_stats(self) -> Dict[str, Any]:
        """Get debug statistics."""
        return {
            "call_count": self._call_count,
            "total_tokens": self._total_tokens,
        }


# ===== Structured Event Logger =====

@dataclass
class LoggedEvent:
    """A logged event with structured data."""
    timestamp: datetime
    event_type: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "content": self.content,
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        def default_handler(obj):
            if hasattr(obj, 'to_dict'):
                return obj.to_dict()
            if hasattr(obj, '__dict__'):
                return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
            return str(obj)
        return json.dumps(self.to_dict(), ensure_ascii=False, default=default_handler)


class StructuredLogger:
    """
    Structured event logger that writes JSON events to a file.
    
    Useful for debugging and post-hoc analysis of agent runs.
    
    Usage:
        logger = StructuredLogger("agent_run.jsonl")
        logger.log("action", "execute command", {"command": "ls"})
        logger.log("observation", "file1.txt\\nfile2.txt")
    """
    
    def __init__(self, log_file: str):
        """
        Args:
            log_file: Path to log file (JSONL format)
        """
        self.log_file = Path(log_file)
        self._events: List[LoggedEvent] = []
    
    def log(self, event_type: str, content: str, metadata: Dict = None) -> LoggedEvent:
        """
        Log an event.
        
        Args:
            event_type: Type of event
            content: Event content
            metadata: Additional metadata
            
        Returns:
            The logged event
        """
        event = LoggedEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            content=content,
            metadata=metadata or {},
        )
        
        self._events.append(event)
        
        # Append to file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(event.to_json() + "\n")
        
        return event
    
    def get_events(self, event_type: str = None) -> List[LoggedEvent]:
        """
        Get logged events, optionally filtered by type.
        
        Args:
            event_type: Optional type to filter by
            
        Returns:
            List of events
        """
        if event_type:
            return [e for e in self._events if e.event_type == event_type]
        return self._events.copy()
    
    def clear(self) -> None:
        """Clear in-memory events (does not affect file)."""
        self._events.clear()


# ===== Convenience Functions =====

def log_action(action: str, details: Dict = None) -> None:
    """Log an agent action."""
    if details:
        event_logger.info(f"ACTION: {action} | {details}")
    else:
        event_logger.info(f"ACTION: {action}")


def log_observation(observation: str, truncate: bool = True) -> None:
    """Log an observation."""
    if truncate:
        observation = truncate_content(observation, 500)
    event_logger.info(f"OBSERVATION: {observation}")


def log_error(error: str, exception: Exception = None) -> None:
    """Log an error."""
    if exception:
        event_logger.error(f"ERROR: {error} | {type(exception).__name__}: {exception}")
    else:
        event_logger.error(f"ERROR: {error}")


def log_phase(phase: str, status: str = "start") -> None:
    """Log a phase transition."""
    agent_logger.info(f"{'=' * 20} PHASE: {phase.upper()} ({status}) {'=' * 20}")

