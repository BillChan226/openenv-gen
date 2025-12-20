"""
Coordinator - Orchestrates User Agent and Code Agent interaction

Main entry point for environment generation.
"""

import json
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

# Ensure paths are set up for both direct and module execution
_llm_gen_dir = Path(__file__).parent.parent.absolute()
if str(_llm_gen_dir) not in sys.path:
    sys.path.insert(0, str(_llm_gen_dir))
_agents_dir = _llm_gen_dir.parent.parent.absolute()
if str(_agents_dir) not in sys.path:
    sys.path.insert(0, str(_agents_dir))

from utils.config import AgentConfig, LLMConfig
from utils.llm import LLM
from utils.tool import ToolRegistry

from tools import get_all_tools
from utils.message import Task, Issue, TaskResult, VerifyResult
from specs import PHASES

from agents.user_agent import UserAgent
from agents.code_agent import CodeAgent


@dataclass
class GenerationResult:
    """Result of environment generation."""
    success: bool
    project_path: str
    tasks_completed: int
    tasks_failed: int
    issues_fixed: int
    duration: float
    summary: str


@dataclass
class Checkpoint:
    """Checkpoint for resuming generation."""
    timestamp: str
    current_phase: str
    completed_phases: List[str]
    pending_tasks: List[Dict]
    issues_pending: List[Dict]
    
    def save(self, path: Path):
        """Save checkpoint to file."""
        with open(path, "w") as f:
            json.dump({
                "timestamp": self.timestamp,
                "current_phase": self.current_phase,
                "completed_phases": self.completed_phases,
                "pending_tasks": self.pending_tasks,
                "issues_pending": self.issues_pending,
            }, f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> Optional["Checkpoint"]:
        """Load checkpoint from file."""
        if not path.exists():
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            return cls(**data)
        except (json.JSONDecodeError, KeyError):
            return None


class Coordinator:
    """
    Coordinator - Manages the interaction between User Agent and Code Agent.
    
    Workflow:
    1. User Agent plans tasks
    2. For each task:
       a. Code Agent executes
       b. User Agent verifies
       c. If failed, User Agent creates issue
       d. Code Agent fixes
       e. Repeat until passed or max attempts
    3. Final verification
    """
    
    MAX_FIX_ATTEMPTS = 3
    
    def __init__(
        self,
        llm_config: LLMConfig,
        output_dir: Path,
        enable_checkpoints: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.enable_checkpoints = enable_checkpoints
        self.checkpoint_path = self.output_dir / ".checkpoint.json"
        
        # Create LLM client
        self.llm = LLM(llm_config)
        
        # Setup logging
        self._logger = logging.getLogger("coordinator")
        
        # Create tools
        self._tools = self._create_tools()
        
        # Create agents
        self._user_agent = self._create_user_agent()
        self._code_agent = self._create_code_agent()
        
        # State
        self._current_checkpoint: Optional[Checkpoint] = None
    
    def _create_tools(self) -> ToolRegistry:
        """Create tool registry with all tools."""
        registry = ToolRegistry()
        
        for tool in get_all_tools(
            output_dir=str(self.output_dir),
            work_dir=str(self.output_dir),
        ):
            registry.register(tool)
        
        self._logger.info(f"Registered {len(registry)} tools")
        return registry
    
    def _create_user_agent(self) -> UserAgent:
        """Create User Agent."""
        config = AgentConfig(
            agent_id="user_agent",
            agent_name="UserAgent",
        )
        return UserAgent(
            config=config,
            llm=self.llm,
            output_dir=self.output_dir,
            tools=self._tools,
        )
    
    def _create_code_agent(self) -> CodeAgent:
        """Create Code Agent."""
        config = AgentConfig(
            agent_id="code_agent",
            agent_name="CodeAgent",
        )
        return CodeAgent(
            config=config,
            llm=self.llm,
            output_dir=self.output_dir,
            tools=self._tools,
        )
    
    # ==================== Main Entry Point ====================
    
    async def run(
        self,
        goal: str,
        requirements: List[str],
        resume: bool = True,
    ) -> GenerationResult:
        """
        Run the environment generation.
        
        Args:
            goal: High-level goal description
            requirements: List of specific requirements
            resume: Whether to resume from checkpoint
        
        Returns:
            GenerationResult with status and summary
        """
        start_time = datetime.now()
        self._logger.info(f"Starting generation: {goal[:100]}...")
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check for existing checkpoint
        if resume and self.enable_checkpoints:
            self._current_checkpoint = Checkpoint.load(self.checkpoint_path)
            if self._current_checkpoint:
                self._logger.info(f"Resuming from phase: {self._current_checkpoint.current_phase}")
        
        # Plan tasks
        if self._current_checkpoint and self._current_checkpoint.pending_tasks:
            tasks = [Task.from_dict(t) for t in self._current_checkpoint.pending_tasks]
            self._logger.info(f"Loaded {len(tasks)} pending tasks from checkpoint")
        else:
            tasks = await self._user_agent.plan_tasks(goal, requirements)
        
        # Execute tasks
        completed = 0
        failed = 0
        issues_fixed = 0
        
        for task in tasks:
            self._logger.info(f"\n{'='*50}")
            self._logger.info(f"Task: {task.id} - {task.description[:50]}...")
            self._logger.info(f"{'='*50}")
            
            # Skip if already completed
            if self._current_checkpoint and task.id in self._current_checkpoint.completed_phases:
                self._logger.info(f"Skipping (already completed)")
                completed += 1
                continue
            
            # Execute task
            result = await self._execute_task_with_verification(task)
            
            if result.status.value == "completed":
                completed += 1
                issues_fixed += len(result.issues)  # Issues that were fixed during execution
            else:
                failed += 1
            
            # Save checkpoint
            if self.enable_checkpoints:
                self._save_checkpoint(task.id, tasks, completed)
        
        # Final verification
        final_success = await self._final_verification()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return GenerationResult(
            success=final_success and failed == 0,
            project_path=str(self.output_dir),
            tasks_completed=completed,
            tasks_failed=failed,
            issues_fixed=issues_fixed,
            duration=duration,
            summary=f"Generated environment in {duration:.1f}s: {completed} completed, {failed} failed",
        )
    
    # ==================== Task Execution ====================
    
    async def _execute_task_with_verification(self, task: Task) -> TaskResult:
        """
        Execute a task with verification and fix loop.
        
        Args:
            task: Task to execute
        
        Returns:
            Final TaskResult
        """
        # Execute task
        result = await self._code_agent.execute_task(task)
        self._logger.info(f"  Result: {result.status.value} - {result.summary}")
        
        # Verify result
        verify = await self._user_agent.verify_task_result(
            task=task,
            files_created=result.files_created,
            commands_run=result.commands,
        )
        
        self._logger.info(f"  Verification: {'PASS' if verify.passed else 'FAIL'}")
        
        # Fix loop if failed
        attempt = 0
        while not verify.passed and attempt < self.MAX_FIX_ATTEMPTS:
            attempt += 1
            self._logger.info(f"  Fix attempt {attempt}/{self.MAX_FIX_ATTEMPTS}")
            
            # Create issue
            issue = await self._user_agent.create_issue(
                task_id=task.id,
                problems=verify.problems,
            )
            
            # Fix issue
            fix_result = await self._code_agent.fix_issue(issue)
            self._logger.info(f"    Fixed: {fix_result.fixed} - {fix_result.notes}")
            
            if fix_result.fixed:
                result.issues.append(f"Fixed: {issue.title}")
            
            # Re-verify
            verify = await self._user_agent.verify_task_result(
                task=task,
                files_created=result.files_created + fix_result.changes,
                commands_run=result.commands,
            )
            
            self._logger.info(f"    Re-verification: {'PASS' if verify.passed else 'FAIL'}")
        
        # Update result status based on final verification
        if verify.passed:
            result.status = TaskResult.TaskStatus.COMPLETED if hasattr(TaskResult, 'TaskStatus') else result.status
        
        return result
    
    # ==================== Final Verification ====================
    
    async def _final_verification(self) -> bool:
        """
        Run final verification of the complete project.
        
        User Agent autonomously decides what final verifications are needed
        based on the original goal (e.g., "runnable environment" -> test Docker).
        
        Returns:
            True if all checks pass
        """
        self._logger.info("\n" + "="*50)
        self._logger.info("FINAL VERIFICATION")
        self._logger.info("="*50)
        
        # Create a final verification task for User Agent
        from utils.message import Task, TaskType
        
        final_task = Task(
            id="final_verification",
            type=TaskType.VERIFICATION,
            description=f"Verify the complete {self.output_dir.name} environment is ready and runnable",
            target_directory="",
            requirements=[
                "All required files exist",
                "Docker containers can be built",
                "Services can start successfully",
                "API endpoints respond correctly",
                "Frontend loads without errors",
            ],
            acceptance_criteria=[
                "docker-compose build succeeds",
                "docker-compose up starts all services",
                "Backend health check passes",
                "Frontend is accessible",
            ],
        )
        
        # List all generated files
        import subprocess
        result = subprocess.run(
            ["find", str(self.output_dir), "-type", "f"],
            capture_output=True, text=True
        )
        all_files = [
            f.replace(str(self.output_dir) + "/", "") 
            for f in result.stdout.strip().split("\n") if f
        ]
        
        # Let User Agent verify with full tool access
        verify_result = await self._user_agent.verify_task_result(
            task=final_task,
            files_created=all_files,
            commands_run=[],
        )
        
        # Log results
        for check in verify_result.checks_performed:
            if check in verify_result.passed_checks:
                self._logger.info(f"  ✅ {check}")
            else:
                self._logger.info(f"  ❌ {check}")
        
        if verify_result.problems:
            self._logger.info("\nProblems found:")
            for problem in verify_result.problems:
                self._logger.info(f"  - {problem}")
        
        self._logger.info(f"\nFinal Result: {'PASS' if verify_result.passed else 'FAIL'}")
        self._logger.info(f"Summary: {verify_result.summary}")
        
        return verify_result.passed
    
    # ==================== Checkpoints ====================
    
    def _save_checkpoint(self, completed_phase: str, all_tasks: List[Task], completed_count: int):
        """Save current progress to checkpoint."""
        completed_phases = []
        pending_tasks = []
        
        for i, task in enumerate(all_tasks):
            if i < completed_count:
                completed_phases.append(task.id)
            else:
                pending_tasks.append(task.to_dict())
        
        checkpoint = Checkpoint(
            timestamp=datetime.now().isoformat(),
            current_phase=completed_phase,
            completed_phases=completed_phases,
            pending_tasks=pending_tasks,
            issues_pending=[],
        )
        
        checkpoint.save(self.checkpoint_path)
        self._logger.debug(f"Checkpoint saved: {completed_phase}")

