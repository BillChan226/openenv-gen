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


def _run_compose(
    compose_file: Path,
    args: List[str],
    cwd: Path,
    timeout: int,
) -> subprocess.CompletedProcess:
    """Run `docker compose -f <file> ...`."""
    cmd = ["docker", "compose", "-f", str(compose_file)] + args
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _list_services(compose_file: Path, cwd: Path) -> List[str]:
    """List service names defined by the compose file."""
    try:
        result = _run_compose(compose_file, ["config", "--services"], cwd=cwd, timeout=30)
        if result.returncode != 0:
            return []
        return [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    except Exception:
        return []


def _canonicalize_service_name(service: str, available: List[str]) -> Optional[str]:
    """
    Map common synonyms (e.g., env -> env-adapter) and normalize separators so
    verifiers/agents can request 'env' even if compose uses 'env-adapter'.
    """
    if not service:
        return None

    if service in available:
        return service

    raw = service.strip()
    key = raw.lower().replace("_", "-")

    aliases = {
        "db": "db",
        "database": "db",
        "postgres": "db",
        "postgresql": "db",
        "backend": "backend",
        "api": "backend",
        "server": "backend",
        "frontend": "frontend",
        "web": "frontend",
        "ui": "frontend",
        "env": "env-adapter",
        "env-adapter": "env-adapter",
        "envadapter": "env-adapter",
        "env-adaptor": "env-adapter",
        "env-adapter-service": "env-adapter",
    }

    mapped = aliases.get(key, key).replace("_", "-")

    # Case-insensitive exact match
    for a in available:
        if a.lower() == mapped:
            return a
        if a.lower().replace("_", "-") == mapped:
            return a

    # If only one available service contains this token, pick it.
    token = mapped
    candidates = [a for a in available if token in a.lower().replace("_", "-")]
    if len(candidates) == 1:
        return candidates[0]

    return None

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
                f"Checked: docker/docker-compose.yml, docker/docker-compose.dev.yml, docker/docker-compose.prod.yml, docker-compose.yml"
            )

        try:
            args = ["build"]
            if no_cache:
                args.append("--no-cache")

            if service:
                available = _list_services(compose_file, cwd=self.workspace.root)
                canonical = _canonicalize_service_name(service, available) if available else service
                if available and not canonical:
                    return ToolResult.fail(
                        f"Unknown compose service '{service}'. Available services: {', '.join(available)}"
                    )
                args.append(canonical or service)

            result = _run_compose(compose_file, args, cwd=self.workspace.root, timeout=600)
            
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
            self.workspace.root / "docker/docker-compose.dev.yml",
            self.workspace.root / "docker/docker-compose.prod.yml",
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
                f"Checked: docker/docker-compose.yml, docker/docker-compose.dev.yml, docker/docker-compose.prod.yml, docker-compose.yml"
            )
        
        try:
            args = ["up", "-d"]
            if build:
                args.append("--build")
            if force_recreate:
                args.append("--force-recreate")

            if service:
                available = _list_services(compose_file, cwd=self.workspace.root)
                canonical = _canonicalize_service_name(service, available) if available else service
                if available and not canonical:
                    return ToolResult.fail(
                        f"Unknown compose service '{service}'. Available services: {', '.join(available)}"
                    )
                args.append(canonical or service)

            result = _run_compose(compose_file, args, cwd=self.workspace.root, timeout=300)
            
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
            self.workspace.root / "docker/docker-compose.dev.yml",
            self.workspace.root / "docker/docker-compose.prod.yml",
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
                f"Checked: docker/docker-compose.yml, docker/docker-compose.dev.yml, docker/docker-compose.prod.yml, docker-compose.yml"
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
            self.workspace.root / "docker/docker-compose.dev.yml",
            self.workspace.root / "docker/docker-compose.prod.yml",
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
                f"Checked: docker/docker-compose.yml, docker/docker-compose.dev.yml, docker/docker-compose.prod.yml, docker-compose.yml"
            )
        
        try:
            available = _list_services(compose_file, cwd=self.workspace.root)
            canonical = _canonicalize_service_name(service, available) if available else service
            if available and not canonical:
                return ToolResult.fail(
                    f"Unknown compose service '{service}'. Available services: {', '.join(available)}"
                )

            result = _run_compose(
                compose_file,
                ["logs", "--tail", str(tail), canonical or service],
                cwd=self.workspace.root,
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
            self.workspace.root / "docker/docker-compose.dev.yml",
            self.workspace.root / "docker/docker-compose.prod.yml",
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
                f"Checked: docker/docker-compose.yml, docker/docker-compose.dev.yml, docker/docker-compose.prod.yml, docker-compose.yml"
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
            self.workspace.root / "docker/docker-compose.dev.yml",
            self.workspace.root / "docker/docker-compose.prod.yml",
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
                f"Checked: docker/docker-compose.yml, docker/docker-compose.dev.yml, docker/docker-compose.prod.yml, docker-compose.yml"
            )

        try:
            available = _list_services(compose_file, cwd=self.workspace.root)
            canonical = _canonicalize_service_name(service, available) if available else service
            if available and not canonical:
                return ToolResult.fail(
                    f"Unknown compose service '{service}'. Available services: {', '.join(available)}"
                )

            result = _run_compose(
                compose_file,
                ["restart", canonical or service],
                cwd=self.workspace.root,
                timeout=60,
            )
            
            if result.returncode != 0:
                return ToolResult.fail(f"Restart failed: {result.stderr}")
            
            return ToolResult.ok(data={
                "service": canonical or service,
                "message": f"Service {canonical or service} restarted",
            })
        except Exception as e:
            return ToolResult.fail(f"Restart error: {e}")
    
    def _find_compose_file(self) -> Optional[Path]:
        candidates = [
            self.workspace.root / "docker/docker-compose.yml",
            self.workspace.root / "docker/docker-compose.dev.yml",
            self.workspace.root / "docker/docker-compose.prod.yml",
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

