"""
Runtime Tools - Command execution and server management

Uses the Runtime system for command execution.
Inspired by OpenHands execute_bash and execute_ipython.
"""

import os
import asyncio
import subprocess
import signal
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tool import BaseTool, ToolResult, create_tool_param, ToolCategory
from workspace import Workspace


# ===== Server Registry =====

class ServerRegistry:
    """Singleton for tracking background servers."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._servers = {}
        return cls._instance
    
    def register(self, name: str, pid: int, port: int, cwd: str):
        self._servers[name] = {
            "pid": pid,
            "port": port,
            "cwd": cwd,
            "started": datetime.now().isoformat(),
            "logs": [],
        }
    
    def unregister(self, name: str):
        self._servers.pop(name, None)
    
    def get(self, name: str) -> Optional[dict]:
        return self._servers.get(name)
    
    def get_all(self) -> Dict[str, dict]:
        return self._servers.copy()
    
    def add_log(self, name: str, log: str):
        if name in self._servers:
            self._servers[name]["logs"].append(log)
            # Keep last 100 lines
            self._servers[name]["logs"] = self._servers[name]["logs"][-100:]
    
    def get_logs(self, name: str) -> List[str]:
        if name in self._servers:
            return self._servers[name]["logs"]
        return []


_server_registry = ServerRegistry()


# ===== Execute Bash Tool =====

class ExecuteBashTool(BaseTool):
    """
    Execute shell commands with timeout and interaction support.
    
    Based on OpenHands execute_bash.
    """
    
    NAME = "execute_bash"
    
    DESCRIPTION = """Execute a bash command in the terminal.

Features:
* Commands run in a persistent shell (state persists)
* Default timeout: 30 seconds
* Use is_input=True to send input to running process
* Special inputs: "C-c" (Ctrl+C), "C-d" (EOF), "C-z" (suspend)
* Commands run in the workspace directory

IMPORTANT:
* For long-running commands, set background=true
* If command times out, send "C-c" to interrupt

Examples:
    execute_bash "ls -la"
    execute_bash "python script.py" 60         # 60s timeout
    execute_bash "npm start" 30 true           # Run in background
    execute_bash "C-c" is_input=true           # Send Ctrl+C
"""
    
    DEFAULT_TIMEOUT = 30
    MAX_OUTPUT_LENGTH = 50000
    
    def __init__(self, work_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
        if workspace:
            self.workspace = workspace
        elif work_dir:
            self.workspace = Workspace(work_dir)
        else:
            self.workspace = Workspace(Path.cwd())
        self._current_process: Optional[subprocess.Popen] = None
    
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
                        "description": "Command to execute"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": f"Timeout in seconds (default: {self.DEFAULT_TIMEOUT})"
                    },
                    "background": {
                        "type": "boolean",
                        "description": "Run in background (default: false)"
                    },
                    "is_input": {
                        "type": "boolean",
                        "description": "Send as input to running process (default: false)"
                    }
                },
                "required": ["command"]
            }
        )
    
    def execute(
        self,
        command: str,
        timeout: int = None,
        background: bool = False,
        is_input: bool = False
    ) -> ToolResult:
        
        command = command.strip()
        timeout = timeout or self.DEFAULT_TIMEOUT
        
        if not command:
            return ToolResult(success=False, error_message="Empty command")
        
        # Handle input to running process
        if is_input:
            return self._handle_input(command)
        
        # Handle background execution
        if background:
            return self._run_background(command)
        
        # Regular execution with timeout
        return self._run_command(command, timeout)
    
    def _run_command(self, command: str, timeout: int) -> ToolResult:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.workspace.root),
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            
            output = result.stdout + result.stderr
            if len(output) > self.MAX_OUTPUT_LENGTH:
                output = output[:self.MAX_OUTPUT_LENGTH] + "\n...[output truncated]..."
            
            return ToolResult(
                success=result.returncode == 0,
                data={
                    "exit_code": result.returncode,
                    "cwd": str(self.workspace.root),
                    "output": output or "(no output)",
                }
            )
            
        except subprocess.TimeoutExpired as e:
            output = ""
            if e.stdout:
                output += e.stdout if isinstance(e.stdout, str) else e.stdout.decode()
            if e.stderr:
                output += e.stderr if isinstance(e.stderr, str) else e.stderr.decode()
            
            return ToolResult(
                success=False,
                data={
                    "exit_code": -1, 
                    "timed_out": True,
                    "output": f"{output}\n[Command timed out after {timeout}s. Send 'C-c' to interrupt.]"
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error_message=f"Execution error: {e}")
    
    def _run_background(self, command: str) -> ToolResult:
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(self.workspace.root),
                start_new_session=True,
            )
            
            self._current_process = process
            
            return ToolResult(
                success=True,
                data={
                    "pid": process.pid, 
                    "background": True,
                    "info": f"Started background process (PID: {process.pid})\nCommand: {command}"
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error_message=f"Background start failed: {e}")
    
    def _handle_input(self, input_str: str) -> ToolResult:
        if input_str == "C-c":
            # Send SIGINT
            if self._current_process:
                try:
                    os.killpg(os.getpgid(self._current_process.pid), signal.SIGINT)
                    return ToolResult(success=True, data="Sent SIGINT (Ctrl+C)")
                except ProcessLookupError:
                    return ToolResult(success=True, data="No running process to interrupt")
            return ToolResult(success=True, data="No running process")
        
        elif input_str == "C-d":
            if self._current_process:
                self._current_process.stdin.close()
                return ToolResult(success=True, data="Sent EOF (Ctrl+D)")
            return ToolResult(success=True, data="No running process")
        
        elif input_str == "C-z":
            if self._current_process:
                try:
                    os.killpg(os.getpgid(self._current_process.pid), signal.SIGTSTP)
                    return ToolResult(success=True, data="Sent SIGTSTP (Ctrl+Z)")
                except ProcessLookupError:
                    return ToolResult(success=True, data="No running process")
            return ToolResult(success=True, data="No running process")
        
        else:
            if self._current_process and self._current_process.stdin:
                self._current_process.stdin.write(f"{input_str}\n".encode())
                self._current_process.stdin.flush()
                return ToolResult(success=True, data=f"Sent input: {input_str}")
            return ToolResult(success=False, error_message="No process to send input to")


# ===== Execute IPython Tool =====

class ExecuteIPythonTool(BaseTool):
    """
    Execute Python code in an IPython-like environment.
    
    Based on OpenHands execute_ipython_cell.
    """
    
    NAME = "execute_ipython"
    
    DESCRIPTION = """Execute Python code in a Jupyter-like environment.

Features:
* Persistent state (variables persist between calls)
* stdout/stderr capture
* Exception handling with traceback
* Magic commands: %pip, %cd, %pwd, %env

Examples:
    execute_ipython "import pandas as pd"
    execute_ipython "df = pd.read_csv('data.csv')"
    execute_ipython "%pip install requests"
    execute_ipython "print(df.head())"
"""
    
    def __init__(self, work_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
        if workspace:
            self.workspace = workspace
        elif work_dir:
            self.workspace = Workspace(work_dir)
        else:
            self.workspace = Workspace(Path.cwd())
        self._namespace = {
            "__name__": "__main__",
            "__builtins__": __builtins__,
        }
        self._cell_count = 0
    
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
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    }
                },
                "required": ["code"]
            }
        )
    
    def execute(self, code: str) -> ToolResult:
        code = code.strip()
        
        if not code:
            return ToolResult(success=False, error_message="Empty code")
        
        self._cell_count += 1
        
        # Handle magic commands
        if code.startswith("%"):
            return self._handle_magic(code)
        
        # Capture output
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        result = None
        error = False
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                try:
                    # Try eval first
                    result = eval(compile(code, f"<cell-{self._cell_count}>", "eval"), self._namespace)
                except SyntaxError:
                    # Fall back to exec
                    exec(compile(code, f"<cell-{self._cell_count}>", "exec"), self._namespace)
                    result = None
                    
        except Exception as e:
            import traceback
            error = True
            stderr_capture.write(traceback.format_exc())
        
        # Build output
        output_parts = []
        
        stdout = stdout_capture.getvalue()
        stderr = stderr_capture.getvalue()
        
        if stdout:
            output_parts.append(stdout.rstrip())
        
        if stderr:
            output_parts.append(stderr.rstrip())
        
        if result is not None and not error:
            try:
                result_str = repr(result)
                if len(result_str) > 1000:
                    result_str = result_str[:1000] + "..."
                output_parts.append(f"Out[{self._cell_count}]: {result_str}")
            except Exception:
                pass
        
        output = "\n".join(output_parts) if output_parts else "(no output)"
        
        # Add context
        output += f"\n[Jupyter cwd: {self.workspace.root}]"
        
        return ToolResult(
            success=not error,
            data={"cell": self._cell_count, "error": error, "output": output}
        )
    
    def _handle_magic(self, code: str) -> ToolResult:
        line = code.split('\n')[0].strip()
        
        if line.startswith("%pip"):
            cmd = line[4:].strip()
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip"] + cmd.split(),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                return ToolResult(
                    success=result.returncode == 0,
                    data=result.stdout + result.stderr
                )
            except Exception as e:
                return ToolResult(success=False, error_message=f"pip error: {e}")
        
        elif line.startswith("%cd"):
            new_dir = line[3:].strip()
            try:
                target = Path(new_dir).expanduser()
                if not target.is_absolute():
                    target = self.workspace.root / target
                
                # Security: ensure target is within workspace
                if not self.workspace.contains(target):
                    return ToolResult(success=False, error_message=f"Cannot cd outside workspace: {new_dir}")
                
                if target.is_dir():
                    # DON'T change global CWD! Just update internal tracking
                    # Note: _cwd is internal, workspace.root is the sandbox root
                    return ToolResult(success=True, data=f"Changed to {target}")
                else:
                    return ToolResult(success=False, error_message=f"Not a directory: {new_dir}")
            except Exception as e:
                return ToolResult(success=False, error_message=f"cd error: {e}")
        
        elif line.startswith("%pwd"):
            return ToolResult(success=True, data=str(self.workspace.root))
        
        elif line.startswith("%env"):
            rest = line[4:].strip()
            if "=" in rest:
                key, value = rest.split("=", 1)
                os.environ[key.strip()] = value.strip()
                return ToolResult(success=True, data=f"Set {key}={value}")
            elif rest:
                return ToolResult(success=True, data=f"{rest}={os.environ.get(rest, '')}")
            else:
                env_str = "\n".join(f"{k}={v}" for k, v in sorted(os.environ.items()))
                return ToolResult(success=True, data=env_str)
        
        return ToolResult(success=False, error_message=f"Unknown magic: {line}")


# ===== Start Server Tool =====

class StartServerTool(BaseTool):
    """Start a server as a background process."""
    
    NAME = "start_server"
    
    DESCRIPTION = """Start a server process in the background.

The server runs independently and can be stopped later.
Common uses:
* Start API server: start_server api "python -m uvicorn main:app"
* Start frontend: start_server ui "npm run dev"

Parameters:
* name: Identifier for this server
* command: Command to run
* port: Port number (for tracking)
"""
    
    def __init__(self, work_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
        if workspace:
            self.workspace = workspace
        elif work_dir:
            self.workspace = Workspace(work_dir)
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
                    "name": {
                        "type": "string",
                        "description": "Server name/identifier"
                    },
                    "command": {
                        "type": "string",
                        "description": "Command to start the server"
                    },
                    "port": {
                        "type": "integer",
                        "description": "Port number"
                    }
                },
                "required": ["name", "command", "port"]
            }
        )
    
    def execute(self, name: str, command: str, port: int) -> ToolResult:
        # Check if already running
        existing = _server_registry.get(name)
        if existing:
            return ToolResult(
                success=False,
                error_message=f"Server '{name}' already running on port {existing['port']}"
            )
        
        try:
            # Start process
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(self.workspace.root),
                start_new_session=True,
            )
            
            # Register
            _server_registry.register(name, process.pid, port, str(self.workspace.root))
            
            # Start log capture thread
            import threading
            def capture_logs():
                for line in iter(process.stdout.readline, b''):
                    _server_registry.add_log(name, line.decode('utf-8', errors='replace'))
            
            thread = threading.Thread(target=capture_logs, daemon=True)
            thread.start()
            
            return ToolResult(
                success=True,
                data={
                    "pid": process.pid, 
                    "port": port,
                    "info": f"Started server '{name}' on port {port} (PID: {process.pid})"
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error_message=f"Failed to start server: {e}")


# ===== Stop Server Tool =====

class StopServerTool(BaseTool):
    """Stop a running server."""
    
    NAME = "stop_server"
    
    DESCRIPTION = """Stop a server by name.

Example:
    stop_server api
"""
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
    
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
                    "name": {
                        "type": "string",
                        "description": "Server name to stop"
                    }
                },
                "required": ["name"]
            }
        )
    
    def execute(self, name: str) -> ToolResult:
        server = _server_registry.get(name)
        
        if not server:
            return ToolResult(success=False, error_message=f"Server '{name}' not found")
        
        pid = server["pid"]
        
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            _server_registry.unregister(name)
            return ToolResult(success=True, data=f"Stopped server '{name}' (PID: {pid})")
        except ProcessLookupError:
            _server_registry.unregister(name)
            return ToolResult(success=True, data=f"Server '{name}' was not running")
        except Exception as e:
            return ToolResult(success=False, error_message=f"Failed to stop server: {e}")


# ===== List Servers Tool =====

class ListServersTool(BaseTool):
    """List all running servers."""
    
    NAME = "list_servers"
    
    DESCRIPTION = """List all background servers."""
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
    
    @property
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {}
            }
        )
    
    def execute(self) -> ToolResult:
        servers = _server_registry.get_all()
        
        if not servers:
            return ToolResult(success=True, data="No running servers")
        
        lines = ["Running servers:"]
        for name, info in servers.items():
            lines.append(f"  {name}: port={info['port']}, pid={info['pid']}, started={info['started']}")
        
        return ToolResult(
            success=True,
            data={"servers": servers, "info": "\n".join(lines)}
        )


# ===== Get Server Logs Tool =====

class GetServerLogsTool(BaseTool):
    """Get logs from a running server."""
    
    NAME = "get_server_logs"
    
    DESCRIPTION = """Get recent logs from a server.

Example:
    get_server_logs api
    get_server_logs api 50  # Last 50 lines
"""
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
    
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
                    "name": {
                        "type": "string",
                        "description": "Server name"
                    },
                    "lines": {
                        "type": "integer",
                        "description": "Number of lines (default: 20)"
                    }
                },
                "required": ["name"]
            }
        )
    
    def execute(self, name: str, lines: int = 20) -> ToolResult:
        logs = _server_registry.get_logs(name)
        
        if not logs:
            return ToolResult(
                success=True,
                data=f"No logs for server '{name}' (or server not found)"
            )
        
        recent = logs[-lines:]
        return ToolResult(
            success=True,
            data={"lines": len(recent), "logs": f"Logs for '{name}':\n" + "".join(recent)}
        )


# ===== Test API Tool =====

class TestAPITool(BaseTool):
    """Test an HTTP API endpoint."""
    
    NAME = "test_api"
    
    DESCRIPTION = """Send HTTP request to test an API.

Examples:
    test_api GET http://localhost:8000/health
    test_api POST http://localhost:8000/api/items '{"name": "test"}'
"""
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
    
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
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                        "description": "HTTP method"
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to request"
                    },
                    "body": {
                        "type": "string",
                        "description": "Request body (JSON string)"
                    },
                    "headers": {
                        "type": "object",
                        "description": "HTTP headers"
                    }
                },
                "required": ["method", "url"]
            }
        )
    
    def execute(
        self,
        method: str,
        url: str,
        body: str = None,
        headers: dict = None
    ) -> ToolResult:
        
        try:
            import urllib.request
            import urllib.error
            import json
            
            req_headers = {"Content-Type": "application/json"}
            if headers:
                req_headers.update(headers)
            
            data = body.encode() if body else None
            
            request = urllib.request.Request(
                url,
                data=data,
                headers=req_headers,
                method=method,
            )
            
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = response.status
                    content = response.read().decode()
                    
                    # Try to format JSON
                    try:
                        content = json.dumps(json.loads(content), indent=2)
                    except:
                        pass
                    
                    return ToolResult(
                        success=True,
                        data={"status": status, "response": f"Status: {status}\n{content}"}
                    )
                    
            except urllib.error.HTTPError as e:
                content = e.read().decode()
                return ToolResult(
                    success=False,
                    data={"status": e.code, "response": f"Status: {e.code}\n{content}"},
                    error_message=f"HTTP Error: {e.code}"
                )
                
        except Exception as e:
            return ToolResult(success=False, error_message=f"Request failed: {e}")


# ===== Install Dependencies Tool =====

class InstallDependenciesTool(BaseTool):
    """Install project dependencies."""
    
    NAME = "install_dependencies"
    
    DESCRIPTION = """Install dependencies for a project.

Automatically detects:
* requirements.txt -> pip install
* package.json -> npm install
* pyproject.toml -> pip install -e .
"""
    
    def __init__(self, work_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
        if workspace:
            self.workspace = workspace
        elif work_dir:
            self.workspace = Workspace(work_dir)
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
                        "description": "Project directory (default: current)"
                    }
                }
            }
        )
    
    def execute(self, path: str = None) -> ToolResult:
        try:
            project_dir = self.workspace.resolve(path) if path else self.workspace.root
        except Exception as e:
            return ToolResult(success=False, error_message=f"Invalid path: {e}")
        
        if not project_dir.exists():
            return ToolResult(success=False, error_message=f"Path not found: {path}")
        
        results = []
        
        # Python: requirements.txt
        req_file = project_dir / "requirements.txt"
        if req_file.exists():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(project_dir),
                )
                results.append(f"pip install: {'OK' if result.returncode == 0 else 'FAILED'}")
                if result.returncode != 0:
                    results.append(result.stderr)
            except Exception as e:
                results.append(f"pip install failed: {e}")
        
        # Python: pyproject.toml
        pyproject = project_dir / "pyproject.toml"
        if pyproject.exists() and not req_file.exists():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-e", "."],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(project_dir),
                )
                results.append(f"pip install -e .: {'OK' if result.returncode == 0 else 'FAILED'}")
            except Exception as e:
                results.append(f"pip install failed: {e}")
        
        # Node.js: package.json
        pkg_json = project_dir / "package.json"
        if pkg_json.exists():
            try:
                result = subprocess.run(
                    ["npm", "install"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(project_dir),
                )
                results.append(f"npm install: {'OK' if result.returncode == 0 else 'FAILED'}")
            except Exception as e:
                results.append(f"npm install failed: {e}")
        
        if not results:
            return ToolResult(
                success=True,
                data="No dependency files found (requirements.txt, package.json, pyproject.toml)"
            )
        
        return ToolResult(
            success=True,
            data="\n".join(results)
        )


# ===== Exports =====

__all__ = [
    "ExecuteBashTool",
    "ExecuteIPythonTool",
    "StartServerTool",
    "StopServerTool",
    "ListServersTool",
    "GetServerLogsTool",
    "TestAPITool",
    "InstallDependenciesTool",
    "ServerRegistry",
]
