"""
Agent Interaction Tools - Tools for memory access and task completion

Provides:
- ReadMemoryBankTool: Read project context from Memory Bank
- FinishTool: Signal task completion

For inter-agent communication, use communication_tools.py instead:
- SendMessageTool, AskAgentTool, BroadcastTool, CheckInboxTool, etc.
"""

from typing import TYPE_CHECKING

from ._base import (
    BaseTool,
    ToolResult,
    ToolCategory,
    create_tool_param,
    Workspace,
)

if TYPE_CHECKING:
    from ..multi_agent.agents.base import EnvGenAgent

# Import PlanTool for finish verification (avoid circular import by using late import)


# ============================================================================
# Read Memory Bank Tool
# ============================================================================

class ReadMemoryBankTool(BaseTool):
    """
    Read project context from Memory Bank.
    
    Memory Bank contains structured project knowledge:
    - project_brief: Core requirements and goals
    - tech_context: Technologies and constraints
    - system_patterns: Architecture and design patterns
    - active_context: Current work focus
    - progress: Completed features and known issues
    """
    
    NAME = "read_memory_bank"
    
    DESCRIPTION = """Read project context from the Memory Bank.

Memory Bank contains persistent project knowledge:
- project_brief: Core requirements, goals, scope
- tech_context: Tech stack, dependencies, setup
- system_patterns: Architecture, design patterns, decisions
- active_context: Current focus, recent changes, next steps
- progress: Completed features, in-progress, known issues

Use this at the start of a task to understand project context!

Examples:
    read_memory_bank()                    # Read all memory files
    read_memory_bank(file="progress")     # Read specific file
    read_memory_bank(file="active_context")
"""
    
    def __init__(self, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        self.workspace = workspace
    
    @property
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "enum": ["all", "project_brief", "tech_context", "system_patterns", "active_context", "progress"],
                        "description": "Which memory file to read (default: all)"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["digest", "full"],
                        "description": "digest (default) returns a concise summary; full returns complete file contents"
                    }
                },
                "required": []
            }
        )
    
    def execute(self, file: str = "all", mode: str = "digest") -> ToolResult:
        if not self.workspace:
            return ToolResult(
                success=False,
                error_message="Workspace not configured for ReadMemoryBankTool"
            )
        
        memory_dir = self.workspace.root / "memory-bank"
        
        if not memory_dir.exists():
            return ToolResult(
                success=False,
                error_message="Memory Bank not found. It will be created during project initialization."
            )
        
        file_map = {
            "project_brief": "project_brief.md",
            "tech_context": "tech_context.md",
            "system_patterns": "system_patterns.md",
            "active_context": "active_context.md",
            "progress": "progress.md",
        }
        
        if file == "all":
            if mode == "full":
                contents = {}
                for key, filename in file_map.items():
                    file_path = memory_dir / filename
                    if file_path.exists():
                        contents[key] = file_path.read_text(encoding="utf-8")
                    else:
                        contents[key] = "(file not found)"

                sections = []
                for key, content in contents.items():
                    sections.append(f"=== {key.upper()} ===\n{content}")

                content_out = "\n\n".join(sections)
            else:
                # Digest mode: use MemoryBank's digest to avoid dumping huge context.
                try:
                    from memory.memory_bank import MemoryBank
                    mb = MemoryBank(root_dir=self.workspace.root)
                    content_out = mb.get_digest()
                except Exception:
                    # Fallback to active_context + progress only
                    ac = (memory_dir / file_map["active_context"]).read_text(encoding="utf-8") if (memory_dir / file_map["active_context"]).exists() else ""
                    prog = (memory_dir / file_map["progress"]).read_text(encoding="utf-8") if (memory_dir / file_map["progress"]).exists() else ""
                    content_out = f"=== ACTIVE_CONTEXT ===\n{ac}\n\n=== PROGRESS ===\n{prog}"

            return ToolResult(
                success=True,
                data={
                    "files_read": list(file_map.keys()),
                    "mode": mode,
                    "content": content_out,
                    "info": f"Read memory bank ({mode})."
                }
            )
        
        elif file in file_map:
            file_path = memory_dir / file_map[file]
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                return ToolResult(
                    success=True,
                    data={
                        "file": file,
                        "mode": "full",
                        "content": content,
                        "info": f"Read memory bank file: {file}"
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error_message=f"Memory bank file '{file}' not found."
                )
        
        else:
            return ToolResult(
                success=False,
                error_message=f"Unknown file '{file}'. Valid options: all, project_brief, tech_context, system_patterns, active_context, progress"
            )


# ============================================================================
# Finish Tool
# ============================================================================

class FinishTool(BaseTool):
    """
    Signal that agent's current task is complete.
    
    Key features:
    - Can automatically notify downstream agents to start their work
    - Ends the current agentic loop
    - Agent remains available for new tasks/issues
    """
    
    NAME = "finish"
    
    DESCRIPTION = """Signal your current task is complete.

## Basic Usage
```
finish(message="Completed database schema and seed data")
```

## Notify Downstream Agents (RECOMMENDED!)
Use `notify` to automatically push your work to downstream agents:
```
# DesignAgent notifies all code agents to start
finish(
    message="Design specs created: spec.database.json, spec.api.json, spec.ui.json",
    notify=["database", "backend", "frontend"],
    notify_content="Design complete! Please start implementation based on specs in /design/"
)

# DatabaseAgent notifies backend
finish(
    message="Database schema ready",
    notify=["backend"],
    notify_content="Database schema ready. Tables: users, flights, bookings. See /app/database/init/"
)

# BackendAgent notifies frontend
finish(
    message="API complete with 12 endpoints",
    notify=["frontend"],
    notify_content="API ready at :8000. Endpoints: /auth/*, /flights/*, /bookings/*. See spec.api.json"
)
```

The notify feature:
- Sends HIGH priority messages to specified agents
- Automatically tags with ["task_ready", "from_<your_agent>"]
- Receivers can filter for these with check_inbox(tags=["task_ready"])

## After finish()
- Current task loop ends
- You remain available for issues/questions from other agents
- If you receive an issue, you'll automatically start working on it
"""
    
    def __init__(self, agent_id: str = None, agent: "EnvGenAgent" = None):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        self.agent_id = agent_id or "default"
        self.agent = agent
    
    def set_agent(self, agent: "EnvGenAgent"):
        """Inject agent reference for message sending."""
        self.agent = agent
        self.agent_id = agent.agent_id
    
    @property
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Summary of completed work"
                    },
                    "notify": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Agents to notify (e.g., ['frontend', 'backend'])"
                    },
                    "notify_content": {
                        "type": "string",
                        "description": "Message content for notified agents (defaults to your message)"
                    },
                    "outputs": {
                        "type": "object",
                        "description": "Any output data"
                    }
                },
                "required": ["message"]
            }
        )
    
    def execute(
        self, 
        message: str, 
        notify: list = None,
        notify_content: str = None,
        outputs: dict = None
    ) -> ToolResult:
        from .reasoning_tools import PlanTool
        
        plan_tool = PlanTool.get_instance(self.agent_id)
        plan_status = plan_tool.get_plan_status()
        
        warnings = []
        notifications_sent = []
        
        # Warning 1: Check if there's an incomplete plan (warning only, not blocking)
        if plan_status["has_plan"] and not plan_status["all_complete"]:
            incomplete_count = len(plan_status["incomplete"])
            warnings.append(f"Note: You have {incomplete_count} incomplete plan items.")
        
        # Send notifications to downstream agents
        # NOTE: This is synchronous - notifications will be sent after this method returns
        # by storing them for the agent to process
        if notify and self.agent:
            from uuid import uuid4
            from utils.message import MessageHeader, MessageType, MessagePriority, BaseMessage
            
            bus = getattr(self.agent, "_external_bus", None) or getattr(self.agent, "_message_bus", None)
            
            if bus:
                content = notify_content or f"[{self.agent_id.upper()}] Task complete: {message}"
                tags = ["task_ready", f"from_{self.agent_id}"]
                
                # Store pending notifications on agent for async delivery
                pending = getattr(self.agent, "_pending_notifications", None)
                if pending is None:
                    self.agent._pending_notifications = []
                    pending = self.agent._pending_notifications
                
                for target in notify:
                    try:
                        header = MessageHeader(
                            message_id=str(uuid4()),
                            source_agent_id=self.agent_id,
                            target_agent_id=target,
                            priority=MessagePriority.HIGH,
                        )
                        msg = BaseMessage(
                            header=header,
                            message_type=MessageType.STATUS,
                            payload=content,
                            metadata={
                                "msg_type": "task_ready",
                                "tags": tags,
                                "persist": False,
                                "read": False,
                            }
                        )
                        # Store for async delivery instead of create_task (thread-safe)
                        pending.append((bus, msg))
                        notifications_sent.append(target)
                    except Exception as e:
                        warnings.append(f"Failed to notify {target}: {e}")
        
        # Build response info
        info = f"Task completed: {message}"
        if notifications_sent:
            info += f"\nNotified agents: {', '.join(notifications_sent)}"
        if warnings:
            info += "\n\nNotes:\n" + "\n".join(f"  - {w}" for w in warnings)
        
        return ToolResult(
            success=True,
            data={
                "outputs": outputs or {}, 
                "finished": True,
                "notified": notifications_sent,
                "info": info
            }
        )


# ============================================================================
# Deliver Project Tool (UserAgent only)
# ============================================================================

class DeliverProjectTool(BaseTool):
    """
    Signal that the project is ready for delivery to the user.
    
    This tool is ONLY for UserAgent and triggers the overall shutdown.
    - Only call this when ALL criteria are met (no bugs, fully functional, etc.)
    - This is different from finish() which just ends the current task
    - deliver_project() ends the entire generation process
    """
    
    NAME = "deliver_project"
    
    DESCRIPTION = """Signal that the project is complete and ready for delivery.

CRITICAL: This tool triggers the END of the entire generation process!

Only call this when ALL of these are true:
1. NO outstanding bugs or issues
2. ALL project requirements are satisfied
3. Application is FULLY functional and usable
4. Docker setup is correct and containers run successfully
5. Application is ready for end-users

This is NOT the same as finish()!
- finish() = end current task, stay available for more work
- deliver_project() = generation complete, shutdown all agents

Args:
    confirmation: Must be exactly "CONFIRMED" to proceed
    delivery_summary: Summary of what's being delivered
    checklist: Dict with verification results
"""
    
    def __init__(self, agent: "EnvGenAgent" = None):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        self.agent = agent
        self._delivered = False
    
    def set_agent(self, agent: "EnvGenAgent"):
        """Set the agent that will use this tool."""
        self.agent = agent
    
    @property
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "confirmation": {
                        "type": "string",
                        "description": "Must be exactly 'CONFIRMED' to proceed with delivery"
                    },
                    "delivery_summary": {
                        "type": "string",
                        "description": "Summary of what is being delivered"
                    },
                    "checklist": {
                        "type": "object",
                        "description": "Verification checklist: {no_bugs: bool, requirements_met: bool, fully_functional: bool, docker_ok: bool}",
                        "properties": {
                            "no_bugs": {"type": "boolean"},
                            "requirements_met": {"type": "boolean"},
                            "fully_functional": {"type": "boolean"},
                            "docker_ok": {"type": "boolean"}
                        }
                    }
                },
                "required": ["confirmation", "delivery_summary", "checklist"]
            }
        )
    
    def execute(self, confirmation: str, delivery_summary: str, checklist: dict = None) -> ToolResult:
        # Verify confirmation
        if confirmation != "CONFIRMED":
            return ToolResult(
                success=False,
                error_message=f"Confirmation must be exactly 'CONFIRMED', got '{confirmation}'. "
                              "This is to prevent accidental project delivery."
            )
        
        # Verify checklist
        checklist = checklist or {}
        required_checks = ["no_bugs", "requirements_met", "fully_functional", "docker_ok"]
        failed_checks = []
        
        for check in required_checks:
            if not checklist.get(check, False):
                failed_checks.append(check)
        
        if failed_checks:
            return ToolResult(
                success=False,
                error_message=f"Cannot deliver project. Failed checks: {failed_checks}. "
                              "Please ensure all criteria are met before delivery."
            )
        
        # Set delivered flag
        self._delivered = True
        
        # Also set on agent if available - this triggers shutdown
        if self.agent:
            self.agent._project_delivered = True
            # Set the event that orchestrator is waiting for
            if hasattr(self.agent, '_project_delivered_event'):
                self.agent._project_delivered_event.set()
        
        return ToolResult(
            success=True,
            data={
                "delivered": True,
                "summary": delivery_summary,
                "checklist": checklist,
                "info": "Project successfully delivered! Generation process will now shutdown."
            }
        )
    
    def is_delivered(self) -> bool:
        """Check if project has been delivered."""
        return self._delivered


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "ReadMemoryBankTool",
    "FinishTool",
    "DeliverProjectTool",
]

