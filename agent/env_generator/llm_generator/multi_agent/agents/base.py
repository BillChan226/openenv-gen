"""
EnvGenAgent - Base Agent for Multi-Agent Environment Generation

Inherits from utils.base_agent.BaseAgent and adds:
- Jinja2 prompt templates
- LLM agentic loop (chat + tool calling)
- Environment generation specific tools
- Priority message queue with urgent message handling
- Question preemption during task processing

Subclasses only need to define:
- agent_id, agent_name
- allowed_tool_categories  
- _get_system_prompt() - use j2 templates
- _build_task_prompt() - use j2 templates
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Import base classes from utils
from utils.base_agent import BaseAgent, AgentRole, AgentCapability, AgentMetrics
from utils.config import AgentConfig
from utils.state import AgentState
from utils.message import (
    BaseMessage,
    TaskMessage,
    ResultMessage,
    MessageType,
    MessagePriority,
    MessageHeader,
    MessageTracker,
    create_result_message,
)
from utils.tool import ToolRegistry, BaseTool, ToolResult
from utils.communication import MessageBus

# LLM
from utils.llm import LLM, Message


# ==================== PRIORITY QUEUE ====================

from .priority_queue import PriorityMessageQueue

# Memory
import sys
_memory_dir = Path(__file__).parent.parent.parent
if str(_memory_dir) not in sys.path:
    sys.path.insert(0, str(_memory_dir))
from memory import GeneratorMemory, MemoryBank

# Tools
from ..tools import get_agent_tools, Workspace

if TYPE_CHECKING:
    from ..workspace_manager import WorkspaceManager


# Prompt templates directory
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class ProcessingState(Enum):
    """Agent processing state - simplified."""
    IDLE = "idle"                    # Ready for tasks
    PROCESSING_TASK = "processing"   # Executing a task
    ANSWERING_QUESTION = "answering" # Handling urgent message (preempted)


def safe_json_dumps(obj: Any, indent: int = 2) -> str:
    """Safely serialize object to JSON."""
    def default_handler(o):
        if hasattr(o, 'to_dict'):
            return o.to_dict()
        if hasattr(o, '__dict__'):
            return {k: v for k, v in o.__dict__.items() if not k.startswith('_')}
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, Enum):
            return o.value
        return str(o)
    
    try:
        return json.dumps(obj, indent=indent, default=default_handler)
    except:
        return str(obj)


class EnvGenAgent(BaseAgent):
    """
    Environment Generation Agent Base Class.
    
    Extends BaseAgent with:
    - Jinja2 prompt templates
    - LLM agentic loop (tool calling)
    - Environment generation tools
    
    Subclasses override:
    - _get_system_prompt()
    - _build_task_prompt(task)
    """
    
    # Override in subclass
    agent_id: str = "base"
    agent_name: str = "BaseAgent"
    allowed_tool_categories: List[str] = ["file", "reasoning"]
    
    def __init__(
        self,
        config: AgentConfig,
        llm: LLM,
        workspace_manager: "WorkspaceManager",
        include_vision: bool = False,
    ):
        # Initialize parent with debug logging (stuck detection disabled - write_file repetition is normal)
        super().__init__(
            config=config,
            role=AgentRole.WORKER,
            enable_stuck_detection=False,
            enable_debug_logging=True,
        )
        
        # Override agent_id from class attribute
        self._agent_id = self.agent_id
        self._name = self.agent_name
        
        # LLM
        self.llm = llm
        self._include_vision = include_vision
        
        # Workspace
        self.workspace = workspace_manager
        
        # External MessageBus reference (for inter-agent communication)
        self._external_bus: Optional[MessageBus] = None
        
        # Context
        self._requirements: Dict[str, Any] = {}
        self._design_docs: Dict[str, str] = {}
        self.gen_context = None
        
        # Memory (generator-specific)
        self.memory = GeneratorMemory(llm=llm, short_term_size=50, condenser_max_size=30)
        self.memory_bank: Optional[MemoryBank] = None
        
        # Tool instances for LLM tool calling
        self._tool_instances: Dict[str, BaseTool] = {}
        self._register_env_gen_tools()
        
        # Jinja2 environment
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(PROMPTS_DIR)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # Task completion event for external coordination
        self._task_complete_event = asyncio.Event()
        
        # Project delivery event (only UserAgent uses this)
        self._project_delivered_event = asyncio.Event()
        self._project_delivered = False
        
        # Ready event - set when agent is initialized and running
        self._ready_event = asyncio.Event()
        
        # Shutdown flag
        self._shutdown_requested = False
        
        # Priority message queue (replaces BaseAgent's simple queue for urgent handling)
        self._priority_queue = PriorityMessageQueue(maxsize=100)
        
        # Processing state tracking
        self._processing_state = ProcessingState.IDLE
        
        # Pending question responses (question_id -> Future)
        self._pending_questions: Dict[str, asyncio.Future] = {}
        
        # Urgent messages to inject into current conversation (true interrupt)
        self._interrupt_messages: List[Dict] = []
        
        # Message tracker for sent message status
        self._message_tracker = MessageTracker()
    
    # ==================== LIFECYCLE ====================
    
    async def run_loop(self):
        """
        Convenience method to initialize, start, and run until shutdown.
        
        This is what Orchestrator calls. It wraps the BaseAgent lifecycle.
        """
        # Initialize
        if not await self.initialize():
            self._logger.error(f"[{self.agent_id}] Failed to initialize")
            self._ready_event.set()  # Set even on failure so waiters don't hang
            return
        
        # Start (this starts _main_loop internally)
        if not await self.start():
            self._logger.error(f"[{self.agent_id}] Failed to start")
            self._ready_event.set()  # Set even on failure
            return
        
        # Signal ready - agent is now running and can accept tasks
        self._ready_event.set()
        self._logger.info(f"[{self.agent_id}] Ready to accept tasks")
        
        # Wait until shutdown is requested, checking for issues periodically
        while not self._shutdown_requested and self._running:
            # Check for urgent messages (including issues from other agents)
            try:
                while await self._check_and_handle_urgent():
                    pass  # Handle all pending urgent messages
            except Exception as e:
                self._logger.error(f"[{self.agent_id}] Error handling urgent message: {e}")
            
            await asyncio.sleep(0.5)
        
        # Stop
        await self.stop()
        await self.cleanup()
        
        self._logger.info(f"[{self.agent_id}] run_loop completed")
    
    async def wait_ready(self, timeout: float = 30.0) -> bool:
        """
        Wait until agent is ready to accept tasks.
        
        Returns:
            True if ready, False if timeout or failed to start.
        """
        try:
            await asyncio.wait_for(self._ready_event.wait(), timeout=timeout)
            return self._running  # Check if actually running (not failed)
        except asyncio.TimeoutError:
            self._logger.warning(f"[{self.agent_id}] Timeout waiting for ready")
            return False
    
    def request_shutdown(self):
        """Request the agent to shutdown gracefully."""
        self._shutdown_requested = True
    
    async def on_initialize(self) -> None:
        """Called during initialize() - setup env gen specific resources."""
        self._logger.info(f"[{self.agent_id}] Initializing environment generation agent")
    
    async def on_start(self) -> None:
        """Called during start() - agent is now running."""
        self._logger.info(f"[{self.agent_id}] Started, ready to process tasks")
    
    async def on_stop(self) -> None:
        """Called during stop()."""
        self._logger.info(f"[{self.agent_id}] Stopping")
    
    # ==================== MESSAGE HANDLING WITH PRIORITY ====================
    
    async def receive_message(self, message: BaseMessage) -> None:
        """
        Override BaseAgent.receive_message to use priority queue.
        
        Message priority (agent-controlled):
        - URGENT (4): Immediate attention required
        - HIGH (3): Process as soon as possible
        - NORMAL (2): Standard processing order
        - LOW (1): Process when idle
        
        Priority is set by the SENDER. Only system-critical messages are auto-elevated.
        Same priority messages are processed in FIFO order.
        """
        msg_type = message.metadata.get("msg_type", "").lower()
        
        # Only auto-elevate for system-critical messages
        # Otherwise respect the sender's priority choice
        if msg_type == "shutdown":
            message.header.priority = MessagePriority.URGENT  # System critical
        # All other priorities are set by the sender via send_message(priority=...)
        
        self._logger.debug(f"[{self.agent_id}] Received {msg_type} (priority={message.header.priority.name})")
        
        # Handle ACK/status messages - update our message tracker
        if msg_type in ("ack", "status"):
            original_msg_id = message.metadata.get("original_message_id")
            if original_msg_id and self._message_tracker:
                ack_type = message.metadata.get("ack_type", "")
                if ack_type == "delivered":
                    self._message_tracker.mark_delivered(original_msg_id)
                elif ack_type == "read":
                    self._message_tracker.mark_read(original_msg_id)
                elif message.metadata.get("processing_status") == "in_progress":
                    self._message_tracker.mark_read(original_msg_id)  # Read implies processing
                # Don't add ACK/status to regular inbox - they're metadata only
                if msg_type == "ack":
                    return  # Skip adding ACK to inbox
        
        # Add to inbox for check_inbox() tool
        inbox_msg = {
            "id": message.header.message_id,
            "from": message.header.source_agent_id,
            "type": msg_type or message.message_type.value,
            "content": message.payload if isinstance(message.payload, str) else str(message.payload),
            "tags": message.metadata.get("tags", []),
            "priority": message.header.priority.name.lower(),
            "persist": message.metadata.get("persist", False),
            "read": False,
            "timestamp": datetime.now().isoformat(),
        }
        
        inbox = getattr(self, "_subscription_inbox", None)
        if inbox is None:
            self._subscription_inbox = []
            inbox = self._subscription_inbox
        inbox.append(inbox_msg)
        
        # Auto-send delivery ACK for important message types
        if msg_type in ("issue", "task_ready", "question"):
            await self._send_delivery_ack(message)
        
        # Queue high priority messages for injection into current conversation
        # This enables true interrupt - urgent messages become part of the active conversation
        if message.header.priority in (MessagePriority.URGENT, MessagePriority.HIGH):
            if msg_type in ("issue", "task_ready", "question"):
                self._interrupt_messages.append(inbox_msg)
                self._logger.info(f"[{self.agent_id}] Queued interrupt: {msg_type} from {inbox_msg['from']}")
        
        # Put in priority queue
        await self._priority_queue.put(message)
        
        # Also put in BaseAgent's queue for compatibility with _main_loop
        # (but we'll override processing in process_task)
        await self._message_queue.put(message)
    
    def get_inbox_messages(self, limit: int = 10, clear: bool = True) -> List[Dict]:
        """
        Get messages from inbox.
        
        Args:
            limit: Max messages to return
            clear: Clear non-persistent messages after reading
            
        Returns:
            List of inbox messages
        """
        inbox = getattr(self, "_subscription_inbox", [])
        
        # Get messages (up to limit)
        messages = inbox[:limit]
        
        if clear:
            # Keep persistent messages, remove others
            persistent = [m for m in inbox if m.get("persist", False)]
            self._subscription_inbox = persistent
        
        return messages
    
    async def _send_delivery_ack(self, message: BaseMessage) -> None:
        """
        Send automatic delivery acknowledgement back to sender.
        This lets sender know their important message was delivered.
        """
        sender = message.header.source_agent_id
        if not sender or sender == self.agent_id:
            return
        
        bus = self._external_bus
        if not bus:
            return
        
        msg_type = message.metadata.get("msg_type", "")
        msg_id = message.header.message_id
        
        # Create ACK message
        ack_header = MessageHeader(
            source_agent_id=self.agent_id,
            target_agent_id=sender,
            priority=MessagePriority.LOW,  # ACKs are low priority
            reply_to=msg_id,  # Link to original message
        )
        ack_message = BaseMessage(
            header=ack_header,
            message_type=MessageType.STATUS,
            payload=f"DELIVERED: {msg_type} message received by {self.agent_id}",
            metadata={
                "msg_type": "ack",
                "original_message_id": msg_id,
                "ack_type": "delivered",
            }
        )
        
        try:
            await bus.publish(ack_message)
            self._logger.debug(f"[{self.agent_id}] Sent delivery ACK for {msg_id[:8]}... to {sender}")
        except Exception as e:
            self._logger.warning(f"[{self.agent_id}] Failed to send delivery ACK: {e}")
    
    async def _check_and_handle_urgent(self) -> bool:
        """
        Check for urgent messages and handle them.
        Called during task processing to enable preemption.
        
        Returns:
            True if an urgent message was handled
        """
        urgent_msg = await self._priority_queue.get_if_urgent()
        if not urgent_msg:
            return False
        
        msg_type = urgent_msg.metadata.get("msg_type", "").lower()
        self._logger.info(f"[{self.agent_id}] Handling urgent {msg_type}")
        
        if msg_type == "shutdown":
            self._shutdown_requested = True
            return True
        
        if msg_type == "question":
            # Pause current processing, answer question
            prev_state = self._processing_state
            self._processing_state = ProcessingState.ANSWERING_QUESTION
            
            await self._handle_question(urgent_msg)
            
            self._processing_state = prev_state
            return True
        
        if msg_type == "answer":
            # Handle answer to a question we asked
            await self._handle_answer(urgent_msg)
            return True
        
        if msg_type == "issue":
            # Handle issue reported by another agent (usually UserAgent)
            await self._handle_issue(urgent_msg)
            return True
        
        if msg_type == "task_ready":
            # Upstream agent finished - start our work!
            # Only process if we're IDLE (not already working on something)
            if self._processing_state == ProcessingState.IDLE:
                await self._handle_task_ready(urgent_msg)
                return True
            else:
                # If we're busy, the message stays in inbox for check_inbox()
                self._logger.info(f"[{self.agent_id}] task_ready received but busy, queued for later")
        
        return False
    
    async def _handle_question(self, message: BaseMessage) -> None:
        """Handle a question from another agent."""
        from_agent = message.header.source_agent_id
        question = message.payload if isinstance(message.payload, str) else str(message.payload)
        context = message.metadata.get("context", {})
        question_id = context.get("question_id", message.header.message_id)
        
        self._logger.info(f"[{self.agent_id}] Answering question from {from_agent}")
        
        # Generate answer using LLM
        answer = await self._generate_answer(question, from_agent)
        
        # Send answer back
        await self._send_answer(from_agent, answer, question_id)
    
    async def _generate_answer(self, question: str, from_agent: str) -> str:
        """Generate an answer to a question using LLM."""
        system_prompt = self._get_system_prompt()
        prompt = f"""Another agent ({from_agent}) is asking you a question while you're working.

Question: {question}

Based on your expertise and current work, provide a helpful and concise answer.
Answer directly without using tools."""
        
        messages = [Message.system(system_prompt), Message.user(prompt)]
        
        try:
            response = await self.call_with_retry(self.llm.chat_messages, messages)
            # Handle both LLMResponse object and string response
            if isinstance(response, str):
                return response or "I don't have enough context to answer."
            return response.content or "I don't have enough context to answer."
        except Exception as e:
            self._logger.error(f"Failed to generate answer: {e}")
            return f"Sorry, I couldn't process your question: {e}"
    
    async def _send_answer(self, to_agent: str, answer: str, question_id: str):
        """Send answer back to the asking agent."""
        if self._external_bus:
            from uuid import uuid4
            header = MessageHeader(
                message_id=str(uuid4()),
                source_agent_id=self._agent_id,
                target_agent_id=to_agent,
                priority=MessagePriority.HIGH,
            )
            message = BaseMessage(
                header=header,
                message_type=MessageType.RESULT,
                payload=answer,
                metadata={"msg_type": "answer", "context": {"question_id": question_id}},
            )
            await self._external_bus.send(message)
    
    async def _handle_answer(self, message: BaseMessage) -> None:
        """Handle an answer to a question we asked."""
        context = message.metadata.get("context", {})
        question_id = context.get("question_id")
        answer = message.payload if isinstance(message.payload, str) else str(message.payload)
        
        if question_id and question_id in self._pending_questions:
            self._pending_questions[question_id].set_result(answer)
            self._logger.info(f"[{self.agent_id}] Received answer for question {question_id[:8]}")
    
    async def _handle_issue(self, message: BaseMessage) -> None:
        """
        Handle an issue reported by another agent (typically UserAgent during testing).
        
        This triggers the agent to fix the issue by running an agentic loop focused on the fix.
        """
        from_agent = message.header.source_agent_id
        issue_content = message.payload if isinstance(message.payload, str) else str(message.payload)
        context = message.metadata.get("context", {})
        severity = context.get("severity", "error")
        
        self._logger.info(f"[{self.agent_id}] Received issue from {from_agent}: {issue_content[:100]}...")
        
        # Build a fix prompt
        fix_prompt = f"""## Issue Reported by {from_agent}

**Severity**: {severity}
**Issue**: {issue_content}

## Your Task

Fix this issue in your code. Steps:
1. Use `think()` to analyze the issue and identify the root cause
2. Use `view()` to examine the relevant files
3. Use `str_replace_editor()` or `write_file()` to fix the code
4. Use `lint()` to verify no new errors were introduced
5. When fixed, use `send_message(to_agent="{from_agent}", content="Fixed: <brief description>", msg_type="info")` to report back

Start by thinking about what might cause this issue.
"""
        
        # Run a mini agentic loop to fix the issue
        prev_state = self._processing_state
        self._processing_state = ProcessingState.PROCESSING_TASK
        
        try:
            system_prompt = self._get_system_prompt()
            await self.run_agentic_loop(
                system_prompt=system_prompt,
                initial_prompt=fix_prompt,
                max_steps=30,  # Limit fix attempts
            )
        except Exception as e:
            self._logger.error(f"[{self.agent_id}] Failed to fix issue: {e}")
            # Notify the sender about failure
            if self._external_bus:
                from uuid import uuid4
                header = MessageHeader(
                    message_id=str(uuid4()),
                    source_agent_id=self.agent_id,
                    target_agent_id=from_agent,
                    priority=MessagePriority.NORMAL,
                )
                error_msg = BaseMessage(
                    header=header,
                    message_type=MessageType.STATUS,
                    payload=f"Failed to fix issue: {str(e)[:200]}",
                    metadata={"msg_type": "error"},
                )
                await self._external_bus.send(error_msg)
        finally:
            self._processing_state = prev_state
    
    async def _handle_task_ready(self, message: BaseMessage) -> None:
        """
        Handle task_ready message from upstream agent.
        
        When an upstream agent finishes and notifies us, start our work automatically.
        """
        from_agent = message.header.source_agent_id
        content = message.payload if isinstance(message.payload, str) else str(message.payload)
        tags = message.metadata.get("tags", [])
        
        self._logger.info(f"[{self.agent_id}] Starting work - triggered by {from_agent}: {content[:100]}...")
        
        # Build a task prompt
        task_prompt = f"""## Task Notification from {from_agent}

{content}

## Your Task

Upstream agent has completed their work. Now it's your turn!

1. First, use `view()` to read the relevant design specs in `design/`
2. Create a `plan()` for your implementation
3. Implement all required files
4. When complete, use `finish(notify=[...])` to notify downstream agents

Start working now.
"""
        
        self._processing_state = ProcessingState.PROCESSING_TASK
        
        try:
            system_prompt = self._get_system_prompt()
            await self.run_agentic_loop(
                system_prompt=system_prompt,
                initial_prompt=task_prompt,
                max_steps=2000,
            )
        except Exception as e:
            self._logger.error(f"[{self.agent_id}] Task failed: {e}")
        finally:
            self._processing_state = ProcessingState.IDLE
    
    async def _process_pending_notifications(self) -> None:
        """Process any pending notifications stored by tools (e.g., finish(notify=[...]), report_issue())."""
        pending = getattr(self, "_pending_notifications", None)
        if pending:
            for bus, msg in pending:
                try:
                    await bus.send(msg)
                    target = msg.header.target_agent_id
                    msg_type = msg.metadata.get("msg_type", "notification")
                    self._logger.info(f"[{self.agent_id}] Sent {msg_type} to {target}")
                except Exception as e:
                    self._logger.error(f"[{self.agent_id}] Failed to send notification: {e}")
            
            # Clear pending after processing
            self._pending_notifications = []
        
        # Also process knowledge shares from memory tools
        await self._process_knowledge_shares()
    
    async def _process_knowledge_shares(self) -> None:
        """Process outgoing knowledge shares queued by memory tools."""
        # Check for knowledge shares from memory
        if hasattr(self, 'memory'):
            outgoing = self.memory.get_outgoing_knowledge()
            if not outgoing:
                return
            
            bus = getattr(self, '_external_bus', None) or getattr(self, '_message_bus', None)
            if not bus:
                return
            
            from uuid import uuid4
            
            for share in outgoing:
                knowledge = share.get("knowledge", {})
                targets = share.get("targets", [])
                
                for target in targets:
                    try:
                        header = MessageHeader(
                            message_id=str(uuid4()),
                            source_agent_id=self.agent_id,
                            target_agent_id=target,
                            priority=MessagePriority.NORMAL,
                        )
                        msg = BaseMessage(
                            header=header,
                            message_type=MessageType.INFO,
                            payload=f"[Knowledge Share] {knowledge.get('content', '')}",
                            metadata={
                                "msg_type": "knowledge",
                                "category": knowledge.get("category", "general"),
                                "tags": [knowledge.get("category", "general"), "knowledge_share"],
                                "persist": True,  # Knowledge should persist
                                "read": False,
                            }
                        )
                        await bus.send(msg)
                        self._logger.debug(f"[{self.agent_id}] Shared knowledge to {target}")
                    except Exception as e:
                        self._logger.error(f"[{self.agent_id}] Knowledge share to {target} failed: {e}")
        
        # Also check for knowledge shares from share_knowledge tool
        pending_shares = getattr(self, '_pending_knowledge_shares', None)
        if pending_shares:
            bus = getattr(self, '_external_bus', None) or getattr(self, '_message_bus', None)
            if bus:
                from uuid import uuid4
                
                for share in pending_shares:
                    target = share.get("target")
                    content = share.get("content", "")
                    category = share.get("category", "general")
                    importance = share.get("importance", "normal")
                    
                    try:
                        priority = {
                            "low": MessagePriority.LOW,
                            "normal": MessagePriority.NORMAL,
                            "high": MessagePriority.HIGH,
                        }.get(importance, MessagePriority.NORMAL)
                        
                        header = MessageHeader(
                            message_id=str(uuid4()),
                            source_agent_id=self.agent_id,
                            target_agent_id=target,
                            priority=priority,
                        )
                        msg = BaseMessage(
                            header=header,
                            message_type=MessageType.INFO,
                            payload=f"[{category.upper()}] {content}",
                            metadata={
                                "msg_type": "knowledge",
                                "category": category,
                                "tags": [category, "knowledge_share"],
                                "persist": True,
                                "read": False,
                            }
                        )
                        await bus.send(msg)
                        self._logger.debug(f"[{self.agent_id}] Shared knowledge to {target}")
                    except Exception as e:
                        self._logger.error(f"[{self.agent_id}] Knowledge share to {target} failed: {e}")
            
            self._pending_knowledge_shares = []
    
    def _build_interrupt_prompt(self) -> Optional[str]:
        """
        Build a prompt from queued interrupt messages.
        
        Returns a prompt that naturally injects the messages into the conversation,
        or None if no messages to inject.
        """
        if not self._interrupt_messages:
            return None
        
        parts = ["## Incoming Messages (URGENT - Address Before Continuing)\n"]
        
        for msg in self._interrupt_messages:
            msg_type = msg.get("type", "info")
            from_agent = msg.get("from", "unknown")
            content = msg.get("content", "")
            priority = msg.get("priority", "normal")
            tags = msg.get("tags", [])
            
            # Format based on type
            if msg_type == "issue":
                parts.append(f"**BUG REPORT from {from_agent}** (priority: {priority})")
                parts.append(f"Issue: {content}")
                parts.append("ACTION: Fix this issue immediately, then continue your current task.\n")
            elif msg_type == "task_ready":
                parts.append(f"**TASK NOTIFICATION from {from_agent}** (priority: {priority})")
                parts.append(f"Message: {content}")
                if "task_ready" in tags:
                    parts.append("ACTION: Upstream work is complete. Start your implementation now.\n")
                else:
                    parts.append("\n")
            elif msg_type == "question":
                parts.append(f"**QUESTION from {from_agent}** (priority: {priority})")
                parts.append(f"Question: {content}")
                parts.append("ACTION: Answer this question using send_message(), then continue your task.\n")
            else:
                parts.append(f"**{msg_type.upper()} from {from_agent}** (priority: {priority})")
                parts.append(f"Content: {content}\n")
        
        parts.append("---\nProcess these messages, then continue with your current work.")
        
        return "\n".join(parts)
    
    # ==================== TOOL REGISTRATION ====================
    
    def _register_env_gen_tools(self):
        """Register environment generation tools based on allowed_tool_categories."""
        include_browser = "browser" in self.allowed_tool_categories
        include_docker = "docker" in self.allowed_tool_categories
        include_vision = self._include_vision or ("vision" in self.allowed_tool_categories)
        # get_agent_tools expects a Workspace with .root; wrap WorkspaceManager.base_dir
        workspace_for_tools = Workspace(str(self.workspace.base_dir)) if self.workspace else Workspace(Path.cwd())
        
        agent_tools = get_agent_tools(
            agent_type=self.agent_id,
            workspace=workspace_for_tools,
            include_browser=include_browser,
            include_docker=include_docker,
            include_vision=include_vision,
            llm_client=self.llm,
        )
        
        if not agent_tools:
            self._logger.warning(f"[{self.agent_id}] No tools returned from get_agent_tools")
        
        for tool_instance in agent_tools:
            try:
                # Inject agent reference for communication tools
                if hasattr(tool_instance, 'set_agent'):
                    tool_instance.set_agent(self)
                
                self._tool_instances[tool_instance.NAME] = tool_instance
                
                # Also register in parent's ToolRegistry for compatibility
                self._tools.register(tool_instance)
            except Exception as e:
                name = getattr(tool_instance, "NAME", "<unknown>")
                self._logger.warning(f"Tool {name} init failed: {e}")
    
    def get_tools_for_llm(self) -> List[Dict]:
        """
        Get tool definitions formatted for LLM.
        
        Align with /agent implementation: prefer the ToolRegistry's
        serialization (to_openai_tools) so all tools are encoded uniformly.
        Fallback to per-instance definitions if needed.
        """
        if hasattr(self._tools, "to_openai_tools"):
            try:
                return self._tools.to_openai_tools()
            except Exception as e:
                self._logger.warning(f"[{self.agent_id}] to_openai_tools failed: {e}")
        
        tools = []
        for inst in self._tool_instances.values():
            try:
                if hasattr(inst, "get_tool_param"):
                    tools.append(inst.get_tool_param())
                elif hasattr(inst, "tool_definition"):
                    td = inst.tool_definition
                    # tool_definition might be a method or a property
                    tools.append(td() if callable(td) else td)
                else:
                    continue
            except Exception:
                continue
        return tools
    
    async def _execute_tool(self, tool_name: str, tool_args: Dict) -> ToolResult:
        """Execute a tool and log it."""
        if tool_name in self._tool_instances:
            try:
                exec_fn = self._tool_instances[tool_name].execute
                if asyncio.iscoroutinefunction(exec_fn):
                    result = await exec_fn(**tool_args)
                else:
                    result = await asyncio.to_thread(exec_fn, **tool_args)
                # Log tool call (inherited from BaseAgent)
                self.log_tool_call(tool_name, tool_args, result)
                return result
            except Exception as e:
                return ToolResult(success=False, error_message=str(e))
        return ToolResult(success=False, error_message=f"Unknown tool: {tool_name}")
    
    def _log_tool_details(self, tool_name: str, tool_args: Dict) -> None:
        """Enhanced logging for tool calls with detailed content for important tools."""
        # Helper to truncate long strings
        def truncate(s: str, max_len: int = 200) -> str:
            s = str(s)
            return s[:max_len] + "..." if len(s) > max_len else s
        
        # Format based on tool type
        if tool_name == "think":
            thought = tool_args.get("thought", "")
            self._logger.info(f"[{self.agent_id}] 🧠 THINK: {truncate(thought, 300)}")
        
        elif tool_name == "plan":
            action = tool_args.get("action", "create")
            items = tool_args.get("items", [])
            item_text = tool_args.get("item_text", "")
            item_index = tool_args.get("item_index")
            if action == "create":
                self._logger.info(f"[{self.agent_id}] 📋 PLAN CREATE ({len(items)} items):")
                for i, item in enumerate(items[:10]):  # Show first 10 items
                    self._logger.info(f"    [{i}] {truncate(item, 100)}")
                if len(items) > 10:
                    self._logger.info(f"    ... and {len(items) - 10} more items")
            elif action == "add":
                self._logger.info(f"[{self.agent_id}] 📋 PLAN ADD: {items}")
            elif action == "complete":
                self._logger.info(f"[{self.agent_id}] ✅ PLAN COMPLETE: item #{item_index}")
            elif action == "update":
                self._logger.info(f"[{self.agent_id}] 📝 PLAN UPDATE #{item_index}: {truncate(item_text, 100)}")
            elif action == "remove":
                self._logger.info(f"[{self.agent_id}] ❌ PLAN REMOVE: item #{item_index}")
            elif action == "clear":
                self._logger.info(f"[{self.agent_id}] 🗑️ PLAN CLEAR")
            else:
                self._logger.info(f"[{self.agent_id}] 📋 PLAN {action}: {tool_args}")
        
        elif tool_name == "send_message":
            to_agent = tool_args.get("to_agent", "?")
            content = tool_args.get("content", "")
            msg_type = tool_args.get("msg_type", "update")
            priority = tool_args.get("priority", "normal")
            self._logger.info(f"[{self.agent_id}] 📤 SEND_MESSAGE to={to_agent} type={msg_type} priority={priority}")
            self._logger.info(f"    Content: {truncate(content, 200)}")
        
        elif tool_name == "broadcast":
            message = tool_args.get("message", "")
            self._logger.info(f"[{self.agent_id}] 📢 BROADCAST: {truncate(message, 200)}")
        
        elif tool_name == "ask_agent":
            agent_id = tool_args.get("agent_id", "?")
            question = tool_args.get("question", "")
            self._logger.info(f"[{self.agent_id}] ❓ ASK_AGENT to={agent_id}: {truncate(question, 200)}")
        
        elif tool_name == "check_inbox":
            filters = {k: v for k, v in tool_args.items() if v}
            self._logger.info(f"[{self.agent_id}] 📥 CHECK_INBOX filters={filters if filters else 'none'}")
        
        elif tool_name == "report_issue":
            issue = tool_args.get("issue", "")
            assign_to = tool_args.get("assign_to", "?")
            severity = tool_args.get("severity", "error")
            self._logger.info(f"[{self.agent_id}] 🐛 REPORT_ISSUE to={assign_to} severity={severity}")
            self._logger.info(f"    Issue: {truncate(issue, 200)}")
        
        elif tool_name == "finish":
            message = tool_args.get("message", "")
            notify = tool_args.get("notify", [])
            self._logger.info(f"[{self.agent_id}] 🏁 FINISH notify={notify}")
            self._logger.info(f"    Message: {truncate(message, 200)}")
        
        elif tool_name == "deliver_project":
            summary = tool_args.get("delivery_summary", "")
            self._logger.info(f"[{self.agent_id}] 🚀 DELIVER_PROJECT: {truncate(summary, 200)}")
        
        elif tool_name == "write_file":
            path = tool_args.get("path", tool_args.get("file_path", "?"))
            content_len = len(tool_args.get("content", ""))
            self._logger.info(f"[{self.agent_id}] 📝 WRITE_FILE: {path} ({content_len} chars)")
        
        elif tool_name == "view":
            path = tool_args.get("path", tool_args.get("file_path", "?"))
            self._logger.info(f"[{self.agent_id}] 👁️ VIEW: {path}")
        
        elif tool_name == "lint":
            path = tool_args.get("path", "?")
            self._logger.info(f"[{self.agent_id}] 🔍 LINT: {path}")
        
        elif tool_name == "remember":
            content = tool_args.get("content", "")
            category = tool_args.get("category", "general")
            self._logger.info(f"[{self.agent_id}] 💾 REMEMBER [{category}]: {truncate(content, 150)}")
        
        elif tool_name == "recall":
            query = tool_args.get("query", "")
            self._logger.info(f"[{self.agent_id}] 🔎 RECALL: {truncate(query, 100)}")
        
        elif tool_name == "share_knowledge":
            to_agents = tool_args.get("to_agents", [])
            content = tool_args.get("content", "")
            self._logger.info(f"[{self.agent_id}] 📤 SHARE_KNOWLEDGE to={to_agents}: {truncate(content, 150)}")
        
        elif tool_name in ["docker_build", "docker_up", "docker_down", "docker_logs", "docker_validate"]:
            service = tool_args.get("service", "all")
            self._logger.info(f"[{self.agent_id}] 🐳 {tool_name.upper()}: service={service} args={tool_args}")
        
        elif tool_name == "wait":
            seconds = tool_args.get("seconds", 0)
            reason = tool_args.get("reason", "")
            self._logger.info(f"[{self.agent_id}] ⏳ WAIT: {seconds}s - {reason}")
        
        elif tool_name == "get_time":
            self._logger.info(f"[{self.agent_id}] 🕐 GET_TIME")
        
        elif tool_name == "analyze_image" or tool_name == "view_image":
            image_path = tool_args.get("image_path", tool_args.get("path", "?"))
            self._logger.info(f"[{self.agent_id}] 🖼️ {tool_name.upper()}: {image_path}")
        
        else:
            # Default logging for other tools
            self._logger.info(f"[{self.agent_id}] 🔧 {tool_name}: args={list(tool_args.keys())}")
    
    def _log_tool_result(self, tool_name: str, result: ToolResult, duration_ms: int) -> None:
        """Log tool execution result with appropriate detail level."""
        def truncate(s: str, max_len: int = 150) -> str:
            s = str(s)
            return s[:max_len] + "..." if len(s) > max_len else s
        
        status = "✅" if result.success else "❌"
        
        # Tools where we want to see the result
        verbose_result_tools = {
            "check_inbox", "recall", "get_history", "get_memory_context",
            "get_time", "db_schema", "list_reference_images"
        }
        
        # Tools where result is typically not interesting
        quiet_tools = {"write_file", "view", "lint", "wait", "think"}
        
        if not result.success:
            # Always log errors in detail
            self._logger.warning(f"[{self.agent_id}] {status} {tool_name} FAILED ({duration_ms}ms): {truncate(result.error_message or '', 300)}")
        
        elif tool_name in verbose_result_tools:
            # Show result for important query tools
            result_preview = truncate(str(result.data), 300) if result.data else "empty"
            self._logger.info(f"[{self.agent_id}] {status} {tool_name} ({duration_ms}ms): {result_preview}")
        
        elif tool_name == "check_inbox":
            # Special handling for inbox - show message count
            data = result.data
            if isinstance(data, dict):
                msg_count = data.get("count", 0)
                messages = data.get("messages", [])
                if msg_count > 0:
                    self._logger.info(f"[{self.agent_id}] {status} check_inbox ({duration_ms}ms): {msg_count} messages")
                    for msg in messages[:5]:  # Show first 5
                        from_agent = msg.get("from", "?")
                        msg_type = msg.get("type", "?")
                        content_preview = truncate(msg.get("content", ""), 100)
                        self._logger.info(f"    📩 from={from_agent} type={msg_type}: {content_preview}")
                else:
                    self._logger.info(f"[{self.agent_id}] {status} check_inbox ({duration_ms}ms): inbox empty")
            else:
                self._logger.info(f"[{self.agent_id}] {status} check_inbox ({duration_ms}ms): {truncate(str(data), 100)}")
        
        elif tool_name == "plan":
            # Show plan state after operation
            if isinstance(result.data, dict) and "plan" in result.data:
                plan_items = result.data.get("plan", [])
                completed = sum(1 for p in plan_items if p.get("completed", False))
                self._logger.info(f"[{self.agent_id}] {status} plan ({duration_ms}ms): {completed}/{len(plan_items)} items complete")
        
        elif tool_name in quiet_tools:
            # Minimal logging for high-frequency tools
            self._logger.debug(f"[{self.agent_id}] {status} {tool_name} ({duration_ms}ms)")
        
        else:
            # Default: brief confirmation
            self._logger.info(f"[{self.agent_id}] {status} {tool_name} ({duration_ms}ms)")
    
    # ==================== TASK PROCESSING ====================
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """
        Process task via agentic loop.
        
        Implements the abstract method from BaseAgent.
        """
        # Extract task data from message
        task_data = task.payload if isinstance(task.payload, dict) else {}
        if isinstance(task.payload, str):
            try:
                task_data = json.loads(task.payload)
            except:
                task_data = {"description": task.payload}
        
        # Run agentic loop
        result = await self.execute(task_data)
        
        # Signal completion
        self._task_complete_event.set()
        
        # Create result message
        return create_result_message(
            source_id=self._agent_id,
            target_id=task.header.source_agent_id,
            task_id=task.task_id,
            success=result.get("success", False),
            result_data=result,
        )
    
    async def execute(self, task: Dict) -> Dict:
        """Execute task via agentic loop."""
        system_prompt = self._get_system_prompt()
        task_prompt = self._build_task_prompt(task)
        
        # Log prompt
        # Log using configured model name (LLM wrapper does not expose model_id)
        model_name = getattr(self.llm.config, "model_name", "unknown")
        self.log_prompt(f"{system_prompt}\n---\n{task_prompt}", model=str(model_name))
        
        return await self.run_agentic_loop(
            system_prompt=system_prompt,
            initial_prompt=task_prompt,
            max_steps=task.get("max_steps", 2000),
        )
    
    async def run_agentic_loop(
        self,
        system_prompt: str,
        initial_prompt: str,
        max_steps: int = 2000,
    ) -> Dict:
        """
        Run LLM agentic loop until finish() is called.
        
        Features:
        - Checks for urgent messages (questions) between steps
        - Preempts to answer questions, then resumes
        - Stuck detection and loop breaking
        """
        self._processing_state = ProcessingState.PROCESSING_TASK
        messages = [Message.system(system_prompt), Message.user(initial_prompt)]
        
        files_created = []
        files_modified = []
        no_tool_steps = 0
        tool_schemas = self.get_tools_for_llm()
        tool_names = []
        try:
            for t in tool_schemas:
                fn = t.get("function", {})
                name = fn.get("name")
                if name:
                    tool_names.append(name)
        except Exception as e:
            tool_names = []
            self._logger.warning(f"[{self.agent_id}] Tool schema build failed: {e}")
        if not tool_schemas:
            self._logger.warning(f"[{self.agent_id}] No tools registered for LLM. allowed_tool_categories={getattr(self, 'allowed_tool_categories', [])}")
        else:
            self._logger.info(f"[{self.agent_id}] Tools registered for LLM: {len(tool_names)} -> {', '.join(tool_names[:15])}")
        
        try:
            for step in range(max_steps):
                # Check for shutdown
                if self._shutdown_requested:
                    return {"success": False, "error": "Shutdown requested", "files_created": files_created}
                
                # ==================== MEMORY CONDENSATION ====================
                # Check if messages need condensation (every 10 steps)
                if step > 0 and step % 10 == 0 and hasattr(self, 'memory'):
                    if self.memory.should_condense_messages(messages):
                        self._logger.info(f"[{self.agent_id}] Condensing messages (len={len(messages)})")
                        messages = await self.memory.condense_messages(messages)
                        self._logger.info(f"[{self.agent_id}] After condensation: len={len(messages)}")
                
                # Check and handle urgent messages (questions from other agents)
                # This enables question preemption during task processing
                while await self._check_and_handle_urgent():
                    pass  # Handle all pending urgent messages
                
                # Inject interrupt messages into conversation (true interrupt)
                # These are high-priority messages that become part of the active context
                if self._interrupt_messages:
                    interrupt_prompt = self._build_interrupt_prompt()
                    if interrupt_prompt:
                        messages.append(Message.user(interrupt_prompt))
                        self._logger.info(f"[{self.agent_id}] Injected {len(self._interrupt_messages)} interrupt message(s)")
                    self._interrupt_messages.clear()
                
                # Check stuck detection (inherited)
                if self.check_if_stuck():
                    breaker_prompt = self.get_loop_breaker_prompt()
                    if breaker_prompt:
                        messages.append(Message.user(breaker_prompt))
                        self.clear_stuck_history()
                # LLM call with retry (inherited)
                tools = tool_schemas
                response = None
                try:
                    response = await self.call_with_retry(
                        self.llm.chat_messages,  # returns LLMResponse with tool_calls/content
                        messages,
                        tools=tools,
                    )
                except Exception as e:
                    self._logger.error(f"LLM call failed: {e}")
                    return {"success": False, "error": str(e), "files_created": files_created}
                
                if response is None:
                    self._logger.error(f"[{self.agent_id}] LLM returned no response")
                    return {"success": False, "error": "LLM returned no response", "files_created": files_created}
                
                tool_count = len(response.tool_calls or [])
                self._logger.info(
                    f"[{self.agent_id}] Step {step + 1}/{max_steps} "
                    f"(state={self._processing_state.value}, tool_calls={tool_count})"
                )
                
                # Log response
                self.log_response(response.content or "", tokens=getattr(response, 'usage', {}).get('total_tokens', 0))
                
                if not response.tool_calls:
                    self._logger.info(f"[{self.agent_id}] No tool calls this step; content_len={len(response.content or '')}")
                    no_tool_steps += 1
                    if no_tool_steps in (1, 3):
                        # Nudge with explicit tool list
                        if tool_names:
                            messages.append(
                                Message.user(
                                    f"Use tools now. Available: {', '.join(tool_names[:12])}. "
                                    f"Start with plan() or relevant inspection tools, then finish() when done."
                                )
                            )
                        else:
                            messages.append(Message.user("Use available tools now."))
                    if no_tool_steps >= 20:
                        self._logger.warning(f"[{self.agent_id}] Too many text-only steps without tool use; aborting loop.")
                        return {
                            "success": False,
                            "error": "LLM did not use tools; aborted to avoid stuck loop",
                            "files_created": files_created,
                            "files_modified": files_modified,
                        }
                    if response.content:
                        messages.append(Message.assistant(response.content))
                        messages.append(Message.user("Use tools to complete your task. Call finish() when done."))
                        # Record for stuck detection
                        self.record_action("no_tool_call")
                    continue
                else:
                    no_tool_steps = 0
                
                # Summarize tool calls for observability
                summary = []
                for tc in response.tool_calls:
                    try:
                        fn = getattr(tc, "function", None) or tc.get("function", {})
                        name = getattr(fn, "name", None) or fn.get("name", "unknown")
                        args_raw = getattr(fn, "arguments", None) or fn.get("arguments", "{}")
                        try:
                            arg_dict = json.loads(args_raw)
                            arg_preview = ",".join(list(arg_dict.keys())[:4])
                        except Exception:
                            arg_preview = "args_parse_error"
                        summary.append(f"{name}({arg_preview})")
                    except Exception:
                        summary.append("tool_call_parse_error")
                self._logger.info(f"[{self.agent_id}] Tool calls: {', '.join(summary)}")
                
                # Process tool calls
                for tool_call in response.tool_calls:
                    # Normalize tool_call structure (object or dict)
                    try:
                        fn = getattr(tool_call, "function", None) or tool_call.get("function", {})
                        tool_name = getattr(fn, "name", None) or fn.get("name")
                        args_raw = getattr(fn, "arguments", None) or fn.get("arguments", "{}")
                        tool_call_id = getattr(tool_call, "id", None) or tool_call.get("id") or f"call_{step}"
                    except Exception:
                        tool_name = None
                        args_raw = "{}"
                        tool_call_id = f"call_{step}"
                    
                    try:
                        tool_args = json.loads(args_raw)
                    except Exception:
                        tool_args = {}
                    
                    # Enhanced tool logging for debugging
                    self._log_tool_details(tool_name, tool_args)
                    
                    # Record for stuck detection
                    self.record_action(f"{tool_name}({list(tool_args.keys())})")
                    
                    # Handle finish
                    # Handle finish() - for most agents, this ends the loop
                    # For UserAgent, finish() triggers downstream agents but doesn't end the loop
                    if tool_name == "finish":
                        # UserAgent uses finish(notify=[...]) to trigger other agents, but keeps running
                        if self.agent_id == "user":
                            self._logger.info(f"[{self.agent_id}] finish() with notify - triggering downstream agents. Loop continues until deliver_project().")
                            # Don't return, just execute the tool and continue
                            result = await self._execute_tool(tool_name, tool_args)
                            messages.append(Message.assistant(tool_calls=[tool_call]))
                            result_str = result.data if result.success else f"Error: {result.error_message}"
                            if isinstance(result_str, dict):
                                result_str = json.dumps(result_str, indent=2)
                            messages.append(Message.tool(str(result_str)[:10000], tool_call_id))
                            messages.append(Message.user(
                                "Downstream agents notified. Continue monitoring with check_inbox() and respond to questions. "
                                "When all agents complete and testing passes, use deliver_project() to end."
                            ))
                            continue
                        # For non-UserAgent: execute finish(), process pending notifications, then return
                        result = await self._execute_tool(tool_name, tool_args)
                        await self._process_pending_notifications()  # Send task_ready to downstream agents
                        return {
                            "success": True,
                            "summary": tool_args.get('message', 'Done'),
                            "files_created": files_created,
                            "files_modified": files_modified,
                            "finish": tool_args,
                        }
                    
                    # Handle deliver_project() - only UserAgent should use this
                    if tool_name == "deliver_project":
                        result = await self._execute_tool(tool_name, tool_args)
                        if result.success:
                            return {
                                "success": True,
                                "summary": tool_args.get('delivery_summary', 'Project delivered'),
                                "files_created": files_created,
                                "files_modified": files_modified,
                                "delivered": True,
                            }
                        else:
                            # Delivery failed (e.g., checklist not met) - continue loop
                            messages.append(Message.assistant(tool_calls=[tool_call]))
                            messages.append(Message.tool(f"Error: {result.error_message}", tool_call_id))
                            continue
                    
                    # Execute tool
                    import time as _time
                    _tool_start = _time.time()
                    result = await self._execute_tool(tool_name, tool_args)
                    _tool_duration_ms = int((_time.time() - _tool_start) * 1000)
                    
                    # Log tool result for important tools
                    self._log_tool_result(tool_name, result, _tool_duration_ms)
                    
                    # Track files
                    if tool_name in ["write_file", "create"]:
                        path = tool_args.get("path") or tool_args.get("file_path")
                        if path:
                            files_created.append(path)
                            # Record in memory
                            if hasattr(self, 'memory'):
                                self.memory.record_file_created(path)
                    elif tool_name == "str_replace_editor":
                        path = tool_args.get("path")
                        if path:
                            files_modified.append(path)
                            if hasattr(self, 'memory'):
                                self.memory.record_file_modified(path)
                    elif tool_name == "lint":
                        path = tool_args.get("path")
                        if path and hasattr(self, 'memory'):
                            self.memory.record_lint(path, result.success)
                    
                    # Record tool call to memory for tracking/loop detection
                    if hasattr(self, 'memory'):
                        loop_info = self.memory.record_tool_call(
                            tool_name=tool_name,
                            tool_args=tool_args,
                            result=result.data if result.success else result.error_message,
                            success=result.success,
                            duration_ms=_tool_duration_ms
                        )
                        # Warn if potential loop detected
                        # Potential loop detection - logged at debug level (normal for batch operations)
                        if loop_info.get("is_potential_loop") and loop_info.get("consecutive_count", 0) % 20 == 0:
                            self._logger.debug(
                                f"[{self.agent_id}] Batch operation: {loop_info['consecutive_count']} "
                                f"consecutive {tool_name} calls"
                            )
                    
                    # Record observation per call (for stuck detection)
                    if result.success:
                        self.record_observation(str(result.data)[:200] if result.data else "OK")
                    else:
                        self.record_error(result.error_message or "")
                        # Also record error in memory
                        if hasattr(self, 'memory'):
                            self.memory.record_error(result.error_message or "", context=f"tool={tool_name}")
                    
                    # Process any pending notifications from tools (e.g., finish(notify=[...]))
                    await self._process_pending_notifications()
                    
                    # Add messages per tool call
                    messages.append(Message.assistant(tool_calls=[tool_call]))
                    result_str = result.data if result.success else f"Error: {result.error_message}"
                    if isinstance(result_str, dict):
                        result_str = json.dumps(result_str, indent=2)
                    messages.append(Message.tool(str(result_str)[:10000], tool_call_id))
            
            return {"success": False, "error": f"Max steps ({max_steps})", "files_created": files_created}
        
        finally:
            # Reset processing state
            self._processing_state = ProcessingState.IDLE
    
    # ==================== PROMPT METHODS (OVERRIDE IN SUBCLASS) ====================
    
    def _get_system_prompt(self) -> str:
        """Get system prompt. Override in subclass to use j2 templates."""
        return f"You are {self.agent_name}. Use tools to complete tasks. Call finish() when done."
    
    def _build_task_prompt(self, task: Dict) -> str:
        """Build task prompt. Override in subclass to use j2 templates."""
        description = task.get("description", "")
        related_files = task.get("related_files", [])
        
        parts = []
        if description:
            parts.append(f"## Task\n\n{description}")
        else:
            parts.append(f"## Task\n\n{safe_json_dumps(task)}")
        
        if related_files:
            files_str = "\n".join(f"- {f}" for f in related_files)
            parts.append(f"## Related Files\n\n{files_str}")
        
        parts.append("Use tools to complete this task. Call finish() when done.")
        return "\n\n".join(parts)
    
    # ==================== JINJA2 HELPERS ====================
    
    def render_template(self, template_path: str, **kwargs) -> str:
        """Render a Jinja2 template."""
        try:
            template = self._jinja_env.get_template(template_path)
            return template.render(**kwargs)
        except Exception as e:
            self._logger.warning(f"Template error {template_path}: {e}")
            return ""
    
    def render_macro(self, template_path: str, macro_name: str, **kwargs) -> str:
        """Render a specific macro from a template."""
        try:
            template = self._jinja_env.get_template(template_path)
            macro = getattr(template.module, macro_name, None)
            if macro:
                return macro(**kwargs)
            self._logger.warning(f"Macro {macro_name} not found in {template_path}")
            return ""
        except Exception as e:
            self._logger.warning(f"Macro error {template_path}.{macro_name}: {e}")
            return ""
    
    # ==================== EXTERNAL MESSAGEBUS ====================
    
    def set_message_bus(self, bus: MessageBus):
        """Set external MessageBus and register with it."""
        self._external_bus = bus
        # Expose for communication tools (they read _message_bus)
        self._message_bus = bus
        bus.register_agent(self)
        self._logger.info(f"[{self.agent_id}] Registered with external MessageBus")
    
    # ==================== TASK API FOR ORCHESTRATOR ====================
    
    async def send_task(self, task: Dict) -> asyncio.Event:
        """
        Send task to this agent. Returns completion event.
        
        Used by Orchestrator to send tasks without going through MessageBus.
        """
        self._task_complete_event.clear()
        
        # Create TaskMessage
        from uuid import uuid4
        task_id = str(uuid4())
        header = MessageHeader(
            message_id=str(uuid4()),
            source_agent_id="orchestrator",
            target_agent_id=self._agent_id,
            priority=MessagePriority.NORMAL,
        )
        
        task_msg = TaskMessage(
            header=header,
            task_id=task_id,
            task_name=task.get("name", "task"),
            payload=task,
        )
        
        # Put in message queue (inherited from BaseAgent)
        await self.receive_message(task_msg)
        
        return self._task_complete_event
    
    # ==================== CONTEXT SETTERS ====================
    
    def set_gen_context(self, context):
        """Set generation context (ports, settings)."""
        self.gen_context = context
    
    def set_requirements(self, requirements: Dict):
        """Set project requirements."""
        self._requirements = requirements
    
    def set_design_docs(self, docs: Dict[str, str]):
        """Set design documents."""
        self._design_docs = docs
    
    def init_memory_bank(self, project_info: Dict):
        """Initialize persistent memory bank."""
        if not self.workspace:
            return
        memory_dir = Path(self.workspace.base_dir) / ".memory" / self.agent_id
        memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory_bank = MemoryBank(memory_dir)
    
    # ==================== FILE HELPERS ====================
    
    def list_files(self, directory: str = "") -> List[str]:
        """List files in workspace."""
        try:
            target = Path(self.workspace.base_dir) / directory
            if target.exists():
                return [str(f.relative_to(self.workspace.base_dir)) for f in target.rglob("*") if f.is_file()]
        except:
            pass
        return []
    
    def read_file(self, path: str) -> Optional[str]:
        """Read file from workspace."""
        try:
            file_path = Path(self.workspace.base_dir) / path
            if file_path.exists():
                return file_path.read_text()
        except:
            pass
        return None
