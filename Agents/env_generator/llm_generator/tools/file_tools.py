"""
File Operation Tools

These tools give the agent the ability to interact with the filesystem,
similar to how a human developer would.
"""

import os
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils.tool import BaseTool, ToolDefinition, ToolParameter, ToolResult, ToolCategory


class ReadFileTool(BaseTool):
    """
    Read file contents.
    
    Similar to how I use read_file to understand code before modifying it.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_file",
            description="Read the contents of a file. Use this to understand existing code before making changes.",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="Path to the file to read (relative to project root)",
                    required=True,
                ),
                ToolParameter(
                    name="start_line",
                    param_type=int,
                    description="Start line number (1-indexed, optional)",
                    required=False,
                    default=None,
                ),
                ToolParameter(
                    name="end_line", 
                    param_type=int,
                    description="End line number (1-indexed, optional)",
                    required=False,
                    default=None,
                ),
            ],
            returns="File contents as string, with line numbers",
            examples=[
                {"input": {"path": "src/main.py"}, "output": "1|import os\n2|..."},
            ],
            tags=["file", "read"],
        )
    
    async def execute(
        self, 
        path: str, 
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        **kwargs
    ) -> ToolResult:
        try:
            file_path = self.base_dir / path
            
            if not file_path.exists():
                return ToolResult.fail(f"File not found: {path}")
            
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            
            # Apply line range if specified
            if start_line is not None:
                start_idx = max(0, start_line - 1)
                end_idx = end_line if end_line else len(lines)
                lines = lines[start_idx:end_idx]
                line_offset = start_idx
            else:
                line_offset = 0
            
            # Add line numbers
            numbered_lines = [
                f"{i + line_offset + 1:4}|{line}" 
                for i, line in enumerate(lines)
            ]
            
            return ToolResult.ok("\n".join(numbered_lines))
            
        except Exception as e:
            return ToolResult.fail(f"Error reading file: {e}")


class WriteFileTool(BaseTool):
    """
    Write content to a file.
    
    Used for creating new files or completely rewriting existing ones.
    For partial modifications, use SearchReplaceTool instead.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write_file",
            description="Write content to a file. Creates parent directories if needed. Use for new files or complete rewrites.",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="Path to write to (relative to project root)",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    param_type=str,
                    description="Content to write",
                    required=True,
                ),
            ],
            returns="Success message with file path",
            tags=["file", "write", "create"],
        )
    
    async def execute(self, path: str, content: str, **kwargs) -> ToolResult:
        try:
            file_path = self.base_dir / path
            
            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            file_path.write_text(content, encoding="utf-8")
            
            return ToolResult.ok(f"Written {len(content)} bytes to {path}")
            
        except Exception as e:
            return ToolResult.fail(f"Error writing file: {e}")


class ListDirTool(BaseTool):
    """
    List directory contents.
    
    Helps agent understand project structure before generating code.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_dir",
            description="List files and directories in a path. Use to understand project structure.",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="Directory path (relative to project root, default: '.')",
                    required=False,
                    default=".",
                ),
                ToolParameter(
                    name="recursive",
                    param_type=bool,
                    description="List recursively",
                    required=False,
                    default=False,
                ),
            ],
            returns="List of files and directories",
            tags=["file", "list", "directory"],
        )
    
    async def execute(
        self, 
        path: str = ".",
        recursive: bool = False,
        **kwargs
    ) -> ToolResult:
        try:
            dir_path = self.base_dir / path
            
            if not dir_path.exists():
                return ToolResult.fail(f"Directory not found: {path}")
            
            if not dir_path.is_dir():
                return ToolResult.fail(f"Not a directory: {path}")
            
            items = []
            
            if recursive:
                for item in sorted(dir_path.rglob("*")):
                    rel_path = item.relative_to(dir_path)
                    # Skip node_modules, __pycache__, etc.
                    if any(p in str(rel_path) for p in ["node_modules", "__pycache__", ".git"]):
                        continue
                    prefix = "[DIR] " if item.is_dir() else "[FILE]"
                    items.append(f"{prefix} {rel_path}")
            else:
                for item in sorted(dir_path.iterdir()):
                    prefix = "[DIR] " if item.is_dir() else "[FILE]"
                    items.append(f"{prefix} {item.name}")
            
            return ToolResult.ok("\n".join(items) if items else "(empty directory)")
            
        except Exception as e:
            return ToolResult.fail(f"Error listing directory: {e}")


class FileExistsTool(BaseTool):
    """
    Check if a file exists.
    
    Quick check before reading or to verify generation.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_exists",
            description="Check if a file or directory exists",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="Path to check",
                    required=True,
                ),
            ],
            returns="Boolean indicating existence",
            tags=["file", "check"],
        )
    
    async def execute(self, path: str, **kwargs) -> ToolResult:
        file_path = self.base_dir / path
        exists = file_path.exists()
        is_dir = file_path.is_dir() if exists else False
        
        return ToolResult.ok({
            "exists": exists,
            "is_directory": is_dir,
            "path": str(file_path),
        })

