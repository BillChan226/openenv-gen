"""
Code Operation Tools

These tools give the agent the ability to search and modify code,
similar to grep and search_replace that I use.
"""

import ast
import re
import json
from pathlib import Path
from typing import List, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils.tool import BaseTool, ToolDefinition, ToolParameter, ToolResult, ToolCategory


class GrepTool(BaseTool):
    """
    Search for patterns in files.
    
    This is one of my most-used tools. It helps find:
    - Where a function is defined
    - Where a variable is used
    - All imports in a file
    - Specific error patterns
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="grep",
            description="Search for a pattern in files. Use regex for complex patterns. Returns matching lines with context.",
            category=ToolCategory.SEARCH,
            parameters=[
                ToolParameter(
                    name="pattern",
                    param_type=str,
                    description="Regex pattern to search for",
                    required=True,
                ),
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="File or directory to search in (default: '.')",
                    required=False,
                    default=".",
                ),
                ToolParameter(
                    name="file_pattern",
                    param_type=str,
                    description="Glob pattern for file types (e.g., '*.py', '*.tsx')",
                    required=False,
                    default="*",
                ),
                ToolParameter(
                    name="context_lines",
                    param_type=int,
                    description="Number of context lines before/after match",
                    required=False,
                    default=2,
                ),
            ],
            returns="Matching lines with file paths and line numbers",
            examples=[
                {"input": {"pattern": "def process_task", "path": "src/"}, 
                 "output": "src/agent.py:42: def process_task(self, task):"},
            ],
            tags=["search", "grep", "find"],
        )
    
    async def execute(
        self,
        pattern: str,
        path: str = ".",
        file_pattern: str = "*",
        context_lines: int = 2,
        **kwargs
    ) -> ToolResult:
        try:
            search_path = self.base_dir / path
            
            if not search_path.exists():
                return ToolResult.fail(f"Path not found: {path}")
            
            # Compile regex
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                return ToolResult.fail(f"Invalid regex pattern: {e}")
            
            matches = []
            
            # Get files to search
            if search_path.is_file():
                files = [search_path]
            else:
                files = list(search_path.rglob(file_pattern))
            
            for file_path in files:
                if not file_path.is_file():
                    continue
                
                # Skip binary and ignored files
                if any(p in str(file_path) for p in ["node_modules", "__pycache__", ".git", ".pyc"]):
                    continue
                
                try:
                    content = file_path.read_text(encoding="utf-8")
                    lines = content.split("\n")
                    
                    for i, line in enumerate(lines):
                        if regex.search(line):
                            # Get context
                            start = max(0, i - context_lines)
                            end = min(len(lines), i + context_lines + 1)
                            
                            rel_path = file_path.relative_to(self.base_dir)
                            
                            context = []
                            for j in range(start, end):
                                prefix = ">" if j == i else " "
                                context.append(f"{prefix} {j+1:4}|{lines[j]}")
                            
                            matches.append({
                                "file": str(rel_path),
                                "line": i + 1,
                                "match": line.strip(),
                                "context": "\n".join(context),
                            })
                            
                except (UnicodeDecodeError, PermissionError):
                    continue
            
            if not matches:
                return ToolResult.ok(f"No matches found for pattern: {pattern}")
            
            # Format output
            output = []
            for m in matches[:20]:  # Limit results
                output.append(f"\n{m['file']}:{m['line']}")
                output.append(m['context'])
            
            return ToolResult.ok("\n".join(output))
            
        except Exception as e:
            return ToolResult.fail(f"Error searching: {e}")


class SearchReplaceTool(BaseTool):
    """
    Search and replace in a file.
    
    This is how I make targeted modifications without rewriting entire files.
    Much safer than rewriting - only changes what's needed.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_replace",
            description="Replace text in a file. Use for targeted modifications. The old_string must match exactly.",
            category=ToolCategory.CODE,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="File path to modify",
                    required=True,
                ),
                ToolParameter(
                    name="old_string",
                    param_type=str,
                    description="Exact string to find (must be unique in file)",
                    required=True,
                ),
                ToolParameter(
                    name="new_string",
                    param_type=str,
                    description="String to replace with",
                    required=True,
                ),
                ToolParameter(
                    name="replace_all",
                    param_type=bool,
                    description="Replace all occurrences (default: False, replace first only)",
                    required=False,
                    default=False,
                ),
            ],
            returns="Success message with number of replacements",
            examples=[
                {"input": {"path": "src/main.py", "old_string": "def old_name", "new_string": "def new_name"},
                 "output": "Replaced 1 occurrence in src/main.py"},
            ],
            tags=["edit", "replace", "modify"],
        )
    
    async def execute(
        self,
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
        **kwargs
    ) -> ToolResult:
        try:
            file_path = self.base_dir / path
            
            if not file_path.exists():
                return ToolResult.fail(f"File not found: {path}")
            
            content = file_path.read_text(encoding="utf-8")
            
            # Check if old_string exists
            count = content.count(old_string)
            if count == 0:
                return ToolResult.fail(f"String not found in {path}. Make sure old_string matches exactly.")
            
            if count > 1 and not replace_all:
                return ToolResult.fail(
                    f"String found {count} times. Use replace_all=True to replace all, "
                    "or provide more context to make old_string unique."
                )
            
            # Replace
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replaced = count
            else:
                new_content = content.replace(old_string, new_string, 1)
                replaced = 1
            
            # Write back
            file_path.write_text(new_content, encoding="utf-8")
            
            return ToolResult.ok(f"Replaced {replaced} occurrence(s) in {path}")
            
        except Exception as e:
            return ToolResult.fail(f"Error replacing: {e}")


class EditLinesTool(BaseTool):
    """
    Edit specific lines in a file.
    
    More precise than search_replace when you know exactly which lines to change.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="edit_lines",
            description="Replace lines N to M in a file with new content. Use when you know exact line numbers.",
            category=ToolCategory.CODE,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="File path to modify",
                    required=True,
                ),
                ToolParameter(
                    name="start_line",
                    param_type=int,
                    description="Start line number (1-indexed, inclusive)",
                    required=True,
                ),
                ToolParameter(
                    name="end_line",
                    param_type=int,
                    description="End line number (1-indexed, inclusive)",
                    required=True,
                ),
                ToolParameter(
                    name="new_content",
                    param_type=str,
                    description="New content to replace the lines with",
                    required=True,
                ),
            ],
            returns="Success message with lines modified",
            examples=[
                {"input": {"path": "src/main.py", "start_line": 10, "end_line": 15, "new_content": "def new_function():\n    pass"},
                 "output": "Replaced lines 10-15 in src/main.py"},
            ],
            tags=["edit", "lines", "modify"],
        )
    
    async def execute(
        self,
        path: str,
        start_line: int,
        end_line: int,
        new_content: str,
        **kwargs
    ) -> ToolResult:
        try:
            file_path = self.base_dir / path
            
            if not file_path.exists():
                return ToolResult.fail(f"File not found: {path}")
            
            lines = file_path.read_text(encoding="utf-8").split('\n')
            total_lines = len(lines)
            
            # Validate line numbers
            if start_line < 1 or end_line < 1:
                return ToolResult.fail("Line numbers must be >= 1")
            if start_line > end_line:
                return ToolResult.fail("start_line must be <= end_line")
            if start_line > total_lines:
                return ToolResult.fail(f"start_line ({start_line}) exceeds file length ({total_lines})")
            
            # Convert to 0-indexed
            start_idx = start_line - 1
            end_idx = min(end_line, total_lines)  # Clamp to file length
            
            # Build new content
            new_lines = new_content.split('\n')
            result_lines = lines[:start_idx] + new_lines + lines[end_idx:]
            
            # Write back
            file_path.write_text('\n'.join(result_lines), encoding="utf-8")
            
            return ToolResult.ok({
                "message": f"Replaced lines {start_line}-{end_line} in {path}",
                "old_lines": end_line - start_line + 1,
                "new_lines": len(new_lines),
            })
            
        except Exception as e:
            return ToolResult.fail(f"Error editing lines: {e}")


class InsertLinesTool(BaseTool):
    """
    Insert lines at a specific position in a file.
    
    Useful for adding new functions, imports, or code blocks.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="insert_lines",
            description="Insert new lines at a specific position in a file (after line N).",
            category=ToolCategory.CODE,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="File path to modify",
                    required=True,
                ),
                ToolParameter(
                    name="after_line",
                    param_type=int,
                    description="Insert after this line number (0 = insert at beginning)",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    param_type=str,
                    description="Content to insert",
                    required=True,
                ),
            ],
            returns="Success message",
            examples=[
                {"input": {"path": "src/main.py", "after_line": 5, "content": "import os"},
                 "output": "Inserted 1 line(s) after line 5 in src/main.py"},
            ],
            tags=["edit", "insert", "add"],
        )
    
    async def execute(
        self,
        path: str,
        after_line: int,
        content: str,
        **kwargs
    ) -> ToolResult:
        try:
            file_path = self.base_dir / path
            
            if not file_path.exists():
                return ToolResult.fail(f"File not found: {path}")
            
            lines = file_path.read_text(encoding="utf-8").split('\n')
            total_lines = len(lines)
            
            if after_line < 0:
                return ToolResult.fail("after_line must be >= 0")
            if after_line > total_lines:
                after_line = total_lines  # Append at end
            
            # Insert
            new_lines = content.split('\n')
            result_lines = lines[:after_line] + new_lines + lines[after_line:]
            
            # Write back
            file_path.write_text('\n'.join(result_lines), encoding="utf-8")
            
            return ToolResult.ok(f"Inserted {len(new_lines)} line(s) after line {after_line} in {path}")
            
        except Exception as e:
            return ToolResult.fail(f"Error inserting lines: {e}")


class EditFunctionTool(BaseTool):
    """
    Edit a specific function or class in a file.
    
    Finds the function/class by name and replaces its entire body.
    More intuitive than line numbers for code modifications.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="edit_function",
            description="Replace an entire function or class definition by name. Finds it and replaces with new code.",
            category=ToolCategory.CODE,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="File path to modify",
                    required=True,
                ),
                ToolParameter(
                    name="name",
                    param_type=str,
                    description="Function or class name to find and replace",
                    required=True,
                ),
                ToolParameter(
                    name="new_code",
                    param_type=str,
                    description="Complete new function/class definition including signature",
                    required=True,
                ),
            ],
            returns="Success message with location modified",
            examples=[
                {"input": {
                    "path": "src/main.py",
                    "name": "process_data",
                    "new_code": "def process_data(data):\n    # New implementation\n    return data * 2"
                 },
                 "output": "Replaced function 'process_data' at lines 15-25 in src/main.py"},
            ],
            tags=["edit", "function", "class", "modify"],
        )
    
    async def execute(
        self,
        path: str,
        name: str,
        new_code: str,
        **kwargs
    ) -> ToolResult:
        try:
            file_path = self.base_dir / path
            
            if not file_path.exists():
                return ToolResult.fail(f"File not found: {path}")
            
            content = file_path.read_text(encoding="utf-8")
            lines = content.split('\n')
            
            # Find the function/class definition
            start_line = None
            end_line = None
            indent_level = None
            
            # Patterns to match
            patterns = [
                f"def {name}(",
                f"async def {name}(",
                f"class {name}(",
                f"class {name}:",
            ]
            
            for i, line in enumerate(lines):
                stripped = line.lstrip()
                
                # Check if this is the target definition
                if start_line is None:
                    for pattern in patterns:
                        if stripped.startswith(pattern):
                            start_line = i
                            indent_level = len(line) - len(stripped)
                            break
                
                # Find the end of the definition (next line with same or less indentation)
                elif start_line is not None and i > start_line:
                    if stripped and not stripped.startswith('#'):
                        current_indent = len(line) - len(stripped)
                        if current_indent <= indent_level:
                            end_line = i
                            break
            
            if start_line is None:
                return ToolResult.fail(f"Could not find function/class '{name}' in {path}")
            
            # If we didn't find end, it goes to EOF
            if end_line is None:
                end_line = len(lines)
            
            # Build new content
            new_lines = new_code.split('\n')
            # Preserve original indentation
            if indent_level > 0:
                indent = ' ' * indent_level
                new_lines = [indent + line if line.strip() else line for line in new_lines]
            
            result_lines = lines[:start_line] + new_lines + lines[end_line:]
            
            # Write back
            file_path.write_text('\n'.join(result_lines), encoding="utf-8")
            
            return ToolResult.ok({
                "message": f"Replaced '{name}' at lines {start_line + 1}-{end_line} in {path}",
                "old_lines": end_line - start_line,
                "new_lines": len(new_lines),
            })
            
        except Exception as e:
            return ToolResult.fail(f"Error editing function: {e}")


class LintTool(BaseTool):
    """
    Lint/check code for errors.
    
    I use this after generating code to verify it's syntactically correct.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="lint",
            description="Check code files for syntax errors and common issues",
            category=ToolCategory.CODE,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="File or directory to lint",
                    required=True,
                ),
            ],
            returns="List of issues found, or 'No issues' if clean",
            tags=["lint", "check", "verify"],
        )
    
    async def execute(self, path: str, **kwargs) -> ToolResult:
        try:
            target = self.base_dir / path
            
            if not target.exists():
                return ToolResult.fail(f"Path not found: {path}")
            
            issues = []
            
            # Get files to check
            if target.is_file():
                files = [target]
            else:
                files = list(target.rglob("*"))
            
            for file_path in files:
                if not file_path.is_file():
                    continue
                
                suffix = file_path.suffix.lower()
                
                if suffix == ".py":
                    issue = self._lint_python(file_path)
                    if issue:
                        issues.append(issue)
                
                elif suffix in [".ts", ".tsx"]:
                    issue = self._lint_typescript(file_path)
                    if issue:
                        issues.append(issue)
                
                elif suffix == ".json":
                    issue = self._lint_json(file_path)
                    if issue:
                        issues.append(issue)
            
            if issues:
                return ToolResult.ok({
                    "passed": False,
                    "issues": issues,
                })
            else:
                return ToolResult.ok({
                    "passed": True,
                    "message": "No issues found",
                })
                
        except Exception as e:
            return ToolResult.fail(f"Error linting: {e}")
    
    def _lint_python(self, file_path: Path) -> Optional[str]:
        """Check Python syntax"""
        try:
            content = file_path.read_text(encoding="utf-8")
            compile(content, str(file_path), "exec")
            return None
        except SyntaxError as e:
            return f"{file_path.name}:{e.lineno}: SyntaxError - {e.msg}"
    
    def _lint_typescript(self, file_path: Path) -> Optional[str]:
        """Basic TypeScript/JSX check"""
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Check bracket balance
            opens = content.count("{") + content.count("(") + content.count("[")
            closes = content.count("}") + content.count(")") + content.count("]")
            
            if opens != closes:
                return f"{file_path.name}: Unbalanced brackets (open={opens}, close={closes})"
            
            # Check for common JSX issues
            if file_path.suffix == ".tsx":
                # Check for unclosed tags (simple heuristic)
                jsx_opens = len(re.findall(r"<[A-Z]\w+[^/>]*>", content))
                jsx_closes = len(re.findall(r"</[A-Z]\w+>", content))
                self_closing = len(re.findall(r"<[A-Z]\w+[^>]*/\s*>", content))
                
                if jsx_opens - self_closing > jsx_closes + 5:  # Allow some tolerance
                    return f"{file_path.name}: Possible unclosed JSX tags"
            
            return None
        except Exception as e:
            return f"{file_path.name}: Error reading file - {e}"
    
    def _lint_json(self, file_path: Path) -> Optional[str]:
        """Check JSON syntax"""
        try:
            content = file_path.read_text(encoding="utf-8")
            json.loads(content)
            return None
        except json.JSONDecodeError as e:
            return f"{file_path.name}:{e.lineno}: JSONError - {e.msg}"


class SyntaxCheckTool(BaseTool):
    """
    Quick syntax check for a code string.
    
    Used to verify generated code before writing to file.
    """
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="syntax_check",
            description="Check if a code string has valid syntax (Python or JSON)",
            category=ToolCategory.CODE,
            parameters=[
                ToolParameter(
                    name="code",
                    param_type=str,
                    description="Code string to check",
                    required=True,
                ),
                ToolParameter(
                    name="language",
                    param_type=str,
                    description="Language: 'python' or 'json'",
                    required=False,
                    default="python",
                    choices=["python", "json"],
                ),
            ],
            returns="{'valid': bool, 'error': str or None}",
            tags=["syntax", "check", "verify"],
        )
    
    async def execute(
        self,
        code: str,
        language: str = "python",
        **kwargs
    ) -> ToolResult:
        try:
            if language == "python":
                compile(code, "<string>", "exec")
                return ToolResult.ok({"valid": True, "error": None})
            
            elif language == "json":
                json.loads(code)
                return ToolResult.ok({"valid": True, "error": None})
            
            else:
                return ToolResult.fail(f"Unsupported language: {language}")
                
        except SyntaxError as e:
            return ToolResult.ok({
                "valid": False,
                "error": f"Line {e.lineno}: {e.msg}",
            })
        except json.JSONDecodeError as e:
            return ToolResult.ok({
                "valid": False,
                "error": f"Line {e.lineno}: {e.msg}",
            })
        except Exception as e:
            return ToolResult.ok({
                "valid": False,
                "error": str(e),
            })

