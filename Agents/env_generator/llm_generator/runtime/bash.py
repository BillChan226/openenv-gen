"""
BashSession - Persistent bash shell execution

Inspired by OpenHands BashSession using subprocess with persistent state.
"""

import os
import signal
import asyncio
import subprocess
import time
import threading
from pathlib import Path
from typing import Optional, Tuple, Union
from dataclasses import dataclass
from queue import Queue, Empty
import logging

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from events.action import CmdRunAction
from events.observation import CmdOutputObservation, ErrorObservation

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of command execution."""
    output: str
    exit_code: int
    timed_out: bool = False
    duration: float = 0.0


class BashSession:
    """
    Persistent bash session with timeout and interactive support.
    
    Features:
    - Persistent environment (env vars, cwd persist between commands)
    - Timeout handling (soft and hard)
    - Interactive input support (Ctrl+C, etc.)
    - Background process tracking
    """
    
    DEFAULT_TIMEOUT = 30
    POLL_INTERVAL = 0.1
    MAX_OUTPUT_SIZE = 50000
    
    def __init__(self, work_dir: str = None, timeout: int = None):
        self.work_dir = Path(work_dir) if work_dir else Path.cwd()
        self.default_timeout = timeout or self.DEFAULT_TIMEOUT
        self._cwd = str(self.work_dir.absolute())
        
        self._process: Optional[subprocess.Popen] = None
        self._output_queue: Queue = Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._is_running = False
        self._last_command: str = ""
        self._initialized = False
        
        # Background processes tracking
        self._background_pids: set = set()
    
    def initialize(self) -> None:
        """Initialize the bash session."""
        if self._initialized:
            return
        
        # Start persistent bash process
        self._process = subprocess.Popen(
            ["/bin/bash", "--norc", "--noprofile"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self._cwd,
            env={**os.environ, "PS1": "", "PS2": ""},
            bufsize=0,
            universal_newlines=False,
        )
        
        # Start output reader thread
        self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self._reader_thread.start()
        
        # Set up bash environment
        self._send_command("set +o history")  # Disable history
        self._send_command(f"cd {self._cwd}")
        self._initialized = True
        
        logger.info(f"BashSession initialized in {self._cwd}")
    
    def _read_output(self) -> None:
        """Background thread to read process output."""
        try:
            while self._process and self._process.poll() is None:
                if self._process.stdout:
                    byte = self._process.stdout.read(1)
                    if byte:
                        self._output_queue.put(byte)
        except Exception as e:
            logger.error(f"Output reader error: {e}")
    
    def _send_command(self, command: str) -> None:
        """Send a command to the bash process."""
        if self._process and self._process.stdin:
            self._process.stdin.write(f"{command}\n".encode())
            self._process.stdin.flush()
    
    def _collect_output(self, timeout: float = 0.5) -> str:
        """Collect output from the queue."""
        output_bytes = []
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            try:
                byte = self._output_queue.get(timeout=0.01)
                output_bytes.append(byte)
            except Empty:
                if output_bytes and time.time() > deadline - 0.1:
                    break
        
        return b"".join(output_bytes).decode("utf-8", errors="replace")
    
    @property
    def cwd(self) -> str:
        """Get current working directory."""
        return self._cwd
    
    async def execute(self, action: CmdRunAction) -> Union[CmdOutputObservation, ErrorObservation]:
        """
        Execute a command.
        
        Args:
            action: CmdRunAction with command to execute
            
        Returns:
            CmdOutputObservation or ErrorObservation
        """
        if not self._initialized:
            self.initialize()
        
        command = action.command.strip()
        timeout = action.timeout or self.default_timeout
        
        # Handle empty command
        if not command:
            return ErrorObservation(
                content="Empty command",
                cause=action.id,
            )
        
        # Handle special keys (Ctrl+C, etc.)
        if action.is_input:
            return await self._handle_input(action)
        
        # Execute command with marker for completion detection
        marker = f"__CMD_DONE_{time.time_ns()}__"
        full_command = f"{command}; echo {marker} $?"
        
        start_time = time.time()
        self._last_command = command
        self._is_running = True
        
        # Send command
        self._send_command(full_command)
        
        # Wait for completion
        output_parts = []
        timed_out = False
        exit_code = -1
        
        while self._is_running:
            await asyncio.sleep(self.POLL_INTERVAL)
            
            # Collect output
            new_output = self._collect_output(0.1)
            if new_output:
                output_parts.append(new_output)
            
            # Check for completion marker
            full_output = "".join(output_parts)
            if marker in full_output:
                # Extract exit code and clean output
                marker_pos = full_output.rfind(marker)
                output = full_output[:marker_pos].strip()
                
                # Parse exit code
                after_marker = full_output[marker_pos + len(marker):].strip()
                try:
                    exit_code = int(after_marker.split()[0]) if after_marker else 0
                except (ValueError, IndexError):
                    exit_code = 0
                
                self._is_running = False
                break
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                timed_out = True
                self._is_running = False
                break
        
        duration = time.time() - start_time
        output = "".join(output_parts)
        
        # Clean up output (remove marker line)
        if marker in output:
            output = output[:output.rfind(marker)].strip()
        
        # Truncate if too long
        if len(output) > self.MAX_OUTPUT_SIZE:
            output = output[:self.MAX_OUTPUT_SIZE] + "\n...[output truncated]..."
        
        # Update cwd if command was cd
        if command.startswith("cd "):
            self._update_cwd()
        
        # Build observation
        if timed_out:
            output += f"\n[Command timed out after {timeout}s. Send Ctrl+C to interrupt or wait for completion.]"
            exit_code = -1
        
        return CmdOutputObservation(
            content=output,
            command=command,
            exit_code=exit_code,
            working_dir=self._cwd,
            duration=duration,
            timed_out=timed_out,
            cause=action.id,
            tool_call_id=action.tool_call_id,
        )
    
    async def _handle_input(self, action: CmdRunAction) -> CmdOutputObservation:
        """Handle input to running process (Ctrl+C, etc.)."""
        command = action.command.strip()
        
        if command == "C-c":
            # Send SIGINT
            if self._process:
                self._process.send_signal(signal.SIGINT)
            return CmdOutputObservation(
                content="Sent SIGINT (Ctrl+C)",
                command="C-c",
                exit_code=130,
                cause=action.id,
            )
        
        elif command == "C-d":
            # Send EOF
            if self._process and self._process.stdin:
                self._process.stdin.close()
            return CmdOutputObservation(
                content="Sent EOF (Ctrl+D)",
                command="C-d",
                exit_code=0,
                cause=action.id,
            )
        
        elif command == "C-z":
            # Send SIGTSTP
            if self._process:
                self._process.send_signal(signal.SIGTSTP)
            return CmdOutputObservation(
                content="Sent SIGTSTP (Ctrl+Z)",
                command="C-z",
                exit_code=0,
                cause=action.id,
            )
        
        else:
            # Send as stdin input
            if self._process and self._process.stdin:
                self._process.stdin.write(f"{command}\n".encode())
                self._process.stdin.flush()
            return CmdOutputObservation(
                content=f"Sent input: {command}",
                command=command,
                exit_code=0,
                cause=action.id,
            )
    
    def _update_cwd(self) -> None:
        """Update current working directory from bash."""
        marker = f"__PWD_{time.time_ns()}__"
        self._send_command(f"echo {marker} $(pwd)")
        
        time.sleep(0.2)
        output = self._collect_output(0.3)
        
        if marker in output:
            after_marker = output[output.find(marker) + len(marker):].strip()
            if after_marker:
                new_cwd = after_marker.split()[0]
                if os.path.isdir(new_cwd):
                    self._cwd = new_cwd
    
    def close(self) -> None:
        """Close the bash session."""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        self._initialized = False
        logger.info("BashSession closed")
    
    def __del__(self):
        self.close()


# Convenience function for simple execution
async def run_bash(command: str, cwd: str = None, timeout: int = 30) -> CommandResult:
    """
    Simple helper to run a bash command.
    
    Args:
        command: Command to execute
        cwd: Working directory
        timeout: Timeout in seconds
        
    Returns:
        CommandResult with output and exit code
    """
    session = BashSession(work_dir=cwd, timeout=timeout)
    try:
        action = CmdRunAction(command=command, timeout=timeout)
        result = await session.execute(action)
        
        if isinstance(result, CmdOutputObservation):
            return CommandResult(
                output=result.content,
                exit_code=result.exit_code,
                timed_out=result.timed_out,
                duration=result.duration,
            )
        else:
            return CommandResult(
                output=result.content,
                exit_code=1,
            )
    finally:
        session.close()

