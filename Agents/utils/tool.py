"""
Tool Interface Module - Defines tools that Agents can use

Supports:
- BaseTool: Tool base class
- ToolRegistry: Tool registry
- ToolResult: Tool execution result
- Decorators: Simplify tool definition
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, Type, TypeVar, get_type_hints
from uuid import uuid4
import asyncio
import inspect
import functools


class ToolCategory(Enum):
    """Tool category"""
    FILE_SYSTEM = "file_system"     # File system operations
    NETWORK = "network"             # Network operations
    CODE = "code"                   # Code execution
    SHELL = "shell"                 # Shell commands
    DATA = "data"                   # Data processing
    LLM = "llm"                     # LLM calls
    SEARCH = "search"               # Search
    CUSTOM = "custom"               # Custom


class ToolStatus(Enum):
    """Tool status"""
    AVAILABLE = "available"
    BUSY = "busy"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class ToolParameter:
    """Tool parameter definition"""
    name: str
    param_type: type
    description: str = ""
    required: bool = True
    default: Any = None
    choices: list = field(default_factory=list)  # Allowed values list
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.param_type.__name__ if hasattr(self.param_type, '__name__') else str(self.param_type),
            "description": self.description,
            "required": self.required,
            "default": self.default,
            "choices": self.choices,
        }


@dataclass
class ToolResult:
    """Tool execution result"""
    success: bool = True
    data: Any = None
    error_message: Optional[str] = None
    execution_time: float = 0.0  # seconds
    metadata: dict = field(default_factory=dict)
    
    @classmethod
    def ok(cls, data: Any = None, **metadata) -> "ToolResult":
        """Create success result"""
        return cls(success=True, data=data, metadata=metadata)
    
    @classmethod
    def fail(cls, error_message: str, **metadata) -> "ToolResult":
        """Create failure result"""
        return cls(success=False, error_message=error_message, metadata=metadata)


@dataclass
class ToolDefinition:
    """Tool definition/description"""
    name: str
    description: str
    category: ToolCategory = ToolCategory.CUSTOM
    parameters: list[ToolParameter] = field(default_factory=list)
    returns: str = ""  # Return value description
    examples: list[dict] = field(default_factory=list)  # Usage examples
    tags: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": [p.to_dict() for p in self.parameters],
            "returns": self.returns,
            "examples": self.examples,
            "tags": self.tags,
        }
    
    def to_openai_function(self) -> dict:
        """Convert to OpenAI Function Calling format"""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": self._python_type_to_json(param.param_type),
                "description": param.description,
            }
            if param.choices:
                prop["enum"] = param.choices
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }
    
    @staticmethod
    def _python_type_to_json(py_type: type) -> str:
        """Convert Python type to JSON Schema type"""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        return type_map.get(py_type, "string")


class BaseTool(ABC):
    """
    Tool Base Class
    
    All tools must inherit this class and implement the execute method
    """
    
    def __init__(self):
        self._status = ToolStatus.AVAILABLE
        self._execution_count = 0
        self._last_executed: Optional[datetime] = None
    
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return tool definition"""
        pass
    
    @property
    def name(self) -> str:
        return self.definition.name
    
    @property
    def description(self) -> str:
        return self.definition.description
    
    @property
    def status(self) -> ToolStatus:
        return self._status
    
    def set_status(self, status: ToolStatus) -> None:
        self._status = status
    
    def validate_params(self, **kwargs) -> tuple[bool, str]:
        """
        Validate parameters
        
        Returns:
            (is_valid, error_message)
        """
        for param in self.definition.parameters:
            if param.required and param.name not in kwargs:
                return False, f"Missing required parameter: {param.name}"
            
            if param.name in kwargs:
                value = kwargs[param.name]
                # Type check
                if not isinstance(value, param.param_type):
                    # Try type conversion
                    try:
                        kwargs[param.name] = param.param_type(value)
                    except (ValueError, TypeError):
                        return False, f"Parameter '{param.name}' should be {param.param_type.__name__}"
                
                # Choices check
                if param.choices and value not in param.choices:
                    return False, f"Parameter '{param.name}' must be one of {param.choices}"
        
        return True, ""
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute tool
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Execution result
        """
        pass
    
    async def __call__(self, **kwargs) -> ToolResult:
        """Make tool callable"""
        # Validate parameters
        valid, error = self.validate_params(**kwargs)
        if not valid:
            return ToolResult.fail(error)
        
        # Check status
        if self._status == ToolStatus.DISABLED:
            return ToolResult.fail("Tool is disabled")
        if self._status == ToolStatus.ERROR:
            return ToolResult.fail("Tool is in error state")
        
        # Execute
        start_time = datetime.now()
        self._status = ToolStatus.BUSY
        
        try:
            result = await self.execute(**kwargs)
            result.execution_time = (datetime.now() - start_time).total_seconds()
            self._execution_count += 1
            self._last_executed = datetime.now()
            return result
        except Exception as e:
            return ToolResult.fail(str(e))
        finally:
            self._status = ToolStatus.AVAILABLE


class ToolRegistry:
    """
    Tool Registry
    
    Manages registration and lookup of all available tools
    """
    
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._category_index: dict[ToolCategory, list[str]] = {
            cat: [] for cat in ToolCategory
        }
        self._tag_index: dict[str, list[str]] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register tool"""
        name = tool.name
        if name in self._tools:
            raise ValueError(f"Tool '{name}' already registered")
        
        self._tools[name] = tool
        
        # Update category index
        category = tool.definition.category
        self._category_index[category].append(name)
        
        # Update tag index
        for tag in tool.definition.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(name)
    
    def unregister(self, name: str) -> bool:
        """Unregister tool"""
        if name not in self._tools:
            return False
        
        tool = self._tools[name]
        del self._tools[name]
        
        # Clean up indexes
        category = tool.definition.category
        if name in self._category_index[category]:
            self._category_index[category].remove(name)
        
        for tag in tool.definition.tags:
            if tag in self._tag_index and name in self._tag_index[tag]:
                self._tag_index[tag].remove(name)
        
        return True
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get tool"""
        return self._tools.get(name)
    
    def get_all(self) -> list[BaseTool]:
        """Get all tools"""
        return list(self._tools.values())
    
    def get_by_category(self, category: ToolCategory) -> list[BaseTool]:
        """Get tools by category"""
        names = self._category_index.get(category, [])
        return [self._tools[n] for n in names if n in self._tools]
    
    def get_by_tag(self, tag: str) -> list[BaseTool]:
        """Get tools by tag"""
        names = self._tag_index.get(tag, [])
        return [self._tools[n] for n in names if n in self._tools]
    
    def search(self, query: str) -> list[BaseTool]:
        """Search tools (name or description contains query)"""
        query = query.lower()
        results = []
        for tool in self._tools.values():
            if query in tool.name.lower() or query in tool.description.lower():
                results.append(tool)
        return results
    
    def list_definitions(self) -> list[ToolDefinition]:
        """List all tool definitions"""
        return [tool.definition for tool in self._tools.values()]
    
    def to_openai_functions(self) -> list[dict]:
        """Export as OpenAI Function Calling format"""
        return [tool.definition.to_openai_function() for tool in self._tools.values()]
    
    def __contains__(self, name: str) -> bool:
        return name in self._tools
    
    def __len__(self) -> int:
        return len(self._tools)


# ===== Tool Decorators =====

T = TypeVar('T')


def tool(
    name: str = None,
    description: str = None,
    category: ToolCategory = ToolCategory.CUSTOM,
    tags: list[str] = None,
):
    """
    Tool decorator - Convert function to tool
    
    Usage:
        @tool(name="read_file", description="Read file contents")
        async def read_file(path: str) -> str:
            '''Read file at specified path'''
            with open(path) as f:
                return f.read()
    """
    def decorator(func: Callable) -> Type[BaseTool]:
        func_name = name or func.__name__
        func_description = description or func.__doc__ or ""
        
        # Parse function signature to get parameters
        sig = inspect.signature(func)
        hints = get_type_hints(func) if hasattr(func, '__annotations__') else {}
        
        parameters = []
        for param_name, param in sig.parameters.items():
            if param_name in ['self', 'cls']:
                continue
            
            param_type = hints.get(param_name, str)
            has_default = param.default != inspect.Parameter.empty
            
            parameters.append(ToolParameter(
                name=param_name,
                param_type=param_type,
                required=not has_default,
                default=param.default if has_default else None,
            ))
        
        # Create tool class
        class FunctionTool(BaseTool):
            def __init__(self):
                super().__init__()
                self._func = func
            
            @property
            def definition(self) -> ToolDefinition:
                return ToolDefinition(
                    name=func_name,
                    description=func_description,
                    category=category,
                    parameters=parameters,
                    tags=tags or [],
                )
            
            async def execute(self, **kwargs) -> ToolResult:
                try:
                    if asyncio.iscoroutinefunction(self._func):
                        result = await self._func(**kwargs)
                    else:
                        result = self._func(**kwargs)
                    return ToolResult.ok(result)
                except Exception as e:
                    return ToolResult.fail(str(e))
        
        FunctionTool.__name__ = f"{func_name}Tool"
        return FunctionTool
    
    return decorator


# ===== Built-in Tool Examples =====

class EchoTool(BaseTool):
    """Example tool - Echo input"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="echo",
            description="Echo the input message",
            category=ToolCategory.CUSTOM,
            parameters=[
                ToolParameter(
                    name="message",
                    param_type=str,
                    description="Message to echo",
                    required=True,
                ),
            ],
            returns="The echoed message",
            examples=[
                {"input": {"message": "Hello"}, "output": "Hello"},
            ],
        )
    
    async def execute(self, message: str, **kwargs) -> ToolResult:
        return ToolResult.ok(message)


class SleepTool(BaseTool):
    """Example tool - Sleep for specified time"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="sleep",
            description="Sleep for specified seconds",
            category=ToolCategory.CUSTOM,
            parameters=[
                ToolParameter(
                    name="seconds",
                    param_type=float,
                    description="Seconds to sleep",
                    required=True,
                ),
            ],
        )
    
    async def execute(self, seconds: float, **kwargs) -> ToolResult:
        await asyncio.sleep(seconds)
        return ToolResult.ok(f"Slept for {seconds} seconds")


# Global tool registry
global_registry = ToolRegistry()
