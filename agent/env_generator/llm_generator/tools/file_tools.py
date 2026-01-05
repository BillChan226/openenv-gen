"""
File Tools - File viewing and editing

Uses the Runtime system for file operations.
Inspired by OpenHands str_replace_editor.
"""

import os
from pathlib import Path
from typing import Optional, Union

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tool import BaseTool, ToolResult, create_tool_param, ToolCategory
from workspace import Workspace


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
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None):
        super().__init__()
        self._category = ToolCategory.FILE
        # Support both old (output_dir) and new (workspace) API
        if workspace:
            self.workspace = workspace
        elif output_dir:
            self.workspace = Workspace(output_dir)
        else:
            self.workspace = Workspace(Path.cwd())
    
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
    
    def _find_similar_paths(self, path: str) -> list:
        """Find similar paths in workspace to help with typos."""
        from pathlib import Path as P
        filename = P(path).name
        parent = P(path).parent
        suggestions = []
        
        # Search for files with similar names
        try:
            search_dir = self.workspace.root
            if parent and str(parent) != ".":
                try:
                    search_dir = self.workspace.resolve(str(parent))
                except:
                    pass
            
            if search_dir.exists():
                # Look for similar files
                for f in search_dir.rglob("*"):
                    if f.is_file() and filename.lower() in f.name.lower():
                        rel = str(f.relative_to(self.workspace.root))
                        suggestions.append(rel)
                        if len(suggestions) >= 5:
                            break
        except:
            pass
        
        return suggestions
    
    def execute(self, path: str, view_range: list = None) -> ToolResult:
        try:
            file_path = self.workspace.resolve(path)
        except Exception as e:
            return ToolResult(success=False, error_message=f"Invalid path: {e}")
        
        if not file_path.exists():
            # Try to find similar files to help the user
            suggestions = self._find_similar_paths(path)
            msg = f"Path not found: {path}"
            if suggestions:
                msg += f". Did you mean: {', '.join(suggestions[:3])}?"
            return ToolResult(success=False, error_message=msg)
        
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
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        if workspace:
            self.workspace = workspace
        elif output_dir:
            self.workspace = Workspace(output_dir)
        else:
            self.workspace = Workspace(Path.cwd())
    
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
    
    def _rel_path(self, abs_path: Path) -> str:
        """Convert absolute path to relative for display in error messages."""
        try:
            return str(abs_path.relative_to(self.workspace.root))
        except ValueError:
            return str(abs_path.name)  # Fallback to just filename
    
    def execute(
        self,
        command: str,
        path: str,
        file_text: str = None,
        old_str: str = None,
        new_str: str = None,
        insert_line: int = None,
    ) -> ToolResult:
        try:
            file_path = self.workspace.resolve(path)
        except Exception as e:
            return ToolResult(success=False, error_message=f"Invalid path: {path}")
        
        if command == "create":
            return self._create(file_path, file_text or "", path)
        elif command == "str_replace":
            return self._str_replace(file_path, old_str or "", new_str or "", path)
        elif command == "insert":
            return self._insert(file_path, insert_line or 0, new_str or "", path)
        elif command == "undo_edit":
            return self._undo(file_path, path)
        else:
            return ToolResult(success=False, error_message=f"Unknown command: {command}")
    
    def _create(self, path: Path, content: str, orig_path: str = "") -> ToolResult:
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
            display_path = orig_path or self._rel_path(path)
            return ToolResult(
                success=True,
                data={"action": "create", "path": display_path, "lines": lines, "info": f"File created: {display_path} ({lines} lines)"}
            )
        except Exception as e:
            return ToolResult(success=False, error_message=f"Create failed: {e}")
    
    def _str_replace(self, path: Path, old_str: str, new_str: str, orig_path: str = "") -> ToolResult:
        if not path.exists():
            return ToolResult(success=False, error_message=f"File not found: {orig_path or self._rel_path(path)}")
        
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
            display_path = orig_path or self._rel_path(path)
            return ToolResult(
                success=True,
                data={"action": "str_replace", "path": display_path, "line": line_num, "info": f"Replacement done at line {line_num}"}
            )
        except Exception as e:
            return ToolResult(success=False, error_message=f"Write failed: {e}")
    
    def _insert(self, path: Path, line_num: int, new_str: str, orig_path: str = "") -> ToolResult:
        if not path.exists():
            return ToolResult(success=False, error_message=f"File not found: {orig_path or self._rel_path(path)}")
        
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
            display_path = orig_path or self._rel_path(path)
            return ToolResult(
                success=True,
                data={"action": "insert", "path": display_path, "lines_added": len(new_lines), "info": f"Inserted {len(new_lines)} lines after line {line_num}"}
            )
        except Exception as e:
            return ToolResult(success=False, error_message=f"Write failed: {e}")
    
    def _undo(self, path: Path, orig_path: str = "") -> ToolResult:
        prev = _file_history.get_previous(str(path))
        
        if prev is None:
            return ToolResult(success=False, error_message="No undo history for this file")
        
        try:
            path.write_text(prev, encoding='utf-8')
            display_path = orig_path or self._rel_path(path)
            return ToolResult(
                success=True,
                data={"action": "undo", "path": display_path, "info": f"Reverted: {display_path}"}
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
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        if workspace:
            self.workspace = workspace
        elif output_dir:
            self.workspace = Workspace(output_dir)
        else:
            self.workspace = Workspace(Path.cwd())
    
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
        try:
            file_path = self.workspace.resolve(path)
        except Exception as e:
            return ToolResult(success=False, error_message=f"Invalid path: {e}")
        
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
            is_new = not file_path.exists()
            if not is_new:
                _file_history.save(str(file_path), file_path.read_text(encoding='utf-8'))
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            
            lines = content.count('\n') + 1
            action = "Created" if is_new else "Overwrote"
            return ToolResult(
                success=True,
                data={"path": path, "lines": lines, "is_new": is_new, "message": f"{action} {path} ({lines} lines)"},
            )
        except Exception as e:
            return ToolResult(success=False, error_message=f"Write failed: {e}")


# ===== Delete File Tool =====

class DeleteFileTool(BaseTool):
    """Delete a file from the workspace."""
    
    NAME = "delete_file"
    
    DESCRIPTION = """Delete a file from the workspace.

Examples:
    delete_file "temp.txt"              # Delete temp.txt
    delete_file "src/old_module.py"     # Delete a specific file
    delete_file "build/output.js"       # Delete build artifact

Note: This only deletes files, not directories. Use with caution.
"""
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        if workspace:
            self.workspace = workspace
        elif output_dir:
            self.workspace = Workspace(output_dir)
        else:
            self.workspace = Workspace(Path.cwd())
    
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
                        "description": "Path to the file to delete (relative to workspace)"
                    }
                },
                "required": ["path"]
            }
        )
    
    def execute(self, path: str) -> ToolResult:
        try:
            file_path = self.workspace.resolve(path)
        except Exception as e:
            return ToolResult(success=False, error_message=f"Invalid path: {e}")
        
        if not file_path.exists():
            return ToolResult(success=False, error_message=f"File not found: {path}")
        
        if file_path.is_dir():
            return ToolResult(
                success=False, 
                error_message=f"Cannot delete directory: {path}. Use execute_bash with 'rm -r' for directories."
            )
        
        try:
            file_path.unlink()
            return ToolResult(
                success=True,
                data={
                    "deleted": str(path),
                    "message": f"Successfully deleted: {path}"
                }
            )
        except PermissionError:
            return ToolResult(success=False, error_message=f"Permission denied: {path}")
        except Exception as e:
            return ToolResult(success=False, error_message=f"Delete failed: {e}")


# ===== View Image Tool =====

import base64

def _encode_image_to_base64(image_path: Path) -> Optional[str]:
    """Encode image file to base64 string"""
    if not image_path.exists():
        return None
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None

def _get_image_mime_type(image_path: Path) -> str:
    """Get MIME type from file extension"""
    ext = image_path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    return mime_map.get(ext, "image/png")


class ViewImageTool(BaseTool):
    """View/load an image file for design reference.
    
    This tool loads images (screenshots, mockups, design references) and makes them
    available for the LLM to analyze. The image is returned as base64 for multimodal
    LLM processing.
    """
    
    NAME = "view_image"
    
    DESCRIPTION = """Load an image file (screenshot, mockup, design reference) for analysis.

Use this tool to:
- Load a reference screenshot to recreate a design
- View a mockup image to understand the expected UI
- Compare with generated screenshots

Supported formats: PNG, JPG, JPEG, GIF, WebP, SVG

Examples:
    view_image "design/mockup.png"              # Load a design mockup
    view_image "screenshots/reference.jpg"      # Load a reference screenshot
    view_image "ui-spec/dashboard.png"          # Load UI specification image

By default, this tool returns ONLY metadata (path, size, mime) to avoid exploding LLM context.
If you truly need the raw base64 payload, pass include_base64=true (WARNING: huge).
"""
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        if workspace:
            self.workspace = workspace
        elif output_dir:
            self.workspace = Workspace(output_dir)
        else:
            self.workspace = Workspace(Path.cwd())
    
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
                        "description": "Path to the image file (relative to workspace or absolute)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of what to look for in the image"
                    },
                    "include_base64": {
                        "type": "boolean",
                        "description": "Include base64 payload in tool output (WARNING: very large). Default: false."
                    }
                },
                "required": ["path"]
            }
        )
    
    def execute(self, path: str, description: str = None, include_base64: bool = False) -> ToolResult:
        # Try workspace path first, then absolute path
        try:
            image_path = self.workspace.resolve(path)
        except Exception:
            image_path = Path(path)
        
        if not image_path.exists():
            # Try common reference directories
            for prefix in ["design", "mockups", "screenshots", "references", "images"]:
                alt_path = self.workspace.root / prefix / path
                if alt_path.exists():
                    image_path = alt_path
                    break
        
        if not image_path.exists():
            return ToolResult(
                success=False,
                error_message=f"Image not found: {path}. Checked workspace and common directories."
            )
        
        # Check if it's a supported image format
        supported_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
        if image_path.suffix.lower() not in supported_exts:
            return ToolResult(
                success=False,
                error_message=f"Unsupported image format: {image_path.suffix}. Supported: {supported_exts}"
            )
        
        # Get file size
        file_size = image_path.stat().st_size
        if file_size > 20 * 1024 * 1024:  # 20MB limit
            return ToolResult(
                success=False,
                error_message=f"Image too large: {file_size / 1024 / 1024:.1f}MB. Maximum: 20MB"
            )
        
        mime_type = _get_image_mime_type(image_path)

        # Only include base64 if explicitly requested (to avoid blowing up LLM context)
        payload = {}
        if include_base64:
            image_base64 = _encode_image_to_base64(image_path)
            if not image_base64:
                return ToolResult(success=False, error_message=f"Failed to read image: {path}")
            payload["image_base64"] = image_base64
            payload["multimodal_content"] = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{image_base64}",
                    "detail": "high"
                }
            }

        return ToolResult(
            success=True,
            data={
                "path": str(path),
                "mime_type": mime_type,
                "size_bytes": file_size,
                "size_display": f"{file_size / 1024:.1f}KB" if file_size < 1024*1024 else f"{file_size / 1024 / 1024:.1f}MB",
                "description": description,
                "message": f"Image loaded: {path} ({mime_type}, {file_size / 1024:.1f}KB)",
                **payload
            }
        )


# ===== List Reference Images Tool =====

class ListReferenceImagesTool(BaseTool):
    """List available reference images from the screenshot library."""
    
    NAME = "list_reference_images"
    
    DESCRIPTION = """List available reference images from the screenshot library.

The screenshot library contains design references, UI mockups, and component examples
that can be used as reference for generating web pages.

Examples:
    list_reference_images                        # List all projects
    list_reference_images "atlassian_home"       # List images for atlassian_home project

Use copy_reference_image to copy images to your workspace for use.
"""
    
    # Default screenshot library path (relative to llm_generator)
    SCREENSHOT_LIB_PATH = Path(__file__).parent.parent / "screenshot"
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None, screenshot_lib: Path = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        if workspace:
            self.workspace = workspace
        elif output_dir:
            self.workspace = Workspace(output_dir)
        else:
            self.workspace = Workspace(Path.cwd())
        self.screenshot_lib = screenshot_lib or self.SCREENSHOT_LIB_PATH
    
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
                    "project": {
                        "type": "string",
                        "description": "Project name to list images for (optional, lists all projects if not provided)"
                    }
                },
                "required": []
            }
        )
    
    def execute(self, project: str = None) -> ToolResult:
        if not self.screenshot_lib.exists():
            return ToolResult(
                success=False,
                error_message=f"Screenshot library not found: {self.screenshot_lib}"
            )
        
        result = {"projects": {}}
        
        if project:
            # List images for specific project
            project_path = self.screenshot_lib / project
            if not project_path.exists():
                return ToolResult(
                    success=False,
                    error_message=f"Project not found: {project}. Available: {[d.name for d in self.screenshot_lib.iterdir() if d.is_dir()]}"
                )
            
            images = self._list_images(project_path)
            result["projects"][project] = images
            result["total_images"] = len(images)
        else:
            # List all projects and their images
            total = 0
            for proj_dir in sorted(self.screenshot_lib.iterdir()):
                if proj_dir.is_dir() and not proj_dir.name.startswith('.'):
                    images = self._list_images(proj_dir)
                    result["projects"][proj_dir.name] = images
                    total += len(images)
            result["total_images"] = total
        
        return ToolResult(
            success=True,
            data=result
        )
    
    def _list_images(self, path: Path) -> list:
        """List all images in a directory"""
        supported_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
        images = []
        
        for f in sorted(path.iterdir()):
            if f.is_file() and f.suffix.lower() in supported_exts:
                size = f.stat().st_size
                images.append({
                    "name": f.name,
                    "size": f"{size / 1024:.1f}KB" if size < 1024*1024 else f"{size / 1024 / 1024:.1f}MB",
                    "type": f.suffix.lower()[1:]
                })
        
        return images


# ===== Copy Reference Image Tool =====

class CopyReferenceImageTool(BaseTool):
    """Copy reference images from the screenshot library to workspace."""
    
    NAME = "copy_reference_image"
    
    DESCRIPTION = """Copy a reference image from the screenshot library to your workspace.

This allows you to use existing design references for your project.
Images are copied to workspace/screenshots/ by default.

Examples:
    copy_reference_image "atlassian_home/atlassian_home.png"
    copy_reference_image "atlassian_home/jira_example.png" "design/reference.png"
    copy_reference_image "atlassian_home/user_bar.png" "components/navbar-ref.png"

Use list_reference_images to see available images first.
"""
    
    SCREENSHOT_LIB_PATH = Path(__file__).parent.parent / "screenshot"
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None, screenshot_lib: Path = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        if workspace:
            self.workspace = workspace
        elif output_dir:
            self.workspace = Workspace(output_dir)
        else:
            self.workspace = Workspace(Path.cwd())
        self.screenshot_lib = screenshot_lib or self.SCREENSHOT_LIB_PATH
    
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
                    "source": {
                        "type": "string",
                        "description": "Source image path (e.g., 'atlassian_home/mockup.png')"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination path in workspace (default: screenshots/<source_name>)"
                    }
                },
                "required": ["source"]
            }
        )
    
    def execute(self, source: str, destination: str = None) -> ToolResult:
        import shutil
        
        # Resolve source path
        source_path = self.screenshot_lib / source
        if not source_path.exists():
            return ToolResult(
                success=False,
                error_message=f"Source image not found: {source}. Use list_reference_images to see available images."
            )
        
        # Determine destination
        if destination:
            dest_path = self.workspace.resolve(destination)
        else:
            # Default to screenshots directory
            dest_path = self.workspace.root / "screenshots" / source_path.name
        
        # Create parent directory if needed
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            shutil.copy2(source_path, dest_path)
            
            return ToolResult(
                success=True,
                data={
                    "source": source,
                    "destination": str(dest_path.relative_to(self.workspace.root)),
                    "size": f"{dest_path.stat().st_size / 1024:.1f}KB",
                    "message": f"Copied {source} to {dest_path.relative_to(self.workspace.root)}"
                }
            )
        except Exception as e:
            return ToolResult(success=False, error_message=f"Copy failed: {e}")


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
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        if workspace:
            self.workspace = workspace
        elif output_dir:
            self.workspace = Workspace(output_dir)
        else:
            self.workspace = Workspace(Path.cwd())
    
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
        try:
            search_path = self.workspace.resolve(path or "")
        except Exception as e:
            return ToolResult(success=False, error_message=f"Invalid path: {e}")
        
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
                    data={"matches": [], "info": f"No files matching '{pattern}' in {path or '.'}"}
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
