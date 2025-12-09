"""
Planning Agent Module - Agent with built-in planning capabilities

Provides:
- PlanningAgent: Agent that can create, track, and execute plans
- Automatic plan state tracking
- Plan history management
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4
import logging

from .base_agent import BaseAgent, AgentRole
from .config import AgentConfig
from .message import TaskMessage, ResultMessage, create_result_message
from .planner import Planner, Plan, PlanStep, PlanExecutor, StepStatus
from .reasoning import ReActEngine, ReasoningResult
from .memory import AgentMemory
from .tool import ToolRegistry


@dataclass
class PlanRecord:
    """Record of a plan execution"""
    plan: Plan
    task_id: str
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    success: bool = False
    final_result: Any = None


class PlanningAgent(BaseAgent):
    """
    Agent with built-in planning and reasoning capabilities
    
    Features:
    - Automatic plan creation for complex tasks
    - Plan execution tracking
    - Plan history
    - Integrated reasoning (ReAct)
    - Memory integration
    
    Usage:
        class MyAgent(PlanningAgent):
            async def execute_step(self, step: PlanStep) -> Any:
                # Implement step execution
                if step.action == "search":
                    return await self.tools.get("search")(**step.action_input)
                ...
        
        agent = MyAgent(config)
        await agent.initialize()
        await agent.start()
        
        # Agent automatically creates and executes plans
    """
    
    def __init__(
        self,
        config: AgentConfig,
        role: AgentRole = AgentRole.WORKER,
        enable_reasoning: bool = True,
    ):
        super().__init__(config, role)
        
        # Planning components
        self._planner: Optional[Planner] = None
        self._reasoner: Optional[ReActEngine] = None
        self._memory = AgentMemory(
            short_term_size=config.memory.short_term_memory_size,
            long_term_size=1000,
        )
        
        # Plan tracking
        self._current_plan: Optional[Plan] = None
        self._plan_history: list[PlanRecord] = []
        self._enable_reasoning = enable_reasoning
        
        # Configuration
        self._auto_plan = True  # Automatically create plans for tasks
        self._min_steps_for_plan = 1  # Create plan if task seems to need multiple steps
    
    async def on_initialize(self) -> None:
        """Initialize planning components"""
        await super().on_initialize()
        
        # Initialize planner
        self._planner = Planner(self._config.llm)
        
        # Initialize reasoner
        if self._enable_reasoning:
            self._reasoner = ReActEngine(
                self._config.llm,
                self._tools,
                memory=self._memory,
            )
        
        self._logger.info(f"Planning agent initialized with planner and reasoner")
    
    # ===== Plan Properties =====
    
    @property
    def current_plan(self) -> Optional[Plan]:
        """Get the current active plan"""
        return self._current_plan
    
    @property
    def plan_history(self) -> list[PlanRecord]:
        """Get plan execution history"""
        return self._plan_history.copy()
    
    @property
    def planner(self) -> Optional[Planner]:
        """Get the planner instance"""
        return self._planner
    
    @property
    def reasoner(self) -> Optional[ReActEngine]:
        """Get the reasoner instance"""
        return self._reasoner
    
    @property
    def memory(self) -> AgentMemory:
        """Get agent memory"""
        return self._memory
    
    # ===== Plan Status Methods =====
    
    def get_plan_status(self) -> dict:
        """
        Get current plan status
        
        Returns:
            Dict with plan status information
        """
        if not self._current_plan:
            return {
                "has_plan": False,
                "message": "No active plan",
            }
        
        plan = self._current_plan
        return {
            "has_plan": True,
            "plan_id": plan.plan_id,
            "task": plan.task,
            "status": plan.status,
            "progress": plan.progress(),
            "progress_percent": f"{plan.progress() * 100:.1f}%",
            "total_steps": len(plan.steps),
            "completed_steps": len(plan.get_completed_steps()),
            "pending_steps": len(plan.get_pending_steps()),
            "failed_steps": len([s for s in plan.steps if s.status == StepStatus.FAILED]),
            "is_complete": plan.is_complete(),
            "has_failed": plan.has_failed(),
            "next_steps": [
                {"step_id": s.step_id, "description": s.description}
                for s in plan.get_next_steps()
            ],
        }
    
    def get_plan_details(self) -> Optional[dict]:
        """
        Get detailed plan information
        
        Returns:
            Complete plan details or None if no plan
        """
        if not self._current_plan:
            return None
        
        plan = self._current_plan
        return {
            "plan_id": plan.plan_id,
            "task": plan.task,
            "status": plan.status,
            "progress": plan.progress(),
            "created_at": plan.created_at.isoformat(),
            "steps": [
                {
                    "step_id": s.step_id,
                    "description": s.description,
                    "action": s.action,
                    "status": s.status.value,
                    "status_icon": self._get_status_icon(s.status),
                    "result": s.result,
                    "error": s.error,
                    "dependencies": s.dependencies,
                    "can_execute": s.can_execute({
                        x.step_id for x in plan.steps 
                        if x.status == StepStatus.COMPLETED
                    }),
                }
                for s in plan.steps
            ],
            "metadata": plan.metadata,
        }
    
    def print_plan(self) -> str:
        """
        Get formatted plan string for display
        
        Returns:
            Formatted plan string
        """
        if not self._current_plan:
            return "No active plan."
        
        return str(self._current_plan)
    
    def _get_status_icon(self, status: StepStatus) -> str:
        """Get emoji icon for status"""
        return {
            StepStatus.PENDING: "⏳",
            StepStatus.RUNNING: "🔄",
            StepStatus.COMPLETED: "✅",
            StepStatus.FAILED: "❌",
            StepStatus.SKIPPED: "⏭️",
            StepStatus.BLOCKED: "🔒",
        }.get(status, "❓")
    
    # ===== Plan Management =====
    
    async def create_plan(
        self,
        task: str,
        constraints: list[str] = None,
        context: str = None,
    ) -> Plan:
        """
        Create a new plan for a task
        
        Args:
            task: Task description
            constraints: Planning constraints
            context: Additional context
            
        Returns:
            Created plan
        """
        if not self._planner:
            raise RuntimeError("Planner not initialized")
        
        tools = self._tools.to_openai_functions()
        
        plan = await self._planner.create_plan(
            task=task,
            tools=tools,
            constraints=constraints,
            context=context,
        )
        
        self._current_plan = plan
        self._logger.info(f"Created plan with {len(plan.steps)} steps for: {task}")
        
        # Store in memory
        self._memory.remember(
            f"Created plan for: {task}",
            memory_type="short",
            metadata={"plan_id": plan.plan_id},
        )
        
        return plan
    
    async def execute_plan(self, plan: Plan = None) -> bool:
        """
        Execute a plan step by step
        
        Args:
            plan: Plan to execute (uses current_plan if not provided)
            
        Returns:
            Whether plan completed successfully
        """
        plan = plan or self._current_plan
        if not plan:
            self._logger.warning("No plan to execute")
            return False
        
        self._current_plan = plan
        plan.status = "running"
        
        record = PlanRecord(plan=plan, task_id=str(uuid4()))
        
        try:
            while not plan.is_complete() and not plan.has_failed():
                next_steps = plan.get_next_steps()
                
                if not next_steps:
                    if plan.get_pending_steps():
                        self._logger.error("Plan stuck - possible circular dependency")
                        plan.status = "failed"
                        break
                    continue
                
                for step in next_steps:
                    await self._execute_plan_step(step)
            
            # Record completion
            record.completed_at = datetime.now()
            record.success = plan.is_complete() and not plan.has_failed()
            
            if record.success:
                plan.status = "completed"
                # Collect results from all steps
                record.final_result = {
                    s.step_id: s.result for s in plan.steps
                }
            else:
                plan.status = "failed"
            
            self._plan_history.append(record)
            
            # Store in memory
            self._memory.remember(
                f"Plan {'completed' if record.success else 'failed'}: {plan.task}",
                memory_type="long",
                importance=0.8 if record.success else 0.9,
            )
            
            return record.success
            
        except Exception as e:
            self._logger.error(f"Plan execution error: {e}")
            plan.status = "failed"
            record.completed_at = datetime.now()
            record.success = False
            self._plan_history.append(record)
            return False
    
    async def _execute_plan_step(self, step: PlanStep) -> Any:
        """Execute a single plan step"""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()
        
        self._logger.info(f"Executing step {step.step_id}: {step.description}")
        
        try:
            # Call subclass implementation
            result = await self.execute_step(step)
            
            step.result = result
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now()
            
            self._logger.info(f"Step {step.step_id} completed")
            
            # Store in working memory
            self._memory.working.add_step(
                thought=f"Executing: {step.description}",
                action=step.action,
                action_input=step.action_input,
                observation=str(result)[:500],  # Truncate long results
            )
            
            return result
            
        except Exception as e:
            step.error = str(e)
            step.status = StepStatus.FAILED
            step.completed_at = datetime.now()
            
            self._logger.error(f"Step {step.step_id} failed: {e}")
            raise
    
    async def execute_step(self, step: PlanStep) -> Any:
        """
        Execute a single step - subclasses should override this
        
        Default implementation uses tools or reasoning
        
        Args:
            step: Step to execute
            
        Returns:
            Step result
        """
        action = step.action.lower()
        
        if action == "think":
            # Use reasoning for thinking steps
            if self._reasoner:
                result = await self._reasoner.run(
                    task=step.description,
                    context=f"This is part of the plan: {self._current_plan.task if self._current_plan else 'unknown'}",
                )
                return result.answer
            return f"Thought about: {step.description}"
        
        elif action == "finish":
            return step.action_input
        
        else:
            # Try to execute as tool
            tool = self._tools.get(action)
            if tool:
                kwargs = step.action_input if isinstance(step.action_input, dict) else {}
                result = await tool(**kwargs)
                return result.data if result.success else f"Error: {result.error_message}"
            
            # Fallback: use reasoning
            if self._reasoner:
                result = await self._reasoner.run(
                    task=f"{action}: {step.description}",
                )
                return result.answer
            
            return f"Executed: {action}"
    
    async def revise_current_plan(self, feedback: str) -> Plan:
        """
        Revise the current plan based on feedback
        
        Args:
            feedback: Reason for revision
            
        Returns:
            Revised plan
        """
        if not self._current_plan or not self._planner:
            raise RuntimeError("No plan to revise")
        
        tools = self._tools.to_openai_functions()
        
        revised = await self._planner.revise_plan(
            self._current_plan,
            feedback,
            tools,
        )
        
        self._current_plan = revised
        self._logger.info(f"Plan revised: {feedback}")
        
        return revised
    
    # ===== Task Processing =====
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """
        Process task with planning
        
        Automatically creates and executes a plan for complex tasks.
        """
        task_description = task.task_description or task.task_name
        task_params = task.task_params
        
        # Set working memory task
        self._memory.working.set_task(task.task_id)
        self._memory.working.set("task_name", task.task_name)
        self._memory.working.set("task_params", task_params)
        
        try:
            if self._auto_plan:
                # Create and execute plan
                plan = await self.create_plan(
                    task=task_description,
                    constraints=task_params.get("constraints", []),
                    context=task_params.get("context"),
                )
                
                success = await self.execute_plan(plan)
                
                if success:
                    # Compile results
                    result_data = {
                        "plan_id": plan.plan_id,
                        "status": "completed",
                        "steps_completed": len(plan.get_completed_steps()),
                        "results": {s.step_id: s.result for s in plan.steps},
                    }
                else:
                    result_data = {
                        "plan_id": plan.plan_id,
                        "status": "failed",
                        "error": self._get_plan_error(),
                    }
                
                return create_result_message(
                    source_id=self.agent_id,
                    target_id=task.header.source_agent_id,
                    task_id=task.task_id,
                    success=success,
                    result_data=result_data,
                )
            
            else:
                # Direct reasoning without planning
                if self._reasoner:
                    result = await self._reasoner.run(task_description)
                    return create_result_message(
                        source_id=self.agent_id,
                        target_id=task.header.source_agent_id,
                        task_id=task.task_id,
                        success=result.success,
                        result_data=result.answer,
                        error_message=result.error,
                    )
                
                return create_result_message(
                    source_id=self.agent_id,
                    target_id=task.header.source_agent_id,
                    task_id=task.task_id,
                    success=False,
                    error_message="No reasoning capability available",
                )
                
        except Exception as e:
            self._logger.error(f"Task processing error: {e}")
            return create_result_message(
                source_id=self.agent_id,
                target_id=task.header.source_agent_id,
                task_id=task.task_id,
                success=False,
                error_message=str(e),
            )
    
    def _get_plan_error(self) -> str:
        """Get error message from failed plan"""
        if not self._current_plan:
            return "Unknown error"
        
        for step in self._current_plan.steps:
            if step.status == StepStatus.FAILED:
                return f"Step {step.step_id} failed: {step.error}"
        
        return "Plan did not complete"
    
    # ===== Status Override =====
    
    def get_status(self) -> dict:
        """Get agent status including plan information"""
        status = super().get_status()
        status["plan"] = self.get_plan_status()
        status["plan_history_count"] = len(self._plan_history)
        status["memory_stats"] = self._memory.stats()
        return status

