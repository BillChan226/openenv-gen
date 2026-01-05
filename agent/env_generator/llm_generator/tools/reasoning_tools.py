"""
Reasoning Tools - Agent thinking and planning tools

Provides:
- ThinkTool: Deep analysis and reasoning without ac- PlanTool: Create and track implementation plans with checklist
- VerifyPlanTool: Verification test plan tracking for QA

These tools support agent self-reflection and structured task management.
"""

from ._base import (
    BaseTool,
    ToolResult,
    ToolCategory,
    create_tool_param,
)


# ============================================================================
# Think Tool
# ============================================================================

class ThinkTool(BaseTool):
    """
    Think/reason without taking action.
    
    Use for deep analysis, debugging, brainstorming - NOT for planning.
    For planning with tracked tasks, use plan() instead.
    """
    
    NAME = "think"
    
    DESCRIPTION = """Use this tool to think through complex problems.

The thought is recorded but no action is taken.
Useful for:
- Deep analysis of a problem
- Debugging and understanding errors
- Brainstorming different approaches
- Reasoning about implementation details

For creating a tracked plan with checklist, use plan() instead.

Example:
    think "The error says X, which means Y. I should try Z."
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
                    "thought": {
                        "type": "string",
                        "description": "Your reasoning and analysis"
                    }
                },
                "required": ["thought"]
            }
        )
    
    def execute(self, thought: str) -> ToolResult:
        return ToolResult(
            success=True,
            data={"thought": thought, "info": f"Thought recorded: {thought[:200]}..."}
        )


# ============================================================================
# Wait Tool
# ============================================================================

class GetTimeTool(BaseTool):
    """
    Get current time and elapsed time since generation started.
    
    Helps agents understand how much time has passed and make time-based decisions.
    """
    
    NAME = "get_time"
    
    DESCRIPTION = """Get current time and how long the generation has been running.

Use this to:
- Check how much time has passed
- Decide if you've been waiting long enough
- Know the current time for logging/debugging

Returns:
- current_time: Current time (e.g., "14:30:45")
- elapsed_minutes: Minutes since generation started
- elapsed_formatted: Human-readable elapsed time (e.g., "5 minutes 30 seconds")

Example:
    get_time()  # Returns {"current_time": "14:30:45", "elapsed_minutes": 5.5, ...}
"""
    
    # Class variable to store generation start time
    _start_time = None
    
    @classmethod
    def set_start_time(cls):
        """Called at generation start to record the start time."""
        from datetime import datetime
        cls._start_time = datetime.now()
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        # Initialize start time if not set
        if GetTimeTool._start_time is None:
            GetTimeTool.set_start_time()
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={},
            required=[]
        )
    
    def execute(self) -> ToolResult:
        from datetime import datetime
        
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_datetime = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate elapsed time
        if GetTimeTool._start_time:
            elapsed = now - GetTimeTool._start_time
            elapsed_seconds = elapsed.total_seconds()
            elapsed_minutes = elapsed_seconds / 60
            
            # Format elapsed time
            mins = int(elapsed_seconds // 60)
            secs = int(elapsed_seconds % 60)
            if mins > 0:
                elapsed_formatted = f"{mins} minute{'s' if mins != 1 else ''} {secs} second{'s' if secs != 1 else ''}"
            else:
                elapsed_formatted = f"{secs} second{'s' if secs != 1 else ''}"
        else:
            elapsed_minutes = 0
            elapsed_formatted = "unknown"
        
        return ToolResult(
            success=True,
            data={
                "current_time": current_time,
                "current_datetime": current_datetime,
                "elapsed_minutes": round(elapsed_minutes, 1),
                "elapsed_formatted": elapsed_formatted,
                "info": f"Current time: {current_time}, Elapsed: {elapsed_formatted}"
            }
        )


class WaitTool(BaseTool):
    """
    Wait/pause for a specified duration.
    
    Use this when you need to wait for other agents to complete their work,
    or when you're in a monitoring/polling loop and want to avoid rapid API calls.
    """
    
    NAME = "wait"
    
    DESCRIPTION = """Wait for a specified number of seconds before continuing.

Use this tool when:
- Waiting for other agents to complete their work
- In a monitoring loop (e.g., periodically checking inbox)
- After sending messages, giving agents time to respond
- Avoiding rapid polling that wastes API tokens

Example:
    wait(seconds=30)  # Wait 30 seconds before next action
    wait(seconds=10, reason="Waiting for backend agent to process request")

Recommended wait times:
- Quick check: 5-10 seconds
- Waiting for agent response: 15-30 seconds
- Waiting for major work: 60+ seconds
"""
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "seconds": {
                    "type": "integer",
                    "description": "Number of seconds to wait (1-300)",
                    "minimum": 1,
                    "maximum": 300
                },
                "reason": {
                    "type": "string",
                    "description": "Optional: Why you're waiting (for logging)"
                }
            },
            required=["seconds"]
        )
    
    async def execute(self, seconds: int, reason: str = None) -> ToolResult:
        import asyncio
        
        # Clamp to reasonable range
        seconds = max(1, min(300, seconds))
        
        # Use asyncio.sleep so event loop can process urgent messages during wait
        await asyncio.sleep(seconds)
        
        info = f"Waited {seconds} seconds"
        if reason:
            info += f" ({reason})"
        
        return ToolResult(
            success=True,
            data={"waited_seconds": seconds, "reason": reason, "info": info}
        )


# ============================================================================
# Plan Tool
# ============================================================================

class PlanTool(BaseTool):
    """
    Create and track a plan with checklist items.
    
    Unlike think(), plan creates a TRACKED list of tasks that must be completed
    before finish() can be called. Use plan() to define what you will do,
    then use it again to check progress or mark items complete.
    """
    
    NAME = "plan"
    
    DESCRIPTION = """Create or manage a tracked plan with checklist items.

Plans are YOUR tracking tool - you can have multiple plans during your work.
finish() does NOT require plan completion - it's for agent state transition.

Actions:
- "create": Create a new plan with items (replaces any existing plan)
- "status": Check current plan status and progress
- "complete": Mark a specific item as complete
- "add": Add new items to existing plan
- "remove": Remove an item from plan (by index or text)
- "update": Update an item's text (by index)
- "clear": Clear the current plan entirely (start fresh)

Creating a plan:
    plan(action="create", items=["Create api.js", "Create Dashboard.jsx", "Create App.jsx"])

Checking status:
    plan(action="status")

Marking item complete:
    plan(action="complete", item_index=0)  # Mark first item complete
    plan(action="complete", item_text="Create api.js")  # Or by text match

Adding items to existing plan:
    plan(action="add", items=["Create Login.jsx", "Create Profile.jsx"])

Removing an item:
    plan(action="remove", item_index=2)  # Remove by index
    plan(action="remove", item_text="Create Profile.jsx")  # Or by text

Updating an item:
    plan(action="update", item_index=0, item_text="Create api.js with auth")

Clearing plan (to start a new one):
    plan(action="clear")  # Removes all items, ready for new plan
"""
    
    # Class-level registry of instances by agent_id (for static lookups)
    _instances: dict = {}
    
    def __init__(self, agent_id: str = None):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        self.agent_id = agent_id or "default"
        # Instance-level plan state - each PlanTool instance has its own plan
        self._current_plan: list = []
        self._plan_completed: list = []
        # Register this instance
        PlanTool._instances[self.agent_id] = self
    
    @classmethod
    def get_instance(cls, agent_id: str = None) -> "PlanTool":
        """Get PlanTool instance for a specific agent_id."""
        agent_id = agent_id or "default"
        if agent_id not in cls._instances:
            # Create a new instance if not found
            cls._instances[agent_id] = PlanTool(agent_id=agent_id)
        return cls._instances[agent_id]
    
    def reset(self):
        """Reset plan state (called at start of each task)."""
        self._current_plan = []
        self._plan_completed = []
    
    def get_plan_status(self) -> dict:
        """Get current plan status for finish verification."""
        total = len(self._current_plan)
        completed = sum(self._plan_completed) if self._plan_completed else 0
        incomplete = [
            self._current_plan[i] 
            for i in range(total) 
            if not self._plan_completed[i]
        ]
        return {
            "has_plan": total > 0,
            "total": total,
            "completed": completed,
            "incomplete": incomplete,
            "all_complete": total > 0 and completed == total,
            "agent_id": self.agent_id,
        }
    
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
                    "action": {
                        "type": "string",
                        "enum": ["create", "status", "complete", "add", "remove", "update", "clear"],
                        "description": "Action: create, status, complete, add, remove, update, or clear"
                    },
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of plan items (required for 'create' action)"
                    },
                    "item_index": {
                        "type": "integer",
                        "description": "Index of item to mark complete (for 'complete' action)"
                    },
                    "item_text": {
                        "type": "string",
                        "description": "Text of item to mark complete (alternative to item_index)"
                    }
                },
                "required": ["action"]
            }
        )
    
    def execute(self, action: str, items: list = None, item_index: int = None, item_text: str = None) -> ToolResult:
        if action == "create":
            if not items or len(items) == 0:
                return ToolResult(
                    success=False,
                    error_message="'items' is required for 'create' action. Provide a list of plan items."
                )
            
            self._current_plan = items
            self._plan_completed = [False] * len(items)
            
            checklist = "\n".join(f"  [ ] {i+1}. {item}" for i, item in enumerate(items))
            return ToolResult(
                success=True,
                data={
                    "action": "created",
                    "total_items": len(items),
                    "checklist": checklist,
                    "info": f"Plan created with {len(items)} items. You MUST complete all items before calling finish()."
                }
            )
        
        elif action == "status":
            status = self.get_plan_status()
            
            if not status["has_plan"]:
                return ToolResult(
                    success=True,
                    data={"info": "No plan created yet. Use plan(action='create', items=[...]) to create one."}
                )
            
            checklist_lines = []
            for i, item in enumerate(self._current_plan):
                mark = "[x]" if self._plan_completed[i] else "[ ]"
                checklist_lines.append(f"  {mark} {i+1}. {item}")
            
            return ToolResult(
                success=True,
                data={
                    "total": status["total"],
                    "completed": status["completed"],
                    "remaining": status["total"] - status["completed"],
                    "checklist": "\n".join(checklist_lines),
                    "can_finish": status["all_complete"],
                    "info": f"Progress: {status['completed']}/{status['total']} items complete."
                }
            )
        
        elif action == "complete":
            if not self._current_plan:
                return ToolResult(
                    success=False,
                    error_message="No plan exists. Create one first with plan(action='create', items=[...])"
                )
            
            # Find item by index or text
            target_index = None
            
            if item_index is not None:
                if 0 <= item_index < len(self._current_plan):
                    target_index = item_index
                else:
                    return ToolResult(
                        success=False,
                        error_message=f"Invalid item_index {item_index}. Valid range: 0-{len(self._current_plan)-1}"
                    )
            elif item_text:
                # Find by text match (partial match allowed)
                for i, item in enumerate(self._current_plan):
                    if item_text.lower() in item.lower():
                        target_index = i
                        break
                
                if target_index is None:
                    return ToolResult(
                        success=False,
                        error_message=f"Could not find item matching '{item_text}'"
                    )
            else:
                return ToolResult(
                    success=False,
                    error_message="Provide either 'item_index' or 'item_text' to mark an item complete."
                )
            
            if self._plan_completed[target_index]:
                return ToolResult(
                    success=True,
                    data={"info": f"Item {target_index+1} was already marked complete: {self._current_plan[target_index]}"}
                )
            
            self._plan_completed[target_index] = True
            status = self.get_plan_status()
            
            return ToolResult(
                success=True,
                data={
                    "action": "marked_complete",
                    "item": self._current_plan[target_index],
                    "progress": f"{status['completed']}/{status['total']}",
                    "can_finish": status["all_complete"],
                    "info": f"Marked complete: {self._current_plan[target_index]}. Progress: {status['completed']}/{status['total']}"
                }
            )
        
        elif action == "add":
            if not items or len(items) == 0:
                return ToolResult(
                    success=False,
                    error_message="'items' is required for 'add' action. Provide a list of new items to add."
                )
            
            if not self._current_plan:
                return ToolResult(
                    success=False,
                    error_message="No plan exists. Use plan(action='create', items=[...]) first."
                )
            
            # Add new items (all start as incomplete)
            start_index = len(self._current_plan)
            self._current_plan.extend(items)
            self._plan_completed.extend([False] * len(items))
            
            added_items = "\n".join(f"  [ ] {start_index + i + 1}. {item}" for i, item in enumerate(items))
            status = self.get_plan_status()
            
            return ToolResult(
                success=True,
                data={
                    "action": "added",
                    "added_count": len(items),
                    "new_items": added_items,
                    "total_items": len(self._current_plan),
                    "info": f"Added {len(items)} items to plan. Total: {status['total']} items, {status['completed']} complete."
                }
            )
        
        elif action == "remove":
            if not self._current_plan:
                return ToolResult(
                    success=False,
                    error_message="No plan exists. Nothing to remove."
                )
            
            # Find item by index or text
            target_index = None
            
            if item_index is not None:
                if 0 <= item_index < len(self._current_plan):
                    target_index = item_index
                else:
                    return ToolResult(
                        success=False,
                        error_message=f"Invalid item_index {item_index}. Valid range: 0-{len(self._current_plan)-1}"
                    )
            elif item_text:
                for i, item in enumerate(self._current_plan):
                    if item_text.lower() in item.lower():
                        target_index = i
                        break
                
                if target_index is None:
                    return ToolResult(
                        success=False,
                        error_message=f"Could not find item matching '{item_text}'"
                    )
            else:
                return ToolResult(
                    success=False,
                    error_message="Provide either 'item_index' or 'item_text' to remove an item."
                )
            
            removed_item = self._current_plan.pop(target_index)
            self._plan_completed.pop(target_index)
            status = self.get_plan_status()
            
            return ToolResult(
                success=True,
                data={
                    "action": "removed",
                    "removed_item": removed_item,
                    "total_items": len(self._current_plan),
                    "info": f"Removed: '{removed_item}'. Remaining: {status['total']} items, {status['completed']} complete."
                }
            )
        
        elif action == "update":
            if not self._current_plan:
                return ToolResult(
                    success=False,
                    error_message="No plan exists. Nothing to update."
                )
            
            if item_index is None:
                return ToolResult(
                    success=False,
                    error_message="'item_index' is required for 'update' action."
                )
            
            if not item_text:
                return ToolResult(
                    success=False,
                    error_message="'item_text' is required for 'update' action (the new text)."
                )
            
            if not (0 <= item_index < len(self._current_plan)):
                return ToolResult(
                    success=False,
                    error_message=f"Invalid item_index {item_index}. Valid range: 0-{len(self._current_plan)-1}"
                )
            
            old_text = self._current_plan[item_index]
            self._current_plan[item_index] = item_text
            
            return ToolResult(
                success=True,
                data={
                    "action": "updated",
                    "item_index": item_index,
                    "old_text": old_text,
                    "new_text": item_text,
                    "info": f"Updated item {item_index + 1}: '{old_text}' -> '{item_text}'"
                }
            )
        
        elif action == "clear":
            old_count = len(self._current_plan)
            self._current_plan = []
            self._plan_completed = []
            
            return ToolResult(
                success=True,
                data={
                    "action": "cleared",
                    "cleared_items": old_count,
                    "info": f"Plan cleared ({old_count} items removed). Ready to create a new plan."
                }
            )
        
        else:
            return ToolResult(
                success=False,
                error_message=f"Unknown action '{action}'. Use 'create', 'status', 'complete', 'add', 'remove', 'update', or 'clear'."
            )


# ============================================================================
# Verify Plan Tool (for User Agent QA)
# ============================================================================

class VerifyPlanTool(BaseTool):
    """
    Verification plan tracker for UserAgent QA.

    This is intentionally separate from PlanTool (CodeAgent implementation plan).
    It tracks *verification test cases* so the verifier can ensure coverage
    (e.g., System menu toggle, navigation back/forward, Create Issue flow).
    """

    NAME = "verify_plan"

    DESCRIPTION = """Track a verification test plan as a checklist.

Use this during verification (frontend/final verification) to ensure you:
- Create a test plan table/checklist
- Execute each test and mark it complete

Actions:
- create: set a new verification checklist
- status: show current completion status
- complete: mark a checklist item complete

Examples:
    verify_plan(action="create", items=["[P0] NAV-001: Switch pages and return works", ...])
    verify_plan(action="status")
    verify_plan(action="complete", item_text="NAV-001")
"""

    _current_plan: list = []
    _plan_completed: list = []
    _plan_results: list = []  # "pass", "fail", "skip"

    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)

    @classmethod
    def reset(cls):
        """Reset verification plan state."""
        cls._current_plan = []
        cls._plan_completed = []
        cls._plan_results = []

    @classmethod
    def get_plan_status(cls) -> dict:
        """Get current verification plan status."""
        total = len(cls._current_plan)
        completed = sum(cls._plan_completed)
        passed = cls._plan_results.count("pass")
        failed = cls._plan_results.count("fail")
        skipped = cls._plan_results.count("skip")
        incomplete = [
            cls._current_plan[i]
            for i in range(total)
            if not cls._plan_completed[i]
        ]
        return {
            "has_plan": total > 0,
            "total": total,
            "completed": completed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "incomplete": incomplete,
            "all_complete": total > 0 and completed == total,
        }

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
                    "action": {
                        "type": "string",
                        "enum": ["create", "status", "complete"],
                        "description": "Action to perform"
                    },
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of test items (for 'create')"
                    },
                    "item_index": {
                        "type": "integer",
                        "description": "Index of item to mark complete"
                    },
                    "item_text": {
                        "type": "string",
                        "description": "Text/ID of item to mark complete"
                    },
                    "result": {
                        "type": "string",
                        "enum": ["pass", "fail", "skip"],
                        "description": "Result of the test case"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notes about the test result"
                    }
                },
                "required": ["action"]
            }
        )

    def execute(
        self,
        action: str,
        items: list = None,
        item_index: int = None,
        item_text: str = None,
        result: str = "pass",
        notes: str = None
    ) -> ToolResult:
        
        if action == "create":
            if not items:
                return ToolResult(
                    success=False,
                    error_message="'items' required for 'create' action."
                )
            VerifyPlanTool._current_plan = items
            VerifyPlanTool._plan_completed = [False] * len(items)
            VerifyPlanTool._plan_results = [""] * len(items)
            checklist = "\n".join(f"  [ ] {i+1}. {item}" for i, item in enumerate(items))
            return ToolResult(
                success=True,
                data={
                    "action": "created",
                    "total_items": len(items),
                    "checklist": checklist,
                    "info": f"Verification plan created with {len(items)} test cases."
                }
            )

        elif action == "status":
            status = VerifyPlanTool.get_plan_status()
            if not status["has_plan"]:
                return ToolResult(
                    success=True,
                    data={"info": "No verification plan. Use verify_plan(action='create', items=[...])."}
                )
            lines = []
            for i, item in enumerate(VerifyPlanTool._current_plan):
                if VerifyPlanTool._plan_completed[i]:
                    res = VerifyPlanTool._plan_results[i]
                    mark = "[PASS]" if res == "pass" else "[FAIL]" if res == "fail" else "[SKIP]"
                else:
                    mark = "[    ]"
                lines.append(f"  {mark} {i+1}. {item}")
            return ToolResult(
                success=True,
                data={
                    "total": status["total"],
                    "completed": status["completed"],
                    "passed": status["passed"],
                    "failed": status["failed"],
                    "skipped": status["skipped"],
                    "checklist": "\n".join(lines),
                    "info": f"Progress: {status['completed']}/{status['total']} ({status['passed']} pass, {status['failed']} fail)"
                }
            )

        elif action == "complete":
            if not VerifyPlanTool._current_plan:
                return ToolResult(
                    success=False,
                    error_message="No verification plan exists."
                )
            target = None
            if item_index is not None and 0 <= item_index < len(VerifyPlanTool._current_plan):
                target = item_index
            elif item_text:
                for i, item in enumerate(VerifyPlanTool._current_plan):
                    if item_text.lower() in item.lower():
                        target = i
                        break
            if target is None:
                return ToolResult(
                    success=False,
                    error_message="Could not find item to complete."
                )
            VerifyPlanTool._plan_completed[target] = True
            VerifyPlanTool._plan_results[target] = result
            status = VerifyPlanTool.get_plan_status()
            return ToolResult(
                success=True,
                data={
                    "action": "marked_complete",
                    "item": VerifyPlanTool._current_plan[target],
                    "result": result,
                    "notes": notes,
                    "progress": f"{status['completed']}/{status['total']}",
                    "info": f"[{result.upper()}] {VerifyPlanTool._current_plan[target]}"
                }
            )

        return ToolResult(
            success=False,
            error_message=f"Unknown action '{action}'."
        )


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "ThinkTool",
    "GetTimeTool",
    "WaitTool",
    "PlanTool",
    "VerifyPlanTool",
]

