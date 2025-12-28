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
import asyncio
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
from memory import GeneratorMemory


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
        # Enable stuck detection to catch infinite loops
        super().__init__(config, role=AgentRole.SUPERVISOR, enable_stuck_detection=False)
        
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
        
        # Memory system - similar to CodeAgent
        self._memory = GeneratorMemory(
            llm=self.llm,
            short_term_size=50,  # Smaller than CodeAgent
            long_term_size=200,
            condenser_max_size=40,  # More aggressive condensing
        )
    
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
        
        # Step 1: Select reference images for this project
        selected_images = await self._select_reference_images(goal, requirements)
        if selected_images:
            self._logger.info(f"Selected {len(selected_images)} reference images")
        
        # Render the planning prompt with reference images
        prompt = self.jinja.get_template("user/plan_tasks.j2").render(
            goal=goal,
            requirements="\n".join(f"- {r}" for r in requirements),
            reference_images=selected_images,
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
                # Get task-specific reference images from LLM selection
                task_images = task_data.get("reference_images", [])
                # If no task-specific images, use all selected images for design/frontend tasks
                if not task_images and task_data["type"] in ["design", "frontend"]:
                    task_images = selected_images
                
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
                    reference_images=task_images,
                    acceptance_criteria=task_data.get("acceptance_criteria", []),
                )
                tasks.append(task)
            
            self._logger.info(f"Planned {len(tasks)} tasks")
            return tasks
            
        except (json.JSONDecodeError, KeyError) as e:
            self._logger.error(f"Failed to parse task plan: {e}")
            return self._create_default_tasks(goal, requirements, selected_images)
    
    def _create_default_tasks(self, goal: str, requirements: List[str], selected_images: List[Dict] = None) -> List[Task]:
        """Create default task list based on standard phases."""
        tasks = []
        selected_images = selected_images or []
        
        for phase in PHASES:
            spec = get_phase_spec(phase["id"])
            # Add reference images for design and frontend phases
            task_images = selected_images if phase["type"].value in ["design", "frontend"] else []
            
            task = Task(
                id=phase["id"],
                type=phase["type"],
                description=f"{phase['description']} for: {goal}",
                requirements=requirements,
                target_directory=phase["target_directory"],
                reference_images=task_images,
                acceptance_criteria=[
                    f"All files in {phase['target_directory']} are created",
                    "No syntax errors",
                    "Follows project structure",
                ],
            )
            tasks.append(task)
        
        return tasks
    
    async def _select_reference_images(self, goal: str, requirements: List[str]) -> List[Dict[str, str]]:
        """
        Select relevant reference images from the screenshot library.
        
        Returns list of dicts: [{path, description, purpose}]
        """
        from tools.file_tools import ListReferenceImagesTool, CopyReferenceImageTool
        
        # Get list tool
        list_tool = ListReferenceImagesTool(workspace=self.workspace)
        
        # List all available images
        result = list_tool.execute()
        if not result.success:
            self._logger.warning(f"Failed to list reference images: {result.error_message}")
            return []
        
        available_images = result.data.get("projects", {})
        if not available_images:
            self._logger.info("No reference images available")
            return []
        
        # Format available images for LLM
        image_list = []
        for project, images in available_images.items():
            for img in images:
                image_list.append({
                    "path": f"{project}/{img['name']}",
                    "size": img["size"],
                    "type": img["type"]
                })
        
        if not image_list:
            return []
        
        self._logger.info(f"Found {len(image_list)} reference images in library")
        
        # Ask LLM to select relevant images (prompt is in template)
        prompt = self.jinja.get_template("user/select_reference_images.j2").render(
            goal=goal,
            requirements=requirements,
            image_list_json=json.dumps(image_list, indent=2),
        )
        
        try:
            response = await self.llm.chat_with_response(
                prompt=prompt,
                system="You are a design assistant selecting reference images for web development.",
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            
            data = json.loads(response.content)
            selected = data.get("selected_images", [])
            
            if not selected:
                self._logger.info("LLM selected no reference images")
                return []
            
            # Copy selected images to workspace and update paths
            copy_tool = CopyReferenceImageTool(workspace=self.workspace)
            copied_images = []
            
            for img in selected:
                source_path = img.get("path", "")
                purpose = img.get("purpose", "")
                
                # Copy to workspace
                copy_result = copy_tool.execute(source=source_path)
                if copy_result.success:
                    workspace_path = copy_result.data.get("destination", "")
                    copied_images.append({
                        "path": workspace_path,
                        "source": source_path,
                        "purpose": purpose,
                        "description": f"Reference image: {purpose}"
                    })
                    self._logger.info(f"Copied reference image: {source_path} -> {workspace_path}")
                else:
                    self._logger.warning(f"Failed to copy {source_path}: {copy_result.error_message}")
            
            return copied_images
            
        except Exception as e:
            self._logger.error(f"Failed to select reference images: {e}")
            return []
    
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

        # Before running tool-based verification, generate and log a short test plan table.
        # This improves coverage for UI regressions (e.g., menus that can't be closed, missing Create Issue).
        if task.type.value in ["frontend", "verification"]:
            # Reset verify_plan state for this verification run
            try:
                vp_tool = self._tools.get("verify_plan") if self._tools else None
                if vp_tool:
                    await vp_tool(action="reset")
            except Exception:
                pass

            plan = await self._generate_verification_test_plan(task, result_context)
            if plan:
                result_context["verification_plan"] = plan
                # Also create a tracked checklist in verify_plan so the verifier must complete it.
                try:
                    items = []
                    for t in (plan.get("tests") or [])[:18]:
                        pr = (t.get("priority") or "P1").upper()
                        tid = t.get("id") or "TEST"
                        title = t.get("title") or ""
                        items.append(f"[{pr}] {tid}: {title}".strip())
                    if items:
                        vp_tool = self._tools.get("verify_plan") if self._tools else None
                        if vp_tool:
                            await vp_tool(action="create", items=items)
                except Exception:
                    pass
        
        # Render verification prompt
        prompt = self.jinja.get_template("user/verify_result.j2").render(
            task=task,
            result=result_context,
        )
        
        # Let LLM decide what verifications to perform and execute them
        from utils.llm import Message
        
        messages = [Message.user(prompt)]
        
        # High max_steps to allow thorough verification - agent will finish when done
        max_steps = 500  # Allow enough steps for full coverage testing
        
        step = 0
        # Safety: prevent verification from hanging indefinitely on an LLM call.
        verify_llm_timeout_s = 180  # Increased from 120 to allow more complex reasoning
        
        # Reset memory for this verification session
        self._memory.reset_for_task()
        self._memory.set_phase(f"verify_{task.id}")
        
        verdict: Optional[VerifyResult] = None
        while step < max_steps:
            step += 1
            
            # Condense memory periodically to prevent context overflow
            if step % 5 == 0:
                was_condensed = await self._memory.condense_if_needed()
                if was_condensed:
                    self._logger.debug(f"  Memory condensed at verify step {step}")
            
            # Get LLM decision with tool access
            try:
                response = await asyncio.wait_for(
                    self.llm.chat_messages(
                        messages=messages,
                        temperature=0.3,
                        tools=self._tools.to_openai_tools() if self._tools else None,
                    ),
                    timeout=verify_llm_timeout_s,
                )
            except asyncio.TimeoutError:
                self._logger.warning(
                    f"Verification timed out waiting for LLM response after {verify_llm_timeout_s}s "
                    f"(last step: {step}). Falling back to basic verification."
                )
                break
            
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
                
                # Log tool with details
                detail = ""
                if tool_name == "view":
                    detail = f" - {tool_args.get('path', '')}"
                elif tool_name == "view_image":
                    detail = f" - {tool_args.get('path', '')}"
                elif tool_name in ["analyze_image", "analyze_screenshot"]:
                    detail = f" - {tool_args.get('image_path', '')}{(' (focus: ' + tool_args.get('focus_area', '') + ')') if tool_args.get('focus_area') else ''}"
                elif tool_name == "grep":
                    detail = f" - '{tool_args.get('pattern', '')}' in {tool_args.get('path', '')}"
                elif tool_name == "glob":
                    detail = f" - {tool_args.get('pattern', '')}"
                elif tool_name == "project_structure":
                    detail = f" - {tool_args.get('path', '/') or '/'}"
                elif tool_name == "execute_bash":
                    cmd = tool_args.get("command", "")[:40]
                    detail = f" - {cmd}{'...' if len(tool_args.get('command', '')) > 40 else ''}"
                
                self._logger.info(f"  Verify step {step}: {tool_name}{detail}")
                
                # Record tool call in memory
                self._memory.record_tool_call(tool_name)
                self._memory.remember(
                    f"Verify step {step}: {tool_name}{detail}",
                    memory_type="short",
                    importance=0.5,
                )
                
                # Execute tool
                tool_result = await self._execute_verify_tool(tool_name, tool_args)
                
                # Truncate tool result to prevent context overflow
                tool_result_str = str(tool_result)
                MAX_TOOL_RESULT_CHARS = 15000  # ~4k tokens
                if len(tool_result_str) > MAX_TOOL_RESULT_CHARS:
                    tool_result_str = tool_result_str[:MAX_TOOL_RESULT_CHARS] + "\n... [TRUNCATED - output too long]"
                
                # Add to conversation using Message objects
                tool_calls_data = [{"id": tool_id, "type": "function", "function": {"name": tool_name, "arguments": tool_args_str}}]
                messages.append(Message.assistant(content=None, tool_calls=tool_calls_data))
                messages.append(Message.tool(tool_call_id=tool_id, content=tool_result_str))
                
                # Sliding window: keep only last N messages to prevent context overflow
                # IMPORTANT: Must keep complete tool call pairs (assistant + tool)
                MAX_MESSAGES = 30
                if len(messages) > MAX_MESSAGES:
                    # Keep first message (system/user prompt) and last N-1 messages
                    # But ensure we don't start with a 'tool' message (which needs preceding 'assistant' with tool_calls)
                    keep_messages = messages[-(MAX_MESSAGES-1):]
                    
                    # Find the first valid starting point (not a tool message)
                    start_idx = 0
                    for i, msg in enumerate(keep_messages):
                        msg_dict = msg.to_dict() if hasattr(msg, 'to_dict') else msg
                        if msg_dict.get('role') != 'tool':
                            start_idx = i
                            break
                    
                    messages = [messages[0]] + keep_messages[start_idx:]
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
                        verdict = VerifyResult(
                            task_id=task.id,
                            passed=data.get("passed", False),
                            checks_performed=data.get("checks_performed", []),
                            passed_checks=data.get("passed_checks", []),
                            failed_checks=data.get("failed_checks", []),
                            problems=data.get("problems", []),
                            summary=data.get("summary", "Verification complete"),
                        )
                        break
                except (json.JSONDecodeError, AttributeError) as e:
                    self._logger.warning(f"Failed to parse verify response: {e}")
                
                # Fallback: basic checks
                break
        
        # Log verify_plan coverage for debugging but don't force failure
        # The agent should decide what's important to verify
        if verdict and task.type.value in ["frontend", "verification"]:
            try:
                from tools.code_tools import VerifyPlanTool
                status = VerifyPlanTool.get_status()
                if status.get("has_plan") and not status.get("all_complete"):
                    incomplete = status.get("incomplete", [])[:5]
                    self._logger.info(f"  Note: Some planned tests not executed: {incomplete}")
                    # Don't force failure - agent decided what was important to verify
            except Exception:
                pass

        if verdict:
            return verdict

        # Fallback to basic file check if LLM verification didn't work
        return self._basic_verify(task, files_created, commands_run)

    async def _generate_verification_test_plan(self, task: Task, result_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a short verification checklist/table before running browser tests.
        Logged in plain text for debugging, and passed into the verification prompt context.
        """
        try:
            prompt = self.jinja.get_template("user/verification_test_plan.j2").render(
                task=task,
                result=result_context,
            )
        except Exception as e:
            self._logger.warning(f"Failed to render verification_test_plan.j2: {e}")
            return None

        try:
            from utils.llm import Message
            response = await asyncio.wait_for(
                self.llm.chat_messages(messages=[Message.user(prompt)], temperature=0.2),
                timeout=60,
            )
        except asyncio.TimeoutError:
            self._logger.warning("Verification test plan generation timed out (60s); continuing without plan.")
            return None
        except Exception as e:
            self._logger.warning(f"Verification test plan generation failed: {e}")
            return None

        content = (response.content or "").strip()
        if not content:
            return None

        import re
        m = re.search(r"\\{[\\s\\S]*\\}", content)
        if not m:
            return None

        try:
            plan = json.loads(m.group())
        except Exception:
            return None

        if not isinstance(plan, dict):
            return None

        tests = plan.get("tests")
        if isinstance(tests, list) and tests:
            self._logger.info(f"Verification Test Plan: {plan.get('plan_title', task.id)} ({len(tests)} tests)")
            for t in tests[:18]:
                tid = t.get("id", "?")
                pr = t.get("priority", "?")
                area = t.get("area", "")
                title = t.get("title", "")
                self._logger.info(f"  - {tid} [{pr}] {area}: {title}")

        return plan
    
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
            # Safety: cap verification tool runtime so the whole run can't hang.
            timeout_s = 90  # Default timeout
            if tool_name == "execute_bash":
                timeout_s = 300  # Long for npm install, builds, etc.
            elif tool_name.startswith("docker_"):
                timeout_s = 180  # Docker operations can be slow
            elif tool_name.startswith("browser_"):
                timeout_s = 60  # Browser operations (increased from 45)
            elif tool_name in ("start_server", "run_background"):
                timeout_s = 120  # Server startup
            elif tool_name in ("project_structure", "view", "glob", "grep", "lint"):
                timeout_s = 30

            try:
                result = await asyncio.wait_for(tool(**tool_args), timeout=timeout_s)
            except asyncio.TimeoutError:
                self._logger.warning(f"  Verify tool timed out after {timeout_s}s: {tool_name}")
                return f"Error: tool timeout after {timeout_s}s"
            if not result.success:
                err = result.error_message or ""
                # For execute_bash, show more detail from data
                if tool_name == "execute_bash" and isinstance(result.data, dict):
                    output = result.data.get("output", "")
                    exit_code = result.data.get("exit_code", "?")
                    timed_out = result.data.get("timed_out", False)
                    if timed_out:
                        err = f"TIMEOUT after {result.data.get('timeout_seconds', '?')}s"
                        if output:
                            err += f" | Output: {output[:400]}"
                    elif not err and output:
                        err = f"exit={exit_code} | {output[:400]}"
                    elif not err:
                        err = f"exit={exit_code}, no output"
                elif not err:
                    err = "Unknown error"
                err_preview = err.replace("\n", " ")
                if len(err_preview) > 500:
                    err_preview = err_preview[:500] + "..."
                self._logger.warning(f"  Verify tool failed: {tool_name} - {err_preview}")
                # Record error in memory
                self._memory.record_error(err_preview, f"tool={tool_name}")
            return str(result.data) if result.success else f"Error: {result.error_message}"
        except Exception as e:
            self._logger.warning(f"  Verify tool exception: {tool_name} - {e}")
            self._memory.record_error(str(e), f"tool={tool_name}")
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
    
    # ==================== Code Agent Interaction ====================
    
    async def review_plan(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review Code Agent's plan and provide feedback.
        
        Called by Code Agent via request_review() tool.
        
        Args:
            request: Review request with subject, message, context
        
        Returns:
            Dict with approved (bool), feedback, suggestions
        """
        self._logger.info(f"Reviewing Code Agent's plan: {request.get('message', '')[:50]}...")
        
        # Build prompt for review (template)
        prompt = self.jinja.get_template("user/review_plan.j2").render(
            subject=request.get("subject", "plan"),
            message=request.get("message", ""),
            context=request.get("context", "No additional context"),
        )
        
        try:
            response = await self.llm.chat_with_response(
                prompt=prompt,
                system=self._get_system_prompt(),
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            
            data = json.loads(response.content)
            
            self._logger.info(f"  Review result: {'APPROVED' if data.get('approved') else 'NEEDS REVISION'}")
            
            return {
                "approved": data.get("approved", False),
                "feedback": data.get("feedback", ""),
                "suggestions": data.get("suggestions", []),
                "missing_items": data.get("missing_items", []),
                "concerns": data.get("concerns", []),
            }
            
        except Exception as e:
            self._logger.error(f"Error reviewing plan: {e}")
            # Default to approve to avoid blocking
            return {
                "approved": True,
                "feedback": f"Review failed ({e}), proceeding with plan.",
                "suggestions": [],
            }
    
    async def answer_question(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Answer Code Agent's question or provide guidance.
        
        Called by Code Agent via ask_user_agent() tool.
        
        Args:
            request: Ask request with question, context, options
        
        Returns:
            Dict with answer, guidance, choice (if options provided)
        """
        self._logger.info(f"Code Agent asks: {request.get('question', '')[:50]}...")
        
        # Build prompt for answering (template)
        prompt = self.jinja.get_template("user/answer_question.j2").render(
            question=request.get("question", ""),
            context=request.get("context", "No additional context"),
            options=request.get("options", []),
        )
        
        try:
            response = await self.llm.chat_with_response(
                prompt=prompt,
                system=self._get_system_prompt(),
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            
            data = json.loads(response.content)
            
            self._logger.info(f"  Answer: {data.get('answer', '')[:100]}...")
            
            return {
                "answer": data.get("answer", ""),
                "guidance": data.get("guidance", ""),
                "choice": data.get("choice"),
                "reasoning": data.get("reasoning", ""),
            }
            
        except Exception as e:
            self._logger.error(f"Error answering question: {e}")
            return {
                "answer": f"I couldn't process your question ({e}). Please proceed with your best judgment.",
                "guidance": "Use your expertise to make a reasonable decision.",
            }
    
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

