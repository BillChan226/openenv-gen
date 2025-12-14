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

