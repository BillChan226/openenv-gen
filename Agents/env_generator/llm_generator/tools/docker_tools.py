"""
Docker Tools

Dedicated tools for Docker Compose operations:
- docker_build: Build images
- docker_up: Start containers
- docker_down: Stop containers
- docker_logs: View logs
- docker_status: Container status
- docker_restart: Restart services
"""

import asyncio
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tool import BaseTool, ToolResult, ToolCategory, create_tool_param
from workspace import Workspace


class DockerBuildTool(BaseTool):
    """Build Docker images using docker-compose."""
    
    NAME = "docker_build"
    DESCRIPTION = """Build Docker images for the project.

Can build all services or a specific service.
Uses docker-compose build.

Example:
  docker_build()  # Build all
  docker_build(service="backend", no_cache=True)
"""
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
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
                    "service": {
                        "type": "string",
                        "description": "Specific service to build (optional, builds all if not specified)"
                    },
                    "no_cache": {
                        "type": "boolean",
                        "description": "Build without cache (default: false)"
                    },
                },
                "required": [],
            },
        )
    
    async def execute(self, service: str = None, no_cache: bool = False) -> ToolResult:
        compose_file = self._find_compose_file()
        if not compose_file:
            return ToolResult.fail(
                f"docker-compose.yml not found in {self.workspace.root}. "
                f"Checked: docker/docker-compose.yml and docker-compose.yml"
            )
        
        # Use docker compose (v2) instead of docker-compose
        cmd = ["docker", "compose", "-f", str(compose_file), "build"]
        
        if no_cache:
            cmd.append("--no-cache")
        
        if service:
            cmd.append(service)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace.root),
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes
            )
            
            if result.returncode != 0:
                return ToolResult.fail(
                    f"Build failed:\n{result.stderr[:1000]}"
                )
            
            return ToolResult.ok(data={
                "success": True,
                "service": service or "all",
                "output": result.stdout[:500] if result.stdout else "Build completed",
            })
        except subprocess.TimeoutExpired:
            return ToolResult.fail("Build timed out after 10 minutes")
        except Exception as e:
            return ToolResult.fail(f"Build error: {e}")
    
    def _find_compose_file(self) -> Optional[Path]:
        """Find docker-compose.yml in project."""
        candidates = [
            self.workspace.root / "docker/docker-compose.yml",
            self.workspace.root / "docker-compose.yml",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None


class DockerUpTool(BaseTool):
    """Start Docker containers."""
    
    NAME = "docker_up"
    DESCRIPTION = """Start Docker containers using docker-compose up.

Starts containers in detached mode by default.

Example:
  docker_up()  # Start all
  docker_up(service="backend")
  docker_up(build=True)  # Build before starting
"""
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
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
                    "service": {
                        "type": "string",
                        "description": "Specific service to start"
                    },
                    "build": {
                        "type": "boolean",
                        "description": "Build images before starting (default: false)"
                    },
                    "force_recreate": {
                        "type": "boolean",
                        "description": "Force recreate containers (default: false)"
                    },
                },
                "required": [],
            },
        )
    
    async def execute(
        self,
        service: str = None,
        build: bool = False,
        force_recreate: bool = False,
    ) -> ToolResult:
        compose_file = self._find_compose_file()
        if not compose_file:
            return ToolResult.fail(
                f"docker-compose.yml not found in {self.workspace.root}. "
                f"Checked: docker/docker-compose.yml and docker-compose.yml"
            )
        
        # Use docker compose (v2) instead of docker-compose
        cmd = ["docker", "compose", "-f", str(compose_file), "up", "-d"]
        
        if build:
            cmd.append("--build")
        
        if force_recreate:
            cmd.append("--force-recreate")
        
        if service:
            cmd.append(service)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace.root),
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            if result.returncode != 0:
                return ToolResult.fail(
                    f"Failed to start:\n{result.stderr[:1000]}"
                )
            
            return ToolResult.ok(data={
                "success": True,
                "service": service or "all",
                "message": "Containers started successfully",
            })
        except subprocess.TimeoutExpired:
            return ToolResult.fail("Start timed out")
        except Exception as e:
            return ToolResult.fail(f"Start error: {e}")
    
    def _find_compose_file(self) -> Optional[Path]:
        candidates = [
            self.workspace.root / "docker/docker-compose.yml",
            self.workspace.root / "docker-compose.yml",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None


class DockerDownTool(BaseTool):
    """Stop and remove Docker containers."""
    
    NAME = "docker_down"
    DESCRIPTION = """Stop and remove Docker containers.

Example:
  docker_down()
  docker_down(volumes=True)  # Also remove volumes
"""
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
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
                    "volumes": {
                        "type": "boolean",
                        "description": "Also remove volumes (default: false)"
                    },
                },
                "required": [],
            },
        )
    
    async def execute(self, volumes: bool = False) -> ToolResult:
        compose_file = self._find_compose_file()
        if not compose_file:
            return ToolResult.fail(
                f"docker-compose.yml not found in {self.workspace.root}. "
                f"Checked: docker/docker-compose.yml and docker-compose.yml"
            )
        
        # Use docker compose (v2) instead of docker-compose
        cmd = ["docker", "compose", "-f", str(compose_file), "down"]
        
        if volumes:
            cmd.append("-v")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace.root),
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            return ToolResult.ok(data={
                "success": True,
                "message": "Containers stopped and removed",
            })
        except Exception as e:
            return ToolResult.fail(f"Down error: {e}")
    
    def _find_compose_file(self) -> Optional[Path]:
        candidates = [
            self.workspace.root / "docker/docker-compose.yml",
            self.workspace.root / "docker-compose.yml",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None


class DockerLogsTool(BaseTool):
    """Get logs from Docker containers."""
    
    NAME = "docker_logs"
    DESCRIPTION = """Get logs from a Docker container.

Example:
  docker_logs(service="backend")
  docker_logs(service="backend", tail=50)
"""
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
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
                    "service": {
                        "type": "string",
                        "description": "Service name to get logs from"
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Number of lines to show (default: 100)"
                    },
                },
                "required": ["service"],
            },
        )
    
    async def execute(self, service: str, tail: int = 100) -> ToolResult:
        compose_file = self._find_compose_file()
        if not compose_file:
            return ToolResult.fail(
                f"docker-compose.yml not found in {self.workspace.root}. "
                f"Checked: docker/docker-compose.yml and docker-compose.yml"
            )
        
        # Use docker compose (v2) instead of docker-compose
        cmd = [
            "docker", "compose", "-f", str(compose_file),
            "logs", "--tail", str(tail), service
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace.root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            logs = result.stdout or result.stderr or "(no logs)"
            
            return ToolResult.ok(data={
                "service": service,
                "logs": logs[:5000],  # Limit output
                "lines": len(logs.split("\n")),
            })
        except Exception as e:
            return ToolResult.fail(f"Logs error: {e}")
    
    def _find_compose_file(self) -> Optional[Path]:
        candidates = [
            self.workspace.root / "docker/docker-compose.yml",
            self.workspace.root / "docker-compose.yml",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None


class DockerStatusTool(BaseTool):
    """Get status of Docker containers."""
    
    NAME = "docker_status"
    DESCRIPTION = """Check status of all Docker containers.

Returns running/stopped status for each service.

Example:
  docker_status()
"""
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
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
                "properties": {},
                "required": [],
            },
        )
    
    async def execute(self) -> ToolResult:
        compose_file = self._find_compose_file()
        if not compose_file:
            return ToolResult.fail(
                f"docker-compose.yml not found in {self.workspace.root}. "
                f"Checked: docker/docker-compose.yml and docker-compose.yml"
            )
        
        # Use docker compose (v2) instead of docker-compose
        cmd = ["docker", "compose", "-f", str(compose_file), "ps"]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace.root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            # Parse output
            lines = result.stdout.strip().split("\n")
            services = []
            
            for line in lines[1:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[0]
                        status = "running" if "Up" in line else "stopped"
                        services.append({"name": name, "status": status})
            
            return ToolResult.ok(data={
                "services": services,
                "raw": result.stdout[:1000],
            })
        except Exception as e:
            return ToolResult.fail(f"Status error: {e}")
    
    def _find_compose_file(self) -> Optional[Path]:
        candidates = [
            self.workspace.root / "docker/docker-compose.yml",
            self.workspace.root / "docker-compose.yml",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None


class DockerRestartTool(BaseTool):
    """Restart Docker containers."""
    
    NAME = "docker_restart"
    DESCRIPTION = """Restart a Docker service.

Example:
  docker_restart(service="backend")
"""
    
    def __init__(self, output_dir: str = None, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
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
                    "service": {
                        "type": "string",
                        "description": "Service to restart"
                    },
                },
                "required": ["service"],
            },
        )
    
    async def execute(self, service: str) -> ToolResult:
        compose_file = self._find_compose_file()
        if not compose_file:
            return ToolResult.fail(
                f"docker-compose.yml not found in {self.workspace.root}. "
                f"Checked: docker/docker-compose.yml and docker-compose.yml"
            )
        
        # Use docker compose (v2) instead of docker-compose
        cmd = ["docker", "compose", "-f", str(compose_file), "restart", service]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace.root),
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode != 0:
                return ToolResult.fail(f"Restart failed: {result.stderr}")
            
            return ToolResult.ok(data={
                "service": service,
                "message": f"Service {service} restarted",
            })
        except Exception as e:
            return ToolResult.fail(f"Restart error: {e}")
    
    def _find_compose_file(self) -> Optional[Path]:
        candidates = [
            self.workspace.root / "docker/docker-compose.yml",
            self.workspace.root / "docker-compose.yml",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None


def create_docker_tools(output_dir: str = None, workspace: Workspace = None) -> List[BaseTool]:
    """Create all Docker tools."""
    return [
        DockerBuildTool(output_dir=output_dir, workspace=workspace),
        DockerUpTool(output_dir=output_dir, workspace=workspace),
        DockerDownTool(output_dir=output_dir, workspace=workspace),
        DockerLogsTool(output_dir=output_dir, workspace=workspace),
        DockerStatusTool(output_dir=output_dir, workspace=workspace),
        DockerRestartTool(output_dir=output_dir, workspace=workspace),
    ]

