"""
Code Tools - Search and edit code

Provides:
- grep: Regex content search
- edit_file: LLM-friendly editing with partial content
- lint: Syntax checking
"""

import os
import re
import ast
import json
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from utils.tool import BaseTool, ToolResult, create_tool_param, ToolCategory
from .path_utils import resolve_path


# ===== Grep Tool =====

class GrepTool(BaseTool):
    """
    Search file contents using regex.
    
    Inspired by OpenHands grep tool.
    """
    
    NAME = "grep"
    
    DESCRIPTION = """Search file contents using regular expressions.

* Full regex support: "def\\s+\\w+", "class.*Model"
* Filter by file pattern: include="*.py"
* Shows file:line:content format
* Searches recursively

Examples:
    grep "import" /src                    # Find all imports
    grep "def main" /src "*.py"           # Find main in Python files
    grep "TODO|FIXME" /project            # Find todos
"""
    
    MAX_RESULTS = 100
    MAX_LINE_LENGTH = 200
    
    def __init__(self, output_dir: str = None):
        super().__init__(name=self.NAME, category=ToolCategory.CODE)
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
    
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
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for"
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search"
                    },
                    "include": {
                        "type": "string",
                        "description": "File pattern to include (e.g., '*.py')"
                    }
                },
                "required": ["pattern", "path"]
            }
        )
    
    def execute(self, pattern: str, path: str, include: str = "*") -> ToolResult:
        search_path = resolve_path(path, self.output_dir)
        
        if not search_path.exists():
            return ToolResult(success=False, error_message=f"Path not found: {path}")
        
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return ToolResult(success=False, error_message=f"Invalid regex: {e}")
        
        results = []
        files_searched = 0
        
        # Determine files to search
        if search_path.is_file():
            files = [search_path]
        else:
            import fnmatch
            files = []
            for root, dirs, filenames in os.walk(search_path):
                # Skip hidden and common ignore dirs
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in 
                          ('node_modules', '__pycache__', 'venv', '.git', 'dist', 'build')]
                
                for f in filenames:
                    if fnmatch.fnmatch(f, include):
                        files.append(Path(root) / f)
        
        # Search files
        for file_path in files:
            files_searched += 1
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            try:
                                rel_path = file_path.relative_to(search_path)
                            except ValueError:
                                rel_path = file_path
                            
                            line_content = line.strip()[:self.MAX_LINE_LENGTH]
                            results.append(f"{rel_path}:{line_num}: {line_content}")
                            
                            if len(results) >= self.MAX_RESULTS:
                                break
            except Exception:
                continue
            
            if len(results) >= self.MAX_RESULTS:
                break
        
        if not results:
            return ToolResult(
                success=True,
                data={"matches": 0, "info": f"No matches for '{pattern}' ({files_searched} files searched)"}
            )
        
        output = [f"Found {len(results)} matches:"] + results
        if len(results) >= self.MAX_RESULTS:
            output.append(f"... (showing first {self.MAX_RESULTS} results)")
        
        return ToolResult(
            success=True,
            data={"matches": len(results), "output": "\n".join(output)}
        )


# ===== Edit File Tool =====

class EditFileTool(BaseTool):
    """
    LLM-friendly file editing with partial content.
    
    Based on OpenHands edit_file / llm_based_edit.
    Allows using "# ... existing code ..." to skip unchanged parts.
    """
    
    NAME = "edit_file"
    
    DESCRIPTION = """Edit a file using LLM-friendly partial content.

You can use "# ... existing code ..." to indicate parts that stay the same.
This is useful for large files where you only want to change a small part.

The edit will:
1. Read the current file content
2. Match your partial content to the file
3. Apply only the changes you specified

For small, precise edits, use str_replace_editor instead.

Parameters:
- path: File to edit
- content: New content (can use "# ... existing code ..." markers)
- start: Start line for editing (optional)
- end: End line for editing (optional)

Example:
    edit_file /path/to/file.py "
def function():
    # ... existing code ...
    new_line = True  # This is added
    # ... existing code ...
"
"""
    
    SKIP_MARKERS = [
        "# ... existing code ...",
        "// ... existing code ...",
        "/* ... existing code ... */",
        "# ... rest of code ...",
        "// ... rest of code ...",
    ]
    
    def __init__(self, output_dir: str = None):
        super().__init__(name=self.NAME, category=ToolCategory.CODE)
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
    
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
                    "path": {
                        "type": "string",
                        "description": "File path to edit"
                    },
                    "content": {
                        "type": "string",
                        "description": "New content (use '# ... existing code ...' for unchanged parts)"
                    },
                    "start": {
                        "type": "integer",
                        "description": "Start line (optional, 1-indexed)"
                    },
                    "end": {
                        "type": "integer",
                        "description": "End line (optional, 1-indexed, -1 for end of file)"
                    }
                },
                "required": ["path", "content"]
            }
        )
    
    def execute(
        self,
        path: str,
        content: str,
        start: int = None,
        end: int = None
    ) -> ToolResult:
        
        file_path = resolve_path(path, self.output_dir)
        
        # If file doesn't exist, create it
        if not file_path.exists():
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding='utf-8')
                return ToolResult(
                    success=True,
                    data={"action": "create", "info": f"Created new file: {file_path}"}
                )
            except Exception as e:
                return ToolResult(success=False, error_message=f"Create failed: {e}")
        
        # Read current content
        try:
            current = file_path.read_text(encoding='utf-8')
            current_lines = current.splitlines(keepends=True)
        except Exception as e:
            return ToolResult(success=False, error_message=f"Read failed: {e}")
        
        total_lines = len(current_lines)
        
        # Handle line range
        if start is not None:
            start = max(1, start) - 1  # Convert to 0-indexed
        else:
            start = 0
        
        if end is not None:
            if end == -1:
                end = total_lines
            else:
                end = min(end, total_lines)
        else:
            end = total_lines
        
        # Check if content has skip markers
        has_markers = any(marker in content for marker in self.SKIP_MARKERS)
        
        if has_markers:
            # Process partial content
            new_content = self._apply_partial_edit(current_lines[start:end], content)
        else:
            # Full replacement of range
            new_content = content
        
        # Build final content
        new_lines = new_content.splitlines(keepends=True)
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'
        
        final_content = ''.join(current_lines[:start] + new_lines + current_lines[end:])
        
        # Write
        try:
            file_path.write_text(final_content, encoding='utf-8')
            return ToolResult(
                success=True,
                data={
                    "action": "edit",
                    "range": [start + 1, end],
                    "lines_changed": len(new_lines),
                    "info": f"Edited {file_path} (lines {start+1}-{end})"
                }
            )
        except Exception as e:
            return ToolResult(success=False, error_message=f"Write failed: {e}")
    
    def _apply_partial_edit(self, original_lines: List[str], new_content: str) -> str:
        """Apply edit with skip markers."""
        new_lines = new_content.split('\n')
        result = []
        original_idx = 0
        
        for new_line in new_lines:
            # Check if this is a skip marker
            is_marker = any(marker in new_line for marker in self.SKIP_MARKERS)
            
            if is_marker:
                # Try to find where to resume in original
                # Look at next non-marker line
                next_content_idx = None
                for i, nl in enumerate(new_lines[new_lines.index(new_line) + 1:], start=new_lines.index(new_line) + 1):
                    if not any(m in nl for m in self.SKIP_MARKERS):
                        next_content_idx = i
                        break
                
                if next_content_idx is not None:
                    next_content = new_lines[next_content_idx].strip()
                    # Find this in original
                    for i in range(original_idx, len(original_lines)):
                        orig_stripped = original_lines[i].rstrip('\n\r')
                        if next_content and next_content in orig_stripped:
                            # Copy everything from original_idx to i
                            for j in range(original_idx, i):
                                result.append(original_lines[j].rstrip('\n\r'))
                            original_idx = i
                            break
                else:
                    # Skip marker at end - copy rest of original
                    for j in range(original_idx, len(original_lines)):
                        result.append(original_lines[j].rstrip('\n\r'))
                    original_idx = len(original_lines)
            else:
                result.append(new_line)
                # Try to advance original_idx
                for i in range(original_idx, len(original_lines)):
                    if new_line.strip() and new_line.strip() in original_lines[i]:
                        original_idx = i + 1
                        break
        
        return '\n'.join(result)


# ===== Lint Tool =====

class LintTool(BaseTool):
    """
    Enhanced lint tool using real linters (ruff, eslint, sqlfluff).
    Falls back to basic checks if tools are not installed.
    """
    
    NAME = "lint"
    
    DESCRIPTION = """Check code for syntax errors and style issues.

Supports:
- Python: Uses ruff (fast linter), falls back to ast.parse
- JavaScript/TypeScript: Uses eslint if available
- JSON: Validates JSON structure
- SQL: Uses sqlfluff if available

Returns errors with line numbers and suggestions.
"""
    
    def __init__(self, output_dir: str = None):
        super().__init__(name=self.NAME, category=ToolCategory.CODE)
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self._tool_cache = {}  # Cache which tools are available
    
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
                    "path": {
                        "type": "string",
                        "description": "File path to check"
                    }
                },
                "required": ["path"]
            }
        )
    
    def _check_tool_available(self, tool_name: str) -> bool:
        """Check if a linting tool is available."""
        if tool_name in self._tool_cache:
            return self._tool_cache[tool_name]
        
        available = shutil.which(tool_name) is not None
        self._tool_cache[tool_name] = available
        return available
    
    def execute(self, path: str) -> ToolResult:
        file_path = resolve_path(path, self.output_dir)
        
        if not file_path.exists():
            return ToolResult(success=False, error_message=f"File not found: {path}")
        
        ext = file_path.suffix.lower()
        
        if ext == '.py':
            return self._lint_python(file_path)
        elif ext == '.json':
            return self._lint_json(file_path)
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            return self._lint_javascript(file_path)
        elif ext == '.sql':
            return self._lint_sql(file_path)
        else:
            return ToolResult(
                success=True,
                data=f"No lint rules for {ext} files"
            )
    
    def _lint_python(self, file_path: Path) -> ToolResult:
        """Lint Python using ruff, fall back to ast.parse."""
        # Try ruff first (fast and comprehensive)
        if self._check_tool_available('ruff'):
            try:
                result = subprocess.run(
                    ['ruff', 'check', '--output-format=json', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                errors = []
                if result.stdout:
                    try:
                        ruff_errors = json.loads(result.stdout)
                        for err in ruff_errors:
                            errors.append({
                                "line": err.get("location", {}).get("row", 0),
                                "column": err.get("location", {}).get("column", 0),
                                "code": err.get("code", ""),
                                "msg": err.get("message", ""),
                                "fix": err.get("fix", {}).get("message") if err.get("fix") else None
                            })
                    except json.JSONDecodeError:
                        pass
                
                if errors:
                    error_summary = "; ".join([f"L{e['line']}: [{e['code']}] {e['msg']}" for e in errors[:5]])
                    return ToolResult(
                        success=False,
                        data={"errors": errors, "tool": "ruff"},
                        error_message=f"Found {len(errors)} issues: {error_summary}"
                    )
                
                return ToolResult(
                    success=True,
                    data={"errors": [], "tool": "ruff", "message": f"Python lint OK: {file_path.name}"}
                )
            except subprocess.TimeoutExpired:
                pass  # Fall back to basic check
            except Exception:
                pass  # Fall back to basic check
        
        # Fallback to ast.parse (basic syntax check)
        try:
            content = file_path.read_text(encoding='utf-8')
            ast.parse(content)
            return ToolResult(
                success=True,
                data={"errors": [], "tool": "ast", "message": f"Python syntax OK: {file_path.name}"}
            )
        except SyntaxError as e:
            return ToolResult(
                success=False,
                data={"errors": [{"line": e.lineno, "column": e.offset, "msg": e.msg}], "tool": "ast"},
                error_message=f"Syntax error at line {e.lineno}: {e.msg}"
            )
    
    def _lint_javascript(self, file_path: Path) -> ToolResult:
        """Lint JavaScript/TypeScript using eslint."""
        # Try eslint
        if self._check_tool_available('npx'):
            try:
                result = subprocess.run(
                    ['npx', '--yes', 'eslint', '--format=json', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=file_path.parent
                )
                
                errors = []
                if result.stdout:
                    try:
                        eslint_result = json.loads(result.stdout)
                        for file_result in eslint_result:
                            for msg in file_result.get("messages", []):
                                errors.append({
                                    "line": msg.get("line", 0),
                                    "column": msg.get("column", 0),
                                    "code": msg.get("ruleId", ""),
                                    "msg": msg.get("message", ""),
                                    "severity": "error" if msg.get("severity") == 2 else "warning"
                                })
                    except json.JSONDecodeError:
                        pass
                
                if errors:
                    error_summary = "; ".join([f"L{e['line']}: {e['msg']}" for e in errors[:5]])
                    return ToolResult(
                        success=False,
                        data={"errors": errors, "tool": "eslint"},
                        error_message=f"Found {len(errors)} issues: {error_summary}"
                    )
                
                return ToolResult(
                    success=True,
                    data={"errors": [], "tool": "eslint", "message": f"JS/TS lint OK: {file_path.name}"}
                )
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                pass
        
        # Fallback: basic syntax check with esprima-style parsing
        return ToolResult(
            success=True,
            data={"errors": [], "tool": "none", "message": f"No JS linter available for: {file_path.name}"}
        )
    
    def _lint_sql(self, file_path: Path) -> ToolResult:
        """Lint SQL using sqlfluff."""
        if self._check_tool_available('sqlfluff'):
            try:
                result = subprocess.run(
                    ['sqlfluff', 'lint', '--format=json', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                errors = []
                if result.stdout:
                    try:
                        sqlfluff_result = json.loads(result.stdout)
                        for violation in sqlfluff_result:
                            for v in violation.get("violations", []):
                                errors.append({
                                    "line": v.get("start_line_no", 0),
                                    "column": v.get("start_line_pos", 0),
                                    "code": v.get("code", ""),
                                    "msg": v.get("description", "")
                                })
                    except json.JSONDecodeError:
                        pass
                
                if errors:
                    error_summary = "; ".join([f"L{e['line']}: [{e['code']}] {e['msg']}" for e in errors[:5]])
                    return ToolResult(
                        success=False,
                        data={"errors": errors, "tool": "sqlfluff"},
                        error_message=f"Found {len(errors)} issues: {error_summary}"
                    )
                
                return ToolResult(
                    success=True,
                    data={"errors": [], "tool": "sqlfluff", "message": f"SQL lint OK: {file_path.name}"}
                )
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                pass
        
        # Fallback: no SQL linting
        return ToolResult(
            success=True,
            data={"errors": [], "tool": "none", "message": f"No SQL linter available for: {file_path.name}"}
        )
    
    def _lint_json(self, file_path: Path) -> ToolResult:
        """Lint JSON (basic validation)."""
        try:
            content = file_path.read_text(encoding='utf-8')
            json.loads(content)
            return ToolResult(
                success=True,
                data={"errors": [], "tool": "json", "message": f"JSON syntax OK: {file_path.name}"}
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                data={"errors": [{"line": e.lineno, "column": e.colno, "msg": e.msg}], "tool": "json"},
                error_message=f"JSON error at line {e.lineno}: {e.msg}"
            )


# ===== Think Tool =====

class ThinkTool(BaseTool):
    """
    Think/reason without taking action.
    
    Use for complex planning, brainstorming, debugging.
    """
    
    NAME = "think"
    
    DESCRIPTION = """Use this tool to think through complex problems.

The thought is recorded but no action is taken.
Useful for:
- Complex multi-step planning
- Debugging analysis
- Brainstorming solutions
- Understanding error messages

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


# ===== Finish Tool =====

class FinishTool(BaseTool):
    """
    Signal task completion.
    """
    
    NAME = "finish"
    
    DESCRIPTION = """Use when the task is complete.

Provide a summary of what was done and any outputs.
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
                    "message": {
                        "type": "string",
                        "description": "Summary of completed work"
                    },
                    "outputs": {
                        "type": "object",
                        "description": "Any output data"
                    }
                },
                "required": ["message"]
            }
        )
    
    def execute(self, message: str, outputs: dict = None) -> ToolResult:
        return ToolResult(
            success=True,
            data={"outputs": outputs or {}, "finished": True, "info": f"Task completed: {message}"}
        )


# ===== Exports =====

__all__ = [
    "GrepTool",
    "EditFileTool",
    "LintTool",
    "ThinkTool",
    "FinishTool",
]
