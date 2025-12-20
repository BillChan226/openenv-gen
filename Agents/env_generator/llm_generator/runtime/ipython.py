"""
IPythonSession - Python code execution environment

Provides IPython-like execution with persistent state.
"""

import os
import sys
import io
import traceback
import asyncio
from pathlib import Path
from typing import Optional, Any, Dict, Union
from dataclasses import dataclass
import logging
from contextlib import redirect_stdout, redirect_stderr

sys.path.insert(0, str(Path(__file__).parent.parent))

from events.action import IPythonRunCellAction
from events.observation import IPythonOutputObservation, ErrorObservation

logger = logging.getLogger(__name__)


@dataclass
class CellResult:
    """Result of cell execution."""
    output: str
    error: bool = False
    error_type: str = ""
    result: Any = None


class IPythonSession:
    """
    IPython-like Python execution environment.
    
    Features:
    - Persistent namespace (variables persist between cells)
    - Stdout/stderr capture
    - Exception handling with traceback
    - Magic commands support (%pip, %cd, etc.)
    - Import agent skills automatically
    """
    
    MAX_OUTPUT_SIZE = 50000
    
    def __init__(self, work_dir: str = None):
        self.work_dir = Path(work_dir) if work_dir else Path.cwd()
        self._cwd = str(self.work_dir.absolute())
        
        # Persistent namespace for code execution
        self._namespace: Dict[str, Any] = {
            "__name__": "__main__",
            "__doc__": None,
            "__builtins__": __builtins__,
        }
        
        self._cell_count = 0
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize the IPython session."""
        if self._initialized:
            return
        
        # DON'T change global CWD - it affects the entire process!
        # Instead, set WORK_DIR in namespace and use it in code
        self._namespace['WORK_DIR'] = self._cwd
        self._namespace['os'] = os
        
        # Add common imports to namespace
        self._exec_silent("""
import os
import sys
import json
import time
import asyncio
from pathlib import Path
""")
        
        # Try to import httpx for HTTP requests
        self._exec_silent("""
try:
    import httpx
except ImportError:
    pass
""")
        
        self._initialized = True
        logger.info(f"IPythonSession initialized in {self._cwd}")
    
    def _exec_silent(self, code: str) -> None:
        """Execute code silently (no output capture)."""
        try:
            exec(compile(code, "<init>", "exec"), self._namespace)
        except Exception as e:
            logger.warning(f"Silent exec failed: {e}")
    
    @property
    def cwd(self) -> str:
        return self._cwd
    
    async def execute(self, action: IPythonRunCellAction) -> Union[IPythonOutputObservation, ErrorObservation]:
        """
        Execute Python code.
        
        Args:
            action: IPythonRunCellAction with code to execute
            
        Returns:
            IPythonOutputObservation or ErrorObservation
        """
        if not self._initialized:
            self.initialize()
        
        code = action.code.strip()
        
        if not code:
            return ErrorObservation(
                content="Empty code",
                cause=action.id,
            )
        
        self._cell_count += 1
        
        # Handle magic commands
        if code.startswith("%"):
            return await self._handle_magic(code, action)
        
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        result = None
        error = False
        error_type = ""
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Try to evaluate as expression first (for return value)
                try:
                    result = eval(compile(code, f"<cell-{self._cell_count}>", "eval"), self._namespace)
                except SyntaxError:
                    # Execute as statements
                    exec(compile(code, f"<cell-{self._cell_count}>", "exec"), self._namespace)
                    result = None
                    
        except Exception as e:
            error = True
            error_type = type(e).__name__
            # Get full traceback
            tb = traceback.format_exc()
            stderr_capture.write(tb)
        
        # Build output
        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()
        
        output_parts = []
        
        if stdout_output:
            output_parts.append(stdout_output.rstrip())
        
        if stderr_output:
            output_parts.append(stderr_output.rstrip())
        
        if result is not None and not error:
            # Format result
            try:
                result_str = repr(result)
                if len(result_str) > 1000:
                    result_str = result_str[:1000] + "..."
                output_parts.append(f"Out[{self._cell_count}]: {result_str}")
            except Exception:
                pass
        
        output = "\n".join(output_parts)
        
        # Add context info
        output += f"\n[Jupyter current working directory: {self._cwd}]"
        output += f"\n[Jupyter Python interpreter: {sys.executable}]"
        
        # Truncate if needed
        if len(output) > self.MAX_OUTPUT_SIZE:
            output = output[:self.MAX_OUTPUT_SIZE] + "\n...[output truncated]..."
        
        return IPythonOutputObservation(
            content=output,
            code=code,
            error=error,
            error_type=error_type,
            cause=action.id,
            tool_call_id=action.tool_call_id,
        )
    
    async def _handle_magic(self, code: str, action: IPythonRunCellAction) -> IPythonOutputObservation:
        """Handle magic commands."""
        lines = code.split("\n")
        first_line = lines[0].strip()
        
        # %pip install
        if first_line.startswith("%pip"):
            pip_cmd = first_line[4:].strip()
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, "-m", "pip"] + pip_cmd.split(),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                output = result.stdout + result.stderr
                return IPythonOutputObservation(
                    content=output,
                    code=code,
                    error=result.returncode != 0,
                    cause=action.id,
                )
            except Exception as e:
                return IPythonOutputObservation(
                    content=f"pip error: {e}",
                    code=code,
                    error=True,
                    error_type="PipError",
                    cause=action.id,
                )
        
        # %cd
        elif first_line.startswith("%cd"):
            new_dir = first_line[3:].strip()
            try:
                target = Path(new_dir).expanduser()
                if not target.is_absolute():
                    target = Path(self._cwd) / target
                
                if target.is_dir():
                    # DON'T change global CWD! Just update internal tracking
                    self._cwd = str(target.absolute())
                    self._namespace['WORK_DIR'] = self._cwd
                    return IPythonOutputObservation(
                        content=f"Changed to {self._cwd}",
                        code=code,
                        cause=action.id,
                    )
                else:
                    return IPythonOutputObservation(
                        content=f"Directory not found: {new_dir}",
                        code=code,
                        error=True,
                        cause=action.id,
                    )
            except Exception as e:
                return IPythonOutputObservation(
                    content=f"cd error: {e}",
                    code=code,
                    error=True,
                    cause=action.id,
                )
        
        # %pwd
        elif first_line.startswith("%pwd"):
            return IPythonOutputObservation(
                content=self._cwd,
                code=code,
                cause=action.id,
            )
        
        # %env
        elif first_line.startswith("%env"):
            rest = first_line[4:].strip()
            if "=" in rest:
                # Set env var
                key, value = rest.split("=", 1)
                os.environ[key.strip()] = value.strip()
                return IPythonOutputObservation(
                    content=f"Set {key}={value}",
                    code=code,
                    cause=action.id,
                )
            elif rest:
                # Get env var
                value = os.environ.get(rest, "")
                return IPythonOutputObservation(
                    content=f"{rest}={value}",
                    code=code,
                    cause=action.id,
                )
            else:
                # List all
                env_str = "\n".join(f"{k}={v}" for k, v in sorted(os.environ.items()))
                return IPythonOutputObservation(
                    content=env_str,
                    code=code,
                    cause=action.id,
                )
        
        # Unknown magic
        else:
            return IPythonOutputObservation(
                content=f"Unknown magic command: {first_line}",
                code=code,
                error=True,
                error_type="MagicError",
                cause=action.id,
            )
    
    def add_to_namespace(self, name: str, value: Any) -> None:
        """Add a value to the session namespace."""
        self._namespace[name] = value
    
    def get_from_namespace(self, name: str) -> Any:
        """Get a value from the session namespace."""
        return self._namespace.get(name)
    
    def reset_namespace(self) -> None:
        """Reset the namespace to initial state."""
        self._namespace = {
            "__name__": "__main__",
            "__doc__": None,
            "__builtins__": __builtins__,
        }
        self._cell_count = 0
        self.initialize()
    
    def close(self) -> None:
        """Close the session."""
        self._namespace.clear()
        self._initialized = False
        logger.info("IPythonSession closed")


# Convenience function for simple execution
async def run_python(code: str, cwd: str = None) -> CellResult:
    """
    Simple helper to run Python code.
    
    Args:
        code: Python code to execute
        cwd: Working directory
        
    Returns:
        CellResult with output
    """
    session = IPythonSession(work_dir=cwd)
    try:
        action = IPythonRunCellAction(code=code)
        result = await session.execute(action)
        
        return CellResult(
            output=result.content,
            error=result.error,
            error_type=result.error_type,
        )
    finally:
        session.close()

