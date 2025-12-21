"""
Code Agent - Software Developer

Responsibilities:
- Receive tasks from User Agent
- Plan and generate code files
- Fix issues reported by User Agent
- Execute commands for testing
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader

from utils.base_agent import BaseAgent, AgentRole
from utils.config import AgentConfig
from utils.llm import LLM, Message
from utils.tool import ToolRegistry, ToolResult

from utils.message import Task, Issue, TaskResult, FixResult, TaskStatus

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from workspace import Workspace


class CodeAgent(BaseAgent):
    """
    Code Agent - Generates and fixes code.
    
    Workflow:
    1. Receive task from User Agent
    2. Plan files to generate
    3. Generate each file
    4. Report completion
    5. Fix issues if reported
    """
    
    MAX_STEPS = 999  # No practical limit - rely on finish tool
    
    def __init__(
        self,
        config: AgentConfig,
        llm: LLM,
        workspace: Workspace = None,
        output_dir: Path = None,  # Legacy, use workspace
        tools: ToolRegistry = None,
    ):
        super().__init__(config, role=AgentRole.WORKER)
        
        self.llm = llm
        self._tools = tools
        
        # Support both workspace (new) and output_dir (legacy)
        if workspace:
            self.workspace = workspace
        elif output_dir:
            self.workspace = Workspace(output_dir)
        else:
            self.workspace = Workspace(Path.cwd())
        
        # For backward compatibility
        self.output_dir = self.workspace.root
        
        # Setup Jinja2 for prompts
        prompt_dir = Path(__file__).parent.parent / "prompts"
        self.jinja = Environment(
            loader=FileSystemLoader(str(prompt_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        self._logger = logging.getLogger("agent.code")
    
    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a task from User Agent."""
        self._logger.info(f"Executing task: {task.id} ({task.type.value})")
        
        files_created = []
        files_modified = []
        commands = []
        issues = []
        
        # Get existing files for context
        existing_files = self._get_existing_files()
        task.existing_files = existing_files
        
        # Run the agent loop
        system_prompt = self._get_system_prompt(task)
        user_prompt = self.jinja.get_template("code/execute_task.j2").render(task=task)
        
        messages = [
            Message.system(system_prompt),
            Message.user(user_prompt),
        ]
        
        step = 0
        while step < self.MAX_STEPS:
            step += 1
            self._logger.debug(f"Step {step}/{self.MAX_STEPS}")
            
            # Get next action from LLM
            response = await self.llm.chat_messages(
                messages=messages,
                temperature=0.7,
                tools=self._tools.to_openai_tools(),
            )
            
            if not response:
                issues.append("No response from LLM")
                break
            
            # Check for tool calls
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                # Handle both dict and object formats
                if isinstance(tool_call, dict):
                    tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"]["arguments"]
                    tool_call_id = tool_call["id"]
                else:
                    tool_name = tool_call.function.name
                    tool_args_str = tool_call.function.arguments
                    tool_call_id = tool_call.id
                
                try:
                    tool_args = json.loads(tool_args_str)
                except json.JSONDecodeError:
                    tool_args = {}
                
                self._logger.info(f"  Tool: {tool_name}")
                
                # Handle finish
                if tool_name == "finish":
                    self._logger.info(f"  Task completed: {tool_args.get('summary', 'Done')}")
                    break
                
                # Track if file exists BEFORE executing (for create vs modify detection)
                file_existed_before = False
                if tool_name in ["write_file", "str_replace_editor"]:
                    path = tool_args.get("path") or tool_args.get("file_path")
                    if path:
                        normalized_path = self._normalize_path_for_tracking(path)
                        full_path = self.output_dir / normalized_path
                        file_existed_before = full_path.exists()
                
                # Execute tool
                result = await self._execute_tool(tool_name, tool_args)
                
                # Track file operations (using pre-execution existence check)
                if tool_name in ["write_file", "str_replace_editor"]:
                    path = tool_args.get("path") or tool_args.get("file_path")
                    if path and result.success:
                        normalized_path = self._normalize_path_for_tracking(path)
                        if normalized_path not in files_created and normalized_path not in files_modified:
                            if file_existed_before:
                                files_modified.append(normalized_path)
                            else:
                                files_created.append(normalized_path)
                
                # Track commands
                if tool_name == "execute_bash":
                    commands.append({
                        "command": tool_args.get("command"),
                        "exit_code": result.data.get("exit_code", 0) if isinstance(result.data, dict) else 0,
                        "success": result.success,
                    })
                
                # Add to conversation
                messages.append(Message.assistant(tool_calls=[tool_call]))
                tool_content = str(result.data) if result.success else (result.error_message or "Error")
                messages.append(Message.tool(tool_content, tool_call_id))
            
            else:
                # No tool call - LLM just responded with text
                messages.append(Message.assistant(response.content))
                
                # Check if it's saying it's done
                if any(word in response.content.lower() for word in ["complete", "done", "finished"]):
                    break
                
                # Prompt to continue
                messages.append(Message.user("Continue with the next action."))
            
            # Check stuck detection
            if self.check_if_stuck():
                issues.append("Agent got stuck in a loop")
                break
        
        # Determine status
        if issues:
            status = TaskStatus.FAILED
        elif files_created or files_modified:
            status = TaskStatus.COMPLETED
        else:
            status = TaskStatus.PARTIAL
        
        return TaskResult(
            task_id=task.id,
            status=status,
            files_created=files_created,
            files_modified=files_modified,
            commands=commands,
            issues=issues,
            summary=f"Created {len(files_created)} files, modified {len(files_modified)} files",
        )
    
    async def fix_issue(self, issue: Issue) -> FixResult:
        """Fix an issue reported by User Agent."""
        self._logger.info(f"Fixing issue: {issue.title}")
        
        changes = []
        needs_verification = []
        
        # Render fix prompt
        system_prompt = self._get_system_prompt_for_fix()
        user_prompt = self.jinja.get_template("code/fix_issue.j2").render(issue=issue)
        
        messages = [
            Message.system(system_prompt),
            Message.user(user_prompt),
        ]
        
        step = 0
        fixed = False
        
        while step < 100:  # Allow more steps for complex fixes
            step += 1
            
            response = await self.llm.chat_messages(
                messages=messages,
                temperature=0.5,
                tools=self._tools.to_openai_tools(),
            )
            
            if not response:
                break
            
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                # Handle both dict and object formats
                if isinstance(tool_call, dict):
                    tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"]["arguments"]
                    tool_call_id = tool_call["id"]
                else:
                    tool_name = tool_call.function.name
                    tool_args_str = tool_call.function.arguments
                    tool_call_id = tool_call.id
                
                try:
                    tool_args = json.loads(tool_args_str)
                except json.JSONDecodeError:
                    tool_args = {}
                
                if tool_name == "finish":
                    fixed = tool_args.get("success", True)
                    break
                
                result = await self._execute_tool(tool_name, tool_args)
                
                # Track changes
                if tool_name in ["write_file", "str_replace_editor"] and result.success:
                    path = tool_args.get("path") or tool_args.get("file_path")
                    if path:
                        changes.append(f"Modified: {path}")
                
                messages.append(Message.assistant(tool_calls=[tool_call]))
                tool_content = str(result.data) if result.success else (result.error_message or "Error")
                messages.append(Message.tool(tool_content, tool_call_id))
            else:
                messages.append(Message.assistant(response.content))
                if "fixed" in response.content.lower() or "done" in response.content.lower():
                    fixed = True
                    break
                messages.append(Message.user("Continue fixing."))
        
        # Add verification if specified
        if issue.verification_command:
            needs_verification.append(issue.verification_command)
        
        return FixResult(
            issue_id=issue.id,
            fixed=fixed,
            changes=changes,
            needs_verification=needs_verification,
            notes=f"Made {len(changes)} changes",
        )
    
    async def _execute_tool(self, name: str, args: Dict[str, Any]) -> ToolResult:
        """Execute a tool and return the result."""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult.fail(f"Unknown tool: {name}")
        
        try:
            # Handle path resolution for file tools
            if "path" in args:
                args["path"] = self._resolve_tool_path(args["path"])
            if "file_path" in args:
                args["file_path"] = self._resolve_tool_path(args["file_path"])
            
            result = await tool(**args)
            self._metrics.tool_calls += 1
            return result
        except Exception as e:
            self._logger.error(f"Tool {name} error: {e}")
            return ToolResult.fail(str(e))
    
    def _get_existing_files(self) -> List[str]:
        """Get list of existing files in output directory."""
        if not self.output_dir.exists():
            return []
        
        files = []
        for path in self.output_dir.rglob("*"):
            if path.is_file() and not path.name.startswith("."):
                if any(p in str(path) for p in ["node_modules", "__pycache__", ".git"]):
                    continue
                files.append(str(path.relative_to(self.output_dir)))
        
        return files
    
    def _resolve_tool_path(self, path: str) -> str:
        """
        Resolve a path for tool execution, ensuring it's absolute and within output_dir.
        
        Uses shared path_utils.resolve_path for consistent handling across all agents.
        """
        from env_generator.llm_generator.tools.path_utils import resolve_path
        return str(resolve_path(path, self.output_dir))
    
    def _normalize_path_for_tracking(self, path: str) -> str:
        """
        Normalize a file path to be relative to output_dir.
        
        Uses shared path_utils.normalize_path_for_tracking for consistency.
        """
        from env_generator.llm_generator.tools.path_utils import normalize_path_for_tracking
        return normalize_path_for_tracking(path, self.output_dir)
    
    def _get_system_prompt(self, task: Task) -> str:
        """Get system prompt for task execution."""
        return self.jinja.get_template("code/system.j2").render(
            project_name=self.output_dir.name,
            output_dir=str(self.output_dir),
            current_phase=task.type.value,
            target_directory=task.target_directory,
            tools_description=self._get_tools_description(),
        )
    
    def _get_system_prompt_for_fix(self) -> str:
        """Get system prompt for issue fixing."""
        return self.jinja.get_template("code/system.j2").render(
            project_name=self.output_dir.name,
            output_dir=str(self.output_dir),
            current_phase="fix",
            target_directory="",
            tools_description=self._get_tools_description(),
        )
    
    def _get_tools_description(self) -> str:
        """Get description of available tools."""
        lines = []
        for tool in self._tools.get_all():
            desc = tool.description[:80] if hasattr(tool, 'description') else ''
            lines.append(f"- {tool.name}: {desc}")
        return "\n".join(lines)
    
    async def process_task(self, task):
        """Process a task message - use execute_task instead."""
        pass
