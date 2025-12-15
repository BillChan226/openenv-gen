"""
Runtime Tools for Code Generation Agent

These tools allow the agent to:
1. Run shell commands (install deps, run scripts)
2. Start and manage servers (backend, frontend)
3. Test API endpoints
4. Check browser output / take screenshots

Key Design: The agent can now TEST its own generated code,
see errors, and fix them - just like a human developer.
"""

import os
import sys
import time
import asyncio
import subprocess
import shutil
import json
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils.tool import BaseTool, ToolDefinition, ToolParameter, ToolResult, ToolCategory


def find_python_executable() -> str:
    """
    Find a working Python executable.
    Tries multiple options for cross-platform compatibility.
    """
    candidates = [
        sys.executable,  # Current Python interpreter (most reliable)
        "python3",
        "python",
        "/usr/bin/python3",
        "/usr/local/bin/python3",
        "/opt/homebrew/bin/python3",
    ]
    
    for candidate in candidates:
        if candidate == sys.executable:
            return candidate  # Always trust sys.executable
        if shutil.which(candidate):
            return candidate
    
    # Fallback to sys.executable even if path lookup fails
    return sys.executable


def find_pip_executable() -> str:
    """Find a working pip executable."""
    python_exec = find_python_executable()
    # Use python -m pip for reliability
    return f"{python_exec} -m pip"


def find_uvicorn_command() -> str:
    """Find a working uvicorn command."""
    python_exec = find_python_executable()
    return f"{python_exec} -m uvicorn"


# Global Python executable (cached)
PYTHON_EXECUTABLE = find_python_executable()


@dataclass
class ProcessInfo:
    """Info about a running process"""
    pid: int
    name: str
    command: str
    port: Optional[int] = None
    started_at: datetime = field(default_factory=datetime.now)
    
    
class ProcessManager:
    """Manages background processes started by tools"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._processes: Dict[str, ProcessInfo] = {}
            cls._instance._subprocesses: Dict[str, subprocess.Popen] = {}
        return cls._instance
    
    def add(self, name: str, proc: subprocess.Popen, command: str, port: Optional[int] = None):
        """Register a process"""
        info = ProcessInfo(
            pid=proc.pid,
            name=name,
            command=command,
            port=port,
        )
        self._processes[name] = info
        self._subprocesses[name] = proc
        
    def get(self, name: str) -> Optional[ProcessInfo]:
        """Get process info"""
        return self._processes.get(name)
    
    def stop(self, name: str) -> bool:
        """Stop a process"""
        proc = self._subprocesses.get(name)
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()
            del self._processes[name]
            del self._subprocesses[name]
            return True
        return False
    
    def stop_all(self):
        """Stop all managed processes"""
        for name in list(self._processes.keys()):
            self.stop(name)
            
    def list_running(self) -> List[ProcessInfo]:
        """List all running processes"""
        return list(self._processes.values())


# Global process manager
_process_manager = ProcessManager()


class RunCommandTool(BaseTool):
    """
    Run a shell command and return output.
    
    Usage: Run any shell command to install dependencies,
    build projects, run tests, etc.
    """
    
    def __init__(self, working_dir: Path):
        super().__init__()
        self.working_dir = Path(working_dir)
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="run_command",
            description="Run a shell command and return output. Use for installing deps, building, running tests.",
            category=ToolCategory.SHELL,
            parameters=[
                ToolParameter(
                    name="command",
                    param_type=str,
                    description="The shell command to run",
                    required=True,
                ),
                ToolParameter(
                    name="timeout",
                    param_type=int,
                    description="Max seconds to wait (default 120)",
                    required=False,
                    default=120,
                ),
                ToolParameter(
                    name="cwd",
                    param_type=str,
                    description="Working directory (relative to output_dir)",
                    required=False,
                    default="",
                ),
            ],
            examples=[
                {"input": {"command": "pip install -r requirements.txt"}, "output": "..."},
                {"input": {"command": "npm install", "cwd": "calendar_ui"}, "output": "..."},
            ],
            tags=["shell", "command", "run"],
        )
        
    async def execute(self, command: str, timeout: int = 120, cwd: str = "", **kwargs) -> ToolResult:
        """Execute a shell command."""
        try:
            work_dir = self.working_dir / cwd if cwd else self.working_dir
            
            if not work_dir.exists():
                return ToolResult(
                    success=False,
                    data={"error": f"Directory does not exist: {work_dir}"},
                )
            
            # Run the command
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "PYTHONPATH": str(self.working_dir)},
            )
            
            return ToolResult(
                success=result.returncode == 0,
                data={
                    "return_code": result.returncode,
                    "stdout": result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout,
                    "stderr": result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr,
                    "command": command,
                    "cwd": str(work_dir),
                },
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                data={"error": f"Command timed out after {timeout}s", "command": command},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                data={"error": str(e), "command": command},
            )


class StartServerTool(BaseTool):
    """
    Start a server process in the background.
    
    Usage: Start backend or frontend servers for testing.
    """
    
    def __init__(self, working_dir: Path):
        super().__init__()
        self.working_dir = Path(working_dir)
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="start_server",
            description="Start a server process in background. Returns when server is ready.",
            category=ToolCategory.SHELL,
            parameters=[
                ToolParameter(
                    name="server_name",  # Renamed from 'name' to avoid conflict with call_tool's 'name' param
                    param_type=str,
                    description="Unique name for this server (e.g., 'backend', 'frontend')",
                    required=True,
                ),
                ToolParameter(
                    name="command",
                    param_type=str,
                    description="Command to start the server",
                    required=True,
                ),
                ToolParameter(
                    name="cwd",
                    param_type=str,
                    description="Working directory (relative to output_dir)",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="port",
                    param_type=int,
                    description="Port the server will listen on (for health checking)",
                    required=False,
                    default=None,
                ),
                ToolParameter(
                    name="wait_for_ready",
                    param_type=int,
                    description="Seconds to wait for server to be ready",
                    required=False,
                    default=30,
                ),
            ],
            examples=[
                {"input": {"server_name": "backend", "command": "uvicorn main:app --port 8000", "cwd": "calendar_api", "port": 8000}},
            ],
            tags=["server", "start", "process"],
        )
        
    async def execute(
        self,
        server_name: str,  # Renamed from 'name'
        command: str,
        cwd: str = "",
        port: Optional[int] = None,
        wait_for_ready: int = 30,
        **kwargs
    ) -> ToolResult:
        """Start a server process."""
        try:
            work_dir = self.working_dir / cwd if cwd else self.working_dir
            
            # Stop existing server with same name
            if _process_manager.get(server_name):
                _process_manager.stop(server_name)
                
            # Start the process
            env = {**os.environ, "PYTHONPATH": str(self.working_dir)}
            
            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=str(work_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                preexec_fn=os.setsid if os.name != 'nt' else None,
            )
            
            _process_manager.add(server_name, proc, command, port)
            
            # Wait for server to be ready
            if port:
                import socket
                ready = False
                start_time = time.time()
                
                while time.time() - start_time < wait_for_ready:
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(1)
                            s.connect(("localhost", port))
                            ready = True
                            break
                    except:
                        await asyncio.sleep(0.5)
                        
                if not ready:
                    # Check if process died
                    if proc.poll() is not None:
                        stdout, stderr = proc.communicate()
                        return ToolResult(
                            success=False,
                            data={
                                "error": "Server process exited",
                                "stdout": stdout.decode()[-2000:] if stdout else "",
                                "stderr": stderr.decode()[-2000:] if stderr else "",
                            },
                        )
                    return ToolResult(
                        success=False,
                        data={"error": f"Server did not become ready on port {port} within {wait_for_ready}s"},
                    )
            else:
                # Just wait a bit for the process to start
                await asyncio.sleep(2)
                if proc.poll() is not None:
                    stdout, stderr = proc.communicate()
                    return ToolResult(
                        success=False,
                        data={
                            "error": "Server process exited immediately",
                            "stdout": stdout.decode()[-2000:] if stdout else "",
                            "stderr": stderr.decode()[-2000:] if stderr else "",
                        },
                    )
                    
            return ToolResult(
                success=True,
                data={
                    "message": f"Server '{server_name}' started successfully",
                    "pid": proc.pid,
                    "port": port,
                    "command": command,
                },
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                data={"error": str(e)},
            )


class StopServerTool(BaseTool):
    """Stop a running server."""
    
    def __init__(self):
        super().__init__()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="stop_server",
            description="Stop a running server by name.",
            category=ToolCategory.SHELL,
            parameters=[
                ToolParameter(
                    name="server_name",  # Renamed from 'name' to avoid conflict with call_tool
                    param_type=str,
                    description="Name of server to stop",
                    required=False,
                    default="",
                ),
                ToolParameter(
                    name="stop_all",  # Renamed from 'all' (reserved keyword)
                    param_type=bool,
                    description="If True, stop all servers",
                    required=False,
                    default=False,
                ),
            ],
            tags=["server", "stop"],
        )
        
    async def execute(self, server_name: str = "", stop_all: bool = False, **kwargs) -> ToolResult:
        """Stop server(s)."""
        try:
            if stop_all:
                _process_manager.stop_all()
                return ToolResult(success=True, data={"message": "All servers stopped"})
            elif server_name:
                if _process_manager.stop(server_name):
                    return ToolResult(success=True, data={"message": f"Server '{server_name}' stopped"})
                else:
                    return ToolResult(success=False, data={"error": f"Server '{server_name}' not found"})
            else:
                return ToolResult(success=False, data={"error": "Specify 'server_name' or 'stop_all=True'"})
        except Exception as e:
            return ToolResult(success=False, data={"error": str(e)})


class TestAPITool(BaseTool):
    """
    Test an HTTP API endpoint.
    
    Usage: Make HTTP requests to test if API is working correctly.
    """
    
    def __init__(self):
        super().__init__()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="test_api",
            description="Make HTTP request to test API endpoint. Returns status code and response.",
            category=ToolCategory.NETWORK,
            parameters=[
                ToolParameter(
                    name="method",
                    param_type=str,
                    description="HTTP method (GET, POST, PUT, DELETE)",
                    required=True,
                ),
                ToolParameter(
                    name="url",
                    param_type=str,
                    description="Full URL to request",
                    required=True,
                ),
                ToolParameter(
                    name="json_data",
                    param_type=dict,
                    description="JSON body for POST/PUT requests",
                    required=False,
                    default=None,
                ),
                ToolParameter(
                    name="headers",
                    param_type=dict,
                    description="Custom headers",
                    required=False,
                    default=None,
                ),
                ToolParameter(
                    name="timeout",
                    param_type=int,
                    description="Request timeout in seconds",
                    required=False,
                    default=10,
                ),
            ],
            examples=[
                {"input": {"method": "GET", "url": "http://localhost:8000/health"}},
                {"input": {"method": "POST", "url": "http://localhost:8000/auth/register", "json_data": {"email": "test@test.com"}}},
            ],
            tags=["api", "http", "test"],
        )
        
    async def execute(
        self,
        method: str,
        url: str,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: int = 10,
        **kwargs
    ) -> ToolResult:
        """Test an API endpoint."""
        try:
            import urllib.request
            import urllib.error
            
            # Prepare request
            data = None
            if json_data:
                data = json.dumps(json_data).encode('utf-8')
                
            req = urllib.request.Request(url, data=data, method=method.upper())
            req.add_header('Content-Type', 'application/json')
            req.add_header('Accept', 'application/json')
            
            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)
                    
            # Make request
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    body = response.read().decode('utf-8')
                    try:
                        response_data = json.loads(body)
                    except:
                        response_data = body[:2000]
                        
                    return ToolResult(
                        success=True,
                        data={
                            "status_code": response.status,
                            "response": response_data,
                            "headers": dict(response.headers),
                        },
                    )
            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8') if e.fp else ""
                try:
                    error_data = json.loads(body)
                except:
                    error_data = body[:1000]
                    
                return ToolResult(
                    success=False,
                    data={
                        "status_code": e.code,
                        "error": str(e.reason),
                        "response": error_data,
                    },
                )
            except urllib.error.URLError as e:
                return ToolResult(
                    success=False,
                    data={
                        "error": f"Connection failed: {e.reason}",
                        "url": url,
                    },
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                data={"error": str(e)},
            )


class ListServersTool(BaseTool):
    """List all running servers."""
    
    def __init__(self):
        super().__init__()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_servers",
            description="List all servers that have been started.",
            category=ToolCategory.SHELL,
            parameters=[],
            tags=["server", "list"],
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        servers = _process_manager.list_running()
        return ToolResult(
            success=True,
            data={
                "servers": [
                    {
                        "name": s.name,
                        "pid": s.pid,
                        "port": s.port,
                        "command": s.command,
                        "running_since": s.started_at.isoformat(),
                    }
                    for s in servers
                ]
            },
        )


class CheckFilesExistTool(BaseTool):
    """
    Check if a list of files exist.
    
    Usage: Verify that planned files were actually generated.
    """
    
    def __init__(self, working_dir: Path):
        super().__init__()
        self.working_dir = Path(working_dir)
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="check_files_exist",
            description="Check if multiple files exist. Use to verify planned files were generated.",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="files",
                    param_type=list,
                    description="List of file paths (relative to output_dir)",
                    required=True,
                ),
            ],
            tags=["file", "check", "verify"],
        )
        
    async def execute(self, files: List[str], **kwargs) -> ToolResult:
        """Check if files exist."""
        results = {}
        missing = []
        existing = []
        
        for file_path in files:
            full_path = self.working_dir / file_path
            exists = full_path.exists()
            results[file_path] = exists
            if exists:
                existing.append(file_path)
            else:
                missing.append(file_path)
                
        return ToolResult(
            success=len(missing) == 0,
            data={
                "results": results,
                "existing": existing,
                "missing": missing,
                "total": len(files),
                "existing_count": len(existing),
                "missing_count": len(missing),
            },
        )


class InstallDependenciesTool(BaseTool):
    """
    Install project dependencies.
    
    Usage: Install Python or Node.js dependencies.
    """
    
    def __init__(self, working_dir: Path):
        super().__init__()
        self.working_dir = Path(working_dir)
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="install_dependencies",
            description="Install Python (pip) or Node.js (npm) dependencies in a directory.",
            category=ToolCategory.SHELL,
            parameters=[
                ToolParameter(
                    name="project_type",
                    param_type=str,
                    description="'python' or 'nodejs'",
                    required=True,
                    choices=["python", "nodejs"],
                ),
                ToolParameter(
                    name="cwd",
                    param_type=str,
                    description="Working directory (relative to output_dir)",
                    required=False,
                    default="",
                ),
            ],
            tags=["install", "dependencies", "pip", "npm"],
        )
        
    async def execute(self, project_type: str, cwd: str = "", **kwargs) -> ToolResult:
        """Install dependencies."""
        try:
            work_dir = self.working_dir / cwd if cwd else self.working_dir
            
            if project_type == "python":
                req_file = work_dir / "requirements.txt"
                if not req_file.exists():
                    return ToolResult(
                        success=False,
                        data={"error": "requirements.txt not found"},
                    )
                cmd = f"python3 -m pip install -r requirements.txt"
            elif project_type == "nodejs":
                pkg_file = work_dir / "package.json"
                if not pkg_file.exists():
                    return ToolResult(
                        success=False,
                        data={"error": "package.json not found"},
                    )
                cmd = "npm install"
            else:
                return ToolResult(
                    success=False,
                    data={"error": f"Unknown project type: {project_type}. Use 'python' or 'nodejs'"},
                )
                
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes for dependency install
            )
            
            return ToolResult(
                success=result.returncode == 0,
                data={
                    "return_code": result.returncode,
                    "stdout": result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout,
                    "stderr": result.stderr[-1500:] if len(result.stderr) > 1500 else result.stderr,
                },
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, data={"error": "Dependency installation timed out"})
        except Exception as e:
            return ToolResult(success=False, data={"error": str(e)})


class GetServerLogsTool(BaseTool):
    """Get logs from a running server."""
    
    def __init__(self):
        super().__init__()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_server_logs",
            description="Get recent output from a running server process.",
            category=ToolCategory.SHELL,
            parameters=[
                ToolParameter(
                    name="server_name",  # Renamed from 'name' to avoid conflict
                    param_type=str,
                    description="Server name",
                    required=True,
                ),
                ToolParameter(
                    name="lines",
                    param_type=int,
                    description="Number of lines to return",
                    required=False,
                    default=50,
                ),
            ],
            tags=["server", "logs"],
        )
        
    async def execute(self, server_name: str, lines: int = 50, **kwargs) -> ToolResult:
        """Get server logs."""
        proc = _process_manager._subprocesses.get(server_name)
        if not proc:
            return ToolResult(success=False, data={"error": f"Server '{server_name}' not found"})
            
        poll = proc.poll()
        
        if poll is not None:
            # Process has exited
            stdout, stderr = proc.communicate()
            return ToolResult(
                success=False,
                data={
                    "status": "exited",
                    "return_code": poll,
                    "stdout": stdout.decode()[-3000:] if stdout else "",
                    "stderr": stderr.decode()[-3000:] if stderr else "",
                },
            )
        else:
            return ToolResult(
                success=True,
                data={
                    "status": "running",
                    "pid": proc.pid,
                    "message": "Server is still running (logs not available in real-time)",
                },
            )


class QuickTestTool(BaseTool):
    """
    Quick test for generated backend.
    
    This tool allows the model to quickly verify that a FastAPI backend
    can start and respond to basic requests.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="quick_test",
            description="Quickly test if generated backend can start and respond. Use after generating main.py.",
            category=ToolCategory.SHELL,
            parameters=[
                ToolParameter(
                    name="backend_dir",
                    param_type=str,
                    description="Backend directory (e.g., 'calendar_api')",
                    required=True,
                ),
                ToolParameter(
                    name="port",
                    param_type=int,
                    description="Port to test on",
                    required=False,
                    default=8000,
                ),
                ToolParameter(
                    name="endpoints",
                    param_type=list,
                    description="List of endpoints to test (e.g., ['/health', '/docs'])",
                    required=False,
                    default=["/health", "/docs"],
                ),
            ],
            returns="Test results with success/failure for each endpoint",
            tags=["test", "backend", "quick"],
        )
    
    async def execute(
        self,
        backend_dir: str,
        port: int = 8000,
        endpoints: list = None,
        **kwargs
    ) -> ToolResult:
        """Quick test the backend."""
        if endpoints is None:
            endpoints = ["/health", "/docs"]
        
        results = {
            "backend_dir": backend_dir,
            "port": port,
            "steps": [],
            "success": False,
        }
        
        full_backend_path = self.base_dir / backend_dir
        
        # Step 1: Check if main.py exists
        main_py = full_backend_path / "main.py"
        if not main_py.exists():
            results["steps"].append({"step": "check_main", "success": False, "error": "main.py not found"})
            return ToolResult.fail(results)
        results["steps"].append({"step": "check_main", "success": True})
        
        # Step 2: Check if requirements.txt exists and install
        req_file = full_backend_path / "requirements.txt"
        if req_file.exists():
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await asyncio.wait_for(proc.wait(), timeout=60)
                results["steps"].append({"step": "install_deps", "success": True})
            except Exception as e:
                results["steps"].append({"step": "install_deps", "success": False, "error": str(e)})
        
        # Step 3: Try to start the server
        server_name = f"test_{backend_dir}_{port}"
        
        # First stop any existing server on this port
        await _process_manager.stop_server(server_name)
        await asyncio.sleep(1)
        
        try:
            # Start uvicorn from the parent directory so imports work
            start_cmd = f"{sys.executable} -m uvicorn {backend_dir}.main:app --host 0.0.0.0 --port {port}"
            
            proc = await asyncio.create_subprocess_shell(
                start_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.base_dir),
            )
            
            _process_manager._subprocesses[server_name] = proc
            
            # Wait for server to start
            await asyncio.sleep(3)
            
            # Check if still running
            if proc.returncode is not None:
                stdout, stderr = await proc.communicate()
                results["steps"].append({
                    "step": "start_server",
                    "success": False,
                    "error": stderr.decode()[:500] if stderr else "Server exited immediately",
                })
                return ToolResult.fail(results)
            
            results["steps"].append({"step": "start_server", "success": True, "pid": proc.pid})
            
            # Step 4: Test endpoints
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                for endpoint in endpoints:
                    try:
                        url = f"http://localhost:{port}{endpoint}"
                        resp = await client.get(url)
                        results["steps"].append({
                            "step": f"test_{endpoint}",
                            "success": resp.status_code < 500,
                            "status_code": resp.status_code,
                        })
                    except Exception as e:
                        results["steps"].append({
                            "step": f"test_{endpoint}",
                            "success": False,
                            "error": str(e)[:100],
                        })
            
            # Step 5: Stop server
            await _process_manager.stop_server(server_name)
            results["steps"].append({"step": "stop_server", "success": True})
            
            # Calculate overall success
            failed_steps = [s for s in results["steps"] if not s.get("success", False)]
            results["success"] = len(failed_steps) == 0
            results["failed_count"] = len(failed_steps)
            results["passed_count"] = len(results["steps"]) - len(failed_steps)
            
            if results["success"]:
                return ToolResult.ok(results)
            else:
                return ToolResult(success=False, data=results)
            
        except Exception as e:
            # Cleanup
            await _process_manager.stop_server(server_name)
            results["steps"].append({"step": "error", "success": False, "error": str(e)[:200]})
            return ToolResult.fail(results)


class ShouldTestTool(BaseTool):
    """
    Ask the model if now is a good time to test.
    
    This is a helper that provides context about what's been generated
    and suggests whether testing would be valuable.
    """
    
    def __init__(self, base_dir: Optional[Path] = None, gen_context: Any = None):
        super().__init__()
        self.base_dir = base_dir or Path.cwd()
        self.gen_context = gen_context
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="should_test",
            description="Check if now is a good time to test. Returns recommendation based on what's generated.",
            category=ToolCategory.CUSTOM,
            parameters=[],
            returns="Recommendation on whether to test and what to test",
            tags=["test", "decision"],
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        """Check testing readiness."""
        
        ready_for_test = {
            "backend": False,
            "frontend": False,
            "recommendations": [],
        }
        
        # Check backend
        if self.gen_context and hasattr(self.gen_context, 'files'):
            backend_files = [f for f in self.gen_context.files.keys() if '_api/' in f]
            has_main = any('main.py' in f for f in backend_files)
            has_models = any('models.py' in f for f in backend_files)
            has_routes = any('router' in f.lower() or 'auth.py' in f for f in backend_files)
            
            if has_main and has_models:
                ready_for_test["backend"] = True
                ready_for_test["recommendations"].append(
                    "Backend has main.py and models.py - good time to test with quick_test()"
                )
            elif has_main:
                ready_for_test["recommendations"].append(
                    "Backend has main.py but no models - can test server starts"
                )
            
            if has_routes:
                ready_for_test["recommendations"].append(
                    "Routes detected - can test API endpoints after starting server"
                )
        
        # Fallback: check filesystem
        if not ready_for_test["backend"]:
            for subdir in self.base_dir.iterdir():
                if subdir.is_dir() and subdir.name.endswith('_api'):
                    main_py = subdir / "main.py"
                    if main_py.exists():
                        ready_for_test["backend"] = True
                        ready_for_test["recommendations"].append(
                            f"Found {subdir.name}/main.py - can test backend"
                        )
                        break
        
        # Check frontend
        for subdir in self.base_dir.iterdir():
            if subdir.is_dir() and subdir.name.endswith('_ui'):
                pkg_json = subdir / "package.json"
                if pkg_json.exists():
                    ready_for_test["frontend"] = True
                    ready_for_test["recommendations"].append(
                        f"Found {subdir.name}/package.json - can npm install and test"
                    )
                    break
        
        if not ready_for_test["recommendations"]:
            ready_for_test["recommendations"].append(
                "Not enough files generated yet. Continue generating before testing."
            )
        
        return ToolResult.ok(ready_for_test)
