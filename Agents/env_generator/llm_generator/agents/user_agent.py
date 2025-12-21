"""
User Agent - Simulated user / Product Manager / QA

Responsibilities:
- Understand the goal and break it into tasks
- Delegate tasks to Code Agent
- Verify results and report issues
- Decide when the project is complete
"""

import json
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader

# Ensure paths are set up for both direct and module execution
_llm_gen_dir = Path(__file__).parent.parent.absolute()
if str(_llm_gen_dir) not in sys.path:
    sys.path.insert(0, str(_llm_gen_dir))
_agents_dir = _llm_gen_dir.parent.parent.absolute()
if str(_agents_dir) not in sys.path:
    sys.path.insert(0, str(_agents_dir))

from utils.base_agent import BaseAgent, AgentRole
from utils.config import AgentConfig
from utils.llm import LLM
from utils.tool import ToolRegistry, ToolResult

from utils.message import Task, TaskType, FileSpec, Issue, IssueSeverity, VerifyResult
from specs import PROJECT_STRUCTURE, PHASES, get_phase_spec
from workspace import Workspace


class UserAgent(BaseAgent):
    """
    User Agent - Acts as simulated user, PM, and QA.
    
    Does NOT generate code. Instead:
    1. Plans tasks based on goal
    2. Sends tasks to Code Agent
    3. Verifies results
    4. Reports issues
    """
    
    def __init__(
        self,
        config: AgentConfig,
        llm: LLM,
        workspace: Workspace = None,
        output_dir: Path = None,  # Legacy, use workspace
        tools: Optional[ToolRegistry] = None,
    ):
        super().__init__(config, role=AgentRole.SUPERVISOR)
        
        self.llm = llm
        
        # Support both workspace (new) and output_dir (legacy)
        if workspace:
            self.workspace = workspace
        elif output_dir:
            self.workspace = Workspace(output_dir)
        else:
            self.workspace = Workspace(Path.cwd())
        
        # For backward compatibility
        self.output_dir = self.workspace.root
        
        # Override tools if provided
        if tools:
            self._tools = tools
        
        # Setup Jinja2 for prompts
        prompt_dir = Path(__file__).parent.parent / "prompts"
        self.jinja = Environment(
            loader=FileSystemLoader(str(prompt_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        self._logger = logging.getLogger("agent.user")
    
    # ==================== Task Planning ====================
    
    async def plan_tasks(self, goal: str, requirements: List[str]) -> List[Task]:
        """
        Break down the goal into ordered tasks.
        
        Args:
            goal: The high-level goal
            requirements: Specific requirements
        
        Returns:
            List of Task objects for Code Agent
        """
        self._logger.info(f"Planning tasks for goal: {goal[:100]}...")
        
        # Render the planning prompt
        prompt = self.jinja.get_template("user/plan_tasks.j2").render(
            goal=goal,
            requirements="\n".join(f"- {r}" for r in requirements),
        )
        
        # Call LLM
        response = await self.llm.chat_with_response(
            prompt=prompt,
            system=self._get_system_prompt(),
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        
        # Parse response
        try:
            data = json.loads(response.content)
            tasks = []
            
            for task_data in data.get("tasks", []):
                task = Task(
                    id=task_data["id"],
                    type=TaskType(task_data["type"]),
                    description=task_data["description"],
                    requirements=task_data.get("requirements", []),
                    target_directory=task_data.get("target_directory", ""),
                    file_specs=[
                        FileSpec(
                            path=f["path"],
                            purpose=f["purpose"],
                            requirements=f.get("requirements", []),
                        )
                        for f in task_data.get("file_specs", [])
                    ],
                    acceptance_criteria=task_data.get("acceptance_criteria", []),
                )
                tasks.append(task)
            
            self._logger.info(f"Planned {len(tasks)} tasks")
            return tasks
            
        except (json.JSONDecodeError, KeyError) as e:
            self._logger.error(f"Failed to parse task plan: {e}")
            return self._create_default_tasks(goal, requirements)
    
    def _create_default_tasks(self, goal: str, requirements: List[str]) -> List[Task]:
        """Create default task list based on standard phases."""
        tasks = []
        
        for phase in PHASES:
            spec = get_phase_spec(phase["id"])
            task = Task(
                id=phase["id"],
                type=phase["type"],
                description=f"{phase['description']} for: {goal}",
                requirements=requirements,
                target_directory=phase["target_directory"],
                acceptance_criteria=[
                    f"All files in {phase['target_directory']} are created",
                    "No syntax errors",
                    "Follows project structure",
                ],
            )
            tasks.append(task)
        
        return tasks
    
    # ==================== Verification ====================
    
    async def verify_task_result(
        self,
        task: Task,
        files_created: List[str],
        commands_run: List[Dict],
    ) -> VerifyResult:
        """
        Verify that a task was completed correctly.
        
        User Agent autonomously decides what verification is needed based on:
        - Task type and description
        - Acceptance criteria
        - Whether "runnable" or "testable" is implied
        
        Args:
            task: The task that was executed
            files_created: List of files created
            commands_run: List of commands and their results
        
        Returns:
            VerifyResult with pass/fail and issues
        """
        self._logger.info(f"Verifying task: {task.id}")
        
        # Build context for LLM verification
        result_context = {
            "files_created": files_created,
            "commands": commands_run,
            "issues": [],
        }
        
        # Render verification prompt
        prompt = self.jinja.get_template("user/verify_result.j2").render(
            task=task,
            result=result_context,
        )
        
        # Let LLM decide what verifications to perform and execute them
        from utils.llm import Message
        
        messages = [Message.user(prompt)]
        
        max_steps = 50  # Allow sufficient verification steps
        step = 0
        
        while step < max_steps:
            step += 1
            
            # Get LLM decision with tool access
            response = await self.llm.chat_messages(
                messages=messages,
                temperature=0.3,
                tools=self._tools.to_openai_tools() if self._tools else None,
            )
            
            if not response:
                break
            
            # Check for tool calls - LLM wants to verify something
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                
                # Parse tool call
                if isinstance(tool_call, dict):
                    tool_name = tool_call.get("function", {}).get("name", "")
                    tool_args_str = tool_call.get("function", {}).get("arguments", "{}")
                    tool_id = tool_call.get("id", "")
                else:
                    tool_name = tool_call.function.name
                    tool_args_str = tool_call.function.arguments
                    tool_id = tool_call.id
                
                import json
                try:
                    tool_args = json.loads(tool_args_str) if tool_args_str else {}
                except json.JSONDecodeError:
                    tool_args = {}
                
                self._logger.info(f"  Verify step {step}: {tool_name}")
                
                # Execute tool
                tool_result = await self._execute_verify_tool(tool_name, tool_args)
                
                # Add to conversation using Message objects
                tool_calls_data = [{"id": tool_id, "type": "function", "function": {"name": tool_name, "arguments": tool_args_str}}]
                messages.append(Message.assistant(content=None, tool_calls=tool_calls_data))
                messages.append(Message.tool(tool_call_id=tool_id, content=str(tool_result)))
            else:
                # LLM returned final verdict
                content = response.content if hasattr(response, 'content') else str(response)
                
                # Parse JSON response
                try:
                    # Extract JSON from response
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        data = json.loads(json_match.group())
                        return VerifyResult(
                            task_id=task.id,
                            passed=data.get("passed", False),
                            checks_performed=data.get("checks_performed", []),
                            passed_checks=data.get("passed_checks", []),
                            failed_checks=data.get("failed_checks", []),
                            problems=data.get("problems", []),
                            summary=data.get("summary", "Verification complete"),
                        )
                except (json.JSONDecodeError, AttributeError) as e:
                    self._logger.warning(f"Failed to parse verify response: {e}")
                
                # Fallback: basic checks
                break
        
        # Fallback to basic file check if LLM verification didn't work
        return self._basic_verify(task, files_created, commands_run)
    
    async def _execute_verify_tool(self, tool_name: str, tool_args: Dict) -> str:
        """Execute a tool for verification purposes."""
        if not self._tools:
            return "No tools available"
        
        tool = self._tools.get(tool_name)
        if not tool:
            return f"Tool {tool_name} not found"
        
        try:
            # Handle path resolution for file tools using full resolve_path logic
            if "path" in tool_args:
                tool_args["path"] = self._resolve_path(tool_args["path"])
            if "file_path" in tool_args:
                tool_args["file_path"] = self._resolve_path(tool_args["file_path"])
            
            # Must use **tool_args to unpack as keyword arguments
            result = await tool(**tool_args)
            return str(result.data) if result.success else f"Error: {result.error_message}"
        except Exception as e:
            return f"Tool execution error: {e}"
    
    def _resolve_path(self, path: str) -> str:
        """
        Resolve a path relative to output_dir, avoiding double concatenation.
        
        Handles cases where LLM might return:
        - Absolute paths: /full/path/to/file.js
        - Relative paths: app/backend/src/file.js
        - Paths with project name: atlassian_home/app/backend/src/file.js
        - Paths with full output_dir: env_generator/generated/atlassian_home/app/file.js
        - Already full paths that contain output_dir
        """
        if not path:
            return str(self.output_dir)
        
        # If already absolute, check for duplication
        if path.startswith("/"):
            output_dir_str = str(self.output_dir)
            # Check if path contains output_dir followed by output_dir again (duplication)
            double_pattern = f"{output_dir_str}/{output_dir_str}"
            if double_pattern in path or f"{self.output_dir.name}/{self.output_dir.name}" in path:
                # Fix duplication by finding the last occurrence of output_dir
                idx = path.rfind(output_dir_str)
                if idx > 0:
                    path = path[idx:]
            return path
        
        output_dir_str = str(self.output_dir)
        project_name = self.output_dir.name
        
        # Strip any leading output_dir or project_name prefix to get clean relative path
        clean_path = path
        
        # Remove full output_dir prefix if present (multiple times if needed)
        while True:
            if clean_path.startswith(output_dir_str + "/"):
                clean_path = clean_path[len(output_dir_str) + 1:]
            elif clean_path.startswith(output_dir_str):
                clean_path = clean_path[len(output_dir_str):]
                if clean_path.startswith("/"):
                    clean_path = clean_path[1:]
            else:
                break
        
        # Remove project name prefix if present (e.g., "atlassian_home/app/..." -> "app/...")
        while True:
            if clean_path.startswith(project_name + "/"):
                clean_path = clean_path[len(project_name) + 1:]
            elif clean_path == project_name:
                clean_path = ""
                break
            else:
                break
        
        # Check for "env_generator/generated/project_name" pattern
        # This happens when LLM includes the relative path from workspace root
        relative_output_pattern = f"env_generator/generated/{project_name}"
        if clean_path.startswith(relative_output_pattern + "/"):
            clean_path = clean_path[len(relative_output_pattern) + 1:]
        elif clean_path.startswith(relative_output_pattern):
            clean_path = clean_path[len(relative_output_pattern):]
            if clean_path.startswith("/"):
                clean_path = clean_path[1:]
        
        # Now join with output_dir
        if clean_path:
            return str(self.output_dir / clean_path)
        else:
            return str(self.output_dir)
    
    def _basic_verify(
        self,
        task: Task,
        files_created: List[str],
        commands_run: List[Dict],
    ) -> VerifyResult:
        """Fallback basic verification when LLM verification fails."""
        checks_performed = ["files_created"]
        passed_checks = []
        failed_checks = []
        problems = []
        
        if files_created:
            passed_checks.append("files_created")
        else:
            failed_checks.append("files_created")
            problems.append("No files were created")
        
        passed = len(failed_checks) == 0
        
        return VerifyResult(
            task_id=task.id,
            passed=passed,
            checks_performed=checks_performed,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            problems=problems,
            summary=f"Basic check: {'PASSED' if passed else 'FAILED'}",
        )
    
    # ==================== Issue Creation ====================
    
    async def create_issue(
        self,
        task_id: str,
        problems: List[str],
        error_logs: Optional[str] = None,
    ) -> Issue:
        """
        Create an issue for Code Agent to fix.
        
        Args:
            task_id: The task ID this relates to
            problems: List of problems found
            error_logs: Optional error logs
        
        Returns:
            Issue object
        """
        self._logger.info(f"Creating issue for task {task_id}: {problems[0][:50]}...")
        
        # Use LLM to create a well-structured issue
        prompt = self.jinja.get_template("user/create_issue.j2").render(
            task_id=task_id,
            passed=False,
            failed_checks=problems,
            problems=problems,
            error_logs=error_logs,
        )
        
        response = await self.llm.chat_with_response(
            prompt=prompt,
            system=self._get_system_prompt(),
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        
        try:
            data = json.loads(response.content)
            return Issue.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            self._logger.error(f"Failed to parse issue: {e}")
            # Create a simple issue
            return Issue(
                id=f"issue_{task_id}_001",
                task_id=task_id,
                severity=IssueSeverity.ERROR,
                title=problems[0][:100] if problems else "Unknown issue",
                description="\n".join(problems),
                error_message=error_logs,
            )
    
    # ==================== Helpers ====================
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for User Agent."""
        return self.jinja.get_template("user/system.j2").render(
            project_name=self.output_dir.name,
            tools_description=self._get_tools_description(),
        )
    
    def _get_tools_description(self) -> str:
        """Get description of available tools."""
        tools = [
            "- project_structure(): View current project tree",
            "- list_generated_files(): List all generated files",
            "- view(path): Read file content",
            "- execute_bash(command): Run shell command",
            "- test_api(url, method): Test API endpoint",
        ]
        return "\n".join(tools)
    
    # Required abstract method
    async def process_task(self, task):
        """Process a task message - not used directly, use plan_tasks/verify instead."""
        pass

