"""
Runtime Tools - Unified Process Management and Command Execution

Features:
- Unified ProcessManager for all background processes (servers and generic)
- Clean API for agent to start/stop/interrupt/monitor processes
- Automatic output capture and process lifecycle tracking
- Event-based notification support

Inspired by OpenHands execute_bash and execute_ipython.
"""

import os
import asyncio
import subprocess
import signal
import socket
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Union, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tool import BaseTool, ToolResult, create_tool_param, ToolCategory
from workspace import Workspace


# ===== Environment State Cache =====

class EnvironmentStateCache:
    """
    Caches environment state to avoid repeated failed checks.
    
    Example:
    - Docker daemon unavailable: don't retry docker_build for 5 minutes
    - Port occupied: remember which ports are in use
    - Missing tools: remember which CLI tools aren't installed
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._state = {}
            cls._instance._failure_counts = {}
            cls._instance._last_check = {}
        return cls._instance
    
    def record_failure(self, key: str, error: str, cooldown_seconds: int = 300):
        """Record a failure with cooldown before retry."""
        self._state[key] = {"available": False, "error": error}
        self._failure_counts[key] = self._failure_counts.get(key, 0) + 1
        self._last_check[key] = datetime.now()
    
    def record_success(self, key: str):
        """Record that something is available."""
        self._state[key] = {"available": True, "error": None}
        self._failure_counts[key] = 0
        self._last_check[key] = datetime.now()
    
    def should_skip(self, key: str, cooldown_seconds: int = 300) -> tuple:
        """
        Check if we should skip this operation.
        
        Returns:
            (should_skip: bool, reason: str or None)
        """
        if key not in self._state:
            return False, None
        
        state = self._state[key]
        if state["available"]:
            return False, None
        
        # Check if cooldown has passed
        last_check = self._last_check.get(key)
        if last_check:
            elapsed = (datetime.now() - last_check).total_seconds()
            if elapsed < cooldown_seconds:
                failures = self._failure_counts.get(key, 0)
                return True, f"Skipped: {state['error']} (failed {failures}x, retry in {int(cooldown_seconds - elapsed)}s)"
        
        return False, None
    
    def get_status(self) -> dict:
        """Get current environment status."""
        return {
            k: {
                "available": v["available"],
                "error": v.get("error"),
                "failures": self._failure_counts.get(k, 0)
            }
            for k, v in self._state.items()
        }
    
    def reset(self, key: str = None):
        """Reset state (for testing or manual refresh)."""
        if key:
            self._state.pop(key, None)
            self._failure_counts.pop(key, None)
            self._last_check.pop(key, None)
        else:
            self._state.clear()
            self._failure_counts.clear()
            self._last_check.clear()


# Global instance
env_cache = EnvironmentStateCache()


# ===== Process Types =====

class ProcessType(Enum):
    """Type of background process."""
    SERVER = "server"          # Named server with port
    BACKGROUND = "background"  # Generic background command
    DOCKER = "docker"          # Docker container


class ProcessStatus(Enum):
    """Status of a process."""
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    CRASHED = "crashed"
    TIMEOUT = "timeout"


@dataclass
class ProcessInfo:
    """Information about a tracked process."""
    pid: int
    command: str
    cwd: str
    process_type: ProcessType
    started: datetime = field(default_factory=datetime.now)
    
    # Optional fields
    name: Optional[str] = None           # For named servers
    port: Optional[int] = None           # For servers with ports
    
    # Process handle
    process: Optional[subprocess.Popen] = None
    
    # Output capture
    output_buffer: List[str] = field(default_factory=list)
    output_reader_thread: Optional[threading.Thread] = None
    
    # Status tracking
    status: ProcessStatus = ProcessStatus.STARTING
    exit_code: Optional[int] = None
    finished: Optional[datetime] = None
    
    # Callbacks
    on_exit: Optional[Callable[[int, int], None]] = None
    
    def to_dict(self) -> dict:
        """Convert to serializable dict (exclude process handle)."""
        return {
            "pid": self.pid,
            "name": self.name,
            "command": self.command[:200],  # Truncate long commands
            "cwd": self.cwd,
            "type": self.process_type.value,
            "port": self.port,
            "started": self.started.isoformat(),
            "status": self.status.value,
            "running": self.status in (ProcessStatus.STARTING, ProcessStatus.RUNNING),
            "exit_code": self.exit_code,
            "finished": self.finished.isoformat() if self.finished else None,
        }


# ===== Unified Process Manager =====

class ProcessManager:
    """
    Unified manager for all background processes.
    
    Singleton pattern - use ProcessManager.instance() to get the global instance.
    
    Features:
    - Single registry for servers and background commands
    - Automatic output capture with threading
    - Process lifecycle tracking
    - Clean API for start/stop/interrupt/wait
    """
    
    _instance = None
    
    @classmethod
    def instance(cls) -> "ProcessManager":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset the singleton (for testing)."""
        if cls._instance:
            cls._instance.cleanup_all()
        cls._instance = None
    
    def __init__(self):
        self._processes: Dict[int, ProcessInfo] = {}
        self._names: Dict[str, int] = {}  # name -> pid mapping for named processes
        self._lock = threading.Lock()
        self._watchdog_thread: Optional[threading.Thread] = None
        self._watchdog_running = False
    
    def start(
        self,
        command: str,
        cwd: str,
        name: str = None,
        port: int = None,
        timeout: int = None,
        on_exit: Callable[[int, int], None] = None,
        process_type: ProcessType = None,
    ) -> ProcessInfo:
        """
        Start a background process with unified tracking.
        
        Args:
            command: Shell command to run
            cwd: Working directory
            name: Optional name for the process (required for servers)
            port: Optional port number (for servers)
            timeout: Optional timeout in seconds (process killed after timeout)
            on_exit: Optional callback(pid, exit_code) when process exits
            process_type: Type of process (auto-detected if not specified)
            
        Returns:
            ProcessInfo with process details
        """
        # Auto-detect process type
        if process_type is None:
            process_type = ProcessType.SERVER if port else ProcessType.BACKGROUND
        
        # Check for existing named process
        if name:
            existing_pid = self._names.get(name)
            if existing_pid:
                existing = self._processes.get(existing_pid)
                if existing and existing.status in (ProcessStatus.STARTING, ProcessStatus.RUNNING):
                    # Check if actually alive
                    if self._is_process_alive(existing_pid):
                        raise ValueError(f"Process '{name}' already running (PID: {existing_pid})")
                    else:
                        # Dead process - clean up
                        self._cleanup_process(existing_pid)
        
        # Check port availability for servers
        if port and not self._port_is_free("0.0.0.0", port):
            raise ValueError(f"Port {port} is already in use")
        
        # Start the process
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(cwd),
                start_new_session=True,
                env={**os.environ, "PYTHONUNBUFFERED": "1", "FORCE_COLOR": "0", "NO_COLOR": "1"},
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start process: {e}")
        
        # Create ProcessInfo
        info = ProcessInfo(
            pid=process.pid,
            command=command,
            cwd=str(cwd),
            process_type=process_type,
            name=name,
            port=port,
            process=process,
            status=ProcessStatus.STARTING,
            on_exit=on_exit,
        )
        
        # Register
        with self._lock:
            self._processes[process.pid] = info
            if name:
                self._names[name] = process.pid
        
        # Start output reader thread
        reader_thread = threading.Thread(
            target=self._read_output,
            args=(info,),
            daemon=True
        )
        reader_thread.start()
        info.output_reader_thread = reader_thread
        
        # Start watchdog if not running
        self._ensure_watchdog()
        
        # Handle timeout
        if timeout:
            threading.Timer(timeout, lambda: self._timeout_process(process.pid)).start()
        
        return info
    
    def stop(self, pid_or_name: Union[int, str], force: bool = False) -> bool:
        """
        Stop a process by PID or name.
        
        Args:
            pid_or_name: Process ID or name
            force: Use SIGKILL instead of SIGTERM
            
        Returns:
            True if process was stopped
        """
        info = self._resolve_process(pid_or_name)
        if not info:
            return False
        
        return self._kill_process(info.pid, signal.SIGKILL if force else signal.SIGTERM)
    
    def interrupt(self, pid_or_name: Union[int, str]) -> bool:
        """
        Send SIGINT (Ctrl+C) to a process.
        
        Args:
            pid_or_name: Process ID or name
            
        Returns:
            True if signal was sent
        """
        info = self._resolve_process(pid_or_name)
        if not info:
            return False
        
        return self._kill_process(info.pid, signal.SIGINT)
    
    def wait(self, pid_or_name: Union[int, str], timeout: float = None) -> Optional[int]:
        """
        Wait for a process to exit.
        
        Args:
            pid_or_name: Process ID or name
            timeout: Maximum seconds to wait (None = wait forever)
            
        Returns:
            Exit code, or None if timeout
        """
        info = self._resolve_process(pid_or_name)
        if not info or not info.process:
            return None
        
        try:
            exit_code = info.process.wait(timeout=timeout)
            return exit_code
        except subprocess.TimeoutExpired:
            return None
    
    def get_output(self, pid_or_name: Union[int, str], lines: int = 100) -> str:
        """
        Get recent output from a process.
        
        Args:
            pid_or_name: Process ID or name
            lines: Maximum number of lines to return
            
        Returns:
            Recent output as string
        """
        info = self._resolve_process(pid_or_name)
        if not info:
            return f"Process not found: {pid_or_name}"
        
        with self._lock:
            output_lines = info.output_buffer[-lines:]
        
        if not output_lines:
            return "(no output captured)"
        
        return "".join(output_lines)
    
    def get_status(self, pid_or_name: Union[int, str]) -> Optional[dict]:
        """
        Get status of a process.
        
        Args:
            pid_or_name: Process ID or name
            
        Returns:
            Dict with process info, or None if not found
        """
        info = self._resolve_process(pid_or_name)
        if not info:
            return None
        
        # Update status from process handle
        self._update_process_status(info)
        
        return info.to_dict()
    
    def list_all(self) -> Dict[int, dict]:
        """
        List all tracked processes.
        
        Returns:
            Dict of pid -> process info
        """
        # Update all statuses first
        with self._lock:
            for info in self._processes.values():
                self._update_process_status(info)
        
        return {pid: info.to_dict() for pid, info in self._processes.items()}
    
    def list_by_type(self, process_type: ProcessType) -> Dict[int, dict]:
        """List processes of a specific type."""
        all_procs = self.list_all()
        return {pid: info for pid, info in all_procs.items() if info["type"] == process_type.value}
    
    def cleanup_port(self, port: int) -> str:
        """
        Kill all processes using a specific port.
        
        Returns:
            Status message
        """
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5,
                encoding='utf-8',
                errors='replace',
            )
            
            if result.returncode != 0 or not result.stdout.strip():
                return f"Port {port}: already free"
            
            pids = result.stdout.strip().split('\n')
            killed = []
            
            for pid_str in pids:
                try:
                    pid = int(pid_str.strip())
                    os.kill(pid, signal.SIGTERM)
                    killed.append(pid)
                    # Also clean up from our registry
                    self._cleanup_process(pid)
                except (ValueError, ProcessLookupError):
                    pass
            
            if killed:
                return f"Port {port}: killed PIDs {killed}"
            return f"Port {port}: no process killed"
            
        except FileNotFoundError:
            return f"Port {port}: lsof not available"
        except Exception as e:
            return f"Port {port}: error - {e}"
    
    def cleanup_all(self):
        """Stop all tracked processes."""
        with self._lock:
            pids = list(self._processes.keys())
        
        for pid in pids:
            self.stop(pid, force=True)
        
        self._watchdog_running = False
    
    # ===== Internal Methods =====
    
    def _resolve_process(self, pid_or_name: Union[int, str]) -> Optional[ProcessInfo]:
        """Resolve PID or name to ProcessInfo."""
        if isinstance(pid_or_name, str):
            pid = self._names.get(pid_or_name)
            if pid is None:
                return None
        else:
            pid = pid_or_name
        
        return self._processes.get(pid)
    
    def _kill_process(self, pid: int, sig: int) -> bool:
        """Send signal to a process."""
        try:
            # Try to kill the process group first
            try:
                pgid = os.getpgid(pid)
                os.killpg(pgid, sig)
            except (ProcessLookupError, PermissionError):
                # Fall back to killing just the process
                os.kill(pid, sig)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return False
    
    def _is_process_alive(self, pid: int) -> bool:
        """Check if a process is still alive."""
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # Process exists but we can't signal it
    
    def _update_process_status(self, info: ProcessInfo):
        """Update process status from handle."""
        if not info.process:
            return
        
        poll_result = info.process.poll()
        if poll_result is not None:
            # Process has exited
            if info.status not in (ProcessStatus.STOPPED, ProcessStatus.CRASHED, ProcessStatus.TIMEOUT):
                info.exit_code = poll_result
                info.finished = datetime.now()
                info.status = ProcessStatus.CRASHED if poll_result != 0 else ProcessStatus.STOPPED
                
                # Trigger callback
                if info.on_exit:
                    try:
                        info.on_exit(info.pid, poll_result)
                    except Exception:
                        pass
        elif info.status == ProcessStatus.STARTING:
            # Mark as running once we confirm it's alive
            info.status = ProcessStatus.RUNNING
    
    def _cleanup_process(self, pid: int):
        """Remove a process from tracking."""
        with self._lock:
            info = self._processes.pop(pid, None)
            if info and info.name:
                self._names.pop(info.name, None)
    
    def _timeout_process(self, pid: int):
        """Handle process timeout."""
        info = self._processes.get(pid)
        if info and info.status in (ProcessStatus.STARTING, ProcessStatus.RUNNING):
            info.status = ProcessStatus.TIMEOUT
            self._kill_process(pid, signal.SIGTERM)
    
    def _read_output(self, info: ProcessInfo):
        """Background thread to read process output."""
        try:
            while info.process and info.process.poll() is None:
                if info.process.stdout:
                    line = info.process.stdout.readline()
                    if line:
                        decoded = line.decode('utf-8', errors='replace')
                        with self._lock:
                            info.output_buffer.append(decoded)
                            # Keep last 500 lines
                            if len(info.output_buffer) > 500:
                                info.output_buffer = info.output_buffer[-500:]
            
            # Read remaining output after process exits
            if info.process and info.process.stdout:
                remaining = info.process.stdout.read()
                if remaining:
                    decoded = remaining.decode('utf-8', errors='replace')
                    with self._lock:
                        info.output_buffer.append(decoded)
                        
        except Exception:
            pass
    
    def _ensure_watchdog(self):
        """Start watchdog thread if not running."""
        if self._watchdog_running:
            return
        
        self._watchdog_running = True
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()
    
    def _watchdog_loop(self):
        """Watchdog thread to monitor process status."""
        while self._watchdog_running:
            try:
                with self._lock:
                    for info in list(self._processes.values()):
                        self._update_process_status(info)
            except Exception:
                pass
            time.sleep(1)
    
    @staticmethod
    def _port_is_free(host: str, port: int) -> bool:
        """Check if a port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
            return True
        except OSError:
            return False


# ===== Global ProcessManager Instance =====

def get_process_manager() -> ProcessManager:
    """Get the global ProcessManager instance."""
    return ProcessManager.instance()


# ===== Helper Functions =====

def _port_is_free(host: str, port: int) -> bool:
    """Check if a port is available."""
    return ProcessManager._port_is_free(host, port)


# ===== Find Free Port Tool =====

class FindFreePortTool(BaseTool):
    """
    Find an available TCP port on localhost.
    """

    NAME = "find_free_port"

    DESCRIPTION = """Find an available TCP port on localhost.

Use this when you need to choose a port and want to avoid conflicts.

Examples:
  find_free_port()  -> returns a free port in 8000-8999 (preferred range)
  find_free_port(preferred=[8000,8001,8002]) -> pick first free preferred
  find_free_port(range_start=3000, range_end=3999)
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
                    "preferred": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Preferred ports to try first (in order)."
                    },
                    "range_start": {
                        "type": "integer",
                        "description": "Start of range to search (inclusive). Default: 8000"
                    },
                    "range_end": {
                        "type": "integer",
                        "description": "End of range to search (inclusive). Default: 8999"
                    },
                    "host": {
                        "type": "string",
                        "description": "Host/IP to bind for availability check. Default: 127.0.0.1"
                    }
                },
                "required": []
            }
        )

    def execute(
        self,
        preferred: Optional[List[int]] = None,
        range_start: int = 8000,
        range_end: int = 8999,
        host: str = "127.0.0.1",
    ) -> ToolResult:
        preferred = preferred or []
        for p in preferred:
            if isinstance(p, int) and 1 <= p <= 65535 and _port_is_free(host, p):
                return ToolResult.ok({"port": p, "info": f"Selected free preferred port {p}"})

        for p in range(range_start, range_end + 1):
            if _port_is_free(host, p):
                return ToolResult.ok({"port": p, "info": f"Selected free port {p} in range {range_start}-{range_end}"})

        return ToolResult.fail(f"No free port found in range {range_start}-{range_end} (host={host})")


# ===== Execute Bash Tool =====

class ExecuteBashTool(BaseTool):
    """
    Execute shell commands with timeout support.
    For background processes, use RunBackgroundTool instead.
    """
    
    NAME = "execute_bash"
    
    DESCRIPTION = """Execute a bash command and wait for completion.

Features:
* Commands run in the workspace directory (or specified cwd)
* Default timeout: 1200 seconds (20 min, for long builds/installs)
* Use cwd parameter for subdirectories

Examples:
    execute_bash("ls -la")
    execute_bash("npm install", cwd="app/backend")
    execute_bash("docker compose build")

DO NOT USE execute_bash FOR:
1. **Server commands** - Will block forever!
   - node server.js, npm start, npm run dev, python app.py
   - node -e "require('./server')", node -e "const app=require('./app')"
   - uvicorn, gunicorn, flask run, http-server
   
2. **Long-running/watch processes** - Will timeout!
   - npm run watch, nodemon, tsc --watch, tail -f
   - docker compose up (without -d)

═══════════════════════════════════════════════════════════════════
USE THESE TOOLS INSTEAD FOR SERVERS & LONG-RUNNING PROCESSES:
═══════════════════════════════════════════════════════════════════

1. **run_background(command, cwd, name, port, wait_seconds, timeout)**
   Start a command in background with process tracking.
   
   Examples:
     run_background("npm start", port=3000, name="api", cwd="app/backend")
     run_background("npm run dev", port=5173, name="frontend", cwd="app/frontend")
     run_background("npm run build", name="build", cwd="app/frontend")

2. **list_processes()**
   List all tracked background processes with status.

3. **get_process_output(process, lines=100)**
   Get stdout/stderr logs from a background process.
   
   Examples:
     get_process_output("api")           # By name
     get_process_output(12345, lines=50) # By PID, last 50 lines

4. **stop_process(process, force=False)**
   Stop a background process (SIGTERM, or SIGKILL if force=True).
   
   Examples:
     stop_process("api")              # Graceful stop
     stop_process("api", force=True)  # Force kill

5. **interrupt_process(process)**
   Send Ctrl+C (SIGINT) to a process for graceful shutdown.

6. **wait_for_process(process, timeout=300)**
   Wait for a background process to complete and get exit code.
   
   Example:
     run_background("npm run build", name="build", cwd="app/frontend")
     wait_for_process("build")  # Wait for build to finish

7. **find_free_port(preferred=[], range_start=8000, range_end=8999)**
   Find an available TCP port to avoid conflicts.
"""
    
    DEFAULT_TIMEOUT = 1200
    MAX_OUTPUT_LENGTH = 100000  # Increased for large outputs
    
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
                    "command": {
                        "type": "string",
                        "description": "Command to execute"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory relative to workspace (e.g., 'app/backend')"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": f"Timeout in seconds (default: {self.DEFAULT_TIMEOUT})"
                    }
                },
                "required": ["command"]
            }
        )
    
    def execute(
        self,
        command: str,
        cwd: str = None,
        timeout: int = None,
    ) -> ToolResult:
        import re
        
        command = command.strip()
        timeout = timeout or self.DEFAULT_TIMEOUT
        
        if not command:
            return ToolResult(success=False, error_message="Empty command")
        
        # Determine working directory
        work_dir = self.workspace.root
        
        if cwd:
            work_dir = self.workspace.resolve(cwd)
            if not work_dir.exists():
                return ToolResult(
                    success=False,
                    error_message=f"Working directory does not exist: {cwd}"
                )
        else:
            # Auto-extract from "cd xxx && ..." pattern
            cd_match = re.match(r'^cd\s+([^\s&;]+)\s*&&\s*(.+)$', command)
            if cd_match:
                cd_path = cd_match.group(1)
                actual_command = cd_match.group(2)
                
                if cd_path.startswith('/'):
                    try:
                        rel_path = Path(cd_path).relative_to(self.workspace.root)
                        work_dir = self.workspace.root / rel_path
                        command = actual_command
                    except ValueError:
                        pass
                else:
                    work_dir = self.workspace.resolve(cd_path)
                    if work_dir.exists():
                        command = actual_command
                    else:
                        work_dir = self.workspace.root
        
        # Detect commands that should use run_background
        # 1. Server commands (need port)
        server_patterns = [
            # node -e "..." with require('./server') or require('./app') anywhere in the string
            # Matches: node -e "require('./server')", node -e "const app=require('./server');..."
            (r'\bnode\s+-e\s+["\'].*require\s*\(\s*["\']\.?/?\.?/?server', "node-server"),
            (r'\bnode\s+-e\s+["\'].*require\s*\(\s*["\']\.?/?\.?/?app', "node-server"),
            # node server.js - direct file execution
            # Exclude: node -e/-p (inline scripts), node -c/--check (syntax check)
            (r'\bnode\b(?!\s+(-[epc]|--check)\b).*\b(server|app|index)\.js\b', "node-server"),
            (r'\bnpm\s+(start|run\s+(dev|start|serve))\b', "npm-server"),
            (r'\byarn\s+(start|dev|serve)\b', "yarn-server"),
            (r'\bpnpm\s+(start|dev|serve)\b', "pnpm-server"),
            # python app.py - but NOT python -c (inline scripts)
            (r'\bpython\b(?!\s+-c\b).*\b(app|main|server|run)\.py\b', "python-server"),
            (r'\bpython\s+-m\s+(http\.server|flask|uvicorn|gunicorn)', "python-server"),
            (r'\buvicorn\b', "uvicorn"),
            (r'\bgunicorn\b', "gunicorn"),
            (r'\bflask\s+run\b', "flask"),
            (r'\bhttp-server\b', "http-server"),
            (r'\bnpx\s+(serve|vite|next)\b', "npx-server"),
            (r'\bdocker\s+compose\s+up\b(?!.*--build)', "docker"),  # docker compose up without --build
        ]
        
        # 2. Long-running watch/daemon commands (no port, but still blocks)
        watch_patterns = [
            (r'\bnpm\s+run\s+(watch|dev:watch)\b', "watch"),
            (r'\bnodemon\b', "nodemon"),
            (r'\btsc\s+(-w|--watch)\b', "tsc-watch"),
            (r'\btail\s+-f\b', "tail"),
            (r'\bwatch\b', "watch"),
        ]
        
        # 3. Commands that are better done with dedicated tools (likely to timeout)
        use_tool_patterns = [
            # ANY eslint command - use lint() tool instead (handles config, faster, better timeout)
            (r'\b(npx\s+)?eslint\b', "lint", "Use lint(path) tool instead of running eslint directly. Example: lint('app/backend/server.js')"),
            # npm install without --prefer-offline or on large projects
            (r'\bnpm\s+install\b(?!.*--prefer-offline)', "install_dependencies", "Consider using install_dependencies() tool instead for better timeout handling."),
        ]
        
        import re as regex_module
        
        # Check for commands that should use dedicated tools
        for pattern, tool_name, suggestion in use_tool_patterns:
            if regex_module.search(pattern, command, regex_module.IGNORECASE):
                return ToolResult(
                    success=False,
                    error_message=f"SLOW COMMAND WARNING: This command may timeout!\n\n"
                                  f"Command: {command}\n\n"
                                  f"Suggestion: {suggestion}\n\n"
                                  f"If you really need to run this, use a longer timeout:\n"
                                  f"  execute_bash(\"{command}\", timeout=3600)"
                )
        
        # Check server patterns
        for pattern, name in server_patterns:
            if regex_module.search(pattern, command, regex_module.IGNORECASE):
                cwd_hint = cwd or '.'
                return ToolResult(
                    success=False,
                    error_message=f"SERVER COMMAND DETECTED: Use run_background() for servers!\n\n"
                                  f"Instead of:\n"
                                  f"  execute_bash(\"{command}\")\n\n"
                                  f"Use:\n"
                                  f"  run_background(\"{command}\", port=YOUR_PORT, name=\"{name}\", cwd=\"{cwd_hint}\")\n\n"
                                  f"Then monitor with:\n"
                                  f"  list_processes()           # See all processes\n"
                                  f"  get_process_output(\"{name}\")  # Get logs"
                )
        
        # Check watch patterns
        for pattern, name in watch_patterns:
            if regex_module.search(pattern, command, regex_module.IGNORECASE):
                cwd_hint = cwd or '.'
                return ToolResult(
                    success=False,
                    error_message=f"LONG-RUNNING COMMAND DETECTED: Use run_background()!\n\n"
                                  f"Instead of:\n"
                                  f"  execute_bash(\"{command}\")\n\n"
                                  f"Use:\n"
                                  f"  run_background(\"{command}\", name=\"{name}\", cwd=\"{cwd_hint}\")\n\n"
                                  f"Then monitor with:\n"
                                  f"  get_process_output(\"{name}\")  # Get output\n"
                                  f"  stop_process(\"{name}\")        # Stop when done"
                )
        
        return self._run_command(command, timeout, work_dir)
    
    def _run_command(self, command: str, timeout: int, work_dir: Path = None) -> ToolResult:
        work_dir = work_dir or self.workspace.root
        try:
            # Handle sudo commands
            if command.strip().startswith("sudo "):
                sudo_password = "Gthb20151043"
                modified_cmd = command.replace("sudo ", "sudo -S ", 1)
                result = subprocess.run(
                    modified_cmd,
                    shell=True,
                    input=sudo_password + "\n",
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(work_dir),
                    env={**os.environ, "PYTHONUNBUFFERED": "1"},
                    encoding='utf-8',
                    errors='replace',  # Handle non-UTF8 characters gracefully
                )
            else:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(work_dir),
                    env={**os.environ, "PYTHONUNBUFFERED": "1"},
                    encoding='utf-8',
                    errors='replace',  # Handle non-UTF8 characters gracefully
                )
            
            output = result.stdout + result.stderr
            if len(output) > self.MAX_OUTPUT_LENGTH:
                output = output[:self.MAX_OUTPUT_LENGTH] + "\n...[output truncated]..."
            
            is_success = result.returncode == 0
            return ToolResult(
                success=is_success,
                data={
                    "exit_code": result.returncode,
                    "cwd": str(work_dir),
                    "output": output or "(no output)",
                },
                error_message=None if is_success else f"Command failed (exit {result.returncode}): {output[:500] if output else 'no output'}"
            )
            
        except subprocess.TimeoutExpired as e:
            output = ""
            if e.stdout:
                output += e.stdout if isinstance(e.stdout, str) else e.stdout.decode()
            if e.stderr:
                output += e.stderr if isinstance(e.stderr, str) else e.stderr.decode()
            
            # Provide helpful suggestion based on command type
            cmd_short = command[:50] + "..." if len(command) > 50 else command
            suggestion = (
                f"TIMEOUT: Command exceeded {timeout}s limit.\n\n"
                f"If this is a long-running process, use run_background():\n"
                f"  run_background(\"{cmd_short}\", cwd=\"{work_dir.name}\")\n\n"
                f"Or increase timeout:\n"
                f"  execute_bash(\"{cmd_short}\", timeout={timeout * 2})"
            )
            
            return ToolResult(
                success=False,
                error_message=suggestion,
                data={
                    "exit_code": -1, 
                    "timed_out": True,
                    "timeout_seconds": timeout,
                    "partial_output": output[:2000] if output else "(no output before timeout)"
                }
            )
            
        except Exception as e:
            import traceback
            return ToolResult(
                success=False, 
                error_message=f"Execution error: {e}\n{traceback.format_exc()[:500]}"
            )


# ===== Execute IPython Tool =====

class ExecuteIPythonTool(BaseTool):
    """
    Execute Python code in an IPython-like environment.
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
                    result = eval(compile(code, f"<cell-{self._cell_count}>", "eval"), self._namespace)
                except SyntaxError:
                    exec(compile(code, f"<cell-{self._cell_count}>", "exec"), self._namespace)
                    result = None
                    
        except Exception as e:
            import traceback
            error = True
            stderr_capture.write(traceback.format_exc())
        
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
        output += "\n[Jupyter cwd: ./ (workspace root)]"
        
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
                    encoding='utf-8',
                    errors='replace',
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
                
                if not self.workspace.contains(target):
                    return ToolResult(success=False, error_message=f"Cannot cd outside workspace: {new_dir}")
                
                if target.is_dir():
                    return ToolResult(success=True, data=f"Changed to {target}")
                else:
                    return ToolResult(success=False, error_message=f"Not a directory: {new_dir}")
            except Exception as e:
                return ToolResult(success=False, error_message=f"cd error: {e}")
        
        elif line.startswith("%pwd"):
            # Return "./" to indicate workspace root - never expose absolute paths
            return ToolResult(success=True, data="./ (workspace root)")
        
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


# ===== Run Background Tool (Unified) =====

class RunBackgroundTool(BaseTool):
    """
    Start a command in the background with unified process tracking.
    
    This is the primary tool for running servers and background processes.
    """
    
    NAME = "run_background"
    
    DESCRIPTION = """Start a command in the background with process tracking.

Use this for:
* Starting servers (API, frontend, etc.)
* Long-running background processes
* Commands that need to run while you do other work

Parameters:
* command: The shell command to run
* cwd: Working directory (relative to workspace)
* name: Process name for easy reference (required for servers)
* port: Port number (for servers - will verify port opens)
* wait_seconds: Seconds to wait for port/startup (default: 10)
* timeout: Optional auto-kill after N seconds (for non-server processes)

Examples:
    # Start API server
    run_background("npm start", port=8000, name="api", cwd="app/backend")
    
    # Start frontend dev server
    run_background("npm run dev", port=3000, name="frontend", cwd="app/frontend")
    
    # Run background task
    run_background("npm run build", cwd="app/frontend")
    
    # With timeout (auto-kill after 60s)
    run_background("npm test", timeout=60, cwd="app/backend")

After starting, use these tools to manage:
    list_processes()              - See all processes
    get_process_output("api")     - Get logs from a process
    stop_process("api")           - Stop a process
    interrupt_process("api")      - Send Ctrl+C to a process
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
                    "command": {
                        "type": "string",
                        "description": "Command to run in background"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory relative to workspace"
                    },
                    "name": {
                        "type": "string",
                        "description": "Process name for reference (required for servers)"
                    },
                    "port": {
                        "type": "integer",
                        "description": "Port number to wait for (for servers)"
                    },
                    "wait_seconds": {
                        "type": "integer",
                        "description": "Seconds to wait for port/startup (default: 10)"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Auto-kill after N seconds (for non-server processes)"
                    }
                },
                "required": ["command"]
            }
        )
    
    def execute(
        self,
        command: str,
        cwd: str = None,
        name: str = None,
        port: int = None,
        wait_seconds: int = 10,
        timeout: int = None
    ) -> ToolResult:
        # Resolve working directory
        work_dir = self.workspace.root
        if cwd:
            work_dir = self.workspace.resolve(cwd)
            if not work_dir.exists():
                return ToolResult(
                    success=False,
                    error_message=f"Working directory does not exist: {cwd}"
                )
        
        # Determine process type
        process_type = ProcessType.SERVER if port else ProcessType.BACKGROUND
        
        # Generate name if not provided
        if not name and port:
            name = f"server-{port}"
        
        pm = get_process_manager()
        
        try:
            info = pm.start(
                command=command,
                cwd=str(work_dir),
                name=name,
                port=port,
                timeout=timeout,
                process_type=process_type,
            )
        except ValueError as e:
            return ToolResult(success=False, error_message=str(e))
        except RuntimeError as e:
            return ToolResult(success=False, error_message=str(e))
        
        # Wait for port to open (for servers)
        if port and wait_seconds > 0:
            start_time = time.time()
            port_ready = False
            
            while time.time() - start_time < wait_seconds:
                # Check if process died
                poll_result = info.process.poll() if info.process else None
                if poll_result is not None:
                    # Process exited - get logs
                    time.sleep(0.5)
                    early_output = pm.get_output(info.pid, lines=30)
                    pm._cleanup_process(info.pid)
                    return ToolResult(
                        success=False,
                        error_message=f"Process crashed on startup (exit code: {poll_result}).\nLogs:\n{early_output[:1500]}"
                    )
                
                # Check if port is listening
                if not _port_is_free("127.0.0.1", port):
                    port_ready = True
                    break
                
                time.sleep(0.5)
            
            if not port_ready:
                poll_result = info.process.poll() if info.process else None
                if poll_result is not None:
                    early_output = pm.get_output(info.pid, lines=30)
                    pm._cleanup_process(info.pid)
                    return ToolResult(
                        success=False,
                        error_message=f"Process crashed (exit code: {poll_result}).\nLogs:\n{early_output[:1500]}"
                    )
                # Process running but port not open yet
                return ToolResult(
                    success=True,
                    data={
                        "pid": info.pid,
                        "name": info.name,
                        "port": port,
                        "warning": f"Port {port} not open after {wait_seconds}s, but process is running",
                        "info": f"Started '{name or command[:50]}' (PID: {info.pid}). Check logs with get_process_output(\"{name or info.pid}\")"
                    }
                )
        
        # Update status
        info.status = ProcessStatus.RUNNING
        
        # Build success response
        response_data = {
            "pid": info.pid,
            "cwd": str(work_dir),
        }
        
        if name:
            response_data["name"] = name
        if port:
            response_data["port"] = port
        
        response_data["info"] = f"Started background process (PID: {info.pid})"
        if name:
            response_data["info"] = f"Started '{name}'" + (f" on port {port}" if port else "") + f" (PID: {info.pid})"
        
        response_data["info"] += f"\n\nManage with:\n"
        response_data["info"] += f"  list_processes()                - See all processes\n"
        response_data["info"] += f"  get_process_output(\"{name or info.pid}\")  - Get output\n"
        response_data["info"] += f"  stop_process(\"{name or info.pid}\")        - Stop process\n"
        response_data["info"] += f"  interrupt_process(\"{name or info.pid}\")   - Send Ctrl+C"
        
        return ToolResult(success=True, data=response_data)


# ===== Stop Process Tool =====

class StopProcessTool(BaseTool):
    """Stop a background process by PID or name."""
    
    NAME = "stop_process"
    
    DESCRIPTION = """Stop a background process.

Arguments:
* process: Process PID (number) or name (string)
* force: Use SIGKILL instead of SIGTERM (default: false)

Examples:
    stop_process("api")              # Stop by name
    stop_process(12345)              # Stop by PID
    stop_process("api", force=true)  # Force kill
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
                    "process": {
                        "type": ["string", "integer"],
                        "description": "Process name or PID"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Use SIGKILL instead of SIGTERM (default: false)"
                    }
                },
                "required": ["process"]
            }
        )
    
    def execute(self, process: Union[str, int], force: bool = False) -> ToolResult:
        pm = get_process_manager()
        
        info = pm._resolve_process(process)
        if not info:
            return ToolResult(
                success=False,
                error_message=f"Process not found: {process}"
            )
        
        pid = info.pid
        name = info.name
        
        if pm.stop(process, force=force):
            msg = f"Stopped process"
            if name:
                msg += f" '{name}'"
            msg += f" (PID: {pid})"
            return ToolResult(success=True, data=msg)
        else:
            return ToolResult(
                success=True,
                data=f"Process {process} was already stopped"
            )


# ===== Interrupt Process Tool =====

class InterruptProcessTool(BaseTool):
    """Send interrupt signal (Ctrl+C) to a background process."""
    
    NAME = "interrupt_process"
    
    DESCRIPTION = """Send interrupt signal (SIGINT/Ctrl+C) to a background process.

Use this when:
* A command is hanging and needs to be interrupted
* You want to gracefully stop a server
* You need to cancel a long-running operation

Arguments:
* process: Process PID (number) or name (string)

Examples:
    interrupt_process("api")     # Send Ctrl+C by name
    interrupt_process(12345)     # Send Ctrl+C by PID
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
                    "process": {
                        "type": ["string", "integer"],
                        "description": "Process name or PID"
                    }
                },
                "required": ["process"]
            }
        )
    
    def execute(self, process: Union[str, int]) -> ToolResult:
        pm = get_process_manager()
        
        info = pm._resolve_process(process)
        if not info:
            return ToolResult(
                success=False,
                error_message=f"Process not found: {process}"
            )
        
        if pm.interrupt(process):
            msg = f"Sent SIGINT (Ctrl+C) to"
            if info.name:
                msg += f" '{info.name}'"
            msg += f" (PID: {info.pid})"
            return ToolResult(success=True, data=msg)
        else:
            return ToolResult(
                success=False,
                error_message=f"Failed to send signal to process {process}"
            )


# ===== List Processes Tool =====

class ListProcessesTool(BaseTool):
    """List all background processes."""
    
    NAME = "list_processes"
    
    DESCRIPTION = """List all tracked background processes.

Shows:
* PID - Process ID
* Name - Process name (if set)
* Status - running, stopped, crashed
* Port - Port number (for servers)
* Command - The command that was run
* Started - When the process was started

Examples:
    list_processes()                  # List all processes
    list_processes(type="server")     # List only servers
    list_processes(type="background") # List only background tasks
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
                    "type": {
                        "type": "string",
                        "enum": ["all", "server", "background"],
                        "description": "Filter by process type (default: all)"
                    }
                }
            }
        )
    
    def execute(self, type: str = "all") -> ToolResult:
        pm = get_process_manager()
        
        if type == "server":
            processes = pm.list_by_type(ProcessType.SERVER)
        elif type == "background":
            processes = pm.list_by_type(ProcessType.BACKGROUND)
        else:
            processes = pm.list_all()
        
        if not processes:
            return ToolResult(
                success=True,
                data={"processes": {}, "summary": "No tracked processes"}
            )
        
        # Build summary
        lines = [f"Background Processes ({len(processes)} total):"]
        for pid, info in processes.items():
            status = info.get("status", "unknown").upper()
            name = info.get("name", "-")
            port = info.get("port", "-")
            cmd = info.get("command", "")[:50]
            
            status_emoji = "✓" if info.get("running") else "✗"
            
            line = f"  [{status_emoji}] PID {pid}"
            if name != "-":
                line += f" ({name})"
            if port != "-":
                line += f" ::{port}"
            line += f" [{status}]"
            line += f" - {cmd}..."
            
            lines.append(line)
        
        return ToolResult(
            success=True,
            data={
                "processes": processes,
                "count": len(processes),
                "summary": "\n".join(lines)
            }
        )


# ===== Get Process Output Tool =====

class GetProcessOutputTool(BaseTool):
    """Get output from a background process."""
    
    NAME = "get_process_output"
    
    DESCRIPTION = """Get recent output (stdout/stderr) from a background process.

Use this to:
* Check server logs for errors
* Debug why a process might have failed
* Monitor progress of long-running commands

Arguments:
* process: Process PID (number) or name (string)
* lines: Maximum lines to return (default: 100)

Examples:
    get_process_output("api")           # Get logs from 'api' server
    get_process_output(12345)           # Get logs by PID
    get_process_output("api", lines=50) # Get last 50 lines
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
                    "process": {
                        "type": ["string", "integer"],
                        "description": "Process name or PID"
                    },
                    "lines": {
                        "type": "integer",
                        "description": "Maximum lines to return (default: 100)"
                    }
                },
                "required": ["process"]
            }
        )
    
    def execute(self, process: Union[str, int], lines: int = 100) -> ToolResult:
        pm = get_process_manager()
        
        info = pm._resolve_process(process)
        if not info:
            return ToolResult(
                success=False,
                error_message=f"Process not found: {process}"
            )
        
        output = pm.get_output(process, lines=lines)
        status = pm.get_status(process)
        
        result_data = {
            "pid": info.pid,
            "status": status.get("status", "unknown") if status else "unknown",
            "running": status.get("running", False) if status else False,
            "lines": len(output.split('\n')),
            "output": output,
        }
        
        if info.name:
            result_data["name"] = info.name
        
        return ToolResult(success=True, data=result_data)


# ===== Wait For Process Tool =====

class WaitForProcessTool(BaseTool):
    """Wait for a background process to complete."""
    
    NAME = "wait_for_process"
    
    DESCRIPTION = """Wait for a background process to complete and return its exit code.

Use this when you need to:
* Wait for a build to complete before continuing
* Ensure a background task finishes successfully
* Get the exit code of a completed process

Arguments:
* process: Process PID (number) or name (string)
* timeout: Maximum seconds to wait (default: 300, 0 = wait forever)

Examples:
    wait_for_process("build-task")           # Wait for build to complete
    wait_for_process(12345, timeout=60)      # Wait max 60 seconds
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
                    "process": {
                        "type": ["string", "integer"],
                        "description": "Process name or PID"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum seconds to wait (default: 300)"
                    }
                },
                "required": ["process"]
            }
        )
    
    def execute(self, process: Union[str, int], timeout: int = 300) -> ToolResult:
        pm = get_process_manager()
        
        info = pm._resolve_process(process)
        if not info:
            return ToolResult(
                success=False,
                error_message=f"Process not found: {process}"
            )
        
        # Check if already finished
        status = pm.get_status(process)
        if status and not status.get("running"):
            output = pm.get_output(process, lines=50)
            return ToolResult(
                success=True,
                data={
                    "pid": info.pid,
                    "exit_code": status.get("exit_code"),
                    "status": "already_finished",
                    "output": output,
                }
            )
        
        # Wait for completion
        actual_timeout = timeout if timeout > 0 else None
        exit_code = pm.wait(process, timeout=actual_timeout)
        
        if exit_code is None:
            return ToolResult(
                success=False,
                error_message=f"Process did not complete within {timeout} seconds"
            )
        
        output = pm.get_output(process, lines=50)
        
        return ToolResult(
            success=exit_code == 0,
            data={
                "pid": info.pid,
                "exit_code": exit_code,
                "status": "completed",
                "success": exit_code == 0,
                "output": output,
            },
            error_message=None if exit_code == 0 else f"Process exited with code {exit_code}"
        )


# ===== Cleanup Ports Tool =====

class CleanupPortsTool(BaseTool):
    """Clean up ports by killing processes that occupy them."""
    
    NAME = "cleanup_ports"
    
    DESCRIPTION = """Clean up ports by killing processes that occupy them.

Use this when:
* Server fails to start due to "port already in use"
* Need to free up ports before starting fresh

Arguments:
* ports: List of port numbers to free up
* stop_all: Also stop all tracked processes (default: false)

Examples:
    cleanup_ports([3000, 8000])                # Kill processes on these ports
    cleanup_ports([3000], stop_all=true)       # Also stop all tracked processes
    cleanup_ports([], stop_all=true)           # Only stop tracked processes
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
                    "ports": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of ports to free up"
                    },
                    "stop_all": {
                        "type": "boolean",
                        "description": "Also stop all tracked processes (default: false)"
                    }
                },
                "required": ["ports"]
            }
        )
    
    def execute(self, ports: List[int] = None, stop_all: bool = False) -> ToolResult:
        pm = get_process_manager()
        results = []
        
        # Handle None or invalid ports
        if ports is None:
            ports = []
        if not isinstance(ports, list):
            ports = [ports] if isinstance(ports, int) else []
        
        # Stop all tracked processes if requested
        if stop_all:
            processes = pm.list_all()
            for pid, info in list(processes.items()):
                pm.stop(pid, force=True)
                results.append(f"Stopped tracked process {pid}" + (f" ({info.get('name')})" if info.get('name') else ""))
        
        # Clean up specified ports
        for port in ports:
            result = pm.cleanup_port(port)
            results.append(result)
        
        # Verify ports are free
        freed = []
        still_busy = []
        for port in ports:
            if _port_is_free("127.0.0.1", port):
                freed.append(port)
            else:
                still_busy.append(port)
        
        summary = f"Cleaned {len(freed)} ports"
        if still_busy:
            summary += f", {len(still_busy)} still busy: {still_busy}"
        
        is_success = len(still_busy) == 0 or len(ports) == 0
        
        return ToolResult(
            success=is_success,
            data={
                "freed": freed,
                "still_busy": still_busy,
                "actions": results,
                "summary": summary
            },
            error_message=None if is_success else f"Failed to free ports: {still_busy}"
        )


# ===== Test API Tool =====

class TestAPITool(BaseTool):
    """Test an HTTP API endpoint."""
    
    NAME = "test_api"
    
    DESCRIPTION = """Send HTTP request to test an API.

Examples:
    test_api("GET", "http://localhost:8000/health")
    test_api("POST", "http://localhost:8000/api/items", body='{"name": "test"}')
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
                    encoding='utf-8',
                    errors='replace',
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
                    encoding='utf-8',
                    errors='replace',
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
                    encoding='utf-8',
                    errors='replace',
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


# ===== Legacy Compatibility =====
# Keep old class names as aliases for backward compatibility

class ServerRegistry:
    """Legacy compatibility - use ProcessManager instead."""
    
    @staticmethod
    def get(name: str) -> Optional[dict]:
        pm = get_process_manager()
        info = pm._resolve_process(name)
        if info and info.process_type == ProcessType.SERVER:
            return info.to_dict()
        return None
    
    @staticmethod
    def get_all() -> Dict[str, dict]:
        pm = get_process_manager()
        servers = pm.list_by_type(ProcessType.SERVER)
        return {info.get("name", str(pid)): info for pid, info in servers.items() if info.get("name")}


class BackgroundProcessRegistry:
    """Legacy compatibility - use ProcessManager instead."""
    
    @staticmethod
    def get(pid: int) -> Optional[dict]:
        pm = get_process_manager()
        return pm.get_status(pid)
    
    @staticmethod
    def get_all() -> Dict[int, dict]:
        return get_process_manager().list_all()


# Legacy tool aliases
StartServerTool = RunBackgroundTool
StopServerTool = StopProcessTool
ListServersTool = ListProcessesTool
GetServerLogsTool = GetProcessOutputTool
KillProcessTool = StopProcessTool
ListBackgroundProcessesTool = ListProcessesTool
CheckProcessStatusTool = ListProcessesTool


# ===== Exports =====

__all__ = [
    # Core
    "ProcessManager",
    "ProcessInfo",
    "ProcessType",
    "ProcessStatus",
    "get_process_manager",
    
    # Primary Tools
    "ExecuteBashTool",
    "ExecuteIPythonTool",
    "FindFreePortTool",
    "RunBackgroundTool",
    "StopProcessTool",
    "InterruptProcessTool",
    "ListProcessesTool",
    "GetProcessOutputTool",
    "WaitForProcessTool",
    "CleanupPortsTool",
    "TestAPITool",
    "InstallDependenciesTool",
    
    # Legacy Aliases (backward compatibility)
    "StartServerTool",
    "StopServerTool",
    "ListServersTool",
    "GetServerLogsTool",
    "KillProcessTool",
    "ListBackgroundProcessesTool",
    "CheckProcessStatusTool",
    "ServerRegistry",
    "BackgroundProcessRegistry",
]
