"""
Agent Interaction Tools - Tools for agent-to-agent communication and task completion

Provides:
- ReadMemoryBankTool: Read project context from Memory Bank
- RequestReviewTool: Request User Agent to review plans
- AskUserAgentTool: Ask User Agent for help/clarification
- FinishTool: Signal task completion

These tools enable Code Agent to interact with User Agent and access shared context.
"""

from ._base import (
    BaseTool,
    ToolResult,
    ToolCategory,
    create_tool_param,
    Workspace,
)

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
# Request Review Tool
# ============================================================================

class RequestReviewTool(BaseTool):
    """
    Request User Agent to review and approve the current plan.
    
    Use this after creating a plan with plan() to get User Agent's feedback
    before starting implementation.
    """
    
    NAME = "request_review"
    
    DESCRIPTION = """Request User Agent to review your plan before execution.

Use this after plan(action="create", ...) to get feedback from User Agent.
User Agent will:
- Evaluate if the plan covers all requirements
- Suggest additions or modifications
- Approve or reject the plan

The review result will tell you whether to proceed or revise your plan.

Example:
    plan(action="create", items=["Create api.js", "Create Dashboard.jsx", ...])
    request_review(subject="plan", message="Please review my implementation plan")
"""
    
    # Class-level callback for User Agent interaction
    _review_callback = None
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
    
    @classmethod
    def set_review_callback(cls, callback):
        """Set the callback function for User Agent review."""
        cls._review_callback = callback
    
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
                    "subject": {
                        "type": "string",
                        "enum": ["plan", "design", "implementation"],
                        "description": "What to review: plan, design decision, or implementation approach"
                    },
                    "message": {
                        "type": "string",
                        "description": "Your question or request for the User Agent"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context (e.g., the plan details, code snippet, etc.)"
                    }
                },
                "required": ["subject", "message"]
            }
        )
    
    def execute(self, subject: str, message: str, context: str = None) -> ToolResult:
        # Get current plan if reviewing plan
        from .reasoning_tools import PlanTool
        
        plan_info = ""
        if subject == "plan":
            plan_status = PlanTool.get_plan_status()
            if plan_status["has_plan"]:
                items = "\n".join(f"  {i+1}. {item}" for i, item in enumerate(PlanTool._current_plan))
                plan_info = f"\n\nCurrent Plan:\n{items}"
        
        # Build review request
        review_request = {
            "type": "review_request",
            "subject": subject,
            "message": message,
            "context": (context or "") + plan_info,
        }
        
        # If callback is set, call User Agent synchronously
        if RequestReviewTool._review_callback:
            try:
                response = RequestReviewTool._review_callback(review_request)
                return ToolResult(
                    success=True,
                    data={
                        "approved": response.get("approved", False),
                        "feedback": response.get("feedback", ""),
                        "suggestions": response.get("suggestions", []),
                        "info": f"Review received: {'APPROVED' if response.get('approved') else 'NEEDS REVISION'}"
                    }
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    error_message=f"Error during review: {e}"
                )
        
        # No callback - return pending status (will be handled by agent loop)
        return ToolResult(
            success=True,
            data={
                "status": "pending_review",
                "request": review_request,
                "info": "Review request submitted. Waiting for User Agent response."
            }
        )


# ============================================================================
# Ask User Agent Tool
# ============================================================================

class AskUserAgentTool(BaseTool):
    """
    Ask User Agent for help, clarification, or guidance during execution.
    
    Use when you're uncertain about requirements, need design decisions,
    or want to confirm an approach before implementing.
    """
    
    NAME = "ask_user_agent"
    
    DESCRIPTION = """Ask User Agent for help or clarification.

Use this when you:
- Are unsure about a requirement
- Need to make a design decision
- Want to confirm your understanding
- Need help solving a complex problem

The User Agent will respond with guidance or answers.

Examples:
    ask_user_agent(question="Should the API use JWT or session-based auth?")
    ask_user_agent(question="The requirement says 'dashboard'. What data should it show?")
    ask_user_agent(question="I'm getting this error: X. How should I handle it?", context="error details...")
"""
    
    # Class-level callback for User Agent interaction
    _ask_callback = None
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
    
    @classmethod
    def set_ask_callback(cls, callback):
        """Set the callback function for User Agent questions."""
        cls._ask_callback = callback
    
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
                    "question": {
                        "type": "string",
                        "description": "Your question for the User Agent"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context (code, error message, etc.)"
                    },
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "If asking for a choice, provide the options"
                    }
                },
                "required": ["question"]
            }
        )
    
    def execute(self, question: str, context: str = None, options: list = None) -> ToolResult:
        ask_request = {
            "type": "ask_request",
            "question": question,
            "context": context,
            "options": options,
        }
        
        # If callback is set, call User Agent
        if AskUserAgentTool._ask_callback:
            try:
                response = AskUserAgentTool._ask_callback(ask_request)
                return ToolResult(
                    success=True,
                    data={
                        "answer": response.get("answer", ""),
                        "guidance": response.get("guidance", ""),
                        "choice": response.get("choice"),  # If options were provided
                        "info": f"User Agent response: {response.get('answer', '')[:200]}..."
                    }
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    error_message=f"Error asking User Agent: {e}"
                )
        
        # No callback - return pending status
        return ToolResult(
            success=True,
            data={
                "status": "pending_response",
                "request": ask_request,
                "info": "Question submitted. Waiting for User Agent response."
            }
        )


# ============================================================================
# Finish Tool
# ============================================================================

class FinishTool(BaseTool):
    """
    Signal task completion.
    
    IMPORTANT: If you have created a plan with plan(), all items must be
    marked complete before finish() will succeed!
    """
    
    NAME = "finish"
    
    DESCRIPTION = """Use when the task is complete.

IMPORTANT: If you created a plan with plan(), ALL plan items must be marked
complete before you can finish! Use plan(action="status") to check progress.

Provide a summary of what was done and any outputs.
"""
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
    
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
                    "outputs": {
                        "type": "object",
                        "description": "Any output data"
                    }
                },
                "required": ["message"]
            }
        )
    
    def execute(self, message: str, outputs: dict = None) -> ToolResult:
        # Check if there's an incomplete plan
        from .reasoning_tools import PlanTool
        
        plan_status = PlanTool.get_plan_status()
        
        if plan_status["has_plan"] and not plan_status["all_complete"]:
            incomplete_items = "\n".join(f"  - {item}" for item in plan_status["incomplete"])
            return ToolResult(
                success=False,
                error_message=f"CANNOT FINISH: You have {len(plan_status['incomplete'])} incomplete plan items:\n{incomplete_items}\n\n"
                             f"Either complete these items and mark them done with plan(action='complete', ...), "
                             f"or update your plan if items are no longer needed."
            )
        
        return ToolResult(
            success=True,
            data={"outputs": outputs or {}, "finished": True, "info": f"Task completed: {message}"}
        )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "ReadMemoryBankTool",
    "RequestReviewTool",
    "AskUserAgentTool",
    "FinishTool",
]

