"""
RuntimeManager - Coordinates all runtime sessions

Provides unified interface for action execution.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from ._events import (
    Action, ActionType, CmdRunAction, IPythonRunCellAction,
    FileReadAction, FileEditAction, ThinkAction, FinishAction,
    Observation, CmdOutputObservation, IPythonOutputObservation,
    FileReadObservation, FileEditObservation, ErrorObservation,
    AgentMessageObservation,
)
from .bash import BashSession
from .ipython import IPythonSession

logger = logging.getLogger(__name__)


class RuntimeManager:
    """
    Manages runtime sessions and action execution.
    
    Coordinates:
    - BashSession for shell commands
    - IPythonSession for Python code
    - File operations
    """
    
    def __init__(self, work_dir: str = None, config: dict = None):
        self.work_dir = Path(work_dir) if work_dir else Path.cwd()
        self.config = config or {}
        
        # Sessions
        self._bash: Optional[BashSession] = None
        self._ipython: Optional[IPythonSession] = None
        
        # File history for undo
        self._file_history: Dict[str, list] = {}
        
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize runtime sessions."""
        if self._initialized:
            return
        
        self._bash = BashSession(work_dir=str(self.work_dir))
        self._ipython = IPythonSession(work_dir=str(self.work_dir))
        
        self._bash.initialize()
        self._ipython.initialize()
        
        # Make skills available in IPython
        self._setup_skills()
        
        self._initialized = True
        logger.info(f"RuntimeManager initialized in {self.work_dir}")
    
    def _setup_skills(self) -> None:
        """Set up agent skills in IPython namespace."""
        if not self._ipython:
            return
        
        # Import skills
        try:
            from ..skills import (
                # File operations
                open_file, goto_line, scroll_down, scroll_up,
                create_file, edit_file_by_replace, insert_content_at_line, append_file,
                # Search operations
                search_dir, search_file, find_file, grep,
            )
            
            # File viewing
            self._ipython.add_to_namespace("open_file", open_file)
            self._ipython.add_to_namespace("goto_line", goto_line)
            self._ipython.add_to_namespace("scroll_down", scroll_down)
            self._ipython.add_to_namespace("scroll_up", scroll_up)
            
            # File editing
            self._ipython.add_to_namespace("create_file", create_file)
            self._ipython.add_to_namespace("edit_file_by_replace", edit_file_by_replace)
            self._ipython.add_to_namespace("insert_content_at_line", insert_content_at_line)
            self._ipython.add_to_namespace("append_file", append_file)
            
            # Searching
            self._ipython.add_to_namespace("search_dir", search_dir)
            self._ipython.add_to_namespace("search_file", search_file)
            self._ipython.add_to_namespace("find_file", find_file)
            self._ipython.add_to_namespace("grep", grep)
            
            # Add work_dir as a convenience variable
            self._ipython.add_to_namespace("WORK_DIR", str(self.work_dir))
            
            logger.info("Agent skills loaded into IPython namespace (12 functions)")
        except ImportError as e:
            logger.warning(f"Failed to load skills: {e}")
    
    @property
    def cwd(self) -> str:
        """Get current working directory."""
        if self._bash:
            return self._bash.cwd
        return str(self.work_dir)
    
    async def execute(self, action: Action) -> Observation:
        """
        Execute an action and return observation.
        
        Args:
            action: Action to execute
            
        Returns:
            Observation result
        """
        if not self._initialized:
            self.initialize()
        
        try:
            if action.action_type == ActionType.CMD_RUN:
                return await self._execute_cmd(action)
            
            elif action.action_type == ActionType.IPYTHON_RUN:
                return await self._execute_ipython(action)
            
            elif action.action_type == ActionType.FILE_READ:
                return await self._execute_file_read(action)
            
            elif action.action_type == ActionType.FILE_EDIT:
                return await self._execute_file_edit(action)
            
            elif action.action_type == ActionType.THINK:
                return AgentMessageObservation(
                    content=f"Thought: {action.thought}",
                    cause=action.id,
                )
            
            elif action.action_type == ActionType.FINISH:
                return AgentMessageObservation(
                    content=f"Task completed: {action.final_message}",
                    cause=action.id,
                )
            
            else:
                return ErrorObservation(
                    content=f"Unsupported action type: {action.action_type}",
                    cause=action.id,
                )
                
        except Exception as e:
            logger.error(f"Action execution error: {e}", exc_info=True)
            return ErrorObservation(
                content=f"Execution error: {e}",
                error_type=type(e).__name__,
                cause=action.id,
            )
    
    async def _execute_cmd(self, action: CmdRunAction) -> Observation:
        """Execute bash command."""
        if not self._bash:
            return ErrorObservation(
                content="Bash session not initialized",
                cause=action.id,
            )
        return await self._bash.execute(action)
    
    async def _execute_ipython(self, action: IPythonRunCellAction) -> Observation:
        """Execute Python code."""
        if not self._ipython:
            return ErrorObservation(
                content="IPython session not initialized",
                cause=action.id,
            )
        return await self._ipython.execute(action)
    
    async def _execute_file_read(self, action: FileReadAction) -> Observation:
        """Read a file."""
        path = Path(action.path)
        if not path.is_absolute():
            path = self.work_dir / path
        
        if not path.exists():
            return ErrorObservation(
                content=f"File not found: {action.path}",
                cause=action.id,
            )
        
        if path.is_dir():
            return await self._list_directory(path, action)
        
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            total = len(lines)
            
            # Handle view_range
            start, end = 1, total
            if action.view_range:
                start = max(1, action.view_range[0])
                if len(action.view_range) > 1:
                    end = total if action.view_range[1] == -1 else min(action.view_range[1], total)
            
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
            
            return FileReadObservation(
                content="\n".join(output),
                path=str(path),
                cause=action.id,
                tool_call_id=action.tool_call_id,
            )
            
        except Exception as e:
            return ErrorObservation(
                content=f"Read error: {e}",
                cause=action.id,
            )
    
    async def _list_directory(self, path: Path, action: FileReadAction) -> Observation:
        """List directory contents."""
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
        return FileReadObservation(
            content="\n".join(output),
            path=str(path),
            cause=action.id,
        )
    
    async def _execute_file_edit(self, action: FileEditAction) -> Observation:
        """Edit a file."""
        path = Path(action.path)
        if not path.is_absolute():
            path = self.work_dir / path
        
        command = action.command
        
        if command == "view":
            read_action = FileReadAction(path=str(path))
            return await self._execute_file_read(read_action)
        
        elif command == "create":
            if path.exists():
                return ErrorObservation(
                    content=f"File exists: {path}. Use str_replace to edit.",
                    cause=action.id,
                )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(action.file_text, encoding='utf-8')
            return FileEditObservation(
                content=f"Created: {path}",
                path=str(path),
                success=True,
                cause=action.id,
            )
        
        elif command == "str_replace":
            if not path.exists():
                return ErrorObservation(
                    content=f"File not found: {path}",
                    cause=action.id,
                )
            
            content = path.read_text(encoding='utf-8')
            
            # Check uniqueness
            count = content.count(action.old_str)
            if count == 0:
                return ErrorObservation(
                    content="old_str not found in file",
                    cause=action.id,
                )
            if count > 1:
                return ErrorObservation(
                    content=f"old_str found {count} times. Must be unique.",
                    cause=action.id,
                )
            
            # Save for undo
            self._save_file_history(str(path), content)
            
            # Replace
            new_content = content.replace(action.old_str, action.new_str, 1)
            path.write_text(new_content, encoding='utf-8')
            
            line_num = content[:content.find(action.old_str)].count('\n') + 1
            return FileEditObservation(
                content=f"Replaced at line {line_num}",
                path=str(path),
                success=True,
                cause=action.id,
                tool_call_id=action.tool_call_id,
            )
        
        elif command == "insert":
            if not path.exists():
                return ErrorObservation(
                    content=f"File not found: {path}",
                    cause=action.id,
                )
            
            lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
            
            # Save for undo
            self._save_file_history(str(path), ''.join(lines))
            
            # Insert
            new_lines = [l + '\n' if not l.endswith('\n') else l for l in action.new_str.split('\n')]
            result = lines[:action.insert_line] + new_lines + lines[action.insert_line:]
            path.write_text(''.join(result), encoding='utf-8')
            
            return FileEditObservation(
                content=f"Inserted {len(new_lines)} lines after line {action.insert_line}",
                path=str(path),
                success=True,
                cause=action.id,
            )
        
        elif command == "undo_edit":
            prev = self._get_file_history(str(path))
            if prev is None:
                return ErrorObservation(
                    content="No undo history",
                    cause=action.id,
                )
            path.write_text(prev, encoding='utf-8')
            return FileEditObservation(
                content=f"Reverted: {path}",
                path=str(path),
                success=True,
                cause=action.id,
            )
        
        else:
            return ErrorObservation(
                content=f"Unknown command: {command}",
                cause=action.id,
            )
    
    def _save_file_history(self, path: str, content: str) -> None:
        """Save file state for undo."""
        if path not in self._file_history:
            self._file_history[path] = []
        self._file_history[path].append(content)
        if len(self._file_history[path]) > 10:
            self._file_history[path] = self._file_history[path][-10:]
    
    def _get_file_history(self, path: str) -> Optional[str]:
        """Get previous file state for undo."""
        if path in self._file_history and self._file_history[path]:
            return self._file_history[path].pop()
        return None
    
    def close(self) -> None:
        """Close all sessions."""
        if self._bash:
            self._bash.close()
        if self._ipython:
            self._ipython.close()
        self._initialized = False
        logger.info("RuntimeManager closed")
    
    def __del__(self):
        self.close()

