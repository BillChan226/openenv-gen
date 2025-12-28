"""
Reasoning Tools - Agent thinking and planning tools

Provides:
- ThinkTool: Deep analysis and reasoning without action
- PlanTool: Create and track implementation plans with checklist
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

IMPORTANT: You cannot call finish() until ALL plan items are marked complete!

Actions:
- "create": Create a new plan with items (replaces any existing plan)
- "status": Check current plan status and what's left to do
- "complete": Mark a specific item as complete

Creating a plan:
    plan(action="create", items=["Create api.js", "Create Dashboard.jsx", "Create App.jsx"])

Checking status:
    plan(action="status")

Marking item complete:
    plan(action="complete", item_index=0)  # Mark first item complete
    plan(action="complete", item_text="Create api.js")  # Or by text match

The plan is enforced - finish() will fail if incomplete items remain!
"""
    
    # Class-level storage for plan state (shared across instances)
    _current_plan: list = []
    _plan_completed: list = []
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
    
    @classmethod
    def reset(cls):
        """Reset plan state (called at start of each task)."""
        cls._current_plan = []
        cls._plan_completed = []
    
    @classmethod
    def get_plan_status(cls) -> dict:
        """Get current plan status for finish verification."""
        total = len(cls._current_plan)
        completed = sum(cls._plan_completed)
        incomplete = [
            cls._current_plan[i] 
            for i in range(total) 
            if not cls._plan_completed[i]
        ]
        return {
            "has_plan": total > 0,
            "total": total,
            "completed": completed,
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
                        "description": "Action to perform: create new plan, check status, or mark item complete"
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
            
            PlanTool._current_plan = items
            PlanTool._plan_completed = [False] * len(items)
            
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
            status = PlanTool.get_plan_status()
            
            if not status["has_plan"]:
                return ToolResult(
                    success=True,
                    data={"info": "No plan created yet. Use plan(action='create', items=[...]) to create one."}
                )
            
            checklist_lines = []
            for i, item in enumerate(PlanTool._current_plan):
                mark = "[x]" if PlanTool._plan_completed[i] else "[ ]"
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
            if not PlanTool._current_plan:
                return ToolResult(
                    success=False,
                    error_message="No plan exists. Create one first with plan(action='create', items=[...])"
                )
            
            # Find item by index or text
            target_index = None
            
            if item_index is not None:
                if 0 <= item_index < len(PlanTool._current_plan):
                    target_index = item_index
                else:
                    return ToolResult(
                        success=False,
                        error_message=f"Invalid item_index {item_index}. Valid range: 0-{len(PlanTool._current_plan)-1}"
                    )
            elif item_text:
                # Find by text match (partial match allowed)
                for i, item in enumerate(PlanTool._current_plan):
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
            
            if PlanTool._plan_completed[target_index]:
                return ToolResult(
                    success=True,
                    data={"info": f"Item {target_index+1} was already marked complete: {PlanTool._current_plan[target_index]}"}
                )
            
            PlanTool._plan_completed[target_index] = True
            status = PlanTool.get_plan_status()
            
            return ToolResult(
                success=True,
                data={
                    "action": "marked_complete",
                    "item": PlanTool._current_plan[target_index],
                    "progress": f"{status['completed']}/{status['total']}",
                    "can_finish": status["all_complete"],
                    "info": f"Marked complete: {PlanTool._current_plan[target_index]}. Progress: {status['completed']}/{status['total']}"
                }
            )
        
        else:
            return ToolResult(
                success=False,
                error_message=f"Unknown action '{action}'. Use 'create', 'status', or 'complete'."
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
    "PlanTool",
    "VerifyPlanTool",
]

