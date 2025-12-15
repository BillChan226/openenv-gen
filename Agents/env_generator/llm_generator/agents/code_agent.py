"""
Code Generator Agent

This agent has capabilities similar to how I (the assistant) work:
1. THINK - Analyze the task, understand what needs to be done
2. PLAN - Break down into steps, decide which files to generate
3. EXECUTE - Generate code file by file
4. REFLECT - Check if generation is correct, look for issues
5. FIX - If issues found, analyze and fix them

Key Insight: Generation is NOT one-shot. It's iterative:
- Generate some code
- Check if it's correct
- If not, think about what's wrong
- Fix it
- Repeat until satisfied
"""

import re
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from utils.base_agent import BaseAgent, AgentRole
from utils.planning_agent import PlanningAgent
from utils.config import AgentConfig, LLMConfig, LLMProvider
from utils.tool import ToolRegistry
from utils.reasoning import ReActEngine, ReasoningStep
from utils.message import TaskMessage, ResultMessage, create_result_message
from utils.planner import Plan, PlanStep, StepStatus

from ..tools.file_tools import (
    ReadFileTool, WriteFileTool, ListDirTool, FileExistsTool,
    ListGeneratedFilesTool, UpdatePlanTool,
)
from ..tools.code_tools import (
    GrepTool, SearchReplaceTool, LintTool, SyntaxCheckTool,
    EditLinesTool, InsertLinesTool, EditFunctionTool,
)
from ..tools.runtime_tools import (
    RunCommandTool, StartServerTool, StopServerTool, 
    TestAPITool, ListServersTool, CheckFilesExistTool,
    InstallDependenciesTool, GetServerLogsTool,
    QuickTestTool, ShouldTestTool,
)
from ..context import GenerationContext
from ..snippets import get_relevant_snippets, format_snippets_for_prompt


@dataclass
class GenerationStep:
    """Record of a generation step"""
    step_type: str  # "think", "plan", "generate", "reflect", "fix"
    description: str
    input_data: Any = None
    output_data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error: Optional[str] = None


class CodeGeneratorAgent(PlanningAgent):
    """
    Agent that generates code with thinking and planning capabilities.
    
    This agent mimics how a skilled developer works:
    
    1. Understands the task (THINK)
       - What needs to be built?
       - What are the requirements?
       - What files need to be created?
    
    2. Creates a plan (PLAN)
       - Break down into smaller tasks
       - Identify dependencies between files
       - Decide order of generation
    
    3. Generates code iteratively (GENERATE + REFLECT + FIX)
       - Generate a file
       - Check if it's correct
       - If issues, analyze and fix
       - Move to next file
    
    Key difference from simple generators:
    - NOT one-shot: generates, checks, fixes
    - Can use tools to read existing code, grep for patterns
    - Can modify previously generated files if issues found
    """
    
    # System prompt that defines how the agent thinks
    SYSTEM_PROMPT = """You are an expert code generator. You generate high-quality, production-ready code AND test it.

CRITICAL REQUIREMENTS:
1. JSON files MUST be properly formatted with indentation (2 spaces), NOT single-line
2. After generating files, you MUST test them by running the code
3. If tests fail, you MUST fix the issues before proceeding

When generating code:
1. THINK first - understand what's needed
2. Check existing files to maintain consistency  
3. Generate clean, well-documented code
4. For JSON files: ALWAYS use proper formatting with 2-space indentation
5. Verify the code is syntactically correct
6. If you find issues, fix them
7. TEST the code by actually running it!

CRITICAL: When outputting code:
- Output PURE CODE ONLY - no markdown fences, no line numbers
- DO NOT include line numbers like "1|", "  2|", "   3|" in output
- The output should be directly saveable as a file

You have tools available:

FILE TOOLS:
- read_file(path, start_line=N, end_line=M): Read files. Can specify line range for large files.
- write_file: Create new files
- list_dir: List directory contents
- file_exists: Check if a file exists
- list_generated(phase?): List all files generated so far with summaries. USE THIS before trying to read!

PLANNING TOOLS:
- update_plan(action, target, details): Update generation plan mid-execution
  - action='add_file': Add a new file to generate
  - action='remove_file': Skip a planned file
  - action='update_spec': Note that a spec needs updating

SEARCH & EDIT TOOLS:
- grep(pattern, path): *** USE THIS OFTEN! *** Search for patterns across all files
  Examples: grep("class User", "."), grep("def get_db", "."), grep("from.*import", ".")
  Use BEFORE reading files to find WHERE things are defined
- search_replace(path, old_string, new_string): Replace exact text match
- edit_lines(path, start_line, end_line, new_content): Replace specific lines
- insert_lines(path, after_line, content): Insert new lines at position
- edit_function(path, name, new_code): Replace entire function/class by name

WHEN TO USE GREP vs READ_FILE:
- Use GREP when: You need to find where something is defined/used, check imports, find patterns
- Use READ_FILE when: You need to understand the full context of a specific file
- BEST PRACTICE: grep first to find relevant files, then read_file for details

CODE CHECK TOOLS:
- lint: Check code for errors
- syntax_check: Verify code syntax before writing

RUNTIME/TEST TOOLS:
- should_test(): Check if now is a good time to test (returns recommendations)
- quick_test(backend_dir, port?): Quick backend test - starts server, tests endpoints, stops
- run_command(command, cwd?): Run any shell command
- install_dependencies(project_type, cwd): Install pip/npm dependencies
- start_server(name, command, cwd, port): Start a server in background
- stop_server(server_name): Stop a running server
- test_api(method, url, json_data?): Make HTTP request to test endpoint
- get_server_logs(server_name): Get logs from running server

TESTING WORKFLOW:
1. After generating main.py: Call should_test() to check readiness
2. If ready: Call quick_test('app_api') for automated test
3. Or manually: start_server() → test_api() → stop_server()
4. If tests fail: Read error, fix with search_replace or edit_function, retry

WHEN TO TEST:
- After generating main.py or App.tsx (entry points)
- After adding a new router/endpoint
- Before moving to the next phase
- When you're unsure if code works

RUNTIME TOOLS (YOU MUST USE THESE TO TEST YOUR CODE!):
- run_command: Run any shell command (pip install, npm install, python script.py, etc.)
- install_dependencies: Install Python or Node.js dependencies
- start_server: Start a backend or frontend server in background
- stop_server: Stop a running server
- list_servers: List all running servers
- test_api: Make HTTP request to test API endpoint
- get_server_logs: Get logs from a running server if it crashes
- check_files_exist: Verify a list of files exist

MANDATORY WORKFLOW AFTER GENERATING CODE:
1. Generate all code files for the phase
2. Run install_dependencies to install requirements
3. Run start_server to start the backend server
4. Run test_api to test critical endpoints (health, auth/register, auth/login)
5. If ANY test fails:
   a. Use get_server_logs to see errors
   b. Use read_file to examine problematic code
   c. Use search_replace to fix issues
   d. Restart server and re-test
6. Only proceed to next phase after ALL tests pass

DO NOT SKIP TESTING! The code is not done until it runs successfully."""
    
    def __init__(
        self,
        config: AgentConfig,
        output_dir: Path,
        gen_context: Optional[GenerationContext] = None,
        shared_memory: Optional[Any] = None,  # AgentMemory from orchestrator
        event_emitter: Optional[Any] = None,  # EventEmitter for real-time logging
    ):
        super().__init__(config, role=AgentRole.WORKER)
        
        self.output_dir = output_dir
        self.gen_context = gen_context
        self.shared_memory = shared_memory  # Shared across all phases
        self._emitter = event_emitter  # For emitting tool call events
        
        # Generation history
        self.steps: List[GenerationStep] = []
        
        # Override system prompt
        if self._reasoner:
            self._reasoner.system_prompt = self.SYSTEM_PROMPT
        
        # If we have shared memory, use it for reasoning context
        if shared_memory and self._reasoner:
            self._reasoner.memory = shared_memory
    
    async def on_initialize(self) -> None:
        """Initialize with code-specific tools"""
        # Debug removed
        await super().on_initialize()
        
        # Register FILE tools
        # Debug removed
        self.register_tool(ReadFileTool(self.output_dir))
        self.register_tool(WriteFileTool(self.output_dir))
        self.register_tool(ListDirTool(self.output_dir))
        self.register_tool(FileExistsTool(self.output_dir))
        self.register_tool(ListGeneratedFilesTool(self.output_dir, self.gen_context))
        self.register_tool(UpdatePlanTool(self.gen_context))
        self.register_tool(GrepTool(self.output_dir))
        self.register_tool(SearchReplaceTool(self.output_dir))
        self.register_tool(EditLinesTool(self.output_dir))
        self.register_tool(InsertLinesTool(self.output_dir))
        self.register_tool(EditFunctionTool(self.output_dir))
        # Debug removed
        self.register_tool(LintTool(self.output_dir))
        # Debug removed
        self.register_tool(SyntaxCheckTool())
        
        # Debug removed
        
        # Register RUNTIME tools (for testing generated code!)
        self.register_tool(RunCommandTool(self.output_dir))
        self.register_tool(StartServerTool(self.output_dir))
        self.register_tool(StopServerTool())
        self.register_tool(TestAPITool())
        self.register_tool(ListServersTool())
        self.register_tool(CheckFilesExistTool(self.output_dir))
        self.register_tool(InstallDependenciesTool(self.output_dir))
        self.register_tool(GetServerLogsTool())
        self.register_tool(QuickTestTool(self.output_dir))
        self.register_tool(ShouldTestTool(self.output_dir, self.gen_context))
        
        # Debug removed
        all_tool_names = [t.name for t in self._tools.get_all()]
        # Debug removed
        
        self._logger.info(f"CodeGeneratorAgent initialized with {len(self._tools)} tools (including runtime testing tools)")
    
    async def think(self, task: str, context: str = "") -> str:
        """
        Think about a task before acting.
        
        This is like my internal reasoning - analyze the situation,
        consider options, decide on approach.
        
        Uses MEMORY to recall relevant past context!
        """
        self._log_step("think", f"Thinking about: {task}")
        
        if not self._reasoner:
            return f"Analyzed: {task}"
        
        # Recall relevant context from shared memory
        memory_context = ""
        if self.shared_memory:
            # Search for relevant memories
            relevant = self.shared_memory.recall(task[:100], limit=5)
            if relevant:
                memory_context = "\n\nRELEVANT MEMORY:\n"
                for mem in relevant:
                    memory_context += f"- {mem.content[:150]}\n"
            
            # Get recent working context
            working_ctx = self.shared_memory.get_context_string(max_items=5)
            if working_ctx:
                memory_context += f"\n{working_ctx}"
        
        tools_desc = self._get_available_tools_description()
        
        prompt = f"""Think step by step about this task:

TASK: {task}

CONTEXT: {context}
{memory_context}
{tools_desc}

Consider:
1. What exactly needs to be done?
2. What information do I need? (Check memory for relevant past work, or use read_file/grep to gather more)
3. What's the best approach?
4. What could go wrong? (Learn from past fixes in memory)
5. What tools should I use? (read_file, grep, write_file, search_replace, etc.)

Provide your analysis."""

        result = await self._reasoner.run(prompt, context=context)
        
        # Store thinking in memory for future recall
        if self.shared_memory:
            self.shared_memory.working.set("last_analysis", str(result.answer)[:500])
        
        self.steps.append(GenerationStep(
            step_type="think",
            description=task,
            output_data=result.answer,
            success=result.success,
        ))
        
        return result.answer
    
    # ===== INTELLIGENT AGENT METHODS =====
    # These methods make the agent think and act more like a human developer
    
    async def think_before_file(self, file_path: str, purpose: str, existing_files: List[str]) -> dict:
        """
        Think deeply before generating a specific file.
        
        This is called BEFORE each file generation to:
        1. Understand what context is needed
        2. Decide if we need to read other files first
        3. Plan the structure of this file
        4. Anticipate potential issues
        
        Returns a dict with:
        - needs_context: list of files to read first
        - needs_grep: list of patterns to search
        - approach: how to generate this file
        - considerations: things to be careful about
        """
        self._log_step("pre_think", f"Pre-generation thinking for: {file_path}")
        
        if not self._reasoner:
            return {"needs_context": [], "needs_grep": [], "approach": "", "considerations": []}
        
        tools_desc = self._get_available_tools_description()
        
        # Build files list - only show files that actually exist
        if existing_files:
            files_info = f"ALREADY GENERATED FILES (you can read these):\n{chr(10).join(f'- {f}' for f in existing_files[:20])}"
        else:
            files_info = "NO FILES GENERATED YET - this is the first file. Generate based on the description only."
        
        prompt = f"""Before generating {file_path}, I need to think carefully.

*** IMPORTANT: We are creating a NEW project from scratch. ***
*** Only read files that have ALREADY BEEN GENERATED (listed below). ***
*** Do NOT try to read files like pyproject.toml, requirements.txt, etc. - they don't exist yet! ***

FILE TO GENERATE: {file_path}
PURPOSE: {purpose}

{files_info}

{tools_desc}

Think step by step:
1. What ALREADY GENERATED files should I READ for context?
   - ONLY list files from the "ALREADY GENERATED" list above!
   - If no files exist yet, skip this step.
   → Use: read_file(path) or read_file(path, start_line=N, end_line=M) for specific sections

2. What patterns should I SEARCH (grep) for?
   - USE GREP when you need to find WHERE something is defined/used across files
   - grep is faster than reading multiple files when looking for specific patterns
   - Good patterns: "class User", "def get_db", "from calendar_api", "APIRouter"
   → Use: grep(pattern, path) - searches all files in path

3. What's my APPROACH for generating this file?

4. What CONSIDERATIONS/pitfalls should I be careful about?

Respond in this JSON format:
{{
  "needs_context": [],  // Files to read. Empty if first file!
  "needs_grep": [],     // Patterns to search. HIGHLY RECOMMENDED when files exist!
  "approach": "Since [no files exist yet / X files exist], I will...",
  "considerations": ["Make sure to...", "Don't forget to..."]
}}

EXAMPLE for first file (no existing files):
{{
  "needs_context": [],
  "needs_grep": [],
  "approach": "This is the first file. I will generate based on the project description...",
  "considerations": ["Define clear structure", "Include all required fields"]
}}

EXAMPLE when files exist (USE BOTH read and grep!):
{{
  "needs_context": ["env_spec.json", "calendar_api/models.py"],
  "needs_grep": [
    {{"pattern": "class.*Model", "reason": "find all model classes"}},
    {{"pattern": "def get_db", "reason": "find database session dependency"}},
    {{"pattern": "from.*import", "reason": "understand import patterns"}}
  ],
  "approach": "I will read env_spec.json for entities, grep for model classes to understand structure...",
  "considerations": ["Match field names from models", "Use correct imports"]
}}"""

        result = await self._reasoner.run(prompt)
        answer = str(result.answer) if result.answer else "{}"
        
        # Parse JSON response with better error handling
        import json
        thinking = {"needs_context": [], "needs_grep": [], "approach": "", "considerations": []}
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', answer)
            if json_match:
                json_str = json_match.group()
                
                # FIX: Model sometimes returns Python dict syntax (single quotes) instead of JSON
                # Try JSON first, then fall back to ast.literal_eval for Python dict syntax
                try:
                    parsed = json.loads(json_str)
                except json.JSONDecodeError:
                    # Try parsing as Python dict
                    import ast
                    parsed = ast.literal_eval(json_str)
                
                # Ensure all required fields exist
                thinking["needs_context"] = parsed.get("needs_context", [])
                thinking["needs_grep"] = parsed.get("needs_grep", [])
                thinking["approach"] = parsed.get("approach", "")
                thinking["considerations"] = parsed.get("considerations", [])
                
                # Note: We no longer need the nested dict parsing since we now use ast.literal_eval 
                # for the main JSON parsing, which handles Python dict syntax correctly.
            else:
                thinking["approach"] = answer
        except json.JSONDecodeError as e:
            self._log_step("pre_think", f"  JSON parse error: {e}")
            thinking["approach"] = answer
            # Don't try to extract file paths - trust empty defaults if JSON parse failed
        
        # Store in memory
        if self.shared_memory:
            self.shared_memory.working.set(f"pre_think_{file_path}", str(thinking)[:500])
        
        self._log_step("pre_think", f"  Context needed: {thinking.get('needs_context', [])}")
        self._log_step("pre_think", f"  Grep patterns: {len(thinking.get('needs_grep', []))}")
        
        return thinking
    
    async def gather_context_dynamically(self, thinking: dict) -> str:
        """
        Dynamically gather context based on pre-thinking results.
        
        This is like me using read_file and grep tools to understand the codebase
        before making changes.
        """
        context_parts = []
        
        # Read files that the agent decided it needs
        files_to_read = thinking.get("needs_context", [])
        
        # Skip if no files needed (e.g., first file in project)
        if not files_to_read:
            self._log_step("gather", "No context needed - generating from scratch")
            return ""
        
        self._log_step("gather", f"Reading {len(files_to_read)} files...")
        for file_spec in files_to_read[:5]:  # Limit to 5 files
            # Handle both simple paths and line-range specifications
            if isinstance(file_spec, dict):
                file_path = file_spec.get("path", "")
                start_line = file_spec.get("start_line")
                end_line = file_spec.get("end_line")
                reason = file_spec.get("reason", "")
            else:
                file_path = str(file_spec)
                start_line = None
                end_line = None
                reason = ""
            
            if not file_path:
                continue
            
            # Try to resolve the path - LLM might give just "database.py" but file is at "calendar_api/database.py"
            resolved_path = await self._resolve_file_path(file_path)
            
            # Build read_file arguments
            read_args = {"path": resolved_path}
            if start_line is not None:
                read_args["start_line"] = start_line
            if end_line is not None:
                read_args["end_line"] = end_line
            
            result = await self._call_tool_with_log("read_file", **read_args)
            if result.success:
                # read_file returns content with line numbers (e.g., "   1|code")
                # We strip them for context to prevent LLM from mimicking the format
                content = self._strip_line_numbers(result.data)
                
                # Only smart truncate if we're reading the whole file
                if start_line is None and end_line is None:
                    content = self._smart_truncate_file(content, resolved_path)
                else:
                    self._log_step("gather", f"  Read lines {start_line}-{end_line} ({reason})")
                context_parts.append(f"### {resolved_path}\n```\n{content}\n```")
        
        # Search for patterns
        grep_patterns = thinking.get("needs_grep", [])
        self._log_step("gather", f"Running {len(grep_patterns)} grep patterns...")
        for grep_info in grep_patterns[:3]:  # Limit to 3 patterns
            pattern = grep_info.get("pattern", "") if isinstance(grep_info, dict) else str(grep_info)
            if pattern:
                result = await self._call_tool_with_log("grep", pattern=pattern, path=".")
                if result.success and result.data:
                    context_parts.append(f"### Grep: {pattern}\n```\n{result.data[:1500]}\n```")
        
        return "\n\n".join(context_parts)
    
    async def reflect_on_file(self, file_path: str, code: str) -> dict:
        """
        Reflect on a single generated file using TOOL-BASED inspection.
        
        Instead of just passing code to LLM, we:
        1. Run automated checks (syntax, lint)
        2. Let LLM decide what else to check
        3. Execute those checks using tools
        4. LLM analyzes all results
        
        Returns:
        - quality: "good" | "needs_improvement" | "regenerate"
        - issues: list of specific issues
        - suggestions: how to fix
        - checks_performed: what was checked
        """
        self._log_step("reflect", f"Reflecting on: {file_path}")
        
        if not self._reasoner or not code:
            return {"quality": "good", "issues": [], "suggestions": [], "checks_performed": []}
        
        checks_performed = []
        issues_found = []
        
        # ========== GATHER CONTEXT ABOUT PREVIOUS GENERATIONS ==========
        
        # Get list of previously generated files
        previously_generated = []
        if self.gen_context and hasattr(self.gen_context, 'files'):
            previously_generated = list(self.gen_context.files.keys())
        
        # Get relevant memories about this file and related files
        memory_context = ""
        if self.shared_memory:
            # Search for related file generations
            related_memories = self.shared_memory.recall(file_path, limit=5)
            if related_memories:
                memory_context = "RELATED GENERATION HISTORY:\n"
                for mem in related_memories:
                    memory_context += f"- {mem.content[:100]}\n"
            
            # Get recent fix patterns
            fix_patterns = self.shared_memory.long_term.search("FIX PATTERN", limit=3)
            if fix_patterns:
                memory_context += "\nKNOWN FIX PATTERNS:\n"
                for fix in fix_patterns:
                    memory_context += f"- {fix.content[:80]}\n"
        
        self._log_step("reflect", f"  Context: {len(previously_generated)} files generated before this")
        
        # ========== PHASE 1: Automated Tool Checks ==========
        
        # 1. Syntax check - only for supported languages
        language = self._get_language(file_path)
        supported_syntax_languages = {"python", "json"}  # Languages our syntax_check can validate
        
        syntax_ok = True
        if language in supported_syntax_languages:
            self._log_step("reflect", f"  Running syntax check ({language})...")
            # Pass full code to syntax_check, logging will truncate for display
            syntax_result = await self._call_tool_with_log("syntax_check", code=code, language=language)
            
            # Handle None data safely
            syntax_data = syntax_result.data if syntax_result and syntax_result.data else {}
            syntax_ok = syntax_result.success and syntax_data.get("valid", True)
            checks_performed.append("syntax_check")
            
            if not syntax_ok:
                error = syntax_data.get("error", "unknown syntax error")
                issues_found.append(f"SYNTAX ERROR: {error}")
                self._log_step("reflect", f"  Syntax error found: {error}")
        else:
            self._log_step("reflect", f"  Skipping syntax check (not supported for {language})")
        
        # 2. JSON Formatting Check - JSON must be properly indented, not single-line
        if file_path.endswith('.json'):
            self._log_step("reflect", "  Checking JSON formatting...")
            checks_performed.append("json_format_check")
            
            # Check if JSON is minified (single line or no newlines)
            lines = code.strip().split('\n')
            if len(lines) == 1 and len(code) > 100:
                issues_found.append(f"JSON FORMATTING: File is single-line ({len(code)} chars). JSON files must be properly indented for readability.")
                self._log_step("reflect", f"  JSON is minified - needs formatting")
            elif len(lines) < 5 and len(code) > 200:
                issues_found.append(f"JSON FORMATTING: File appears minified ({len(lines)} lines, {len(code)} chars). Please format with proper indentation.")
                self._log_step("reflect", f"  JSON needs better formatting")
            else:
                self._log_step("reflect", f"  JSON formatting OK ({len(lines)} lines)")
        
        # 3. Lint check (if file was written)
        self._log_step("reflect", "  Running lint check...")
        lint_result = await self._call_tool_with_log("lint", path=file_path)
        checks_performed.append("lint")
        
        if lint_result.success and lint_result.data:
            lint_issues = lint_result.data if isinstance(lint_result.data, list) else []
            for issue in lint_issues[:5]:  # Limit to 5
                issues_found.append(f"LINT: {issue}")
        
        # 3. Check file size / completeness
        lines = code.split('\n')
        if len(lines) < 5 and not file_path.endswith(('.json', '.yaml', '.yml')):
            issues_found.append(f"FILE TOO SHORT: Only {len(lines)} lines, might be incomplete")
        
        # Check for TODO/placeholder markers
        if 'TODO' in code or '...' in code or 'FIXME' in code or 'pass  #' in code:
            issues_found.append("INCOMPLETE: Contains TODO, FIXME, or placeholder markers")
        
        # ========== PHASE 2: LLM-Guided Inspection ==========
        
        # Ask LLM what additional checks to perform
        tools_desc = self._get_available_tools_description()
        
        # Build list of previously generated files for context
        prev_files_str = ""
        if previously_generated:
            prev_files_str = f"""
PREVIOUSLY GENERATED FILES IN THIS PROJECT:
{chr(10).join(f"- {f}" for f in previously_generated[:20])}
{"... and more" if len(previously_generated) > 20 else ""}
"""
        
        planning_prompt = f"""I just generated {file_path}. I've already run these automated checks:
- syntax_check: {'PASS' if syntax_ok else 'FAIL'}
- lint: {len([i for i in issues_found if i.startswith('LINT')])} issues found
- completeness: {len(lines)} lines

Issues found so far:
{chr(10).join(f"- {i}" for i in issues_found) if issues_found else "- None yet"}
{prev_files_str}
{memory_context}
{tools_desc}

What ADDITIONAL checks should I perform? Think about:
1. Should I READ any of the previously generated files to verify consistency? 
   (e.g., if this is a router, check if it matches models.py and schemas.py)
2. Should I GREP for specific patterns? (e.g., verify function names are correct)
3. Are there any imports or references to other files that I should verify exist?
4. Based on known fix patterns, any common issues to check for?

Respond in JSON:
{{
  "additional_checks": [
    {{"tool": "read_file", "target": "path/to/file", "reason": "why"}},
    {{"tool": "grep", "pattern": "some_pattern", "reason": "why"}}
  ],
  "quick_assessment": "brief assessment based on current findings"
}}"""

        planning_result = await self._reasoner.run(planning_prompt)
        planning_answer = str(planning_result.answer) if planning_result.answer else "{}"
        
        import json
        additional_checks = []
        try:
            json_match = re.search(r'\{[\s\S]*\}', planning_answer)
            if json_match:
                planning = json.loads(json_match.group())
                additional_checks = planning.get("additional_checks", [])
        except json.JSONDecodeError:
            pass
        
        # Execute additional checks with ITERATIVE EXPLORATION
        # Like me: explore → find something → explore more → find more
        check_results = []
        exploration_history = []  # Track what we've explored
        max_exploration_rounds = 3
        
        for round_num in range(max_exploration_rounds):
            current_round_checks = additional_checks if round_num == 0 else []
            
            # Execute current round's checks
            round_findings = []
            for check in current_round_checks[:5]:
                tool = check.get("tool", "")
                
                if tool == "read_file":
                    target = check.get("target", "")
                    reason = check.get("reason", "")
                    if target and target not in [h.get("target") for h in exploration_history]:
                        self._log_step("reflect", f"  [Round {round_num+1}] Reading {target} ({reason[:30]}...)")
                        result = await self._call_tool_with_log("read_file", path=target)
                        if result.success:
                            content_preview = result.data[:500]
                            check_results.append(f"READ {target}: {len(result.data)} chars")
                            checks_performed.append(f"read_file:{target}")
                            round_findings.append(f"READ {target}: {content_preview}")
                            exploration_history.append({"tool": "read_file", "target": target, "result": content_preview})
                
                elif tool == "grep":
                    pattern = check.get("pattern", "")
                    reason = check.get("reason", "")
                    if pattern and pattern not in [h.get("pattern") for h in exploration_history]:
                        self._log_step("reflect", f"  [Round {round_num+1}] Grep '{pattern}' ({reason[:30]}...)")
                        result = await self._call_tool_with_log("grep", pattern=pattern, path=".")
                        if result.success:
                            matches = result.data[:500] if result.data else "no matches"
                            check_results.append(f"GREP '{pattern}': {matches}")
                            checks_performed.append(f"grep:{pattern}")
                            round_findings.append(f"GREP '{pattern}': {matches}")
                            exploration_history.append({"tool": "grep", "pattern": pattern, "result": matches})
            
            # If we found something, ask LLM if it wants to explore more
            if round_findings and round_num < max_exploration_rounds - 1:
                continue_prompt = f"""Based on exploration round {round_num + 1}, I found:

{chr(10).join(round_findings)}

Do I need to explore further? Maybe:
- Read another file to verify something I found
- Grep for a pattern I noticed
- Check if something is missing

Respond in JSON:
{{
  "should_continue": true/false,
  "reason": "why continue or stop",
  "next_checks": [
    {{"tool": "read_file", "target": "path", "reason": "why"}},
    {{"tool": "grep", "pattern": "pattern", "reason": "why"}}
  ]
}}"""
                
                continue_result = await self._reasoner.run(continue_prompt)
                continue_answer = str(continue_result.answer) if continue_result.answer else "{}"
                
                try:
                    json_match = re.search(r'\{[\s\S]*\}', continue_answer)
                    if json_match:
                        continue_decision = json.loads(json_match.group())
                        if continue_decision.get("should_continue", False):
                            additional_checks = continue_decision.get("next_checks", [])
                            self._log_step("reflect", f"  [Continue] {continue_decision.get('reason', 'Exploring more...')}")
                        else:
                            self._log_step("reflect", f"  [Stop] {continue_decision.get('reason', 'Exploration complete')}")
                            break
                    else:
                        break
                except json.JSONDecodeError:
                    break
            else:
                break
        
        # ========== PHASE 3: Final Assessment ==========
        
        # Prepare summary for final assessment (NOT the full code!)
        code_summary = f"""
FILE: {file_path}
LINES: {len(lines)}
FIRST 20 LINES:
```
{chr(10).join(lines[:20])}
```

LAST 10 LINES:
```
{chr(10).join(lines[-10:])}
```
"""
        
        final_prompt = f"""Based on all checks performed on {file_path}, give your final assessment.

AUTOMATED CHECK RESULTS:
- Syntax: {'PASS' if syntax_ok else 'FAIL'}
- Issues found: {issues_found if issues_found else 'None'}

ADDITIONAL CHECK RESULTS:
{chr(10).join(check_results) if check_results else '- No additional checks performed'}

CODE SUMMARY (not full code):
{code_summary}

Provide final assessment in JSON:
{{
  "quality": "good" | "needs_improvement" | "regenerate",
  "issues": ["specific issue 1", "specific issue 2"],
  "suggestions": ["how to fix 1", "how to fix 2"],
  "confidence": "high" | "medium" | "low"
}}"""

        final_result = await self._reasoner.run(final_prompt)
        final_answer = str(final_result.answer) if final_result.answer else "{}"
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', final_answer)
            if json_match:
                reflection = json.loads(json_match.group())
            else:
                reflection = {"quality": "good", "issues": issues_found, "suggestions": []}
        except json.JSONDecodeError:
            reflection = {"quality": "good", "issues": issues_found, "suggestions": []}
        
        # Merge automated issues with LLM assessment
        # BUT: If syntax_check tool passed, filter out LLM-reported syntax errors
        llm_issues = reflection.get("issues", [])
        if syntax_ok:
            # Remove false positive syntax errors from LLM
            llm_issues = [
                issue for issue in llm_issues 
                if "SYNTAX" not in issue.upper() and "UNTERMINATED" not in issue.upper()
            ]
        
        all_issues = list(set(issues_found + llm_issues))
        reflection["issues"] = all_issues
        reflection["checks_performed"] = checks_performed
        
        # Override quality if we found critical issues
        # Only trust SYNTAX ERRORs from automated checks, not LLM
        automated_syntax_errors = [i for i in issues_found if "SYNTAX ERROR" in i]
        if automated_syntax_errors:
            reflection["quality"] = "regenerate"
        elif len(all_issues) > 3:
            reflection["quality"] = "needs_improvement"
        
        self._log_step("reflect", f"  Quality: {reflection.get('quality', 'unknown')}")
        self._log_step("reflect", f"  Checks: {checks_performed}")
        if all_issues:
            self._log_step("reflect", f"  Issues: {all_issues[:3]}...")
        
        return reflection
    
    async def decide_next_action(self, current_state: dict) -> dict:
        """
        Decide what to do next based on current state.
        
        This gives the agent agency to decide its own next steps,
        rather than following a rigid script.
        
        Returns:
        - action: "generate" | "read" | "grep" | "fix" | "done"
        - target: what to act on
        - reason: why this action
        """
        if not self._reasoner:
            return {"action": "done", "target": None, "reason": "No reasoner"}
        
        tools_desc = self._get_available_tools_description()
        
        prompt = f"""Based on the current state, decide what to do next.

CURRENT STATE:
- Phase: {current_state.get('phase', 'unknown')}
- Files generated: {current_state.get('files_generated', [])}
- Files remaining: {current_state.get('files_remaining', [])}
- Last action result: {current_state.get('last_result', 'none')}
- Issues found: {current_state.get('issues', [])}

{tools_desc}

What should I do next?

Options:
1. "generate" - Generate the next file (use write_file)
2. "read" - Read a file to gather more context (use read_file)
3. "grep" - Search for patterns in codebase (use grep)
4. "fix" - Fix issues in a generated file (use search_replace)
5. "done" - Phase is complete

Respond in JSON:
{{
  "action": "generate" | "read" | "grep" | "fix" | "done",
  "target": "file_path or pattern",
  "reason": "why this action"
}}"""

        result = await self._reasoner.run(prompt)
        answer = str(result.answer) if result.answer else "{}"
        
        import json
        try:
            json_match = re.search(r'\{[\s\S]*\}', answer)
            if json_match:
                decision = json.loads(json_match.group())
            else:
                decision = {"action": "done", "target": None, "reason": "Could not parse"}
        except json.JSONDecodeError:
            decision = {"action": "done", "target": None, "reason": "Parse error"}
        
        self._log_step("decide", f"Next action: {decision.get('action')} on {decision.get('target')}")
        
        return decision
    
    def _get_language(self, file_path: str) -> str:
        """Get language from file extension"""
        ext_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
        }
        for ext, lang in ext_map.items():
            if file_path.endswith(ext):
                return lang
        return "text"
    
    def _strip_line_numbers(self, code: str) -> str:
        """
        Strip line numbers from code if present.
        
        LLMs sometimes output code with embedded line numbers like:
        "   1|from fastapi import FastAPI"
        "   2|from datetime import datetime"
        
        This method removes such line number prefixes.
        """
        lines = code.split("\n")
        cleaned_lines = []
        
        # Pattern: optional spaces, digits, pipe character
        # Examples: "   1|", "  10|", " 100|", "1|"
        line_number_pattern = re.compile(r'^\s*\d+\|')
        
        has_line_numbers = False
        for line in lines:
            if line_number_pattern.match(line):
                has_line_numbers = True
                # Remove the line number prefix
                cleaned = line_number_pattern.sub('', line)
                cleaned_lines.append(cleaned)
            else:
                cleaned_lines.append(line)
        
        if has_line_numbers:
            self._log_step("clean", "Stripped line numbers from generated code")
            return "\n".join(cleaned_lines)
        
        return code
    
    def _get_available_tools_description(self) -> str:
        """
        Get a description of all available tools for the agent.
        
        This is included in prompts so the LLM knows what capabilities it has.
        """
        tools_desc = """
AVAILABLE TOOLS (you can request to use these):

READING & SEARCHING (USE BOTH!):
- read_file(path): Read a specific file to understand its full content
- grep(pattern, path): ***IMPORTANT*** Search for patterns across ALL files
  - ALWAYS use grep when files exist to find definitions, imports, patterns
  - Example patterns: "class User", "def get_", "from calendar_api import"

OTHER TOOLS:
- write_file(path, content): Create or overwrite a file
- list_dir(path): List files in a directory
- file_exists(path): Check if a file exists
- search_replace(path, old_string, new_string): Make targeted edits
- lint(path): Check code for syntax errors
- syntax_check(code, language): Verify code syntax before writing

HOW TO USE TOOLS:
- "needs_context": List of files to READ completely
- "needs_grep": List of patterns to SEARCH across all files
  Format: [{"pattern": "class.*Model", "reason": "find all models"}]
  
BEST PRACTICE: Use GREP first to find where things are, then READ specific files!
"""
        return tools_desc
    
    async def plan_phase_files(
        self,
        phase: str,
        phase_description: str,
        env_name: str,
        env_description: str,
        existing_files: List[str],
        reference_files: Optional[List[dict]] = None,
    ) -> List[dict]:
        """
        DYNAMICALLY plan what files to generate for a phase.
        
        Instead of using a hardcoded file list, the LLM decides:
        - What files are needed for this phase
        - In what order to generate them
        - Dependencies between files
        - Purpose and instructions for each
        
        Args:
            phase: Current phase name (design, backend, frontend, etc.)
            phase_description: What this phase should accomplish
            env_name: Name of the environment being generated
            env_description: Description of the environment
            existing_files: Files already generated in previous phases
            reference_files: Optional hints about expected files (as guidance, not requirement)
        
        Returns:
            List of file specs: [{"path": ..., "purpose": ..., "instructions": ..., "dependencies": [...]}]
        """
        self._log_step("plan_files", f"Dynamically planning files for phase: {phase}")
        
        if not self._reasoner:
            # Fallback to reference files if no reasoner
            return reference_files or []
        
        # Build context about existing project structure
        existing_context = ""
        if existing_files:
            existing_context = "EXISTING FILES:\n" + "\n".join(f"- {f}" for f in existing_files[:30])
        
        # Reference hints (optional guidance - NOT requirements!)
        reference_hint = ""
        if reference_files:
            reference_hint = """
REFERENCE FILES (OPTIONAL GUIDANCE - You can modify, add, or remove from this list!):
These are just suggestions based on typical projects. You should:
- ADD files if you think more are needed
- REMOVE files if they're not necessary
- MODIFY the order based on dependencies
- CHANGE instructions if you have better ideas
"""
            for ref in reference_files[:10]:
                reference_hint += f"- {ref.get('path', 'unknown')}: {ref.get('purpose', '')}\n"
        
        tools_desc = self._get_available_tools_description()
        
        prompt = f"""Plan what files to generate for the {phase} phase.

PROJECT: {env_name}
DESCRIPTION: {env_description}

PHASE: {phase}
PHASE GOAL: {phase_description}

{existing_context}
{reference_hint}
{tools_desc}

Based on the project requirements, decide:
1. What files are ACTUALLY needed for this phase?
2. In what ORDER should they be generated? (dependencies first)
3. What is the PURPOSE of each file?
4. What INSTRUCTIONS should guide the generation?
5. What are the DEPENDENCIES (other files needed for context)?

You can:
- Add files not in the reference list if needed
- Remove files from the reference that aren't necessary
- Reorder files based on dependencies
- Add more specific instructions

Respond in JSON format:
{{
  "files": [
    {{
      "path": "relative/path/to/file.py",
      "purpose": "Brief description of what this file does",
      "instructions": "Detailed instructions for generating this file",
      "dependencies": ["path/to/dependency1.py", "path/to/dependency2.py"]
    }},
    ...
  ],
  "reasoning": "Brief explanation of why these files are needed"
}}"""

        result = await self._reasoner.run(prompt)
        answer = str(result.answer) if result.answer else "{}"
        
        import json
        try:
            json_match = re.search(r'\{[\s\S]*\}', answer)
            if json_match:
                planning = json.loads(json_match.group())
                files = planning.get("files", [])
                reasoning = planning.get("reasoning", "")
                
                self._log_step("plan_files", f"Planned {len(files)} files: {reasoning[:100]}...")
                
                # Validate and clean up file specs
                valid_files = []
                for f in files:
                    if "path" in f:
                        valid_files.append({
                            "path": f["path"],
                            "purpose": f.get("purpose", ""),
                            "instructions": f.get("instructions", ""),
                            "dependencies": f.get("dependencies", []),
                        })
                
                return valid_files
        except json.JSONDecodeError:
            self._log_step("plan_files", "Failed to parse planning response, using reference")
        
        # Fallback to reference files
        return reference_files or []
    
    async def plan_generation(
        self,
        task_description: str,
        target_files: Optional[List[str]] = None,
    ) -> Plan:
        """
        Create a plan for generating files.
        
        Unlike simple generators, we plan:
        - Which files to generate
        - In what order (dependencies matter)
        - What each file should contain
        """
        self._log_step("plan", f"Planning generation for: {task_description}")
        
        # Use parent class planner if available
        if self._planner:
            plan = await self.create_plan(
                task=task_description,
                context=f"Output directory: {self.output_dir}\nTarget files: {target_files}",
            )
            return plan
        
        # Fallback: create simple plan
        steps = []
        if target_files:
            for i, file_path in enumerate(target_files):
                steps.append(PlanStep(
                    step_id=str(i + 1),
                    description=f"Generate {file_path}",
                    action="generate_file",
                    action_input={"path": file_path},
                    dependencies=[str(i)] if i > 0 else [],
                ))
        
        return Plan(
            task=task_description,
            steps=steps,
        )
    
    async def generate_file(
        self,
        file_path: str,
        purpose: str,
        instructions: str,
        dependencies: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Generate a single file with iterative refinement.
        
        Process:
        1. Read any dependency files for context
        2. Generate initial code
        3. Verify syntax
        4. If issues, fix and retry
        5. Write file
        """
        self._log_step("generate", f"Generating: {file_path}")
        
        # Step 1: Gather context from dependencies
        dep_context = ""
        if dependencies:
            for dep in dependencies:
                result = await self.call_tool("read_file", path=dep)
                if result.success:
                    dep_context += f"\n--- {dep} ---\n{result.data[:2000]}\n"
        
        # Step 2: Recall relevant memory context
        memory_context = ""
        if self.shared_memory:
            # Search for related files, schemas, patterns
            relevant = self.shared_memory.recall(f"{purpose} {file_path}", limit=5)
            if relevant:
                memory_context = "\n\nRELATED CONTEXT FROM MEMORY:\n"
                for mem in relevant:
                    memory_context += f"- {mem.content[:200]}\n"
            
            # Check for similar fix patterns
            if "tsx" in file_path or "ts" in file_path:
                fixes = self.shared_memory.long_term.search("FIX PATTERN", limit=3)
                if fixes:
                    memory_context += "\nKNOWN FIX PATTERNS:\n"
                    for fix in fixes:
                        memory_context += f"- {fix.content[:150]}\n"
        
        # Step 3: Get relevant code snippets as examples
        snippets = get_relevant_snippets(file_path, purpose)
        snippets_section = format_snippets_for_prompt(snippets) if snippets else ""
        
        # Step 4: Generate code with format-specific instructions
        format_instructions = ""
        if file_path.endswith(".json"):
            format_instructions = """
CRITICAL JSON FORMAT REQUIREMENTS:
- Output VALID JSON only, NOT Python dict
- Use DOUBLE QUOTES (") for ALL strings - NOT single quotes (')
- Use lowercase: null, true, false - NOT Python None, True, False
- NO trailing commas before } or ]
- The output must be parseable by JSON.parse()
"""
        elif file_path.endswith((".ts", ".tsx")):
            format_instructions = """
TypeScript/React Requirements:
- Use proper TypeScript syntax with type annotations
- Ensure all JSX elements are properly closed
- Use React hooks properly
"""
        
        # Special handling for common problematic files
        if "tsconfig" in file_path.lower() and file_path.endswith(".json"):
            format_instructions += """
TSCONFIG SPECIFIC REQUIREMENTS:
- This is a TypeScript configuration file, NOT a data file
- Use ONLY valid tsconfig.json options (compilerOptions, include, exclude, etc.)
- Valid compilerOptions include: target, module, moduleResolution, strict, esModuleInterop, skipLibCheck, etc.
- For tsconfig.node.json specifically:
  - Use "composite": true for project references
  - Use "module": "ESNext" and "moduleResolution": "bundler" for Vite projects
  - Include only "vite.config.ts" in the include array
  - Example:
    {
      "compilerOptions": {
        "composite": true,
        "skipLibCheck": true,
        "module": "ESNext",
        "moduleResolution": "bundler",
        "allowSyntheticDefaultImports": true,
        "strict": true
      },
      "include": ["vite.config.ts"]
    }
"""
        
        prompt = f"""Generate code for: {file_path}

PURPOSE: {purpose}
{format_instructions}
INSTRUCTIONS:
{instructions}

CONTEXT FROM EXISTING FILES:
{dep_context[:4000] if dep_context else "No dependencies"}
{memory_context}
{snippets_section}

CRITICAL OUTPUT REQUIREMENTS:
1. Generate ONLY the raw code - NO markdown fences (```), NO line numbers, NO explanations
2. DO NOT include line number prefixes like "1|", "  2|", "   3|" etc.
3. Start directly with the code content (e.g., "from fastapi import..." NOT "   1|from fastapi import...")
4. The output should be directly saveable as a file without any preprocessing

The code must be syntactically correct and production-ready.
Follow the patterns shown in the code examples above if provided."""

        if not self._reasoner:
            return None
        
        # Use ReAct to generate with potential tool use
        result = await self._reasoner.run(
            task=prompt,
            context=f"Generating {file_path}",
        )
        
        code = str(result.answer) if result.answer else ""
        
        # Clean up markdown fences if present
        if code.startswith("```"):
            lines = code.split("\n")
            # Remove first line (```json, ```python, etc.)
            if len(lines) > 1:
                lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code = "\n".join(lines)
        
        # CRITICAL: Strip line numbers if present (e.g., "   1|code" -> "code")
        # LLMs sometimes output code with line numbers embedded
        code = self._strip_line_numbers(code)
        
        # For JSON files, convert Python dict format to JSON
        if file_path.endswith(".json"):
            code = self._fix_python_to_json(code)
        
        # Step 2.5: Check for truncation and continue if needed
        code = await self._ensure_complete_code(code, file_path, purpose)
        
        # Step 3: Verify syntax - only for supported languages
        supported_syntax_languages = {".py": "python", ".json": "json"}
        file_ext = "." + file_path.split(".")[-1] if "." in file_path else ""
        
        if file_ext in supported_syntax_languages:
            lang = supported_syntax_languages[file_ext]
            check_result = await self.call_tool("syntax_check", code=code, language=lang)
            
            # Handle None data safely
            check_data = check_result.data if check_result and check_result.data else {}
            if check_result.success and not check_data.get("valid", True):
                # Step 4: Fix syntax error
                error = check_data.get("error", "Unknown error")
                self._log_step("fix", f"Fixing syntax error in {file_path}: {error}")
                
                fix_prompt = f"""The generated code has a syntax error:
ERROR: {error}

ORIGINAL CODE:
{code}

Fix the error and provide the corrected code. Output ONLY the fixed code."""

                fix_result = await self._reasoner.run(fix_prompt)
                fixed_code = str(fix_result.answer) if fix_result.answer else ""
                if fixed_code:
                    # Clean up the fix result - remove markdown fences and line numbers
                    if fixed_code.startswith("```"):
                        lines = fixed_code.split("\n")
                        lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                        fixed_code = "\n".join(lines)
                    fixed_code = self._strip_line_numbers(fixed_code)
                    code = fixed_code
        
        # Step 5: Format JSON files with proper indentation
        if file_path.endswith('.json'):
            try:
                data = json.loads(code)
                code = json.dumps(data, indent=2, ensure_ascii=False)
                self._log_step("generate", "  Formatted JSON with 2-space indentation")
            except json.JSONDecodeError as e:
                self._log_step("generate", f"  WARNING: JSON formatting failed: {e}")
        
        # Step 6: Write file
        write_result = await self.call_tool("write_file", path=file_path, content=code)
        
        if write_result.success:
            self.steps.append(GenerationStep(
                step_type="generate",
                description=f"Generated {file_path}",
                output_data=f"{len(code)} bytes",
                success=True,
            ))
            
            # Update context if available
            if self.gen_context:
                self.gen_context.add_file(file_path, code, self.gen_context.current_phase)
            
            # Generate and store file summary for quick reference
            file_summary = self._generate_file_summary(code, file_path)
            if self.shared_memory:
                self.shared_memory.remember(
                    file_summary,
                    memory_type="working",
                    metadata={"type": "file_summary", "path": file_path},
                    importance=0.8,
                )
                self._log_step("generate", f"  Stored file summary ({len(file_summary)} chars)")
            
            # Check if this is a key file that should trigger testing consideration
            await self._suggest_testing_if_appropriate(file_path)
            
            return code
        else:
            self.steps.append(GenerationStep(
                step_type="generate",
                description=f"Failed to generate {file_path}",
                error=write_result.error_message,
                success=False,
            ))
            return None
    
    async def reflect_on_generation(
        self,
        generated_files: List[str],
        enable_runtime_test: bool = False,  # Optional: run and test the code
        test_config: Optional[Dict[str, Any]] = None,  # Config for runtime testing
    ) -> List[str]:
        """
        Reflect on generated code - find issues.
        
        This is like my process of reviewing code after writing:
        - Check for syntax errors
        - Check imports match exports
        - Check for consistency
        - Check for MISSING files that are imported
        - (OPTIONAL) Run the code and test it
        
        Args:
            generated_files: List of file paths to check
            enable_runtime_test: If True, try to run the code and test it
            test_config: Configuration for testing (env_name, backend_dir, etc.)
        """
        self._log_step("reflect", f"Reflecting on {len(generated_files)} files")
        
        issues = []
        
        # Run lint on all files
        for file_path in generated_files:
            lint_result = await self.call_tool("lint", path=file_path)
            
            if lint_result.success:
                data = lint_result.data
                if isinstance(data, dict) and not data.get("passed", True):
                    for issue in data.get("issues", []):
                        issues.append(f"{file_path}: {issue}")
        
        # Check TypeScript/TSX imports - THIS IS CRITICAL
        tsx_files = [f for f in generated_files if f.endswith((".tsx", ".ts"))]
        for tsx_file in tsx_files:
            read_result = await self.call_tool("read_file", path=tsx_file)
            if read_result.success:
                content = read_result.data
                
                # Find relative imports: import X from './path/File'
                imports = re.findall(r"from\s+['\"](\./[^'\"]+)['\"]", content)
                
                for imp in imports:
                    # Convert import path to file path
                    # './pages/Register' -> check if pages/Register.tsx exists
                    imp_path = imp.replace("./", "")
                    
                    # Get base directory of current file
                    base_dir = str(Path(tsx_file).parent)
                    
                    # Possible file paths
                    possible_paths = [
                        f"{base_dir}/{imp_path}.tsx",
                        f"{base_dir}/{imp_path}.ts",
                        f"{base_dir}/{imp_path}/index.tsx",
                    ]
                    
                    # Check if any exists
                    found = False
                    for possible in possible_paths:
                        exists_result = await self.call_tool("file_exists", path=possible)
                        if exists_result.success and exists_result.data.get("exists"):
                            found = True
                            break
                    
                    if not found:
                        issues.append(f"MISSING FILE: {tsx_file} imports '{imp}' but file does not exist")
        
        # Check for incomplete files (too short might indicate truncation)
        for file_path in generated_files:
            read_result = await self.call_tool("read_file", path=file_path)
            if read_result.success:
                content = read_result.data
                lines = content.strip().split("\n")
                
                # Check if file seems incomplete
                if file_path.endswith(".py"):
                    # Python file should have at least some content
                    if len(lines) < 3:
                        issues.append(f"INCOMPLETE: {file_path} seems incomplete ({len(lines)} lines)")
                    # Check if it ends with incomplete syntax
                    last_line = lines[-1].strip() if lines else ""
                    if last_line.endswith(":") or last_line.endswith(","):
                        issues.append(f"TRUNCATED: {file_path} appears truncated (ends with '{last_line[-20:]}')")
                
                elif file_path.endswith((".tsx", ".ts")):
                    # Check bracket balance
                    open_braces = content.count("{")
                    close_braces = content.count("}")
                    if open_braces != close_braces:
                        issues.append(f"UNBALANCED: {file_path} has unbalanced braces ({open_braces} open, {close_braces} close)")
        
        # ========== OPTIONAL RUNTIME TESTING ==========
        # If enabled, actually run the code and test it
        if enable_runtime_test and test_config:
            self._log_step("reflect", "[RUNTIME TEST] Testing generated code...")
            
            runtime_issues = await self._run_runtime_tests(generated_files, test_config)
            
            if runtime_issues:
                self._log_step("reflect", f"  [RUNTIME ISSUES] Found {len(runtime_issues)} runtime issues")
                issues.extend([f"RUNTIME: {i}" for i in runtime_issues])
            else:
                self._log_step("reflect", "  [RUNTIME OK] Code runs successfully")
        
        self.steps.append(GenerationStep(
            step_type="reflect",
            description=f"Found {len(issues)} issues",
            output_data=issues,
            success=len(issues) == 0,
        ))
        
        return issues
    
    async def _run_runtime_tests(
        self,
        generated_files: List[str],
        config: Dict[str, Any],
    ) -> List[str]:
        """
        Run runtime tests on generated code.
        
        This can:
        1. Install dependencies
        2. Start servers
        3. Test API endpoints
        4. Collect errors
        5. Cleanup
        
        Returns list of runtime issues found.
        """
        runtime_issues = []
        env_name = config.get("env_name", "")
        backend_dir = config.get("backend_dir", f"{env_name}_api")
        
        # Check if this looks like a backend phase
        backend_files = [f for f in generated_files if "_api/" in f or f.endswith(("main.py", "database.py"))]
        if not backend_files:
            self._log_step("runtime", "  No backend files to test")
            return runtime_issues
        
        try:
            # Step 1: Install dependencies
            self._log_step("runtime", "  [1/4] Installing dependencies...")
            install_result = await self._call_tool_with_log(
                "install_dependencies",
                project_type="python",
                cwd=backend_dir,
            )
            
            if not install_result.success:
                error = install_result.data.get("stderr", "Install failed")
                runtime_issues.append(f"Dependency install failed: {error[:100]}")
                return runtime_issues
            
            # Step 2: Start server
            self._log_step("runtime", "  [2/4] Starting server...")
            start_result = await self._call_tool_with_log(
                "start_server",
                server_name="test_backend",  # Renamed to avoid conflict with call_tool's 'name' param
                command=f"{sys.executable} -m uvicorn main:app --host 0.0.0.0 --port 8000",
                cwd=backend_dir,
                port=8000,
                wait_for_ready=30,
            )
            
            if not start_result.success:
                error = start_result.data.get("error", "") or start_result.data.get("stderr", "")
                runtime_issues.append(f"Server start failed: {error[:200]}")
                
                # Analyze the error for common issues
                if "ModuleNotFoundError" in error:
                    module = re.search(r"No module named '(\S+)'", error)
                    if module:
                        runtime_issues.append(f"Missing import: {module.group(1)}")
                elif "ImportError" in error:
                    runtime_issues.append(f"Import error in code")
                elif "SyntaxError" in error:
                    runtime_issues.append(f"Syntax error in Python code")
                
                return runtime_issues
            
            # Step 3: Test endpoints
            self._log_step("runtime", "  [3/4] Testing API endpoints...")
            
            # Test health
            health_result = await self._call_tool_with_log(
                "test_api",
                method="GET",
                url="http://localhost:8000/health",
            )
            if not health_result.success:
                runtime_issues.append("Health endpoint not responding")
            
            # Test register (if auth exists)
            register_result = await self._call_tool_with_log(
                "test_api",
                method="POST",
                url="http://localhost:8000/auth/register",
                json_data={"email": "test@test.com", "password": "testpass123", "name": "Test"},
            )
            if not register_result.success:
                status = register_result.data.get("status_code", "unknown")
                if status == 404:
                    runtime_issues.append("Auth register endpoint missing (404)")
                elif status != 400:  # 400 might mean user exists, which is OK
                    error = register_result.data.get("response", register_result.data.get("error", ""))
                    runtime_issues.append(f"Auth register failed ({status}): {str(error)[:100]}")
            
            # Step 4: Cleanup
            self._log_step("runtime", "  [4/4] Cleanup...")
            await self._call_tool_with_log("stop_server", server_name="test_backend")
            
        except Exception as e:
            runtime_issues.append(f"Runtime test exception: {str(e)[:100]}")
            # Try to cleanup
            await self._call_tool_with_log("stop_server", server_name="test_backend")
        
        return runtime_issues
    
    async def fix_issues(
        self,
        issues: List[str],
    ) -> List[str]:
        """
        Fix identified issues.
        
        For each issue:
        1. Understand what's wrong
        2. Locate the problematic code
        3. Generate a fix
        4. Apply the fix
        
        Special handling for:
        - MISSING FILE: Create the missing file
        - TRUNCATED/INCOMPLETE: Regenerate the file
        """
        self._log_step("fix", f"Fixing {len(issues)} issues")
        
        fixes_applied = []
        
        for issue in issues[:5]:  # Limit to prevent infinite loops
            
            # Handle MISSING FILE issues - CREATE the file
            if issue.startswith("MISSING FILE:"):
                # Parse: "MISSING FILE: src/App.tsx imports './pages/Register' but file does not exist"
                match = re.search(r"imports '([^']+)'", issue)
                if match:
                    import_path = match.group(1)  # './pages/Register'
                    
                    # Find which file has the import
                    source_match = re.search(r"MISSING FILE: ([^\s]+)", issue)
                    if source_match:
                        source_file = source_match.group(1)
                        source_dir = str(Path(source_file).parent)
                        
                        # Convert './pages/Register' to actual path
                        rel_path = import_path.replace("./", "")
                        target_path = f"{source_dir}/{rel_path}.tsx"
                        
                        # Generate the missing file
                        component_name = Path(rel_path).name
                        self._log_step("fix", f"Creating missing file: {target_path}")
                        
                        code = await self._generate_missing_component(component_name, target_path)
                        if code:
                            write_result = await self.call_tool("write_file", path=target_path, content=code)
                            if write_result.success:
                                fixes_applied.append(f"Created missing file: {target_path}")
                                # Store fix pattern in memory for learning
                                if self.shared_memory:
                                    self.shared_memory.remember(
                                        f"FIX PATTERN: Missing import file -> Create the component file {target_path}",
                                        memory_type="long",
                                        metadata={"type": "fix_pattern", "issue": "missing_import"},
                                        importance=0.85,
                                    )
                continue
            
            # Handle TRUNCATED/INCOMPLETE issues - REGENERATE
            if issue.startswith("TRUNCATED:") or issue.startswith("INCOMPLETE:"):
                match = re.search(r"(?:TRUNCATED|INCOMPLETE): ([^\s]+)", issue)
                if match:
                    file_path = match.group(1)
                    self._log_step("fix", f"Regenerating truncated file: {file_path}")
                    
                    # Get the original purpose and regenerate
                    code = await self._regenerate_file(file_path)
                    if code:
                        write_result = await self.call_tool("write_file", path=file_path, content=code)
                        if write_result.success:
                            fixes_applied.append(f"Regenerated: {file_path}")
                            # Store fix pattern
                            if self.shared_memory:
                                self.shared_memory.remember(
                                    f"FIX PATTERN: Truncated/incomplete code -> Regenerate file {file_path} completely",
                                    memory_type="long",
                                    metadata={"type": "fix_pattern", "issue": "truncation"},
                                    importance=0.8,
                                )
                continue
            
            # Handle IMPORT errors - missing module might need new file creation OR import fix
            if issue.startswith("IMPORT:") or issue.startswith("IMPORT ERROR:"):
                # Parse: "IMPORT: Missing module 'xxx'" or "IMPORT ERROR: ModuleNotFoundError: No module named 'xxx'"
                match = re.search(r"No module named ['\"]?([^'\"]+)['\"]?", issue)
                if not match:
                    match = re.search(r"Missing module ['\"](\S+)['\"]", issue)
                
                if match:
                    missing_module = match.group(1)
                    self._log_step("fix", f"[IMPORT FIX] Missing module: {missing_module}")
                    
                    # Check if this is a "relative import needed" issue
                    # e.g., "calendar_api" not found when running from calendar_api/ directory
                    if "relative imports" in issue.lower() or "should be relative" in issue.lower():
                        # Need to fix imports in main.py and other files
                        self._log_step("fix", f"  [FIX] Converting absolute imports to relative imports")
                        
                        # Find all Python files with absolute imports of this module
                        backend_dir = f"{self.gen_context.name}_api" if self.gen_context else ""
                        files_to_fix = ["main.py"]
                        
                        for file_name in files_to_fix:
                            file_path = f"{backend_dir}/{file_name}" if backend_dir else file_name
                            read_result = await self.call_tool("read_file", path=file_path)
                            if read_result.success:
                                content = read_result.data
                                # Replace absolute imports with relative
                                new_content = content.replace(f"from {missing_module}.", "from .")
                                new_content = new_content.replace(f"from {missing_module} import", "from . import")
                                
                                if new_content != content:
                                    write_result = await self.call_tool("write_file", path=file_path, content=new_content)
                                    if write_result.success:
                                        fixes_applied.append(f"Fixed imports in {file_path}: absolute → relative")
                                        self._log_step("fix", f"  [OK] Fixed imports in {file_path}")
                        continue
                    
                    # Check if this is an internal module (should be created)
                    # vs external module (should be installed)
                    if missing_module.startswith(self.gen_context.name if self.gen_context else ""):
                        # Internal module - need to create it
                        module_path = missing_module.replace(".", "/") + ".py"
                        self._log_step("fix", f"  Creating missing internal module: {module_path}")
                        
                        # Generate the module
                        code = await self._generate_missing_module(missing_module, module_path)
                        if code:
                            write_result = await self.call_tool("write_file", path=module_path, content=code)
                            if write_result.success:
                                fixes_applied.append(f"NEW FILE: {module_path}")
                    else:
                        # External module - add to requirements
                        self._log_step("fix", f"  Adding external dependency: {missing_module}")
                        req_path = f"{self.gen_context.name}_api/requirements.txt" if self.gen_context else "requirements.txt"
                        
                        # Read current requirements
                        read_result = await self.call_tool("read_file", path=req_path)
                        if read_result.success:
                            current = read_result.data
                            if missing_module not in current:
                                new_content = current.strip() + f"\n{missing_module}\n"
                                write_result = await self.call_tool("write_file", path=req_path, content=new_content)
                                if write_result.success:
                                    fixes_applied.append(f"Added dependency: {missing_module}")
                continue
            
            # Handle SYNTAX ERROR issues - for data files (JSON/YAML), regenerate completely
            if "SYNTAX" in issue.upper() or "SYNTAX ERROR" in issue.upper():
                # Extract file path from issue
                parts = issue.split(":", 1)
                file_path = parts[0].strip() if len(parts) > 0 else ""
                
                if file_path and file_path.endswith((".json", ".yaml", ".yml")):
                    self._log_step("fix", f"Regenerating data file with syntax error: {file_path}")
                    
                    code = await self._regenerate_file(file_path)
                    if code:
                        # Validate the regenerated JSON
                        if file_path.endswith(".json"):
                            import json
                            try:
                                json.loads(code)
                                write_result = await self.call_tool("write_file", path=file_path, content=code)
                                if write_result.success:
                                    fixes_applied.append(f"Regenerated data file: {file_path}")
                                    continue
                            except json.JSONDecodeError as e:
                                self._log_step("fix", f"Regenerated JSON still invalid: {e}")
                                # Try one more time with explicit JSON instructions
                                code = await self._regenerate_json_file(file_path)
                                if code:
                                    write_result = await self.call_tool("write_file", path=file_path, content=code)
                                    if write_result.success:
                                        fixes_applied.append(f"Regenerated JSON file (2nd attempt): {file_path}")
                                continue
                        else:
                            write_result = await self.call_tool("write_file", path=file_path, content=code)
                            if write_result.success:
                                fixes_applied.append(f"Regenerated: {file_path}")
                            continue
                continue
            
            # Handle JSON FORMATTING issues - reformat the JSON with proper indentation
            if "JSON FORMATTING" in issue:
                # Extract file path
                parts = issue.split(":")
                file_path = None
                for part in parts:
                    if ".json" in part:
                        # Find the .json file path
                        file_path = part.strip().split()[0] if " " in part else part.strip()
                        break
                
                if not file_path:
                    # Try to find from issue text
                    match = re.search(r"([^\s]+\.json)", issue)
                    if match:
                        file_path = match.group(1)
                
                if file_path:
                    self._log_step("fix", f"Reformatting JSON file: {file_path}")
                    
                    # Read current content
                    read_result = await self.call_tool("read_file", path=file_path)
                    if read_result.success:
                        import json
                        try:
                            # Parse and reformat with proper indentation
                            data = json.loads(read_result.data)
                            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
                            
                            write_result = await self.call_tool("write_file", path=file_path, content=formatted_json)
                            if write_result.success:
                                fixes_applied.append(f"Reformatted JSON: {file_path}")
                                self._log_step("fix", f"  [OK] JSON reformatted with proper indentation")
                                
                                # Store fix pattern
                                if self.shared_memory:
                                    self.shared_memory.remember(
                                        f"FIX PATTERN: Single-line JSON -> Reformat with json.dumps(indent=2)",
                                        memory_type="long",
                                        metadata={"type": "fix_pattern", "issue": "json_formatting"},
                                        importance=0.7,
                                    )
                        except json.JSONDecodeError as e:
                            self._log_step("fix", f"  [FAIL] Could not parse JSON: {e}")
                continue
            
            # Handle other issues with INTELLIGENT EXPLORATION + FIX
            parts = issue.split(":", 1)
            if len(parts) != 2:
                continue
            
            file_path, error = parts
            file_path = file_path.strip()
            
            # ========== STEP 1: EXPLORE - Understand the problem ==========
            self._log_step("fix", f"[EXPLORE] Analyzing issue in {file_path}: {error[:50]}...")
            
            # Read the problematic file
            read_result = await self.call_tool("read_file", path=file_path)
            if not read_result.success:
                continue
            
            content = read_result.data
            
            # Ask LLM what context it needs to fix this properly
            explore_prompt = f"""I need to fix this issue:

FILE: {file_path}
ISSUE: {error}

CODE (first 1500 chars):
{content[:1500]}

Before I fix it, what additional context do I need?
Think about:
- What other files might this code depend on?
- What patterns or functions is it using that I should check?
- Are there similar files I should look at for reference?

Respond in JSON:
{{
  "needs_exploration": true/false,
  "exploration_actions": [
    {{"action": "read_file", "path": "...", "reason": "..."}},
    {{"action": "grep", "pattern": "...", "reason": "..."}}
  ],
  "initial_analysis": "what I think the problem is"
}}"""

            exploration_context = ""
            if self._reasoner:
                explore_result = await self._reasoner.run(explore_prompt)
                explore_answer = str(explore_result.answer) if explore_result.answer else "{}"
                
                try:
                    json_match = re.search(r'\{[\s\S]*\}', explore_answer)
                    if json_match:
                        exploration = json.loads(json_match.group())
                        
                        # Execute exploration actions
                        if exploration.get("needs_exploration", False):
                            for action in exploration.get("exploration_actions", [])[:3]:
                                if action.get("action") == "read_file":
                                    path = action.get("path", "")
                                    if path:
                                        self._log_step("fix", f"  [EXPLORE] Reading {path}...")
                                        result = await self.call_tool("read_file", path=path)
                                        if result.success:
                                            exploration_context += f"\n\n=== {path} ===\n{result.data[:1000]}"
                                elif action.get("action") == "grep":
                                    pattern = action.get("pattern", "")
                                    if pattern:
                                        self._log_step("fix", f"  [EXPLORE] Searching for {pattern}...")
                                        result = await self.call_tool("grep", pattern=pattern, path=".")
                                        if result.success and result.data:
                                            exploration_context += f"\n\n=== grep {pattern} ===\n{result.data[:500]}"
                        
                        self._log_step("fix", f"  [ANALYSIS] {exploration.get('initial_analysis', 'Unknown')[:100]}...")
                except json.JSONDecodeError:
                    pass
            
            # ========== STEP 2: FIX - Apply the fix with full context ==========
            fix_prompt = f"""Fix this issue in {file_path}:

ISSUE: {error}

CURRENT CODE:
{content[:2500]}

{f"EXPLORATION CONTEXT:{exploration_context}" if exploration_context else ""}

Based on your analysis, provide the fix as a search_replace operation:
- old_string: exact string to find (must match exactly!)
- new_string: replacement string

Format your response as:
OLD: <exact string to replace>
NEW: <replacement string>

If the fix requires creating a new file, respond:
CREATE_FILE: <path>
CONTENT:
<file content>"""

            if self._reasoner:
                # ========== STEP 3: APPLY FIX with retry ==========
                max_fix_attempts = 2
                fix_successful = False
                
                for fix_attempt in range(max_fix_attempts):
                    result = await self._reasoner.run(fix_prompt)
                    
                    # Parse fix
                    answer = str(result.answer) if result.answer else ""
                    
                    # Handle CREATE_FILE response - agent wants to create a new file
                    if "CREATE_FILE:" in answer:
                        try:
                            file_to_create = answer.split("CREATE_FILE:")[1].split("CONTENT:")[0].strip()
                            file_content = answer.split("CONTENT:")[1].strip()
                            
                            self._log_step("fix", f"  [CREATE] Creating new file: {file_to_create}")
                            write_result = await self.call_tool("write_file", path=file_to_create, content=file_content)
                            if write_result.success:
                                # Use "NEW FILE:" prefix so orchestrator can track this
                                fixes_applied.append(f"NEW FILE: {file_to_create}")
                                fix_successful = True
                                
                                # Store in memory for future reference
                                if self.shared_memory:
                                    self.shared_memory.remember(
                                        f"Created new file {file_to_create} during fix process",
                                        memory_type="working",
                                        metadata={"type": "new_file", "path": file_to_create},
                                        importance=0.8,
                                    )
                        except Exception as e:
                            self._log_step("fix", f"  [ERROR] Failed to create file: {e}")
                    
                    # Handle OLD/NEW response
                    elif "OLD:" in answer and "NEW:" in answer:
                        # Extract old and new strings
                        old_match = answer.split("OLD:")[1].split("NEW:")[0].strip()
                        new_match = answer.split("NEW:")[1].strip()
                        
                        # Clean up any markdown formatting
                        for marker in ["```", "```python", "```typescript", "```json"]:
                            old_match = old_match.replace(marker, "").strip()
                            new_match = new_match.replace(marker, "").strip()
                        
                        # Apply fix
                        replace_result = await self.call_tool(
                            "search_replace",
                            path=file_path,
                            old_string=old_match,
                            new_string=new_match,
                        )
                        
                        if replace_result.success:
                            # ========== STEP 4: VERIFY fix worked ==========
                            self._log_step("fix", f"  [VERIFY] Checking if fix worked...")
                            
                            # Re-check the file
                            verify_result = await self.call_tool("syntax_check", 
                                code=(await self.call_tool("read_file", path=file_path)).data or "",
                                language="python" if file_path.endswith(".py") else "json" if file_path.endswith(".json") else "typescript"
                            )
                            
                            # Handle None data safely
                            verify_data = verify_result.data if verify_result and verify_result.data else {}
                            if verify_result.success and verify_data.get("valid", True):
                                fixes_applied.append(f"Fixed: {error[:50]}...")
                                fix_successful = True
                                
                                # Store specific fix pattern for learning
                                if self.shared_memory:
                                    self.shared_memory.remember(
                                        f"FIX PATTERN: Error '{error[:80]}' in {file_path} -> Replace '{old_match[:50]}' with '{new_match[:50]}'",
                                        memory_type="long",
                                        metadata={"type": "fix_pattern", "file": file_path},
                                        importance=0.75,
                                    )
                                break
                            else:
                                self._log_step("fix", f"  [RETRY] Fix didn't solve the problem, trying again...")
                                # Update prompt with failure info for next attempt
                                fix_prompt = f"""My previous fix attempt failed. The issue persists.

FILE: {file_path}
ORIGINAL ISSUE: {error}
ATTEMPTED FIX: Replace '{old_match[:100]}' with '{new_match[:100]}'
RESULT: Still has errors

Please try a different approach. Maybe I need to:
- Read more context
- Fix a different part of the code
- Fix multiple things at once

Provide a new fix:
OLD: <exact string to replace>
NEW: <replacement string>"""
                        else:
                            self._log_step("fix", f"  [FAIL] search_replace failed: {replace_result.error_message}")
                            # Try with more context
                            fix_prompt = f"""My search_replace failed - couldn't find the exact string.

FILE: {file_path}
ISSUE: {error}
TRIED TO FIND: {old_match[:200]}

The exact string wasn't found. Please provide a more accurate match.
Read the file carefully and provide the EXACT string to replace.

OLD: <exact string from file>
NEW: <replacement>"""
                    
                    if fix_successful:
                        break
        
        self.steps.append(GenerationStep(
            step_type="fix",
            description=f"Applied {len(fixes_applied)} fixes",
            output_data=fixes_applied,
            success=len(fixes_applied) > 0,
        ))
        
        return fixes_applied
    
    async def test_generated_environment(
        self,
        env_name: str,
        backend_dir: str = "",
        frontend_dir: str = "",
    ) -> Dict[str, Any]:
        """
        Test the generated environment by actually running it!
        
        This is a KEY capability - the agent can:
        1. Install dependencies
        2. Start servers
        3. Test API endpoints
        4. Check for errors
        5. Fix issues found during testing
        
        Returns:
            Dict with test results
        """
        self._log_step("test", f"Testing generated environment: {env_name}")
        
        results = {
            "backend_install": None,
            "backend_start": None,
            "api_tests": [],
            "issues_found": [],
            "fixes_applied": [],
        }
        
        # Determine directories
        backend = backend_dir or f"{env_name}_api"
        frontend = frontend_dir or f"{env_name}_ui"
        
        # ========== STEP 1: Install Backend Dependencies ==========
        self._log_step("test", "[1/5] Installing backend dependencies...")
        
        install_result = await self.call_tool(
            "install_dependencies",
            project_type="python",
            cwd=backend,
        )
        
        results["backend_install"] = {
            "success": install_result.success,
            "error": install_result.data.get("stderr", "") if not install_result.success else None,
        }
        
        if not install_result.success:
            error = install_result.data.get("stderr", "Unknown error")
            results["issues_found"].append(f"Backend install failed: {error[:200]}")
            self._log_step("test", f"  [FAIL] Install failed: {error[:100]}")
            return results
        
        self._log_step("test", "  [OK] Dependencies installed")
        
        # ========== STEP 2: Start Backend Server ==========
        self._log_step("test", "[2/5] Starting backend server...")
        
        start_result = await self.call_tool(
            "start_server",
            name="backend",
            command="python -m uvicorn main:app --host 0.0.0.0 --port 8000",
            cwd=backend,
            port=8000,
            wait_for_ready=30,
        )
        
        results["backend_start"] = {
            "success": start_result.success,
            "error": start_result.data.get("error", "") if not start_result.success else None,
        }
        
        if not start_result.success:
            error = start_result.data.get("error", "") or start_result.data.get("stderr", "")
            results["issues_found"].append(f"Backend start failed: {error[:200]}")
            self._log_step("test", f"  [FAIL] Server start failed: {error[:100]}")
            
            # Try to analyze the error and fix
            if "ModuleNotFoundError" in error or "ImportError" in error:
                self._log_step("test", "  [ANALYZE] Import error detected, attempting fix...")
                module = re.search(r"No module named '(\w+)'", error)
                if module:
                    results["issues_found"].append(f"Missing module: {module.group(1)}")
            
            return results
        
        self._log_step("test", "  [OK] Server started on port 8000")
        
        # ========== STEP 3: Test API Health ==========
        self._log_step("test", "[3/5] Testing API health...")
        
        health_result = await self.call_tool(
            "test_api",
            method="GET",
            url="http://localhost:8000/health",
        )
        
        results["api_tests"].append({
            "endpoint": "/health",
            "success": health_result.success,
            "status": health_result.data.get("status_code"),
        })
        
        if health_result.success:
            self._log_step("test", "  [OK] Health check passed")
        else:
            self._log_step("test", f"  [WARN] Health check failed: {health_result.data}")
        
        # ========== STEP 4: Test Auth Endpoints ==========
        self._log_step("test", "[4/5] Testing auth endpoints...")
        
        # Test register
        register_result = await self.call_tool(
            "test_api",
            method="POST",
            url="http://localhost:8000/auth/register",
            json_data={"email": "test@test.com", "password": "testpass123", "name": "Test User"},
        )
        
        results["api_tests"].append({
            "endpoint": "/auth/register",
            "success": register_result.success,
            "status": register_result.data.get("status_code"),
        })
        
        if register_result.success:
            self._log_step("test", "  [OK] Register endpoint works")
        else:
            error = register_result.data.get("error", register_result.data.get("response", ""))
            self._log_step("test", f"  [FAIL] Register failed: {str(error)[:100]}")
            results["issues_found"].append(f"Register endpoint failed: {str(error)[:100]}")
        
        # Test login
        login_result = await self.call_tool(
            "test_api",
            method="POST",
            url="http://localhost:8000/auth/login",
            json_data={"email": "test@test.com", "password": "testpass123"},
        )
        
        results["api_tests"].append({
            "endpoint": "/auth/login",
            "success": login_result.success,
            "status": login_result.data.get("status_code"),
        })
        
        if login_result.success:
            self._log_step("test", "  [OK] Login endpoint works")
        else:
            error = login_result.data.get("error", login_result.data.get("response", ""))
            self._log_step("test", f"  [FAIL] Login failed: {str(error)[:100]}")
            results["issues_found"].append(f"Login endpoint failed: {str(error)[:100]}")
        
        # ========== STEP 5: Cleanup ==========
        self._log_step("test", "[5/5] Cleaning up...")
        
        await self.call_tool("stop_server", server_name="backend")
        self._log_step("test", "  [OK] Server stopped")
        
        # ========== SUMMARY ==========
        total_tests = len(results["api_tests"])
        passed_tests = sum(1 for t in results["api_tests"] if t["success"])
        
        self._log_step("test", f"Test Summary: {passed_tests}/{total_tests} tests passed")
        
        if results["issues_found"]:
            self._log_step("test", f"Issues found: {len(results['issues_found'])}")
            
            # Try to fix issues
            fixes = await self.fix_issues(results["issues_found"])
            results["fixes_applied"] = fixes
        
        self.steps.append(GenerationStep(
            step_type="test",
            description=f"Tested environment: {passed_tests}/{total_tests} passed",
            output_data=results,
            success=passed_tests == total_tests,
        ))
        
        return results
    
    async def generate_and_run_tests(
        self,
        env_name: str,
        test_type: str = "api",  # "api", "unit", "integration"
    ) -> Dict[str, Any]:
        """
        Generate test code, run it, then clean up.
        
        This allows the agent to:
        1. Generate test files in a tests/ folder
        2. Run the tests
        3. Collect results
        4. Delete the test files
        
        Args:
            env_name: Name of the environment (e.g., "calendar")
            test_type: Type of tests to generate ("api", "unit", "integration")
            
        Returns:
            Dict with test results
        """
        self._log_step("generate_test", f"Generating {test_type} tests for {env_name}...")
        
        results = {
            "test_type": test_type,
            "tests_generated": [],
            "tests_run": [],
            "passed": 0,
            "failed": 0,
            "errors": [],
        }
        
        test_dir = f"tests/{env_name}_{test_type}"
        
        # ========== STEP 1: Generate test files ==========
        self._log_step("generate_test", f"[1/4] Generating test files in {test_dir}...")
        
        if test_type == "api":
            # Generate API test file
            test_code = await self._generate_api_test_code(env_name)
            test_file = f"{test_dir}/test_api.py"
        elif test_type == "unit":
            test_code = await self._generate_unit_test_code(env_name)
            test_file = f"{test_dir}/test_unit.py"
        else:
            test_code = await self._generate_integration_test_code(env_name)
            test_file = f"{test_dir}/test_integration.py"
        
        if test_code:
            # Create tests directory and write test file
            await self.call_tool("run_command", command=f"mkdir -p {test_dir}")
            write_result = await self.call_tool("write_file", path=test_file, content=test_code)
            
            if write_result.success:
                results["tests_generated"].append(test_file)
                self._log_step("generate_test", f"  [OK] Generated: {test_file}")
            else:
                results["errors"].append(f"Failed to write {test_file}")
                return results
        
        # ========== STEP 2: Install test dependencies ==========
        self._log_step("generate_test", "[2/4] Installing test dependencies...")
        
        await self.call_tool(
            "run_command", 
            command="pip install pytest pytest-asyncio httpx",
            timeout=60
        )
        
        # ========== STEP 3: Run tests ==========
        self._log_step("generate_test", "[3/4] Running tests...")
        
        run_result = await self.call_tool(
            "run_command",
            command=f"python -m pytest {test_file} -v --tb=short",
            timeout=120,
        )
        
        if run_result.success:
            self._log_step("generate_test", "  [OK] Tests passed")
            results["passed"] = 1
        else:
            self._log_step("generate_test", f"  [FAIL] Tests failed")
            results["failed"] = 1
            results["errors"].append(run_result.data.get("stderr", ""))
        
        results["tests_run"].append({
            "file": test_file,
            "success": run_result.success,
            "output": run_result.data.get("stdout", "")[:1000],
            "error": run_result.data.get("stderr", "")[:500] if not run_result.success else None,
        })
        
        # ========== STEP 4: Cleanup test files ==========
        self._log_step("generate_test", "[4/4] Cleaning up test files...")
        
        await self.call_tool("run_command", command=f"rm -rf {test_dir}")
        self._log_step("generate_test", f"  [OK] Deleted: {test_dir}")
        
        # Summary
        self._log_step("generate_test", f"Test Summary: {results['passed']} passed, {results['failed']} failed")
        
        self.steps.append(GenerationStep(
            step_type="generate_test",
            description=f"Generated and ran {test_type} tests: {results['passed']} passed, {results['failed']} failed",
            output_data=results,
            success=results["failed"] == 0,
        ))
        
        return results
    
    async def _generate_api_test_code(self, env_name: str) -> str:
        """Generate API test code using LLM"""
        
        if not self._reasoner:
            return ""
        
        prompt = f"""Generate a pytest test file for testing the {env_name} FastAPI backend.

The tests should:
1. Test the /health endpoint
2. Test user registration (POST /auth/register)
3. Test user login (POST /auth/login)
4. Test authenticated endpoints if any

Use httpx for HTTP requests. The API runs on http://localhost:8000.

Generate COMPLETE, RUNNABLE test code:

```python
import pytest
import httpx

BASE_URL = "http://localhost:8000"

# Your tests here...
```"""
        
        result = await self._reasoner.run(prompt)
        answer = str(result.answer) if result.answer else ""
        
        # Extract code from response
        if "```python" in answer:
            code = answer.split("```python")[1].split("```")[0].strip()
        elif "```" in answer:
            code = answer.split("```")[1].split("```")[0].strip()
        else:
            code = answer.strip()
        
        return code
    
    async def _generate_unit_test_code(self, env_name: str) -> str:
        """Generate unit test code"""
        # Simplified for now
        return f'''import pytest

def test_placeholder():
    """Placeholder unit test for {env_name}"""
    assert True
'''
    
    async def _generate_integration_test_code(self, env_name: str) -> str:
        """Generate integration test code"""
        return f'''import pytest

def test_integration_placeholder():
    """Placeholder integration test for {env_name}"""
    assert True
'''
    
    async def verify_planned_files(
        self,
        planned_files: List[str],
    ) -> Dict[str, Any]:
        """
        Verify that all planned files were actually generated.
        
        Returns:
            Dict with verification results and missing files
        """
        self._log_step("verify", f"Verifying {len(planned_files)} planned files were generated...")
        
        # Use the check_files_exist tool
        result = await self.call_tool("check_files_exist", files=planned_files)
        
        # Handle None data safely
        data = result.data if result and result.data else {}
        
        if result.success:
            self._log_step("verify", f"  [OK] All {len(planned_files)} files exist")
        else:
            missing = data.get("missing", [])
            self._log_step("verify", f"  [WARN] Missing {len(missing)} files: {missing}")
        
        self.steps.append(GenerationStep(
            step_type="verify",
            description=f"Verified planned files: {data.get('existing_count', 0)}/{len(planned_files)} exist",
            output_data=data,
            success=result.success if result else False,
        ))
        
        return {"missing_files": data.get("missing", []), "all_exist": result.success if result else False}
    
    async def _ensure_complete_code(self, code: str, file_path: str, purpose: str) -> str:
        """
        Check if code is truncated and continue generation if needed.
        
        Truncation indicators:
        - Python: ends with incomplete syntax (`:`, `,`, unclosed brackets)
        - TypeScript: unbalanced braces
        - Ends with `...` or comment indicating more
        """
        if not code or not self._reasoner:
            return code
        
        max_continuations = 3  # Prevent infinite loops
        
        for attempt in range(max_continuations):
            is_truncated, reason = self._detect_truncation(code, file_path)
            
            if not is_truncated:
                break
            
            self._log_step("continue", f"Code truncated ({reason}), continuing generation...")
            
            # Ask LLM to continue with format-specific instructions
            format_hint = ""
            if file_path.endswith(".json"):
                format_hint = """
IMPORTANT: This is a JSON file. You MUST:
- Use double quotes (") for all strings, NOT single quotes (')
- Ensure valid JSON syntax
- Continue the JSON structure properly (add missing array items, close brackets/braces)
"""
            elif file_path.endswith((".ts", ".tsx")):
                format_hint = """
IMPORTANT: This is TypeScript/React code. Ensure:
- Proper TypeScript syntax
- Complete all JSX elements
- Close all braces and parentheses
"""
            
            continue_prompt = f"""The following code for {file_path} was truncated and is incomplete.

INCOMPLETE CODE (last 800 chars):
```
{code[-800:]}
```

PURPOSE: {purpose}

TRUNCATION REASON: {reason}
{format_hint}
Please CONTINUE the code from where it was cut off.
- Do NOT repeat the existing code
- Start EXACTLY from where the code ended
- Complete all remaining functions, classes, and logic
- Output ONLY the continuation, no explanations"""

            result = await self._reasoner.run(continue_prompt)
            continuation = str(result.answer) if result.answer else ""
            
            # Clean up continuation (remove markdown fences, overlapping code, fix JSON format)
            continuation = self._clean_continuation(code, continuation, file_path)
            
            if not continuation:
                break
            
            # Special merge logic for JSON files
            if file_path.endswith(".json"):
                code = self._merge_json_continuation(code, continuation)
            else:
                code = code + "\n" + continuation
            
            self._log_step("continue", f"Added {len(continuation)} chars continuation")
        
        # Final cleanup: strip any remaining line numbers
        code = self._strip_line_numbers(code)
        
        return code
    
    def _detect_truncation(self, code: str, file_path: str) -> tuple:
        """
        Detect if code appears to be truncated.
        
        Returns:
            (is_truncated: bool, reason: str)
        """
        if not code:
            return False, ""
        
        code = code.strip()
        lines = code.split("\n")
        last_line = lines[-1].strip() if lines else ""
        
        # Python truncation indicators
        if file_path.endswith(".py"):
            # Check bracket balance
            open_parens = code.count("(") - code.count(")")
            open_brackets = code.count("[") - code.count("]")
            open_braces = code.count("{") - code.count("}")
            
            if open_parens > 0:
                return True, f"unclosed parentheses ({open_parens} open)"
            if open_brackets > 0:
                return True, f"unclosed brackets ({open_brackets} open)"
            if open_braces > 0:
                return True, f"unclosed braces ({open_braces} open)"
            
            # Ends with incomplete syntax
            if last_line.endswith(":"):
                return True, "ends with colon (incomplete block)"
            if last_line.endswith(","):
                return True, "ends with comma (incomplete list/dict)"
            if last_line.endswith("("):
                return True, "ends with open paren"
            
            # Check for incomplete class/function
            if re.search(r"^\s*(def|class|async def)\s+\w+.*:$", last_line):
                return True, "ends with function/class definition"
        
        # TypeScript/TSX truncation indicators
        elif file_path.endswith((".ts", ".tsx")):
            open_braces = code.count("{") - code.count("}")
            open_parens = code.count("(") - code.count(")")
            
            if open_braces > 0:
                return True, f"unclosed braces ({open_braces} open)"
            if open_parens > 0:
                return True, f"unclosed parentheses ({open_parens} open)"
            
            # JSX specific
            if file_path.endswith(".tsx"):
                # Check for unclosed JSX tags (simple heuristic)
                jsx_opens = len(re.findall(r"<[A-Z][a-zA-Z]*(?:\s|>)", code))
                jsx_closes = len(re.findall(r"</[A-Z][a-zA-Z]*>", code))
                jsx_self_close = len(re.findall(r"<[A-Z][a-zA-Z]*[^>]*/\s*>", code))
                
                if jsx_opens > jsx_closes + jsx_self_close + 2:  # Some tolerance
                    return True, f"unclosed JSX tags"
        
        # JSON truncation
        elif file_path.endswith(".json"):
            open_braces = code.count("{") - code.count("}")
            open_brackets = code.count("[") - code.count("]")
            
            if open_braces != 0 or open_brackets != 0:
                return True, "unbalanced JSON structure"
        
        # General indicators
        if code.endswith("..."):
            return True, "ends with ellipsis"
        if re.search(r"#\s*(TODO|FIXME|continue|more|rest)\s*$", last_line, re.IGNORECASE):
            return True, "ends with TODO/continue comment"
        
        return False, ""
    
    def _clean_continuation(self, original: str, continuation: str, file_path: str = "") -> str:
        """Clean up continuation code to avoid duplication."""
        if not continuation:
            return ""
        
        # Remove markdown fences
        if continuation.startswith("```"):
            lines = continuation.split("\n")
            # Remove first line (```python or similar)
            if len(lines) > 1:
                lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            continuation = "\n".join(lines)
        
        # CRITICAL: Strip line numbers if present (LLM often mimics line number format)
        continuation = self._strip_line_numbers(continuation)
        
        # Special handling for JSON files
        if file_path.endswith(".json"):
            # Convert Python dict format to JSON if needed (single quotes to double)
            # Only do this if it looks like Python dict format
            if "'" in continuation and '"' not in continuation:
                # Replace single quotes with double quotes
                # This is a simple heuristic - be careful with embedded quotes
                continuation = continuation.replace("'", '"')
            
            # Clean up any Python-style None, True, False
            continuation = continuation.replace(": None", ": null")
            continuation = continuation.replace(":None", ":null")
            continuation = continuation.replace(": True", ": true")
            continuation = continuation.replace(":True", ":true")
            continuation = continuation.replace(": False", ": false")
            continuation = continuation.replace(":False", ":false")
        
        # Try to detect overlap and remove it
        # Look for the last 2-3 lines of original in the continuation
        original_lines = original.strip().split("\n")
        if len(original_lines) >= 2:
            last_lines = "\n".join(original_lines[-2:])
            if last_lines in continuation:
                # Remove the overlapping part
                idx = continuation.find(last_lines)
                continuation = continuation[idx + len(last_lines):]
        
        return continuation.strip()
    
    def _merge_json_continuation(self, original: str, continuation: str) -> str:
        """
        Merge JSON continuation properly instead of simple concatenation.
        
        Strategy:
        1. Try to parse the continuation as valid JSON - if valid, try to merge structures
        2. If continuation is invalid, try to fix it first
        3. Find the truncation point and properly connect the pieces
        """
        import json
        
        original = original.strip()
        continuation = continuation.strip()
        
        if not continuation:
            return original
        
        # Clean up Python dict format that LLM sometimes produces
        continuation = self._fix_python_to_json(continuation)
        
        # Remove trailing incomplete characters from original
        while original and original[-1] in " \n\t,":
            original = original[:-1]
        
        # Count bracket balance in original
        open_braces = original.count("{") - original.count("}")
        open_brackets = original.count("[") - original.count("]")
        
        # Try approach 1: Simple merge with proper comma
        if open_braces > 0 or open_brackets > 0:
            continuation = continuation.lstrip()
            
            # Remove leading duplicates or brackets that don't make sense
            # If original is truncated mid-array and continuation starts with array content
            if continuation.startswith(("}", "]")):
                # Continuation seems to just be closing brackets - just append
                merged = original + continuation
            elif continuation.startswith(","):
                merged = original + continuation
            elif continuation.startswith("{") or continuation.startswith('"') or continuation.startswith("["):
                # Need a comma between
                merged = original + ",\n" + continuation
            else:
                merged = original + "\n" + continuation
            
            # Validate the merged result
            try:
                json.loads(merged)
                return merged
            except json.JSONDecodeError:
                pass
        
        # Approach 2: Try to regenerate from scratch by combining content
        # This is a fallback when simple merge fails
        self._log_step("json_merge", "Simple merge failed, trying to extract and rebuild")
        
        # Return original + continuation and let validation catch it
        # The orchestrator will regenerate if still invalid
        if open_braces > 0 or open_brackets > 0:
            if continuation.startswith(","):
                return original + continuation
            else:
                return original + ",\n" + continuation
        
        return original + continuation
    
    def _fix_python_to_json(self, text: str) -> str:
        """
        Fix common Python dict format issues when LLM produces dict instead of JSON.
        
        Handles:
        - Single quotes -> double quotes
        - Python None, True, False -> null, true, false
        - Trailing commas before closing brackets
        """
        import re
        import json
        
        # First, try to parse as JSON directly
        try:
            json.loads(text)
            return text  # Already valid JSON
        except json.JSONDecodeError:
            pass
        
        # Check if this looks like Python dict (has single quotes)
        if "'" in text:
            # Replace single quotes with double quotes
            # Handle escaped quotes and nested structures
            result = []
            in_string = False
            string_char = None
            i = 0
            while i < len(text):
                char = text[i]
                
                if char in ('"', "'") and (i == 0 or text[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                        result.append('"')  # Always use double quote
                    elif char == string_char:
                        in_string = False
                        string_char = None
                        result.append('"')  # Always use double quote
                    else:
                        # Different quote inside string - escape if it's double quote
                        if char == '"':
                            result.append('\\"')
                        else:
                            result.append(char)
                else:
                    result.append(char)
                i += 1
            
            text = ''.join(result)
        
        # Fix Python boolean and None (only outside of strings)
        text = re.sub(r'\bNone\b', 'null', text)
        text = re.sub(r'\bTrue\b', 'true', text)
        text = re.sub(r'\bFalse\b', 'false', text)
        
        # Remove trailing commas before } or ]
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        
        # Validate result
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            # If still invalid, return original and let later validation handle it
            return text
    
    async def _generate_missing_component(self, component_name: str, file_path: str) -> Optional[str]:
        """Generate a missing React component"""
        if not self._reasoner:
            # Fallback: generate simple stub
            return f'''import React from 'react';

const {component_name}: React.FC = () => {{
  return (
    <div>
      <h1>{component_name}</h1>
      <p>This page is under construction.</p>
    </div>
  );
}};

export default {component_name};
'''
        
        prompt = f"""Generate a React TypeScript component for: {component_name}

FILE: {file_path}

This component was imported but didn't exist. Generate a proper implementation.

If it's a page like 'Register', create a registration form.
If it's a page like 'Login', create a login form.
If it's a list page, create a data list with CRUD operations.

Use React hooks, TypeScript types, and follow best practices.
Output ONLY the code, no markdown fences."""

        result = await self._reasoner.run(prompt)
        code = str(result.answer) if result.answer else ""
        
        # Clean up markdown fences if present
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        
        return code if code else None
    
    async def _generate_missing_module(self, module_name: str, file_path: str) -> Optional[str]:
        """Generate a missing Python module"""
        if not self._reasoner:
            # Fallback: generate simple stub module
            return f'''"""
{module_name} module

Auto-generated to fix missing import.
"""

# TODO: Implement this module
pass
'''
        
        # Get context about what this module should do
        prompt = f"""Generate a Python module for: {module_name}

FILE: {file_path}

This module was imported but didn't exist, causing an ImportError.

Based on the module name:
- If it's like 'xxx_api.utils', create common utility functions
- If it's like 'xxx_api.config', create configuration settings  
- If it's like 'xxx_api.exceptions', create custom exception classes
- If it's like 'xxx_api.helpers', create helper functions

Generate a proper implementation with:
1. Module docstring
2. Appropriate imports
3. Useful functions/classes based on the name
4. Type hints

Output ONLY the Python code, no markdown fences."""

        result = await self._reasoner.run(prompt)
        code = str(result.answer) if result.answer else ""
        
        # Clean up markdown fences if present
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        
        return code if code else None
    
    async def _regenerate_file(self, file_path: str) -> Optional[str]:
        """Regenerate a truncated/incomplete file"""
        if not self._reasoner:
            return None
        
        # For JSON files, use specialized method
        if file_path.endswith(".json"):
            return await self._regenerate_json_file(file_path)
        
        # Try to read existing content to understand purpose
        read_result = await self.call_tool("read_file", path=file_path)
        existing = read_result.data[:500] if read_result.success else ""
        
        file_type = "Python" if file_path.endswith(".py") else "TypeScript/React"
        
        prompt = f"""The following {file_type} file was truncated/incomplete. 
Please generate a COMPLETE version.

FILE: {file_path}

EXISTING (truncated) CONTENT:
{existing}

Generate a COMPLETE, working version of this file.
Make sure all functions are complete, all brackets are balanced.
Output ONLY the code, no markdown fences."""

        result = await self._reasoner.run(prompt)
        code = str(result.answer) if result.answer else ""
        
        # Clean up
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        
        return code if code else None
    
    async def _regenerate_json_file(self, file_path: str) -> Optional[str]:
        """
        Regenerate a JSON file from scratch with explicit validation.
        
        This is called when JSON generation/continuation has failed repeatedly.
        We use very explicit instructions to ensure valid JSON output.
        """
        import json
        
        if not self._reasoner:
            return None
        
        # Try to read existing content to understand purpose
        read_result = await self.call_tool("read_file", path=file_path)
        existing = read_result.data if read_result.success else ""
        
        # Try to extract meaningful content from broken JSON
        # Look for recognizable patterns
        content_hints = []
        if '"name"' in existing:
            # Try to extract name
            match = re.search(r'"name"\s*:\s*"([^"]+)"', existing)
            if match:
                content_hints.append(f"Name: {match.group(1)}")
        if '"description"' in existing:
            match = re.search(r'"description"\s*:\s*"([^"]+)"', existing)
            if match:
                content_hints.append(f"Description: {match.group(1)}")
        if '"entities"' in existing:
            content_hints.append("Contains entities array")
        if '"features"' in existing:
            content_hints.append("Contains features array")
        if '"api_endpoints"' in existing:
            content_hints.append("Contains API endpoints")
        
        hints_text = "\n".join(f"- {h}" for h in content_hints) if content_hints else "Unknown structure"
        
        # Determine what kind of JSON file this is
        file_name = file_path.split("/")[-1]
        
        prompt = f"""Generate a COMPLETE, VALID JSON file.

FILE: {file_path}

The previous attempt at this file had JSON syntax errors.

WHAT WE KNOW ABOUT THIS FILE:
{hints_text}

FILE STRUCTURE (from broken content, first 300 chars):
{existing[:300]}

CRITICAL REQUIREMENTS:
1. Output ONLY valid JSON - no Python syntax, no markdown
2. Use DOUBLE QUOTES (") for all strings - NOT single quotes (')
3. Use lowercase: null, true, false - NOT Python None, True, False
4. Ensure ALL brackets {{ }} and [ ] are properly balanced
5. NO trailing commas before closing brackets
6. The entire output must be parseable by JSON.parse()

Generate the COMPLETE JSON file now. Output ONLY the JSON, nothing else."""

        max_attempts = 3
        for attempt in range(max_attempts):
            result = await self._reasoner.run(prompt)
            code = str(result.answer) if result.answer else ""
            
            # Clean up markdown fences
            if code.startswith("```"):
                lines = code.split("\n")
                # Remove first line (```json or similar)
                if len(lines) > 1:
                    lines = lines[1:]
                # Remove last line if it's ```
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                code = "\n".join(lines)
            
            # Apply Python-to-JSON fixes
            code = self._fix_python_to_json(code)
            
            # Validate
            try:
                json.loads(code)
                self._log_step("json_regen", f"Successfully regenerated valid JSON on attempt {attempt + 1}")
                return code
            except json.JSONDecodeError as e:
                self._log_step("json_regen", f"Attempt {attempt + 1} failed: {e}")
                # Add error to prompt for next attempt
                prompt = f"""Your previous JSON output had an error: {e}

Please fix and output VALID JSON ONLY.

Previous output (first 500 chars):
{code[:500]}

Fix the JSON error and output the COMPLETE, VALID JSON."""
        
        # If all attempts failed, return the last attempt anyway
        # The orchestrator will handle it
        self._log_step("json_regen", f"All {max_attempts} attempts failed, returning last attempt")
        return code
    
    async def execute_step(self, step: PlanStep) -> Any:
        """Execute a plan step - override from PlanningAgent"""
        action = step.action.lower()
        
        if action == "generate_file":
            path = step.action_input.get("path", "")
            purpose = step.action_input.get("purpose", step.description)
            instructions = step.action_input.get("instructions", "")
            deps = step.action_input.get("dependencies", [])
            
            return await self.generate_file(path, purpose, instructions, deps)
        
        elif action == "read_file":
            return await self.call_tool("read_file", **step.action_input)
        
        elif action == "grep":
            return await self.call_tool("grep", **step.action_input)
        
        elif action == "lint":
            return await self.call_tool("lint", **step.action_input)
        
        else:
            # Default: use ReAct reasoning
            return await super().execute_step(step)
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """Process a generation task"""
        task_desc = task.task_description or task.task_name
        params = task.task_params
        
        self._log_step("start", f"Processing task: {task_desc}")
        
        try:
            # Think about the task
            analysis = await self.think(task_desc)
            
            # Create plan
            target_files = params.get("target_files", [])
            plan = await self.plan_generation(task_desc, target_files)
            
            # Execute plan
            success = await self.execute_plan(plan)
            
            # Reflect and fix
            generated_files = [s.action_input.get("path") for s in plan.steps 
                            if s.status == StepStatus.COMPLETED]
            
            issues = await self.reflect_on_generation(generated_files)
            if issues:
                await self.fix_issues(issues)
            
            return create_result_message(
                source_id=self.agent_id,
                target_id=task.header.source_agent_id,
                task_id=task.task_id,
                success=success,
                result_data={
                    "files_generated": generated_files,
                    "steps": len(self.steps),
                    "issues_found": len(issues),
                },
            )
            
        except Exception as e:
            self._logger.error(f"Task failed: {e}")
            return create_result_message(
                source_id=self.agent_id,
                target_id=task.header.source_agent_id,
                task_id=task.task_id,
                success=False,
                error_message=str(e),
            )
    
    def _log_step(self, step_type: str, message: str) -> None:
        """Log a step for debugging"""
        self._logger.info(f"[{step_type.upper()}] {message}")
    
    def _generate_file_summary(self, content: str, file_path: str) -> str:
        """
        Generate a structural summary of a file.
        
        Returns a concise summary including:
        - File stats (lines, chars)
        - Key imports
        - Class/function definitions with line numbers
        - Exports (for JS/TS)
        
        This summary is stored in memory for quick reference.
        """
        lines = content.split('\n')
        total_lines = len(lines)
        total_chars = len(content)
        
        summary_parts = [
            f"=== FILE SUMMARY: {file_path} ===",
            f"Total: {total_lines} lines, {total_chars} chars",
            ""
        ]
        
        if file_path.endswith(('.py', '.ts', '.tsx', '.js', '.jsx')):
            # Extract imports
            imports = []
            definitions = []
            exports = []
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                line_num = i + 1
                
                # Imports (first 50 lines usually)
                if i < 50:
                    if stripped.startswith(('import ', 'from ', 'require(')):
                        imports.append(stripped[:60])
                
                # Class and function definitions
                if stripped.startswith('class '):
                    match = stripped.split('(')[0].split(':')[0]
                    definitions.append(f"  L{line_num}: {match}")
                elif stripped.startswith(('def ', 'async def ')):
                    match = stripped.split('(')[0]
                    definitions.append(f"  L{line_num}: {match}")
                elif stripped.startswith(('function ', 'const ', 'export function', 'export const', 'export class')):
                    definitions.append(f"  L{line_num}: {stripped[:50]}")
                
                # Exports
                if 'export ' in stripped or '__all__' in stripped:
                    exports.append(f"  L{line_num}: {stripped[:50]}")
            
            if imports:
                summary_parts.append(f"IMPORTS ({len(imports)}):")
                summary_parts.extend(imports[:5])
                if len(imports) > 5:
                    summary_parts.append(f"  ... and {len(imports) - 5} more")
                summary_parts.append("")
            
            if definitions:
                summary_parts.append(f"DEFINITIONS ({len(definitions)}):")
                summary_parts.extend(definitions[:15])
                if len(definitions) > 15:
                    summary_parts.append(f"  ... and {len(definitions) - 15} more")
                summary_parts.append("")
            
            if exports:
                summary_parts.append(f"EXPORTS ({len(exports)}):")
                summary_parts.extend(exports[:5])
                summary_parts.append("")
        
        elif file_path.endswith('.json'):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    summary_parts.append(f"TOP-LEVEL KEYS: {list(data.keys())[:10]}")
                    for key, value in list(data.items())[:5]:
                        if isinstance(value, list):
                            summary_parts.append(f"  {key}: array[{len(value)}]")
                        elif isinstance(value, dict):
                            summary_parts.append(f"  {key}: object with {len(value)} keys")
                        else:
                            summary_parts.append(f"  {key}: {type(value).__name__}")
                elif isinstance(data, list):
                    summary_parts.append(f"ROOT: array[{len(data)}]")
            except json.JSONDecodeError:
                summary_parts.append("(Invalid JSON)")
        
        summary_parts.append("")
        summary_parts.append("To read specific lines: read_file(path, start_line=N, end_line=M)")
        summary_parts.append("To search: grep(pattern, path)")
        
        return '\n'.join(summary_parts)
    
    def _smart_truncate_file(self, content: str, file_path: str, max_chars: int = 4000) -> str:
        """
        Intelligently truncate a long file to fit within token limits.
        
        Instead of just taking the first N characters, we:
        1. Keep the beginning (imports, class definitions)
        2. Keep the end (often has main logic, exports)
        3. Add a summary of what's in the middle with line numbers
        4. Indicate how to get truncated content
        
        This preserves more useful context for code understanding.
        """
        if len(content) <= max_chars:
            return content
        
        lines = content.split('\n')
        total_lines = len(lines)
        
        # For Python/TypeScript: extract key structure
        if file_path.endswith(('.py', '.ts', '.tsx', '.js', '.jsx')):
            # Keep first 40 lines (imports, class definitions)
            head_lines = 40
            # Keep last 30 lines (main logic, exports)
            tail_lines = 30
            
            if total_lines <= head_lines + tail_lines + 10:
                # File is small enough, just truncate content
                return content[:max_chars] + f"\n... (truncated at {max_chars} chars, total {len(content)} chars)"
            
            head = '\n'.join(lines[:head_lines])
            tail = '\n'.join(lines[-tail_lines:])
            
            # Extract function/class signatures from the middle
            middle_lines = lines[head_lines:-tail_lines]
            omitted_start = head_lines + 1
            omitted_end = total_lines - tail_lines
            
            signatures = []
            for i, line in enumerate(middle_lines):
                stripped = line.strip()
                if stripped.startswith(('def ', 'async def ', 'class ', 'function ', 'const ', 'export ')):
                    signatures.append(f"  L{head_lines + i + 1}: {stripped[:70]}")
            
            middle_summary = f"\n\n=== TRUNCATED: Lines {omitted_start}-{omitted_end} ({len(middle_lines)} lines) ===\n"
            middle_summary += f"To read: read_file('{file_path}', start_line={omitted_start}, end_line={omitted_end})\n"
            middle_summary += f"To search: grep('<pattern>', '{file_path}')\n"
            
            if signatures:
                middle_summary += "\nKey definitions in truncated section:\n" + '\n'.join(signatures[:10])
                if len(signatures) > 10:
                    middle_summary += f"\n  ... and {len(signatures) - 10} more definitions"
            middle_summary += "\n\n"
            
            result = head + middle_summary + tail
            
            # Final size check
            if len(result) > max_chars:
                return result[:max_chars] + f"\n... (further truncated)"
            return result
        
        elif file_path.endswith('.json'):
            # For JSON: keep structure, truncate arrays
            try:
                data = json.loads(content)
                
                def truncate_json(obj, depth=0, path=""):
                    if depth > 3:
                        return "... (nested)"
                    if isinstance(obj, dict):
                        result = {}
                        items = list(obj.items())
                        for k, v in items[:10]:
                            result[k] = truncate_json(v, depth + 1, f"{path}.{k}")
                        if len(items) > 10:
                            result["..."] = f"({len(items) - 10} more keys)"
                        return result
                    elif isinstance(obj, list):
                        if len(obj) > 5:
                            return [
                                truncate_json(obj[0], depth + 1, f"{path}[0]"),
                                f"... ({len(obj) - 2} more items, use grep to find specific items)",
                                truncate_json(obj[-1], depth + 1, f"{path}[-1]")
                            ]
                        return [truncate_json(item, depth + 1, f"{path}[{i}]") for i, item in enumerate(obj)]
                    return obj
                
                truncated = truncate_json(data)
                result = json.dumps(truncated, indent=2, ensure_ascii=False)
                if len(result) > max_chars:
                    result = result[:max_chars] + f"\n... (truncated, use grep to search)"
                return result
            except json.JSONDecodeError:
                pass
        
        # Default: keep head and tail with clear indicators
        head_chars = max_chars // 2
        tail_chars = max_chars // 3
        head = content[:head_chars]
        tail = content[-tail_chars:]
        
        # Find line numbers for head/tail
        head_lines = head.count('\n')
        tail_start_line = total_lines - tail.count('\n')
        
        middle_info = f"\n\n=== TRUNCATED: Lines {head_lines + 1}-{tail_start_line} ===\n"
        middle_info += f"Omitted: {len(content) - head_chars - tail_chars} chars\n"
        middle_info += f"To read: read_file('{file_path}', start_line={head_lines + 1}, end_line={tail_start_line})\n\n"
        
        return head + middle_info + tail
    
    async def _suggest_testing_if_appropriate(self, file_path: str) -> None:
        """
        After generating a key file, suggest or automatically run tests.
        
        Key files that trigger testing consideration:
        - main.py (FastAPI entry point)
        - routers/*.py (API endpoints)
        - App.tsx (React main component)
        """
        # Define key files that should trigger testing
        key_backend_files = ['main.py', 'app.py']
        key_router_patterns = ['routers/', 'routes/', 'endpoints/']
        
        should_consider_test = False
        test_type = None
        
        # Check if this is a backend entry point
        if any(file_path.endswith(f) for f in key_backend_files):
            should_consider_test = True
            test_type = "backend_startup"
            self._log_step("test_hint", f"🧪 Generated entry point: {file_path}")
        
        # Check if this is a router
        elif any(pattern in file_path for pattern in key_router_patterns):
            should_consider_test = True
            test_type = "endpoint"
            self._log_step("test_hint", f"🧪 Generated router: {file_path}")
        
        if should_consider_test:
            # Check if we should test
            should_test_result = await self.call_tool("should_test")
            
            if should_test_result.success and should_test_result.data:
                recommendations = should_test_result.data.get("recommendations", [])
                if should_test_result.data.get("backend", False):
                    self._log_step("test_hint", f"  💡 Backend ready for testing")
                    for rec in recommendations[:2]:
                        self._log_step("test_hint", f"     {rec}")
                    
                    # Store in memory that we're ready to test
                    if self.shared_memory:
                        self.shared_memory.working.set("ready_for_test", "backend")
                        self.shared_memory.working.set("test_suggestion", f"Consider running quick_test() for {file_path}")
    
    async def _resolve_file_path(self, file_path: str) -> str:
        """
        Resolve a file path to an actual existing file in the generated directory.
        
        LLM might return just "database.py" but the file is at "calendar_api/database.py".
        This method tries to find the actual file.
        """
        # First try the exact path
        result = await self.call_tool("file_exists", path=file_path)
        if result.success and result.data:
            return file_path
        
        # If not found, search for the file in the output directory
        if self.gen_context and self.gen_context.output_dir:
            from pathlib import Path
            output_dir = Path(self.gen_context.output_dir)
            
            # Get just the filename
            filename = Path(file_path).name
            
            # Search for files with this name
            matching_files = list(output_dir.rglob(filename))
            if matching_files:
                # Return the first match, relative to output_dir
                relative_path = str(matching_files[0].relative_to(output_dir))
                self._log_step("gather", f"  Resolved '{file_path}' -> '{relative_path}'")
                return relative_path
        
        # If still not found, return original path (will likely fail, but that's expected)
        return file_path
    
    async def _call_tool_with_log(self, tool_name: str, **kwargs):
        """
        Call a tool with detailed logging.
        
        This wraps call_tool to provide better debugging output.
        Also emits events for real-time monitoring.
        """
        from ..events import EventType
        
        # Format args for logging (truncate long values)
        args_display = {}
        for k, v in kwargs.items():
            v_str = repr(v)
            args_display[k] = v_str[:80] + "..." if len(v_str) > 80 else v_str
        
        args_str = ", ".join(f"{k}={v}" for k, v in args_display.items())
        
        self._logger.info(f"[TOOL CALL] {tool_name}({args_str})")
        
        # Emit tool call event (if we have event emitter)
        if self._emitter:
            self._emitter.emit(
                EventType.TOOL_CALL,
                f"{tool_name}",
                {"tool": tool_name, "args": args_display}
            )
        
        result = await self.call_tool(tool_name, **kwargs)
        
        if result.success:
            # Log success with brief result
            data_preview = str(result.data)[:100] if result.data else "None"
            self._logger.info(f"[TOOL OK] {tool_name} -> {data_preview}{'...' if len(str(result.data or '')) > 100 else ''}")
        else:
            # Log failure with error
            error = result.error_message or str(result.data)[:100]
            self._logger.warning(f"[TOOL FAIL] {tool_name} -> {error}")
        
        # Emit tool result event
        if self._emitter:
            self._emitter.emit(
                EventType.TOOL_RESULT,
                f"{tool_name} -> {'✓' if result.success else '✗'}",
                {
                    "tool": tool_name,
                    "success": result.success,
                    "result": str(result.data)[:200] if result.data else None,
                    "error": result.error_message if not result.success else None,
                }
            )
        
        return result
    
    def get_generation_summary(self) -> Dict[str, Any]:
        """Get summary of generation process"""
        return {
            "total_steps": len(self.steps),
            "steps_by_type": {
                step_type: len([s for s in self.steps if s.step_type == step_type])
                for step_type in ["think", "plan", "generate", "reflect", "fix"]
            },
            "successful_steps": len([s for s in self.steps if s.success]),
            "failed_steps": len([s for s in self.steps if not s.success]),
            "errors": [s.error for s in self.steps if s.error],
        }

