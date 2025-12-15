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
from typing import Dict, List, Any


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


class ListGeneratedFilesTool(BaseTool):
    """
    List all files that have been generated so far.
    
    This helps the agent know what's available to read/reference
    and what still needs to be generated.
    """
    
    def __init__(self, base_dir: Optional[Path] = None, gen_context: Any = None):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
        self.gen_context = gen_context  # Reference to GenerationContext
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_generated",
            description="List all files generated so far with their summaries. Use this to know what's available before trying to read files.",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="phase",
                    param_type=str,
                    description="Filter by phase (design/backend/frontend/openenv/docker). Leave empty for all.",
                    required=False,
                    default=None,
                ),
                ToolParameter(
                    name="include_summary",
                    param_type=bool,
                    description="Include file structure summaries (default: True)",
                    required=False,
                    default=True,
                ),
            ],
            returns="List of generated files with metadata",
            tags=["files", "list", "generated"],
        )
    
    async def execute(
        self,
        phase: Optional[str] = None,
        include_summary: bool = True,
        **kwargs
    ) -> ToolResult:
        try:
            generated_files = []
            
            # Get from GenerationContext if available
            if self.gen_context and hasattr(self.gen_context, 'files'):
                for path, info in self.gen_context.files.items():
                    file_phase = info.get('phase', 'unknown') if isinstance(info, dict) else 'unknown'
                    
                    if phase and file_phase != phase:
                        continue
                    
                    file_info = {
                        "path": path,
                        "phase": file_phase,
                        "exists": (self.base_dir / path).exists(),
                    }
                    
                    # Add line count if file exists
                    full_path = self.base_dir / path
                    if full_path.exists():
                        try:
                            content = full_path.read_text(encoding='utf-8')
                            file_info["lines"] = len(content.split('\n'))
                            file_info["chars"] = len(content)
                            
                            # Quick structure summary
                            if include_summary:
                                if path.endswith('.py'):
                                    classes = len([l for l in content.split('\n') if l.strip().startswith('class ')])
                                    functions = len([l for l in content.split('\n') if l.strip().startswith(('def ', 'async def '))])
                                    file_info["structure"] = f"{classes} classes, {functions} functions"
                                elif path.endswith(('.ts', '.tsx')):
                                    exports = len([l for l in content.split('\n') if 'export ' in l])
                                    file_info["structure"] = f"{exports} exports"
                                elif path.endswith('.json'):
                                    import json
                                    try:
                                        data = json.loads(content)
                                        if isinstance(data, dict):
                                            file_info["structure"] = f"keys: {list(data.keys())[:5]}"
                                    except:
                                        pass
                        except:
                            pass
                    
                    generated_files.append(file_info)
            
            # Fallback: scan directory
            if not generated_files:
                for file_path in self.base_dir.rglob('*'):
                    if file_path.is_file() and not any(x in str(file_path) for x in ['node_modules', '.checkpoint', '__pycache__']):
                        rel_path = str(file_path.relative_to(self.base_dir))
                        generated_files.append({
                            "path": rel_path,
                            "phase": "unknown",
                            "exists": True,
                            "lines": len(file_path.read_text(encoding='utf-8', errors='ignore').split('\n')),
                        })
            
            # Sort by phase order
            phase_order = {'design': 0, 'backend': 1, 'frontend': 2, 'openenv': 3, 'docker': 4, 'unknown': 5}
            generated_files.sort(key=lambda x: (phase_order.get(x.get('phase', 'unknown'), 5), x['path']))
            
            return ToolResult.ok({
                "total_files": len(generated_files),
                "files": generated_files,
                "by_phase": {
                    p: len([f for f in generated_files if f.get('phase') == p])
                    for p in set(f.get('phase', 'unknown') for f in generated_files)
                },
            })
            
        except Exception as e:
            return ToolResult.fail(f"Error listing generated files: {e}")


class UpdatePlanTool(BaseTool):
    """
    Update the generation plan mid-execution.
    
    Allows the agent to revise its plan based on what it learns
    during generation.
    """
    
    def __init__(self, gen_context: Any = None):
        super().__init__()
        self.gen_context = gen_context
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="update_plan",
            description="Update the generation plan. Use when you realize the plan needs changes based on what you've learned.",
            category=ToolCategory.CUSTOM,
            parameters=[
                ToolParameter(
                    name="action",
                    param_type=str,
                    description="Action: 'add_file', 'remove_file', 'reorder', 'update_spec'",
                    required=True,
                ),
                ToolParameter(
                    name="target",
                    param_type=str,
                    description="Target file path or spec to update",
                    required=True,
                ),
                ToolParameter(
                    name="details",
                    param_type=str,
                    description="Details of the update (new file purpose, reason for removal, etc.)",
                    required=False,
                    default="",
                ),
            ],
            returns="Confirmation of plan update",
            tags=["plan", "update", "revise"],
        )
    
    async def execute(
        self,
        action: str,
        target: str,
        details: str = "",
        **kwargs
    ) -> ToolResult:
        try:
            if not self.gen_context:
                return ToolResult.fail("No generation context available")
            
            if action == "add_file":
                # Add file to pending generation
                if hasattr(self.gen_context, 'pending_files'):
                    self.gen_context.pending_files.append({
                        "path": target,
                        "purpose": details,
                        "added_dynamically": True,
                    })
                return ToolResult.ok(f"Added '{target}' to pending files: {details}")
            
            elif action == "remove_file":
                # Mark file as not needed
                if hasattr(self.gen_context, 'skipped_files'):
                    self.gen_context.skipped_files.append(target)
                return ToolResult.ok(f"Marked '{target}' as skipped: {details}")
            
            elif action == "update_spec":
                # Update env_spec or other spec
                return ToolResult.ok(f"Plan update noted for '{target}': {details}. Use edit_function or search_replace to modify.")
            
            else:
                return ToolResult.fail(f"Unknown action: {action}. Use 'add_file', 'remove_file', or 'update_spec'")
            
        except Exception as e:
            return ToolResult.fail(f"Error updating plan: {e}")

