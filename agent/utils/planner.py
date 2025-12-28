"""
Planner Module - Task planning and decomposition

Supports:
- Task decomposition into steps
- Dependency management
- Plan execution tracking
- Plan revision
- Custom prompt templates
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4
import json
import logging

from .llm import LLM, Message, LLMConfig
from .prompt import (
    PromptTemplate, 
    PLANNER_SYSTEM_PROMPT, 
    PLANNER_TEMPLATE, 
    format_tools_for_prompt
)
from .prompt_loader import render_prompt


class StepStatus(Enum):
    """Step execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"  # Waiting for dependencies


@dataclass
class PlanStep:
    """Single step in a plan"""
    step_id: int
    description: str
    action: str  # Tool name or "think"
    action_input: dict = field(default_factory=dict)
    expected_output: str = ""
    dependencies: list[int] = field(default_factory=list)  # Step IDs this depends on
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "action": self.action,
            "action_input": self.action_input,
            "expected_output": self.expected_output,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PlanStep":
        return cls(
            step_id=data["step_id"],
            description=data["description"],
            action=data.get("action", "think"),
            action_input=data.get("action_input", {}),
            expected_output=data.get("expected_output", ""),
            dependencies=data.get("dependencies", []),
            status=StepStatus(data.get("status", "pending")),
            result=data.get("result"),
            error=data.get("error"),
        )
    
    def can_execute(self, completed_steps: set[int]) -> bool:
        """Check if all dependencies are met"""
        return all(dep in completed_steps for dep in self.dependencies)


@dataclass
class Plan:
    """Execution plan"""
    plan_id: str = field(default_factory=lambda: str(uuid4()))
    task: str = ""
    steps: list[PlanStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, running, completed, failed
    metadata: dict = field(default_factory=dict)
    
    def add_step(self, step: PlanStep) -> None:
        """Add a step to the plan"""
        self.steps.append(step)
    
    def get_step(self, step_id: int) -> Optional[PlanStep]:
        """Get step by ID"""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def get_next_steps(self) -> list[PlanStep]:
        """Get steps that are ready to execute"""
        completed_ids = {s.step_id for s in self.steps if s.status == StepStatus.COMPLETED}
        
        ready = []
        for step in self.steps:
            if step.status == StepStatus.PENDING and step.can_execute(completed_ids):
                ready.append(step)
        
        return ready
    
    def get_pending_steps(self) -> list[PlanStep]:
        """Get all pending steps"""
        return [s for s in self.steps if s.status == StepStatus.PENDING]
    
    def get_completed_steps(self) -> list[PlanStep]:
        """Get all completed steps"""
        return [s for s in self.steps if s.status == StepStatus.COMPLETED]
    
    def is_complete(self) -> bool:
        """Check if all steps are completed"""
        return all(s.status in [StepStatus.COMPLETED, StepStatus.SKIPPED] for s in self.steps)
    
    def has_failed(self) -> bool:
        """Check if any step has failed"""
        return any(s.status == StepStatus.FAILED for s in self.steps)
    
    def progress(self) -> float:
        """Get progress as percentage (0.0 - 1.0)"""
        if not self.steps:
            return 1.0
        completed = sum(1 for s in self.steps if s.status in [StepStatus.COMPLETED, StepStatus.SKIPPED])
        return completed / len(self.steps)
    
    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "task": self.task,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Plan":
        plan = cls(
            plan_id=data.get("plan_id", str(uuid4())),
            task=data.get("task", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            status=data.get("status", "pending"),
            metadata=data.get("metadata", {}),
        )
        for step_data in data.get("steps", []):
            plan.steps.append(PlanStep.from_dict(step_data))
        return plan
    
    def __str__(self) -> str:
        lines = [f"Plan: {self.task}", f"Status: {self.status}", "Steps:"]
        for step in self.steps:
            status_icon = {
                StepStatus.PENDING: "⏳",
                StepStatus.RUNNING: "🔄",
                StepStatus.COMPLETED: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.SKIPPED: "⏭️",
                StepStatus.BLOCKED: "🔒",
            }.get(step.status, "❓")
            lines.append(f"  {status_icon} {step.step_id}. {step.description}")
        return "\n".join(lines)


# Default templates (can be customized)
DEFAULT_PLANNER_SYSTEM_PROMPT = PLANNER_SYSTEM_PROMPT

DEFAULT_PLANNER_TEMPLATE = PLANNER_TEMPLATE


class Planner:
    """
    Task planner that uses LLM to decompose tasks
    
    Usage:
        # With default templates
        planner = Planner(llm_config)
        
        # With custom templates
        custom_system = "You are a specialized planner for..."
        custom_template = PromptTemplate(
            name="my_planner",
            template="Plan this: {task}...",
            variables=["task", "tools", "constraints"]
        )
        planner = Planner(
            llm_config,
            system_prompt=custom_system,
            plan_template=custom_template,
        )
        
        plan = await planner.create_plan(
            task="Build a REST API",
            tools=tool_definitions,
            constraints=["Use Python", "Include tests"]
        )
    """
    
    def __init__(
        self,
        llm_config: LLMConfig,
        system_prompt: str = None,
        plan_template: PromptTemplate = None,
    ):
        """
        Initialize Planner
        
        Args:
            llm_config: LLM configuration
            system_prompt: Custom system prompt (optional)
            plan_template: Custom planning template (optional)
        """
        self.llm = LLM(llm_config)
        self._system_prompt = system_prompt or DEFAULT_PLANNER_SYSTEM_PROMPT
        self._plan_template = plan_template or DEFAULT_PLANNER_TEMPLATE
        self._logger = logging.getLogger("Planner")
    
    @property
    def system_prompt(self) -> str:
        """Get current system prompt"""
        return self._system_prompt
    
    @system_prompt.setter
    def system_prompt(self, value: str) -> None:
        """Set custom system prompt"""
        self._system_prompt = value
    
    @property
    def plan_template(self) -> PromptTemplate:
        """Get current plan template"""
        return self._plan_template
    
    @plan_template.setter
    def plan_template(self, value: PromptTemplate) -> None:
        """Set custom plan template"""
        self._plan_template = value
    
    def set_templates(
        self,
        system_prompt: str = None,
        plan_template: PromptTemplate = None,
    ) -> None:
        """
        Set custom templates
        
        Args:
            system_prompt: Custom system prompt
            plan_template: Custom planning template
        """
        if system_prompt:
            self._system_prompt = system_prompt
        if plan_template:
            self._plan_template = plan_template
    
    def reset_templates(self) -> None:
        """Reset to default templates"""
        self._system_prompt = DEFAULT_PLANNER_SYSTEM_PROMPT
        self._plan_template = DEFAULT_PLANNER_TEMPLATE
    
    async def create_plan(
        self,
        task: str,
        tools: list[dict] = None,
        constraints: list[str] = None,
        context: str = None,
        max_steps: int = 10,
        **template_vars,
    ) -> Plan:
        """
        Create a plan for the given task
        
        Args:
            task: Task description
            tools: Available tool definitions
            constraints: Planning constraints
            context: Additional context
            max_steps: Maximum number of steps
            **template_vars: Additional variables for custom templates
            
        Returns:
            Generated plan
        """
        tools = tools or []
        constraints = constraints or []
        
        # Format tools for prompt
        tools_str = format_tools_for_prompt(tools) if tools else "No specific tools available. Use 'think' for reasoning steps."
        
        # Format constraints
        constraints_str = "\n".join(f"- {c}" for c in constraints) if constraints else "None"
        if max_steps:
            constraints_str += f"\n- Maximum {max_steps} steps"
        
        # Build template variables
        template_variables = {
            "task": task,
            "tools": tools_str,
            "constraints": constraints_str,
            **template_vars,  # Allow custom variables for custom templates
        }
        
        # Generate prompt
        prompt = self._plan_template.render(**template_variables)
        
        if context:
            prompt = f"## Additional Context\n{context}\n\n{prompt}"
        
        response = await self.llm.chat(
            prompt=prompt,
            system=self._system_prompt,
            temperature=0.3,  # Lower temperature for more consistent planning
        )
        
        # Parse response
        plan = self._parse_plan_response(response, task)
        
        return plan
    
    def _parse_plan_response(self, response: str, task: str) -> Plan:
        """Parse LLM response into Plan object"""
        plan = Plan(task=task)
        
        # Try to extract JSON from response
        try:
            # Find JSON array in response
            json_match = self._extract_json(response)
            if json_match:
                steps_data = json.loads(json_match)
                
                for step_data in steps_data:
                    step = PlanStep(
                        step_id=step_data.get("step_id", len(plan.steps) + 1),
                        description=step_data.get("description", ""),
                        action=step_data.get("action", "think"),
                        action_input=step_data.get("action_input", {}),
                        expected_output=step_data.get("expected_output", ""),
                        dependencies=step_data.get("dependencies", []),
                    )
                    plan.add_step(step)
            else:
                # Fallback: create single step
                plan.add_step(PlanStep(
                    step_id=1,
                    description=task,
                    action="think",
                    expected_output="Complete the task",
                ))
                
        except json.JSONDecodeError as e:
            self._logger.warning(f"Failed to parse plan JSON: {e}")
            # Fallback: create single step
            plan.add_step(PlanStep(
                step_id=1,
                description=task,
                action="think",
                expected_output="Complete the task",
            ))
        
        return plan
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON array from text"""
        # Try to find JSON array
        import re
        
        # Look for ```json ... ``` blocks
        json_block = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text)
        if json_block:
            return json_block.group(1)
        
        # Look for raw JSON array
        array_match = re.search(r'\[\s*\{[\s\S]*\}\s*\]', text)
        if array_match:
            return array_match.group(0)
        
        return None
    
    async def revise_plan(
        self,
        plan: Plan,
        feedback: str,
        tools: list[dict] = None,
    ) -> Plan:
        """
        Revise a plan based on feedback
        
        Args:
            plan: Current plan
            feedback: Feedback or reason for revision
            tools: Available tools
            
        Returns:
            Revised plan
        """
        tools_str = format_tools_for_prompt(tools) if tools else "Same tools as before."
        
        current_plan_str = json.dumps([s.to_dict() for s in plan.steps], indent=2)

        prompt = render_prompt(
            "planner_revise_plan.j2",
            task=plan.task,
            current_plan_json=current_plan_str,
            feedback=feedback,
            tools_str=tools_str,
        )
        
        response = await self.llm.chat(
            prompt=prompt,
            system=self._system_prompt,
            temperature=0.3,
        )
        
        revised_plan = self._parse_plan_response(response, plan.task)
        revised_plan.metadata["revised_from"] = plan.plan_id
        revised_plan.metadata["revision_reason"] = feedback
        
        return revised_plan
    
    async def expand_step(
        self,
        step: PlanStep,
        tools: list[dict] = None,
        context: str = None,
    ) -> list[PlanStep]:
        """
        Expand a step into sub-steps
        
        Args:
            step: Step to expand
            tools: Available tools
            context: Additional context
            
        Returns:
            List of sub-steps
        """
        tools_str = format_tools_for_prompt(tools) if tools else "No specific tools."

        prompt = render_prompt(
            "planner_expand_step.j2",
            description=step.description,
            expected_output=step.expected_output,
            tools_str=tools_str,
            context=context or "",
        )
        
        response = await self.llm.chat(
            prompt=prompt,
            system=self._system_prompt,
            temperature=0.3,
        )
        
        # Parse sub-steps
        sub_steps = []
        json_str = self._extract_json(response)
        
        if json_str:
            try:
                steps_data = json.loads(json_str)
                for i, step_data in enumerate(steps_data):
                    sub_step = PlanStep(
                        step_id=step.step_id * 100 + i + 1,  # e.g., step 2 -> 201, 202, 203
                        description=step_data.get("description", ""),
                        action=step_data.get("action", "think"),
                        action_input=step_data.get("action_input", {}),
                        expected_output=step_data.get("expected_output", ""),
                    )
                    sub_steps.append(sub_step)
            except json.JSONDecodeError:
                pass
        
        return sub_steps


class PlanExecutor:
    """
    Executes plans step by step
    
    Usage:
        executor = PlanExecutor(tool_registry)
        
        async for step, result in executor.execute(plan):
            print(f"Completed: {step.description}")
            print(f"Result: {result}")
    """
    
    def __init__(self, tool_executor=None):
        """
        Args:
            tool_executor: Async function that executes tools
                          signature: async def execute(action: str, action_input: dict) -> Any
        """
        self.tool_executor = tool_executor
        self._logger = logging.getLogger("PlanExecutor")
    
    async def execute(self, plan: Plan):
        """
        Execute plan steps
        
        Yields:
            (step, result) tuples
        """
        plan.status = "running"
        
        while not plan.is_complete() and not plan.has_failed():
            # Get next executable steps
            next_steps = plan.get_next_steps()
            
            if not next_steps:
                # Check for blocked steps
                pending = plan.get_pending_steps()
                if pending:
                    # All pending steps are blocked - this shouldn't happen with valid dependencies
                    self._logger.error("Plan execution stuck - circular dependencies?")
                    plan.status = "failed"
                    break
                continue
            
            # Execute steps (could be parallelized for independent steps)
            for step in next_steps:
                step.status = StepStatus.RUNNING
                step.started_at = datetime.now()
                
                try:
                    if self.tool_executor:
                        result = await self.tool_executor(step.action, step.action_input)
                    else:
                        result = f"Executed: {step.action}"
                    
                    step.result = result
                    step.status = StepStatus.COMPLETED
                    step.completed_at = datetime.now()
                    
                    yield step, result
                    
                except Exception as e:
                    step.error = str(e)
                    step.status = StepStatus.FAILED
                    step.completed_at = datetime.now()
                    self._logger.error(f"Step {step.step_id} failed: {e}")
                    
                    yield step, None
        
        # Update plan status
        if plan.has_failed():
            plan.status = "failed"
        elif plan.is_complete():
            plan.status = "completed"
    
    async def execute_step(self, step: PlanStep) -> Any:
        """Execute a single step"""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()
        
        try:
            if self.tool_executor:
                result = await self.tool_executor(step.action, step.action_input)
            else:
                result = f"Executed: {step.action}"
            
            step.result = result
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now()
            
            return result
            
        except Exception as e:
            step.error = str(e)
            step.status = StepStatus.FAILED
            step.completed_at = datetime.now()
            raise


# Helper function to create custom planner template
def create_planner_template(
    name: str,
    template: str,
    variables: list[str] = None,
    description: str = "",
) -> PromptTemplate:
    """
    Helper to create a custom planner template
    
    Args:
        name: Template name
        template: Template string with {variable} placeholders
        variables: List of variable names (auto-detected if not provided)
        description: Template description
        
    Returns:
        PromptTemplate instance
        
    Example:
        template = create_planner_template(
            name="simple_planner",
            template='''
            Task: {task}
            
            Create a simple step-by-step plan.
            Available actions: {tools}
            
            Respond with JSON array of steps.
            ''',
        )
    """
    return PromptTemplate(
        name=name,
        template=template.strip(),
        description=description,
        variables=variables or [],
    )
