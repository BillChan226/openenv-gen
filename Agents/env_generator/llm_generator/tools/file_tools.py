"""
File Tools - File viewing and editing

Uses the Runtime system for file operations.
Inspired by OpenHands str_replace_editor.
"""

import os
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from utils.tool import BaseTool, ToolResult, create_tool_param, ToolCategory
from .path_utils import resolve_path


# ===== File History =====

class FileHistory:
    """Singleton for file undo history."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._history = {}
            cls._instance.max_history = 10
        return cls._instance
    
    def save(self, path: str, content: str):
        if path not in self._history:
            self._history[path] = []
        self._history[path].append(content)
        if len(self._history[path]) > self.max_history:
            self._history[path] = self._history[path][-self.max_history:]
    
    def get_previous(self, path: str) -> Optional[str]:
        if path in self._history and self._history[path]:
            return self._history[path].pop()
        return None
    
    def clear(self, path: str = None):
        if path:
            self._history.pop(path, None)
        else:
            self._history.clear()


_file_history = FileHistory()


# ===== View Tool =====

class ViewTool(BaseTool):
    """
    View file contents with line numbers, or list directory.
    
    Based on OpenHands str_replace_editor view command.
    """
    
    NAME = "view"
    
    DESCRIPTION = """View a file's content with line numbers.

* Shows line numbers for easy reference
* Specify view_range to see specific lines: [start, end]
* For directories, shows file listing
* Large files are automatically paginated

Examples:
    view /path/to/file.py                    # View entire file
    view /path/to/file.py [100, 200]         # View lines 100-200
    view /path/to/dir                        # List directory contents
"""
    
    def __init__(self, output_dir: str = None):
        super().__init__()
        self._category = ToolCategory.FILE
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
    
    @property
    def tool_definition(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File or directory path to view"
                    },
                    "view_range": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional [start_line, end_line]. Use -1 for end."
                    }
                },
                "required": ["path"]
            }
        )
    
    def get_tool_param(self):
        return self.tool_definition
    
    def execute(self, path: str, view_range: list = None) -> ToolResult:
        file_path = resolve_path(path, self.output_dir)
        
        if not file_path.exists():
            return ToolResult(success=False, error_message=f"Path not found: {path}")
        
        if file_path.is_dir():
            return self._list_directory(file_path)
        
        return self._view_file(file_path, view_range)
    
    def _view_file(self, path: Path, view_range: list = None) -> ToolResult:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except Exception as e:
            return ToolResult(success=False, error_message=f"Cannot read file: {e}")
        
        total = len(lines)
        
        # Parse range
        start, end = 1, total
        if view_range:
            start = max(1, view_range[0])
            if len(view_range) > 1:
                end = total if view_range[1] == -1 else min(view_range[1], total)
        
        # Build output
        output = [f"[File: {path} ({total} lines)]"]
        
        if start > 1:
            output.append(f"({start - 1} lines above)")
        else:
            output.append("(this is the beginning of the file)")
        
        for i in range(start - 1, min(end, total)):
            output.append(f"{i + 1:6}|{lines[i].rstrip()}")
        
        if end < total:
            output.append(f"({total - end} lines below)")
        else:
            output.append("(this is the end of the file)")
        
        return ToolResult(
            success=True,
            data={"total_lines": total, "showing": [start, min(end, total)], "content": "\n".join(output)}
        )
    
    def _list_directory(self, path: Path) -> ToolResult:
        output = [f"[Directory: {path}]"]
        
        def recurse(p: Path, prefix: str = "", depth: int = 0):
            if depth >= 2:
                return
            try:
                items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
                for item in items:
                    if item.name.startswith('.'):
                        continue
                    if item.is_dir():
                        output.append(f"{prefix}{item.name}/")
                        recurse(item, prefix + "  ", depth + 1)
                    else:
                        size = item.stat().st_size
                        output.append(f"{prefix}{item.name} ({size} bytes)")
            except PermissionError:
                output.append(f"{prefix}[Permission denied]")
        
        recurse(path)
        return ToolResult(success=True, data="\n".join(output))


# ===== StrReplaceEditor Tool =====

class StrReplaceEditorTool(BaseTool):
    """
    Powerful file editor with create, edit, insert, and undo.
    
    Direct port from OpenHands str_replace_editor.
    """
    
    NAME = "str_replace_editor"
    
    DESCRIPTION = """Create and edit files using string replacement.

Commands:
* create: Create a new file with content
* str_replace: Replace old_str with new_str (old_str must be unique)
* insert: Insert new_str after a specific line
* undo_edit: Revert to previous version

For str_replace:
- The old_str MUST match exactly (including whitespace)
- old_str MUST be unique in the file
- Include enough context to ensure uniqueness

Examples:
    str_replace_editor create /path/new.py "print('hello')"
    str_replace_editor str_replace /path/file.py "old code" "new code"
    str_replace_editor insert /path/file.py 10 "new line after line 10"
    str_replace_editor undo_edit /path/file.py
"""
    
    def __init__(self, output_dir: str = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
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
                    "command": {
                        "type": "string",
                        "enum": ["create", "str_replace", "insert", "undo_edit"],
                        "description": "Command to execute"
                    },
                    "path": {
                        "type": "string",
                        "description": "File path"
                    },
                    "file_text": {
                        "type": "string",
                        "description": "For create: content of new file"
                    },
                    "old_str": {
                        "type": "string",
                        "description": "For str_replace: exact text to find (must be unique)"
                    },
                    "new_str": {
                        "type": "string",
                        "description": "For str_replace/insert: replacement or new text"
                    },
                    "insert_line": {
                        "type": "integer",
                        "description": "For insert: line number to insert after (0 = start)"
                    }
                },
                "required": ["command", "path"]
            }
        )
    
    def execute(
        self,
        command: str,
        path: str,
        file_text: str = None,
        old_str: str = None,
        new_str: str = None,
        insert_line: int = None,
    ) -> ToolResult:
        
        file_path = resolve_path(path, self.output_dir)
        
        if command == "create":
            return self._create(file_path, file_text or "")
        elif command == "str_replace":
            return self._str_replace(file_path, old_str or "", new_str or "")
        elif command == "insert":
            return self._insert(file_path, insert_line or 0, new_str or "")
        elif command == "undo_edit":
            return self._undo(file_path)
        else:
            return ToolResult(success=False, error_message=f"Unknown command: {command}")
    
    def _create(self, path: Path, content: str) -> ToolResult:
        if path.exists():
            return ToolResult(
                success=False,
                error_message=f"File exists: {path}. Use str_replace to edit."
            )
        
        # Fix: Convert literal \n sequences to actual newlines
        if content and '\\n' in content and content.count('\\n') > content.count('\n'):
            content = content.replace('\\n', '\n')
            content = content.replace('\\t', '\t')
            content = content.replace('\\r', '\r')
        
        # Validate content is not empty or trivially corrupted
        if not content or len(content.strip()) < 2:
            return ToolResult(
                success=False,
                error_message=f"Content is empty or too short (len={len(content)}). Refusing to create corrupted file."
            )
        
        # Validate JSON files
        if path.suffix == '.json':
            import json
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                return ToolResult(
                    success=False,
                    error_message=f"Invalid JSON: {e}. Preview: {content[:200]}..."
                )
        
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            
            lines = content.count('\n') + 1
            return ToolResult(
                success=True,
                data={"action": "create", "path": str(path), "lines": lines, "info": f"File created: {path} ({lines} lines)"}
            )
        except Exception as e:
            return ToolResult(success=False, error_message=f"Create failed: {e}")
    
    def _str_replace(self, path: Path, old_str: str, new_str: str) -> ToolResult:
        if not path.exists():
            return ToolResult(success=False, error_message=f"File not found: {path}")
        
        if not old_str:
            return ToolResult(success=False, error_message="old_str cannot be empty")
        
        try:
            content = path.read_text(encoding='utf-8')
        except Exception as e:
            return ToolResult(success=False, error_message=f"Read failed: {e}")
        
        # Check uniqueness
        count = content.count(old_str)
        
        if count == 0:
            # Try to provide helpful error
            first_line = old_str.split('\n')[0][:50]
            for i, line in enumerate(content.split('\n'), 1):
                if first_line in line:
                    return ToolResult(
                        success=False,
                        error_message=(
                            f"old_str not found exactly. "
                            f"Partial match at line {i}. "
                            f"Check whitespace and indentation."
                        )
                    )
            return ToolResult(success=False, error_message="old_str not found in file")
        
        if count > 1:
            return ToolResult(
                success=False,
                error_message=f"old_str found {count} times. Must be unique. Add more context."
            )
        
        # Save for undo
        _file_history.save(str(path), content)
        
        # Replace
        new_content = content.replace(old_str, new_str, 1)
        
        try:
            path.write_text(new_content, encoding='utf-8')
            
            line_num = content[:content.find(old_str)].count('\n') + 1
            return ToolResult(
                success=True,
                data={"action": "str_replace", "path": str(path), "line": line_num, "info": f"Replacement done at line {line_num}"}
            )
        except Exception as e:
            return ToolResult(success=False, error_message=f"Write failed: {e}")
    
    def _insert(self, path: Path, line_num: int, new_str: str) -> ToolResult:
        if not path.exists():
            return ToolResult(success=False, error_message=f"File not found: {path}")
        
        try:
            content = path.read_text(encoding='utf-8')
            lines = content.splitlines(keepends=True)
        except Exception as e:
            return ToolResult(success=False, error_message=f"Read failed: {e}")
        
        if line_num < 0 or line_num > len(lines):
            return ToolResult(
                success=False,
                error_message=f"Invalid line {line_num} (file has {len(lines)} lines)"
            )
        
        # Save for undo
        _file_history.save(str(path), content)
        
        # Prepare new lines
        new_lines = [l + '\n' if not l.endswith('\n') else l 
                     for l in new_str.split('\n')]
        
        # Insert
        result = lines[:line_num] + new_lines + lines[line_num:]
        
        try:
            path.write_text(''.join(result), encoding='utf-8')
            return ToolResult(
                success=True,
                data={"action": "insert", "path": str(path), "lines_added": len(new_lines), "info": f"Inserted {len(new_lines)} lines after line {line_num}"}
            )
        except Exception as e:
            return ToolResult(success=False, error_message=f"Write failed: {e}")
    
    def _undo(self, path: Path) -> ToolResult:
        prev = _file_history.get_previous(str(path))
        
        if prev is None:
            return ToolResult(success=False, error_message="No undo history for this file")
        
        try:
            path.write_text(prev, encoding='utf-8')
            return ToolResult(
                success=True,
                data={"action": "undo", "path": str(path), "info": f"Reverted: {path}"}
            )
        except Exception as e:
            return ToolResult(success=False, error_message=f"Undo failed: {e}")


# ===== WriteFile Tool =====

class WriteFileTool(BaseTool):
    """Simple file write (creates or overwrites)."""
    
    NAME = "write_file"
    
    DESCRIPTION = """Write content to a file (creates or overwrites).

Use str_replace_editor for more precise editing.
This tool is for creating new files or complete rewrites.
"""
    
    def __init__(self, output_dir: str = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
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
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "File content"}
                },
                "required": ["path", "content"]
            }
        )
    
    def execute(self, path: str, content: str) -> ToolResult:
        file_path = resolve_path(path, self.output_dir)
        
        # Fix: Convert literal \n sequences to actual newlines
        # This handles the case where LLM sends escaped newlines instead of real ones
        if content and '\\n' in content and content.count('\\n') > content.count('\n'):
            # Content likely has literal \n that should be real newlines
            content = content.replace('\\n', '\n')
            # Also handle escaped tabs and other common escape sequences
            content = content.replace('\\t', '\t')
            content = content.replace('\\r', '\r')
        
        # Validate content is not empty or trivially corrupted
        if not content or len(content.strip()) < 2:
            return ToolResult(
                success=False,
                error_message=f"Content is empty or too short (len={len(content)}). Refusing to write potentially corrupted file."
            )
        
        # Validate JSON files
        if file_path.suffix == '.json':
            import json
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                return ToolResult(
                    success=False,
                    error_message=f"Invalid JSON content: {e}. Content preview: {content[:200]}..."
                )
        
        try:
            # Save for undo if exists
            if file_path.exists():
                _file_history.save(str(file_path), file_path.read_text(encoding='utf-8'))
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            
            lines = content.count('\n') + 1
            return ToolResult(
                success=True,
                data={"path": str(file_path), "lines": lines, "message": f"Wrote {lines} lines to {file_path}"},
            )
        except Exception as e:
            return ToolResult(success=False, error_message=f"Write failed: {e}")


# ===== Glob Tool =====

class GlobTool(BaseTool):
    """Find files by glob pattern."""
    
    NAME = "glob"
    
    DESCRIPTION = """Find files matching a glob pattern.

Examples:
    glob "*.py"                 # Python files in current dir
    glob "**/*.ts" /src         # TypeScript files recursively
    glob "test_*.py" /tests     # Test files in tests dir
"""
    
    def __init__(self, output_dir: str = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
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
                    "pattern": {"type": "string", "description": "Glob pattern"},
                    "path": {"type": "string", "description": "Directory to search (default: current)"}
                },
                "required": ["pattern"]
            }
        )
    
    def execute(self, pattern: str, path: str = None) -> ToolResult:
        search_path = resolve_path(path or "", self.output_dir)
        
        if not search_path.exists():
            return ToolResult(success=False, error_message=f"Path not found: {path}")
        
        try:
            matches = list(search_path.glob(pattern))
            
            # Sort and filter
            matches = sorted(m for m in matches if not any(
                p.startswith('.') for p in m.parts
            ))[:100]  # Limit results
            
            if not matches:
                return ToolResult(
                    success=True,
                    data={"matches": [], "info": f"No files matching '{pattern}' in {search_path}"}
                )
            
            rel_matches = []
            for m in matches:
                try:
                    rel_matches.append(str(m.relative_to(search_path)))
                except ValueError:
                    rel_matches.append(str(m))
            
            output = [f"Found {len(matches)} files:"] + rel_matches
            
            return ToolResult(
                success=True,
                data={"matches": rel_matches, "output": "\n".join(output)}
            )
        except Exception as e:
            return ToolResult(success=False, error_message=f"Glob failed: {e}")


# ===== Exports =====

__all__ = [
    "ViewTool",
    "StrReplaceEditorTool",
    "WriteFileTool",
    "GlobTool",
    "FileHistory",
]
