"""
Base Agent for Multi-Agent Environment Generation

Key features:
- Extends utils.BaseAgent for core functionality
- Real-time communication via MessageBus
- Can ask/answer questions from other agents anytime
- Workspace isolation (read-only vs write access)
- Tools integration (browser, docker, file, etc.)
- Jinja2 prompt templates
"""

import asyncio
import json
import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

from utils.base_agent import BaseAgent as CoreBaseAgent
from utils.config import AgentConfig, LLMConfig
from utils.llm import LLM, Message
from utils.tool import ToolRegistry, BaseTool
from utils.communication import MessageBus, EventEmitter
from utils.message import (
    BaseMessage,
    MessageType,
    MessagePriority,
    create_task_message,
)

# Import tools
from ..tools import (
    get_all_tools,
    get_agent_tools,
    Workspace,
)

if TYPE_CHECKING:
    from ..workspace_manager import WorkspaceManager


# Prompt templates directory
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


@dataclass
class ChatMessage:
    """Message for inter-agent communication."""
    from_agent: str
    to_agent: str
    content: str
    msg_type: str  # "question", "answer", "update", "request", "feedback"
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "from": self.from_agent,
            "to": self.to_agent,
            "type": self.msg_type,
            "content": self.content,
            "context": self.context,
            "time": self.timestamp.isoformat(),
        }


class EnvGenAgent(CoreBaseAgent):
    """
    Base agent for environment generation.
    
    Capabilities:
    - LLM-based reasoning and code generation
    - Real-time communication with other agents
    - Workspace-aware file operations
    - Event-driven workflow
    - Tools for file, browser, docker operations
    - Jinja2 prompt templates
    """
    
    agent_id: str = "base"
    agent_name: str = "BaseAgent"
    
    # Tool categories this agent can use (override in subclass)
    allowed_tool_categories: List[str] = ["file", "reasoning"]
    
    def __init__(
        self,
        config: AgentConfig,
        llm: LLM,
        workspace_manager: "WorkspaceManager",
        tools: Optional[ToolRegistry] = None,
    ):
        super().__init__(config)
        
        self.llm = llm
        self.workspace = workspace_manager
        
        # Communication
        self._message_bus: Optional[MessageBus] = None
        self._events: Optional[EventEmitter] = None
        self._other_agents: Dict[str, "EnvGenAgent"] = {}
        
        # Message queue for async processing
        self._inbox: asyncio.Queue[ChatMessage] = asyncio.Queue()
        self._pending_questions: Dict[str, asyncio.Future] = {}
        
        # Context
        self._requirements: Dict[str, Any] = {}
        self._design_docs: Dict[str, str] = {}
        self.context = None  # GenerationContext with ports, etc.
        
        # Logger
        self._logger = logging.getLogger(f"Agent.{self.agent_id}")
        
        # Setup tools
        self._setup_tools(tools)
        
        # Setup prompt templates
        self._setup_prompts()
    
    # ==================== Setup ====================
    
    def _setup_tools(self, external_tools: Optional[ToolRegistry]):
        """Setup tools for this agent."""
        if external_tools:
            self.tools = external_tools
        else:
            # Create workspace for tools
            workspace = Workspace(self.workspace.base_dir)
            
            # Get tools appropriate for this agent type
            self.tools = ToolRegistry()
            agent_tools = get_agent_tools(
                agent_type=self.agent_id,
                workspace=workspace,
                include_browser=(self.agent_id == "user"),  # Only UserAgent gets browser
                include_docker=(self.agent_id == "user"),   # Only UserAgent gets docker
            )
            
            for tool in agent_tools:
                self.tools.register(tool)
    
    def get_available_tools(self) -> List[str]:
        """Get list of tool names this agent can use."""
        return [tool.name for tool in self.tools.get_all_tools()]
    
    def _setup_prompts(self):
        """Setup Jinja2 prompt templates."""
        if PROMPTS_DIR.exists():
            self._jinja_env = Environment(
                loader=FileSystemLoader(str(PROMPTS_DIR)),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            self._jinja_env = None
            self._logger.warning(f"Prompts directory not found: {PROMPTS_DIR}")
    
    def render_prompt(self, template_name: str, **kwargs) -> str:
        """Render a Jinja2 prompt template."""
        if not self._jinja_env:
            raise RuntimeError("Prompt templates not initialized")
        
        template = self._jinja_env.get_template(template_name)
        return template.render(**kwargs)
    
    def render_macro(self, template_name: str, macro_name: str, **kwargs) -> str:
        """Render a specific macro from a Jinja2 template."""
        if not self._jinja_env:
            raise RuntimeError("Prompt templates not initialized")
        
        template = self._jinja_env.get_template(template_name)
        macro = getattr(template.module, macro_name)
        return macro(**kwargs)
    
    def set_message_bus(self, bus: MessageBus):
        """Set message bus for inter-agent communication."""
        self._message_bus = bus
    
    def set_events(self, events: EventEmitter):
        """Set event emitter."""
        self._events = events
    
    def set_other_agents(self, agents: Dict[str, "EnvGenAgent"]):
        """Set references to other agents for direct communication."""
        self._other_agents = agents
        
        # Register communication tools now that we know other agents
        self._register_communication_tools()
    
    def _register_communication_tools(self):
        """Register communication tools after other agents are known."""
        from ..communication_tools import create_communication_tools
        
        comm_tools = create_communication_tools(self)
        for tool in comm_tools:
            self.tools.register(tool)
        
        self._logger.debug(f"Registered {len(comm_tools)} communication tools")
    
    def get_available_agents(self) -> List[Dict[str, str]]:
        """
        Get list of agents this agent can communicate with.
        
        Returns:
            List of dicts with agent info:
            [
                {"id": "design", "name": "DesignAgent", "role": "Project design and architecture"},
                {"id": "backend", "name": "BackendAgent", "role": "API code generation"},
                ...
            ]
        """
        agent_roles = {
            "user": "Requirements refinement, testing, and QA",
            "design": "Project design, architecture, and specifications",
            "database": "Database schema and SQL generation",
            "backend": "Backend API and server code generation",
            "frontend": "Frontend UI and React code generation",
        }
        
        return [
            {
                "id": agent_id,
                "name": agent.agent_name,
                "role": agent_roles.get(agent_id, "Unknown"),
            }
            for agent_id, agent in self._other_agents.items()
        ]
    
    def can_talk_to(self, agent_id: str) -> bool:
        """Check if this agent can communicate with another agent."""
        return agent_id in self._other_agents
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, str]]:
        """Get info about a specific agent."""
        if agent_id not in self._other_agents:
            return None
        
        agent = self._other_agents[agent_id]
        agent_roles = {
            "user": "Requirements refinement, testing, and QA",
            "design": "Project design, architecture, and specifications",
            "database": "Database schema and SQL generation",
            "backend": "Backend API and server code generation",
            "frontend": "Frontend UI and React code generation",
        }
        
        return {
            "id": agent_id,
            "name": agent.agent_name,
            "role": agent_roles.get(agent_id, "Unknown"),
            "tools": agent.get_available_tools()[:10],  # First 10 tools
        }
    
    def get_communication_prompt(self) -> str:
        """
        Generate a prompt section describing available communication tools.
        """
        if not self._other_agents:
            return "You are working alone with no other agents available."
        
        lines = [
            "## Multi-Agent Communication",
            "",
            "You are part of a multi-agent system. Use these TOOLS to communicate:",
            "",
            "### Communication Tools",
            "",
            "| Tool | Usage | Example |",
            "|------|-------|---------|",
            '| `ask_agent` | Ask another agent a question | `ask_agent(agent_id="design", question="What is the API spec?")` |',
            '| `tell_agent` | Send notification to an agent | `tell_agent(agent_id="frontend", message="API ready")` |',
            '| `broadcast` | Notify all agents | `broadcast(message="Schema updated")` |',
            '| `get_agents` | List available agents | `get_agents()` |',
            "",
            "### Available Agents",
            "",
            "| Agent ID | Role |",
            "|----------|------|",
        ]
        
        for info in self.get_available_agents():
            lines.append(f"| `{info['id']}` | {info['role']} |")
        
        lines.extend([
            "",
            "### When to Use Communication Tools",
            "",
            "**Use `ask_agent` when you need:**",
            "- Information from another agent's domain",
            "- Clarification about specifications",
            "- Data format or API contract details",
            "",
            "**Use `tell_agent` when you have:**",
            "- Completed something others should know",
            "- Important information to share",
            "- Warnings or updates",
            "",
            "**Use `broadcast` for:**",
            "- Major milestone completions",
            "- System-wide announcements",
            "",
            "**IMPORTANT: Actually call these tools! Don't just think about communicating.**",
        ])
        
        return "\n".join(lines)
    
    async def receive_requirements(self, requirements: Dict[str, Any]):
        """Receive refined requirements from UserAgent."""
        self._requirements = requirements
        self._logger.debug(f"Received requirements: {list(requirements.keys())}")
    
    async def receive_design(self, design_docs: Dict[str, str]):
        """Receive design documents from DesignAgent."""
        self._design_docs = design_docs
        self._logger.debug(f"Received design docs: {list(design_docs.keys())}")
    
    # ==================== Communication ====================
    
    async def ask(
        self,
        target_agent: str,
        question: str,
        context: Dict = None,
        timeout: float = 60.0,
    ) -> str:
        """
        Ask another agent a question and wait for response.
        
        Example:
            answer = await self.ask("backend", "What endpoint returns user data?")
        """
        if target_agent not in self._other_agents:
            return f"Error: Agent '{target_agent}' not found"
        
        msg = ChatMessage(
            from_agent=self.agent_id,
            to_agent=target_agent,
            content=question,
            msg_type="question",
            context=context or {},
        )
        
        self._logger.info(f"[{self.agent_id}] -> [{target_agent}]: {question[:50]}...")
        
        # Create future for response
        msg_id = f"{self.agent_id}_{target_agent}_{datetime.now().timestamp()}"
        future = asyncio.get_event_loop().create_future()
        self._pending_questions[msg_id] = future
        
        # Send question
        target = self._other_agents[target_agent]
        await target.receive_message(msg, response_id=msg_id)
        
        # Emit event for tracking
        if self._events:
            await self._events.emit("agent_question", self.agent_id, target_agent, question)
        
        try:
            answer = await asyncio.wait_for(future, timeout=timeout)
            return answer
        except asyncio.TimeoutError:
            del self._pending_questions[msg_id]
            return f"Timeout waiting for response from {target_agent}"
    
    async def tell(
        self,
        target_agent: str,
        message: str,
        msg_type: str = "update",
        context: Dict = None,
    ):
        """
        Send a one-way message to another agent.
        
        Example:
            await self.tell("frontend", "Backend API ready at /api/users", msg_type="update")
        """
        if target_agent not in self._other_agents:
            self._logger.warning(f"Agent '{target_agent}' not found")
            return
        
        msg = ChatMessage(
            from_agent=self.agent_id,
            to_agent=target_agent,
            content=message,
            msg_type=msg_type,
            context=context or {},
        )
        
        self._logger.info(f"[{self.agent_id}] -> [{target_agent}] ({msg_type}): {message[:50]}...")
        
        target = self._other_agents[target_agent]
        await target.receive_message(msg)
    
    async def broadcast(
        self,
        message: str,
        msg_type: str = "update",
        context: Dict = None,
        exclude: List[str] = None,
    ):
        """
        Broadcast message to all other agents.
        
        Example:
            await self.broadcast("Design phase complete", msg_type="update")
        """
        exclude = exclude or []
        
        for agent_id, agent in self._other_agents.items():
            if agent_id not in exclude:
                await self.tell(agent_id, message, msg_type, context)
    
    async def receive_message(
        self,
        message: ChatMessage,
        response_id: str = None,
    ):
        """Receive a message from another agent."""
        self._logger.debug(f"Received from [{message.from_agent}]: {message.content[:50]}...")
        
        if message.msg_type == "question":
            # Answer the question
            answer = await self._answer_question(message)
            
            # Send response back
            if response_id:
                source = self._other_agents.get(message.from_agent)
                if source and response_id in source._pending_questions:
                    source._pending_questions[response_id].set_result(answer)
                    del source._pending_questions[response_id]
        else:
            # Just process the message
            await self._process_message(message)
    
    async def _answer_question(self, message: ChatMessage) -> str:
        """
        Answer a question from another agent.
        
        Override this in subclasses for specialized behavior.
        """
        # Default: use LLM to answer based on agent's context
        prompt = f"""You are the {self.agent_name} agent.
Another agent ({message.from_agent}) asks:

{message.content}

Context: {json.dumps(message.context, indent=2) if message.context else "None"}

Provide a helpful, concise answer based on your expertise and current work.
"""
        
        response = await self.llm.generate([Message(role="user", content=prompt)])
        return response.content
    
    async def _process_message(self, message: ChatMessage):
        """
        Process a non-question message.
        
        Override in subclasses for specialized handling.
        """
        # Default: just log it
        self._logger.info(f"[{message.msg_type}] from {message.from_agent}: {message.content[:100]}...")
        
        # Store updates in context
        if message.msg_type == "update" and message.context:
            for key, value in message.context.items():
                self._design_docs[f"{message.from_agent}_{key}"] = value
    
    # ==================== File Operations ====================
    
    def read_file(self, path: str) -> Optional[str]:
        """Read a file (respects workspace permissions)."""
        return self.workspace.read_file(path, self.agent_id)
    
    def write_file(self, path: str, content: str) -> bool:
        """Write a file (only to own workspace)."""
        return self.workspace.write_file(path, content, self.agent_id)
    
    def list_files(self, directory: str = "") -> List[str]:
        """List files in a directory."""
        return self.workspace.list_files(directory, self.agent_id)
    
    # ==================== Tool Execution ====================
    
    async def call_tool(self, tool_name: str, **kwargs) -> Any:
        """Call a tool by name."""
        tool = self.tools.get(tool_name)
        if not tool:
            self._logger.error(f"Tool not found: {tool_name}")
            return None
        
        try:
            result = await tool.execute(**kwargs)
            return result
        except Exception as e:
            self._logger.error(f"Tool {tool_name} failed: {e}")
            return None
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self.tools.list_tools())
    
    # ==================== LLM Interaction ====================
    
    def _build_system_prompt(self, custom_system: str = None) -> str:
        """Build system prompt with agent identity and communication info."""
        parts = [
            f"You are {self.agent_name}, a specialized agent in a multi-agent system.",
            f"Your role: {self._get_role_description()}",
            "",
        ]
        
        # Add communication capabilities
        if self._other_agents:
            parts.append(self.get_communication_prompt())
            parts.append("")
        
        # Add custom system prompt if provided
        if custom_system:
            parts.append(custom_system)
        
        return "\n".join(parts)
    
    def _get_role_description(self) -> str:
        """Get role description for this agent type."""
        roles = {
            "user": "Requirements refinement, application testing, and quality assurance",
            "design": "Project architecture, specifications, and design documents",
            "database": "Database schema, SQL generation, and data management",
            "backend": "Backend API development with Express.js",
            "frontend": "Frontend UI development with React",
        }
        return roles.get(self.agent_id, "Code generation and problem solving")
    
    async def think(self, prompt: str, system: str = None, include_comm_info: bool = True) -> str:
        """
        Have the agent think about something using LLM.
        
        Args:
            prompt: The prompt/question
            system: Optional custom system prompt
            include_comm_info: Whether to include communication capabilities in system prompt
        """
        messages = []
        
        # Build system prompt with agent identity and communication info
        if include_comm_info:
            full_system = self._build_system_prompt(system)
            messages.append(Message(role="system", content=full_system))
        elif system:
            messages.append(Message(role="system", content=system))
        
        messages.append(Message(role="user", content=prompt))
        
        response = await self.llm.generate(messages)
        return response.content
    
    async def generate_code(
        self,
        description: str,
        file_type: str,
        context: Dict = None,
    ) -> str:
        """Generate code using LLM."""
        ctx = context or {}
        
        prompt = f"""Generate {file_type} code for:

{description}

Requirements:
{json.dumps(self._requirements, indent=2) if self._requirements else "No specific requirements"}

Design Context:
{json.dumps(ctx, indent=2) if ctx else "No additional context"}

Generate clean, production-ready code. Only output the code, no explanations.
"""
        
        return await self.think(prompt)
    
    # ==================== Abstract Methods ====================
    
    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task.
        
        Args:
            task: Task specification with "type" and other params
            
        Returns:
            Result with "success" and other fields
        """
        pass
    
    # ==================== Helper Methods ====================
    
    async def request_help(self, problem: str):
        """Request help when stuck - emits event for orchestrator to handle."""
        self._logger.warning(f"Requesting help: {problem}")
        
        if self._events:
            await self._events.emit("agent_stuck", self.agent_id, problem)
        
        # LLM can use ask_agent tool to request help from other agents
        # This method just emits event for orchestrator tracking
        return {
            "status": "help_requested",
            "problem": problem,
            "suggestion": "Use ask_agent tool to request guidance from another agent",
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "has_requirements": bool(self._requirements),
            "has_design": bool(self._design_docs),
            "pending_questions": len(self._pending_questions),
            "available_tools": self.get_available_tools(),
        }
