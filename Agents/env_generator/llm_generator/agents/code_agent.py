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

from ..tools.file_tools import ReadFileTool, WriteFileTool, ListDirTool, FileExistsTool
from ..tools.code_tools import GrepTool, SearchReplaceTool, LintTool, SyntaxCheckTool
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
    SYSTEM_PROMPT = """You are an expert code generator. You generate high-quality, production-ready code.

When generating code:
1. THINK first - understand what's needed
2. Check existing files to maintain consistency
3. Generate clean, well-documented code
4. Verify the code is syntactically correct
5. If you find issues, fix them

You have tools available:
- read_file: Read existing files to understand context
- write_file: Create new files
- grep: Search for patterns in code
- search_replace: Make targeted modifications
- lint: Check code for errors
- syntax_check: Verify code syntax before writing

Always think step by step. If something seems wrong, investigate before proceeding."""
    
    def __init__(
        self,
        config: AgentConfig,
        output_dir: Path,
        gen_context: Optional[GenerationContext] = None,
        shared_memory: Optional[Any] = None,  # AgentMemory from orchestrator
    ):
        super().__init__(config, role=AgentRole.WORKER)
        
        self.output_dir = output_dir
        self.gen_context = gen_context
        self.shared_memory = shared_memory  # Shared across all phases
        
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
        await super().on_initialize()
        
        # Register code generation tools
        self.register_tool(ReadFileTool(self.output_dir))
        self.register_tool(WriteFileTool(self.output_dir))
        self.register_tool(ListDirTool(self.output_dir))
        self.register_tool(FileExistsTool(self.output_dir))
        self.register_tool(GrepTool(self.output_dir))
        self.register_tool(SearchReplaceTool(self.output_dir))
        self.register_tool(LintTool(self.output_dir))
        self.register_tool(SyntaxCheckTool())
        
        self._logger.info(f"CodeGeneratorAgent initialized with {len(self._tools)} tools")
    
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
        
        prompt = f"""Before generating {file_path}, I need to think carefully.

FILE TO GENERATE: {file_path}
PURPOSE: {purpose}

EXISTING FILES IN PROJECT:
{chr(10).join(f"- {f}" for f in existing_files[:20])}

{tools_desc}

Think step by step:
1. What other files should I READ first to understand the context?
   (e.g., if generating a router, I should read models.py and schemas.py)
   → Use: read_file tool
2. What patterns should I SEARCH (grep) for in the codebase?
   (e.g., search for "class User" to understand the User model)
   → Use: grep tool
3. What's my APPROACH for generating this file?
4. What CONSIDERATIONS/pitfalls should I be careful about?

Respond in this JSON format:
{{
  "needs_context": ["file1.py", "file2.py"],
  "needs_grep": [
    {{"pattern": "class.*Model", "reason": "find model definitions"}},
    {{"pattern": "def.*endpoint", "reason": "check existing endpoints"}}
  ],
  "approach": "First I will..., then I will...",
  "considerations": ["Make sure to...", "Don't forget to..."]
}}"""

        result = await self._reasoner.run(prompt)
        answer = str(result.answer) if result.answer else "{}"
        
        # Parse JSON response
        import json
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', answer)
            if json_match:
                thinking = json.loads(json_match.group())
            else:
                thinking = {"needs_context": [], "needs_grep": [], "approach": answer, "considerations": []}
        except json.JSONDecodeError:
            thinking = {"needs_context": [], "needs_grep": [], "approach": answer, "considerations": []}
        
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
        for file_path in files_to_read[:5]:  # Limit to 5 files
            result = await self.call_tool("read_file", path=file_path)
            if result.success:
                content = result.data[:3000]  # Truncate long files
                context_parts.append(f"### {file_path}\n```\n{content}\n```")
                self._log_step("gather", f"Read: {file_path} ({len(content)} chars)")
        
        # Search for patterns
        grep_patterns = thinking.get("needs_grep", [])
        for grep_info in grep_patterns[:3]:  # Limit to 3 patterns
            pattern = grep_info.get("pattern", "") if isinstance(grep_info, dict) else str(grep_info)
            if pattern:
                result = await self.call_tool("grep", pattern=pattern, path=".")
                if result.success and result.data:
                    context_parts.append(f"### Grep: {pattern}\n```\n{result.data[:1500]}\n```")
                    self._log_step("gather", f"Grep '{pattern}': found matches")
        
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
            syntax_result = await self.call_tool("syntax_check", code=code, language=language)
            
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
        
        # 2. Lint check (if file was written)
        self._log_step("reflect", "  Running lint check...")
        lint_result = await self.call_tool("lint", path=file_path)
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
                    if target and target not in [h.get("target") for h in exploration_history]:
                        self._log_step("reflect", f"  [Round {round_num+1}] Reading {target}...")
                        result = await self.call_tool("read_file", path=target)
                        if result.success:
                            content_preview = result.data[:500]
                            check_results.append(f"READ {target}: {len(result.data)} chars")
                            checks_performed.append(f"read_file:{target}")
                            round_findings.append(f"READ {target}: {content_preview}")
                            exploration_history.append({"tool": "read_file", "target": target, "result": content_preview})
                
                elif tool == "grep":
                    pattern = check.get("pattern", "")
                    if pattern and pattern not in [h.get("pattern") for h in exploration_history]:
                        self._log_step("reflect", f"  [Round {round_num+1}] Searching: {pattern}...")
                        result = await self.call_tool("grep", pattern=pattern, path=".")
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
        all_issues = list(set(issues_found + reflection.get("issues", [])))
        reflection["issues"] = all_issues
        reflection["checks_performed"] = checks_performed
        
        # Override quality if we found critical issues
        if any("SYNTAX ERROR" in i for i in all_issues):
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
    
    def _get_available_tools_description(self) -> str:
        """
        Get a description of all available tools for the agent.
        
        This is included in prompts so the LLM knows what capabilities it has.
        """
        tools_desc = """
AVAILABLE TOOLS (you can request to use these):
- read_file(path): Read any file in the project to understand existing code
- write_file(path, content): Create or overwrite a file
- list_dir(path): List files in a directory to explore project structure
- file_exists(path): Check if a file exists
- grep(pattern, path): Search for patterns/text across files (regex supported)
- search_replace(path, old_string, new_string): Make targeted edits to existing files
- lint(path): Check code for syntax errors and style issues
- syntax_check(code, language): Verify code is syntactically valid before writing

HOW TO USE TOOLS:
- To read a file first: Include it in "needs_context" list
- To search for patterns: Include in "needs_grep" list with pattern and reason
- Tools are executed automatically based on your planning decisions
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
        
        prompt = f"""Generate code for: {file_path}

PURPOSE: {purpose}
{format_instructions}
INSTRUCTIONS:
{instructions}

CONTEXT FROM EXISTING FILES:
{dep_context[:4000] if dep_context else "No dependencies"}
{memory_context}
{snippets_section}

Generate ONLY the code, no markdown fences or explanations.
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
                code = str(fix_result.answer) if fix_result.answer else code
        
        # Step 5: Write file
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
    ) -> List[str]:
        """
        Reflect on generated code - find issues.
        
        This is like my process of reviewing code after writing:
        - Check for syntax errors
        - Check imports match exports
        - Check for consistency
        - Check for MISSING files that are imported
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
        
        self.steps.append(GenerationStep(
            step_type="reflect",
            description=f"Found {len(issues)} issues",
            output_data=issues,
            success=len(issues) == 0,
        ))
        
        return issues
    
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
                    
                    # Handle CREATE_FILE response
                    if "CREATE_FILE:" in answer:
                        try:
                            file_to_create = answer.split("CREATE_FILE:")[1].split("CONTENT:")[0].strip()
                            file_content = answer.split("CONTENT:")[1].strip()
                            
                            write_result = await self.call_tool("write_file", path=file_to_create, content=file_content)
                            if write_result.success:
                                fixes_applied.append(f"Created: {file_to_create}")
                                fix_successful = True
                        except Exception:
                            pass
                    
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

