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
from memory import GeneratorMemory, MemoryBank
from tools.code_tools import PlanTool, RequestReviewTool, AskUserAgentTool  # For state management and interaction
from tools.debug_tools import CrossLayerDebugger, APIAlignmentVerifier, EnhancedErrorParser
from tools.reasoning_debugger import ReasoningDebugger, IterativeDebugger


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
    
    MAX_STEPS = 99999  # High limit - rely on stuck detection to break loops
    
    def __init__(
        self,
        config: AgentConfig,
        llm: LLM,
        workspace: Workspace = None,
        output_dir: Path = None,  # Legacy, use workspace
        tools: ToolRegistry = None,
    ):
        # Enable stuck detection to catch infinite loops
        super().__init__(config, role=AgentRole.WORKER, enable_stuck_detection=False)
        
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
        
        # Memory system (based on utils/memory.py AgentMemory)
        self._memory = GeneratorMemory(
            llm=self.llm,
            short_term_size=100,
            long_term_size=500,
            condenser_max_size=80,
        )
        self._memory_bank = MemoryBank(root_dir=self.output_dir)
        
        # User Agent reference for interaction
        self._user_agent = None
        
        # Debug tools for cross-layer error tracing
        self._cross_layer_debugger = CrossLayerDebugger(workspace=self.workspace)
        self._api_verifier = APIAlignmentVerifier(workspace=self.workspace)
        self._reasoning_debugger = ReasoningDebugger(llm_client=self.llm, workspace=self.workspace)
    
    def set_user_agent(self, user_agent):
        """
        Set reference to User Agent for interaction.
        
        This enables:
        - request_review() - Code Agent requests plan review
        - ask_user_agent() - Code Agent asks questions
        """
        self._user_agent = user_agent
        
        # Set up callbacks for tools - store the user_agent reference
        # The tools will call these async methods directly via the code_agent reference
        if user_agent:
            self._logger.info("User Agent interaction enabled")
    
    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a task from User Agent."""
        self._logger.info(f"Executing task: {task.id} ({task.type.value})")
        
        files_created = []
        files_modified = []
        commands = []
        issues = []
        
        # Reset memory and plan state for new task
        self._memory.reset_for_task()
        self._memory.set_phase(task.type.value)
        PlanTool.reset()  # Reset plan checklist for new task
        
        # Get existing files for context
        existing_files = self._get_existing_files()
        task.existing_files = existing_files
        
        # Build memory context
        memory_context = ""
        if self._memory_bank.exists():
            memory_context += f"\n\n<MEMORY_BANK>\n{self._memory_bank.get_context()}\n</MEMORY_BANK>\n"
        
        # Add condenser summary if available
        if self._memory.condenser and self._memory.condenser.summary:
            memory_context += f"\n\n<PREVIOUS_CONTEXT>\n{self._memory.condenser.summary}\n</PREVIOUS_CONTEXT>\n"
        
        # Run the agent loop
        system_prompt = self._get_system_prompt(task)
        if memory_context:
            system_prompt += memory_context
        user_prompt = self.jinja.get_template("code/execute_task.j2").render(task=task)
        
        messages = [
            Message.system(system_prompt),
            Message.user(user_prompt),
        ]
        
        step = 0
        while step < self.MAX_STEPS:
            step += 1
            self._logger.debug(f"Step {step}/{self.MAX_STEPS}")
            
            # Condense memory if too long (every 50 steps)
            if step % 50 == 0:
                was_condensed = await self._memory.condense_if_needed()
                if was_condensed:
                    self._logger.info(f"  Memory condensed at step {step}")
            
            # Add operation state to help LLM awareness (every 20 steps)
            if step % 20 == 0 and step > 0:
                state_context = self._memory.get_operation_context()
                messages.append(Message.user(f"[STATE UPDATE]\n{state_context}"))
            
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
                
                # Show plan details in log
                if tool_name == "plan":
                    action = tool_args.get("action", "")
                    if action == "create":
                        items = tool_args.get("items", [])
                        self._logger.info(f"    create: {len(items)} items - {', '.join(items[:3])}{'...' if len(items) > 3 else ''}")
                    elif action == "complete":
                        item = tool_args.get("item_text") or f"item #{tool_args.get('item_index', '?')}"
                        self._logger.info(f"    done: {item[:50]}")
                    elif action == "status":
                        status = PlanTool.get_plan_status()
                        if status.get("has_plan"):
                            self._logger.info(f"    status: {status['completed']}/{status['total']} done")
                
                # Show tool details in log
                if tool_name == "think":
                    thought = tool_args.get("thought", "")
                    preview = thought[:80].replace('\n', ' ')
                    self._logger.info(f"    > {preview}{'...' if len(thought) > 80 else ''}")
                
                elif tool_name == "view":
                    path = tool_args.get("path", "")
                    self._logger.info(f"    path: {path}")
                
                elif tool_name in ["str_replace_editor", "write_file"]:
                    path = tool_args.get("path", "") or tool_args.get("file_path", "")
                    self._logger.info(f"    file: {path}")
                
                elif tool_name == "grep":
                    pattern = tool_args.get("pattern", "")
                    path = tool_args.get("path", "")
                    self._logger.info(f"    pattern: '{pattern}' in {path}")
                
                elif tool_name == "glob":
                    pattern = tool_args.get("pattern", "")
                    self._logger.info(f"    pattern: {pattern}")
                
                elif tool_name == "lint":
                    path = tool_args.get("path", "")
                    self._logger.info(f"    file: {path}")
                
                elif tool_name == "execute_bash":
                    cmd = tool_args.get("command", "")[:60]
                    self._logger.info(f"    cmd: {cmd}{'...' if len(tool_args.get('command', '')) > 60 else ''}")
                
                elif tool_name == "project_structure":
                    path = tool_args.get("path", "") or "/"
                    self._logger.info(f"    path: {path}")

                elif tool_name == "view_image":
                    path = tool_args.get("path", "")
                    desc = tool_args.get("description", "")
                    if desc:
                        desc_preview = desc[:60].replace("\n", " ")
                        self._logger.info(f"    image: {path} - {desc_preview}{'...' if len(desc) > 60 else ''}")
                    else:
                        self._logger.info(f"    image: {path}")

                elif tool_name in ["analyze_image", "analyze_screenshot"]:
                    image_path = tool_args.get("image_path", "")
                    focus_area = tool_args.get("focus_area", "")
                    if focus_area:
                        self._logger.info(f"    image: {image_path} (focus: {focus_area})")
                    else:
                        self._logger.info(f"    image: {image_path}")
                
                # Record action for stuck detection
                self.record_action(tool_name)
                
                # Track tool call in memory (also handles loop detection)
                tool_info = self._memory.record_tool_call(tool_name)
                
                # Handle finish - Code Agent decides when task is complete
                if tool_name == "finish":
                    summary = tool_args.get('message', tool_args.get('summary', 'Done'))
                    self._logger.info(f"  Task completed: {summary}")
                    self._logger.info(f"  Files created: {len(files_created)}, Files modified: {len(files_modified)}")
                    break
                
                # LOOP PREVENTION: Check for repeated lint on same file
                if tool_name == "lint":
                    lint_path = tool_args.get("path", "")
                    normalized_lint_path = self._normalize_path_for_tracking(lint_path) if lint_path else ""
                    
                    if self._memory.is_file_linted(normalized_lint_path):
                        # Already linted this file - return warning instead of executing
                        self._logger.warning(f"  Duplicate lint detected: {normalized_lint_path}")
                        
                        # Check if all created files are linted (task might be done)
                        should_finish, reason = self._memory.should_force_finish()
                        finish_hint = f" {reason}." if should_finish else ""
                        
                        stats = self._memory.get_file_stats()
                        result = ToolResult(
                            success=False,
                            data=None,
                            error_message=f"WARNING: File '{normalized_lint_path}' has already been linted and passed. "
                                         f"You have linted {stats['linted']} files total. "
                                         f"All files are passing lint.{finish_hint} Call finish() NOW to complete the task."
                        )
                        messages.append(Message.assistant(tool_calls=[tool_call]))
                        messages.append(Message.tool(result.error_message, tool_call_id))
                        
                        # Force finish if too many duplicate attempts
                        if should_finish:
                            self._logger.warning("  Forcing task completion")
                            issues.append("Forced completion due to lint loop")
                            break
                        continue
                    else:
                        self._memory.record_lint(normalized_lint_path, passed=True)
                
                # LOOP PREVENTION: Check for too many consecutive same tool calls
                if tool_info["consecutive_count"] > 50:
                    self._logger.warning(f"  Too many consecutive {tool_name} calls ({tool_info['consecutive_count']})")
                    result = ToolResult(
                        success=False,
                        data=None,
                        error_message=f"WARNING: You have called '{tool_name}' {tool_info['consecutive_count']} times consecutively. "
                                     f"This indicates a loop. Call finish() NOW to complete the task."
                    )
                    messages.append(Message.assistant(tool_calls=[tool_call]))
                    messages.append(Message.tool(result.error_message, tool_call_id))
                    continue
                
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

                # Log failures with useful details (especially important for vision/tools)
                if not result.success:
                    err = result.error_message or ""
                    # For execute_bash, also show output from data if available
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
                        err = "Unknown error (no error_message)"
                    
                    err_preview = err.replace("\n", " ")
                    if len(err_preview) > 500:
                        err_preview = err_preview[:500] + "..."
                    self._logger.warning(f"  Tool failed: {tool_name} - {err_preview}")
                else:
                    # Success summaries for image tools (keep concise)
                    if tool_name == "view_image" and isinstance(result.data, dict):
                        abs_path = result.data.get("absolute_path", "")
                        size = result.data.get("size_display") or result.data.get("size") or ""
                        mime = result.data.get("mime_type", "")
                        self._logger.info(f"    loaded: {abs_path} {f'({size}, {mime})' if (size or mime) else ''}".rstrip())
                    elif tool_name in ["analyze_image", "analyze_screenshot"] and isinstance(result.data, dict):
                        resolved = result.data.get("resolved_path", "")
                        analysis = result.data.get("analysis", {}) if isinstance(result.data.get("analysis", {}), dict) else {}
                        layout = analysis.get("layout_type", "")
                        system = analysis.get("design_system", "")
                        extra = ", ".join([x for x in [layout and f"layout={layout}", system and f"system={system}"] if x])
                        self._logger.info(f"    analyzed: {resolved}{f' ({extra})' if extra else ''}")
                
                # Track file operations (using pre-execution existence check)
                if tool_name in ["write_file", "str_replace_editor"]:
                    path = tool_args.get("path") or tool_args.get("file_path")
                    if path and result.success:
                        normalized_path = self._normalize_path_for_tracking(path)
                        if normalized_path not in files_created and normalized_path not in files_modified:
                            if file_existed_before:
                                files_modified.append(normalized_path)
                                self._memory.record_file_modified(normalized_path)
                            else:
                                files_created.append(normalized_path)
                                self._memory.record_file_created(normalized_path)
                
                # Track commands
                if tool_name == "execute_bash":
                    exit_code = result.data.get("exit_code", 0) if isinstance(result.data, dict) else 0
                    commands.append({
                        "command": tool_args.get("command"),
                        "exit_code": exit_code,
                        "success": result.success,
                    })
                
                # Track errors in memory
                if not result.success and result.error_message:
                    self._memory.record_error(result.error_message, f"Tool: {tool_name}")
                
                # Add tool result to short-term memory for context
                self._memory.remember(
                    f"[{tool_name}] {'Success' if result.success else 'Failed'}: {str(result.data)[:200] if result.data else result.error_message[:200] if result.error_message else 'No output'}",
                    memory_type="short",
                    metadata={"type": "tool_result", "tool": tool_name},
                    importance=0.5 if result.success else 0.8,
                )
                
                # Add to conversation
                messages.append(Message.assistant(tool_calls=[tool_call]))
                tool_content = str(result.data) if result.success else (result.error_message or "Error")
                # Hard safety cap: never feed huge tool outputs back into the LLM context
                if len(tool_content) > 20000:
                    tool_content = tool_content[:20000] + "\n...[tool output truncated]..."
                messages.append(Message.tool(tool_content, tool_call_id))
                
                # Sliding window: prevent context overflow by keeping only recent messages
                # IMPORTANT: Must keep complete tool call pairs (assistant + tool)
                MAX_MESSAGES = 60
                if len(messages) > MAX_MESSAGES:
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
                # No tool call - LLM just responded with text
                messages.append(Message.assistant(response.content))
                self._logger.warning(f"  LLM returned text without tool call")
                
                # Check if it's saying it's done - but only accept if we made progress
                if any(word in response.content.lower() for word in ["complete", "done", "finished"]):
                    if files_created or files_modified:
                        break
                    # No files created but says done - prompt to actually do work
                    messages.append(Message.user(
                        "ERROR: You said 'done' but created 0 files. You MUST use tool calls to create files. "
                        "Call write_file() or str_replace_editor() to create the required files. "
                        "Do NOT respond with text - call a tool NOW."
                    ))
                else:
                    # Prompt to use tools
                    messages.append(Message.user(
                        "You must use tool calls, not text responses. "
                        "Call a tool like write_file(), plan(), or think(). Do not respond with text."
                    ))
            
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
    
    async def diagnose_error(self, error: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Diagnose an error using cross-layer debugging.
        
        Args:
            error: The error message
            context: Optional additional context (logs, file contents)
        
        Returns:
            Dict with diagnosis information including root cause and fix suggestions
        """
        # First try pattern-based diagnosis (fast)
        trace = self._cross_layer_debugger.trace_error(error)
        
        diagnosis = {
            "origin_layer": trace.origin_layer,
            "immediate_cause": trace.immediate_cause,
            "root_cause": trace.root_cause,
            "fix_suggestion": trace.fix_suggestion,
            "confidence": trace.confidence,
            "affected_files": trace.affected_files,
        }
        
        # If confidence is low, try LLM-based reasoning
        if trace.confidence < 0.7 and self._reasoning_debugger:
            try:
                # Build context from workspace
                llm_context = context or {}
                if not llm_context:
                    llm_context = self._build_debug_context()
                
                llm_diagnosis = await self._reasoning_debugger.debug_error(
                    error=error,
                    context=llm_context,
                )
                
                # Use LLM diagnosis if more confident
                if llm_diagnosis.confidence > trace.confidence:
                    diagnosis = {
                        "origin_layer": llm_diagnosis.origin_layer,
                        "immediate_cause": llm_diagnosis.immediate_cause,
                        "root_cause": llm_diagnosis.root_cause,
                        "fix_suggestion": "; ".join(llm_diagnosis.fix_steps),
                        "confidence": llm_diagnosis.confidence,
                        "affected_files": llm_diagnosis.affected_files,
                        "code_changes": [
                            {
                                "file": c.file,
                                "action": c.action,
                                "target": c.target,
                                "replacement": c.replacement,
                            }
                            for c in llm_diagnosis.code_changes
                        ],
                        "reasoning": llm_diagnosis.reasoning,
                    }
            except Exception as e:
                self._logger.warning(f"LLM diagnosis failed: {e}")
        
        return diagnosis
    
    def _build_debug_context(self) -> Dict[str, str]:
        """Build context for debugging by reading relevant files."""
        context = {}
        
        # Frontend API
        api_file = self.output_dir / "app/frontend/src/services/api.js"
        if api_file.exists():
            context["frontend_api"] = api_file.read_text()[:2000]
        
        # Backend routes
        routes_dir = self.output_dir / "app/backend/src/routes"
        if routes_dir.exists():
            routes_content = []
            for route_file in routes_dir.glob("*.js"):
                routes_content.append(f"// {route_file.name}\n{route_file.read_text()[:1000]}")
            context["backend_routes"] = "\n\n".join(routes_content)[:3000]
        
        # Database schema
        schema_file = self.output_dir / "app/database/init/01_schema.sql"
        if schema_file.exists():
            context["database_schema"] = schema_file.read_text()[:2000]
        
        # Docker compose
        compose_file = self.output_dir / "docker/docker-compose.yml"
        if compose_file.exists():
            context["docker_compose"] = compose_file.read_text()
        
        return context
    
    async def verify_api_alignment(self) -> List[Dict[str, Any]]:
        """
        Verify that frontend API calls align with backend routes.
        
        Returns list of alignment issues found.
        """
        frontend_dir = self.output_dir / "app/frontend"
        backend_dir = self.output_dir / "app/backend"
        
        issues = self._api_verifier.verify_alignment(frontend_dir, backend_dir)
        
        return [
            {
                "type": issue.issue_type,
                "description": issue.description,
                "suggestion": issue.suggestion,
                "severity": issue.severity,
            }
            for issue in issues
        ]
    
    async def fix_with_feedback_loop(
        self,
        issue: Issue,
        verify_fn=None,
        max_iterations: int = 5,
    ) -> FixResult:
        """
        Fix an issue with iterative verification.
        
        This implements the fix -> verify -> analyze -> fix feedback loop.
        
        Args:
            issue: The issue to fix
            verify_fn: Optional async function that returns (success: bool, new_error: str)
            max_iterations: Maximum number of fix attempts
        
        Returns:
            FixResult with fix status and details
        """
        current_issue = issue
        all_changes = []
        all_commands = []
        iteration_history = []
        
        for iteration in range(max_iterations):
            self._logger.info(f"Fix iteration {iteration + 1}/{max_iterations}")
            
            # 1. Diagnose current error for better context
            diagnosis = await self.diagnose_error(current_issue.description)
            self._logger.info(f"  Diagnosis: {diagnosis['root_cause'][:100]}...")
            
            # Add diagnosis to issue context
            enhanced_issue = Issue(
                id=f"{current_issue.id}_iter{iteration}",
                task_id=current_issue.task_id,
                severity=current_issue.severity,
                title=current_issue.title,
                description=current_issue.description + f"\n\nDIAGNOSIS: {diagnosis['root_cause']}\nSUGGESTED FIX: {diagnosis['fix_suggestion']}",
                related_files=diagnosis.get("affected_files", current_issue.related_files),
                verification_command=current_issue.verification_command,
            )
            
            # 2. Attempt fix
            fix_result = await self.fix_issue(enhanced_issue)
            all_changes.extend(fix_result.changes)
            
            iteration_history.append({
                "iteration": iteration + 1,
                "issue": current_issue.title,
                "diagnosis": diagnosis["root_cause"],
                "fixed": fix_result.fixed,
                "changes": fix_result.changes,
            })
            
            if not fix_result.fixed:
                self._logger.warning("  Fix attempt did not succeed")
                continue
            
            # 3. Verify if we have a verify function
            if verify_fn:
                try:
                    success, new_error = await verify_fn()
                    
                    if success:
                        self._logger.info(f"  Fix verified successfully after {iteration + 1} iterations!")
                        return FixResult(
                            issue_id=issue.id,
                            fixed=True,
                            changes=list(dict.fromkeys(all_changes)),
                            needs_verification=[],
                            notes=f"Fixed after {iteration + 1} iterations. History: {json.dumps(iteration_history, indent=2)}",
                        )
                    
                    # New error - update for next iteration
                    if new_error and new_error != current_issue.description:
                        self._logger.info(f"  New error after fix: {new_error[:100]}...")
                        current_issue = Issue(
                            id=f"{issue.id}_followup_{iteration}",
                            task_id=issue.task_id,
                            severity=issue.severity,
                            title=f"Follow-up: {new_error[:50]}",
                            description=new_error,
                            related_files=fix_result.changes,
                        )
                    else:
                        # Same error, likely needs different approach
                        self._logger.warning("  Same error persists, may need manual intervention")
                        break
                        
                except Exception as e:
                    self._logger.error(f"  Verification error: {e}")
            else:
                # No verification function, return after first fix
                return fix_result
        
        return FixResult(
            issue_id=issue.id,
            fixed=False,
            changes=list(dict.fromkeys(all_changes)),
            needs_verification=[issue.verification_command] if issue.verification_command else [],
            notes=f"Max iterations ({max_iterations}) reached. History: {json.dumps(iteration_history, indent=2)}",
        )
    
    async def fix_issue(self, issue: Issue) -> FixResult:
        """Fix an issue reported by User Agent."""
        self._logger.info(f"Fixing issue: {issue.title}")
        
        changes: list[str] = []
        commands: list[str] = []
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
            self._logger.debug(f"Fix step {step}/100")
            
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
                
                # Record action for stuck detection
                self.record_action(tool_name)
                
                if tool_name == "finish":
                    # Log what the agent claimed (keeps debugging possible when it finishes early)
                    msg = tool_args.get("message") or tool_args.get("summary") or ""
                    if msg:
                        self._logger.info(f"  Finish called: {msg[:200]}{'...' if len(msg) > 200 else ''}")
                    fixed = tool_args.get("success", True)
                    break

                # Log tool invocation (plain text, concise)
                detail = ""
                if tool_name in ["view", "view_image"]:
                    detail = f" - {tool_args.get('path', '')}"
                elif tool_name in ["write_file", "edit_file", "str_replace_editor", "delete_file"]:
                    detail = f" - {tool_args.get('path') or tool_args.get('file_path') or tool_args.get('target_file') or ''}"
                elif tool_name == "execute_bash":
                    cmd = (tool_args.get("command") or "")[:80]
                    detail = f" - {cmd}{'...' if len(tool_args.get('command') or '') > 80 else ''}"
                elif tool_name == "test_api":
                    detail = f" - {tool_args.get('method', '')} {tool_args.get('url', '')}"
                elif tool_name == "lint":
                    detail = f" - {tool_args.get('path', '') or tool_args.get('file', '')}"
                elif tool_name == "grep":
                    detail = f" - '{tool_args.get('pattern', '')}' in {tool_args.get('path', '')}"
                elif tool_name == "glob":
                    detail = f" - {tool_args.get('pattern', '')}"
                elif tool_name == "project_structure":
                    detail = f" - {tool_args.get('path', '/') or '/'}"
                elif tool_name == "plan":
                    if tool_args.get("action") == "create":
                        items = tool_args.get("items") or []
                        preview = "; ".join([str(x) for x in items[:4]])
                        detail = f" - create: {preview}{'...' if len(items) > 4 else ''}"
                    elif tool_args.get("action") == "complete":
                        detail = f" - complete: {tool_args.get('item_text', '')}"
                    else:
                        detail = f" - {tool_args.get('action', '')}"
                self._logger.info(f"  Tool: {tool_name}{detail}")
                
                result = await self._execute_tool(tool_name, tool_args)
                
                # Track changes
                if tool_name in ["write_file", "edit_file", "str_replace_editor", "delete_file"] and result.success:
                    path = tool_args.get("path") or tool_args.get("file_path") or tool_args.get("target_file")
                    if path:
                        changes.append(str(path))
                if tool_name == "execute_bash" and result.success:
                    cmd = tool_args.get("command")
                    if cmd:
                        commands.append(cmd)

                # Log result (success/fail + short preview)
                if result.success:
                    info = ""
                    if isinstance(result.data, dict) and result.data.get("info"):
                        info = str(result.data.get("info"))
                    elif isinstance(result.data, str):
                        info = result.data
                    if info:
                        info = info.replace("\n", " ")
                        self._logger.info(f"    Result: OK - {info[:180]}{'...' if len(info) > 180 else ''}")
                    else:
                        self._logger.info("    Result: OK")
                else:
                    err = result.error_message or ""
                    # For execute_bash, show more detail
                    if tool_name == "execute_bash" and isinstance(result.data, dict):
                        output = result.data.get("output", "")
                        exit_code = result.data.get("exit_code", "?")
                        timed_out = result.data.get("timed_out", False)
                        if timed_out:
                            err = f"TIMEOUT after {result.data.get('timeout_seconds', '?')}s"
                            if output:
                                err += f" | Output: {output[:300]}"
                        elif not err and output:
                            err = f"exit={exit_code} | {output[:300]}"
                        elif not err:
                            err = f"exit={exit_code}, no output"
                    elif not err:
                        err = "Unknown error"
                    err = err.replace("\n", " ")
                    self._logger.warning(f"    Result: FAIL - {err[:400]}{'...' if len(err) > 400 else ''}")
                
                messages.append(Message.assistant(tool_calls=[tool_call]))
                tool_content = str(result.data) if result.success else (result.error_message or "Error")
                # Keep tool outputs bounded in fix mode too
                if len(tool_content) > 20000:
                    tool_content = tool_content[:20000] + "\n...[tool output truncated]..."
                messages.append(Message.tool(tool_content, tool_call_id))
                
                # Sliding window: prevent context overflow
                # IMPORTANT: Must keep complete tool call pairs (assistant + tool)
                MAX_MESSAGES = 50
                if len(messages) > MAX_MESSAGES:
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
                messages.append(Message.assistant(response.content))
                if "fixed" in response.content.lower() or "done" in response.content.lower():
                    fixed = True
                    break
                messages.append(Message.user("Continue fixing."))
        
        # Add verification if specified
        if issue.verification_command:
            needs_verification.append(issue.verification_command)
        
        # Deduplicate + keep stable ordering
        changes = list(dict.fromkeys(changes))
        commands = list(dict.fromkeys(commands))

        return FixResult(
            issue_id=issue.id,
            fixed=fixed,
            changes=[f"Changed: {c}" for c in changes],
            needs_verification=needs_verification,
            notes=f"Made {len(changes)} changes; ran {len(commands)} commands",
        )
    
    async def _execute_tool(self, name: str, args: Dict[str, Any]) -> ToolResult:
        """Execute a tool and return the result."""
        
        # Special handling for User Agent interaction tools
        if name == "request_review" and self._user_agent:
            self._logger.info("  → Requesting review from User Agent...")
            try:
                # Get plan context
                plan_status = PlanTool.get_plan_status()
                if plan_status.get("has_plan"):
                    plan_info = f"\n\nPlan: {plan_status['completed']}/{plan_status['total']} complete"
                    if plan_status.get("incomplete"):
                        plan_info += f"\nPending: {', '.join(plan_status['incomplete'][:5])}"
                else:
                    plan_info = ""
                
                request = {
                    "type": "review_request",
                    "subject": args.get("subject", "plan"),
                    "message": args.get("message", ""),
                    "context": (args.get("context", "") or "") + plan_info,
                }
                response = await self._user_agent.review_plan(request)
                approved = response.get("approved", False)
                self._logger.info(f"  ← Review result: {'APPROVED' if approved else 'NEEDS REVISION'}")
                return ToolResult(
                    success=True,
                    data={
                        "approved": approved,
                        "feedback": response.get("feedback", ""),
                        "suggestions": response.get("suggestions", []),
                        "info": f"Review received: {'APPROVED' if approved else 'NEEDS REVISION'}"
                    }
                )
            except Exception as e:
                self._logger.error(f"Review error: {e}")
                return ToolResult(success=False, error_message=f"Error during review: {e}")
        
        if name == "ask_user_agent" and self._user_agent:
            self._logger.info("  → Asking User Agent for help...")
            try:
                request = {
                    "type": "ask",
                    "question": args.get("question", ""),
                    "context": args.get("context", ""),
                    "options": args.get("options", []),
                }
                response = await self._user_agent.answer_question(request)
                self._logger.info(f"  ← User Agent responded")
                return ToolResult(
                    success=True,
                    data={
                        "answer": response.get("answer", ""),
                        "guidance": response.get("guidance", ""),
                        "choice": response.get("choice", ""),
                    }
                )
            except Exception as e:
                self._logger.error(f"Ask error: {e}")
                return ToolResult(success=False, error_message=f"Error asking User Agent: {e}")
        
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
