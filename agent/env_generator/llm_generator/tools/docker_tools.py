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

# Import environment cache for avoiding repeated failures
try:
    from .runtime_tools import env_cache
except ImportError:
    env_cache = None


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
        encoding='utf-8',
        errors='replace',
    )


def _find_compose_file_global(workspace_root: Path) -> Optional[Path]:
    """
    Find docker-compose file - very forgiving, searches many locations.
    """
    # Try many possible locations
    candidates = [
        # Standard locations
        workspace_root / "docker/docker-compose.yml",
        workspace_root / "docker/docker-compose.dev.yml",
        workspace_root / "docker/docker-compose.prod.yml",
        workspace_root / "docker-compose.yml",
        workspace_root / "docker-compose.yaml",
        # Alternative locations
        workspace_root / "compose.yml",
        workspace_root / "compose.yaml",
        workspace_root / ".docker/docker-compose.yml",
        workspace_root / "infra/docker-compose.yml",
        workspace_root / "deploy/docker-compose.yml",
    ]
    for path in candidates:
        if path.exists():
            return path
    
    # Last resort: search recursively for any docker-compose file
    for pattern in ["**/docker-compose.yml", "**/docker-compose.yaml", "**/compose.yml"]:
        matches = list(workspace_root.glob(pattern))
        if matches:
            return matches[0]
    
    return None


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
        # Check environment cache - skip if Docker daemon was recently unavailable
        if env_cache:
            should_skip, reason = env_cache.should_skip("docker_daemon", cooldown_seconds=300)
            if should_skip:
                return ToolResult.fail(
                    f"{reason}\n"
                    "Docker daemon is not available. Either:\n"
                    "1. Start Docker Desktop/daemon\n"
                    "2. Wait 5 minutes for automatic retry\n"
                    "3. Use non-Docker testing (npm start, etc.)"
                )
        
        compose_file = self._find_compose_file()
        if not compose_file:
            return ToolResult.fail(
                "docker-compose.yml not found. "
                "Checked: docker/docker-compose.yml, docker/docker-compose.dev.yml, docker/docker-compose.prod.yml, docker-compose.yml"
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
                stderr_lower = (result.stderr or "").lower()
                # Detect Docker daemon unavailable
                if "cannot connect to the docker daemon" in stderr_lower or "docker.sock" in stderr_lower:
                    if env_cache:
                        env_cache.record_failure("docker_daemon", "Cannot connect to Docker daemon")
                    return ToolResult.fail(
                        f"Docker daemon unavailable:\n{result.stderr[:500]}\n\n"
                        "This failure has been cached. Will skip docker operations for 5 minutes.\n"
                        "Start Docker Desktop or use non-Docker testing."
                    )
                return ToolResult.fail(
                    f"Build failed:\n{result.stderr[:1000]}"
                )
            
            # Mark Docker as available on success
            if env_cache:
                env_cache.record_success("docker_daemon")
            
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
        return _find_compose_file_global(self.workspace.root)
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
                "docker-compose.yml not found. "
                "Checked: docker/docker-compose.yml, docker/docker-compose.dev.yml, docker/docker-compose.prod.yml, docker-compose.yml"
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
        return _find_compose_file_global(self.workspace.root)


class DockerDownTool(BaseTool):
    """Stop and remove Docker containers."""
    
    NAME = "docker_down"
    DESCRIPTION = """Stop and remove Docker containers.

Example:
  docker_down()
  docker_down(volumes=True)  # Also remove volumes
  docker_down(remove_orphans=True)  # Remove orphan containers from previous runs
  docker_down(volumes=True, remove_orphans=True)  # Full cleanup
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
                    "remove_orphans": {
                        "type": "boolean",
                        "description": "Remove orphan containers from previous runs (default: false). Use this when you see 'No such container' errors."
                    },
                },
                "required": [],
            },
        )
    
    async def execute(self, volumes: bool = False, remove_orphans: bool = False) -> ToolResult:
        compose_file = self._find_compose_file()
        if not compose_file:
            return ToolResult.fail(
                "docker-compose.yml not found. "
                "Checked: docker/docker-compose.yml, docker/docker-compose.dev.yml, docker/docker-compose.prod.yml, docker-compose.yml"
            )
        
        # Use docker compose (v2) instead of docker-compose
        cmd = ["docker", "compose", "-f", str(compose_file), "down"]
        
        if volumes:
            cmd.append("-v")
        
        if remove_orphans:
            cmd.append("--remove-orphans")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace.root),
                capture_output=True,
                text=True,
                timeout=60,
                encoding='utf-8',
                errors='replace',
            )
            
            return ToolResult.ok(data={
                "success": True,
                "message": "Containers stopped and removed",
            })
        except Exception as e:
            return ToolResult.fail(f"Down error: {e}")
    
    def _find_compose_file(self) -> Optional[Path]:
        return _find_compose_file_global(self.workspace.root)


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
                "docker-compose.yml not found. "
                "Checked: docker/docker-compose.yml, docker/docker-compose.dev.yml, docker/docker-compose.prod.yml, docker-compose.yml"
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
        return _find_compose_file_global(self.workspace.root)


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
                "docker-compose.yml not found. "
                "Checked: docker/docker-compose.yml, docker/docker-compose.dev.yml, docker/docker-compose.prod.yml, docker-compose.yml"
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
                encoding='utf-8',
                errors='replace',
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
        return _find_compose_file_global(self.workspace.root)


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
                "docker-compose.yml not found. "
                "Checked: docker/docker-compose.yml, docker/docker-compose.dev.yml, docker/docker-compose.prod.yml, docker-compose.yml"
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
        return _find_compose_file_global(self.workspace.root)


class DockerValidateTool(BaseTool):
    """Validate Docker configuration and build context paths."""
    
    NAME = "docker_validate"
    DESCRIPTION = """Validate docker-compose.yml configuration.

Checks:
- Whether build context paths exist and are correct
- Whether Dockerfiles exist in each context
- Whether source files would be included in builds

This is critical for debugging "placeholder" or stale container issues.

Example:
  docker_validate()
  docker_validate(fix=True)  # Auto-fix common path issues
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
                    "fix": {
                        "type": "boolean",
                        "description": "Auto-fix common path issues (default: false)"
                    },
                },
                "required": [],
            },
        )
    
    async def execute(self, fix: bool = False) -> ToolResult:
        compose_file = _find_compose_file_global(self.workspace.root)
        if not compose_file:
            return ToolResult.fail(
                "docker-compose.yml not found in workspace"
            )
        
        issues = []
        fixes_applied = []
        valid_services = []
        
        # Parse docker-compose.yml
        try:
            import yaml
            with open(compose_file, 'r') as f:
                compose_data = yaml.safe_load(f)
        except Exception as e:
            return ToolResult.fail(f"Failed to parse docker-compose.yml: {e}")
        
        services = compose_data.get('services', {})
        compose_dir = compose_file.parent
        
        for service_name, service_config in services.items():
            build_config = service_config.get('build', {})
            
            if isinstance(build_config, str):
                context_path = build_config
                dockerfile = "Dockerfile"
            elif isinstance(build_config, dict):
                context_path = build_config.get('context', '.')
                dockerfile = build_config.get('dockerfile', 'Dockerfile')
            else:
                continue  # No build config, probably uses image
            
            # Resolve context path relative to compose file location
            resolved_context = (compose_dir / context_path).resolve()
            
            # Check if context exists
            if not resolved_context.exists():
                # Check if using wrong relative path
                # Common mistake: ./app/X when it should be ../app/X
                alt_path = (compose_dir.parent / context_path.lstrip('./')).resolve()
                if alt_path.exists():
                    issues.append({
                        "service": service_name,
                        "issue": "WRONG_RELATIVE_PATH",
                        "current": context_path,
                        "expected": f"../{context_path.lstrip('./')}",
                        "detail": f"Context '{context_path}' resolves to non-existent '{resolved_context}'. "
                                  f"Correct path should be '../{context_path.lstrip('./')}' which exists at '{alt_path}'"
                    })
                    
                    if fix:
                        # Auto-fix the path
                        fixed_path = f"../{context_path.lstrip('./')}"
                        if isinstance(build_config, str):
                            services[service_name]['build'] = fixed_path
                        else:
                            services[service_name]['build']['context'] = fixed_path
                        fixes_applied.append({
                            "service": service_name,
                            "old": context_path,
                            "new": fixed_path
                        })
                else:
                    issues.append({
                        "service": service_name,
                        "issue": "CONTEXT_NOT_FOUND",
                        "path": context_path,
                        "detail": f"Build context '{context_path}' does not exist"
                    })
            else:
                # Context exists, check Dockerfile
                dockerfile_path = resolved_context / dockerfile
                if not dockerfile_path.exists():
                    issues.append({
                        "service": service_name,
                        "issue": "DOCKERFILE_NOT_FOUND",
                        "path": f"{context_path}/{dockerfile}",
                    })
                else:
                    # Check for key source files
                    key_files = []
                    if service_name in ['frontend', 'web', 'ui']:
                        key_files = ['package.json', 'src/App.jsx', 'src/main.jsx', 'index.html']
                    elif service_name in ['backend', 'api', 'server']:
                        key_files = ['package.json', 'server.js', 'app.js', 'index.js']
                    
                    missing_files = []
                    found_files = []
                    for kf in key_files:
                        if (resolved_context / kf).exists():
                            found_files.append(kf)
                        else:
                            # Try alternative
                            pass  # Some files are optional
                    
                    valid_services.append({
                        "service": service_name,
                        "context": context_path,
                        "dockerfile": f"{context_path}/{dockerfile}",
                        "source_files": found_files[:5],  # Limit
                    })
        
        # Apply fixes if requested
        if fix and fixes_applied:
            try:
                with open(compose_file, 'w') as f:
                    yaml.dump(compose_data, f, default_flow_style=False, sort_keys=False)
            except Exception as e:
                return ToolResult.fail(f"Failed to write fixes: {e}")
        
        # Summary
        if issues:
            result_data = {
                "valid": False,
                "issues": issues,
                "valid_services": valid_services,
                "message": f"Found {len(issues)} issue(s) in docker-compose.yml",
            }
            if fixes_applied:
                result_data["fixes_applied"] = fixes_applied
                result_data["message"] += f". Applied {len(fixes_applied)} fix(es)."
            
            return ToolResult.ok(data=result_data)
        else:
            return ToolResult.ok(data={
                "valid": True,
                "services": valid_services,
                "message": "All Docker configurations are valid",
            })


class DockerInspectImageTool(BaseTool):
    """Inspect files inside a Docker image."""
    
    NAME = "docker_inspect_image"
    DESCRIPTION = """Check if specific files exist inside a built Docker image.

Useful for debugging when containers show stale/placeholder content.
Verifies that source code was actually included in the Docker build.

Example:
  docker_inspect_image(service="frontend", paths=["src/App.jsx", "dist/index.html"])
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
                        "description": "Service name to inspect"
                    },
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Paths to check inside the container"
                    },
                },
                "required": ["service"],
            },
        )
    
    async def execute(self, service: str, paths: List[str] = None) -> ToolResult:
        compose_file = _find_compose_file_global(self.workspace.root)
        if not compose_file:
            return ToolResult.fail("docker-compose.yml not found")
        
        # Default paths to check based on service
        if not paths:
            if service in ['frontend', 'web', 'ui']:
                paths = [
                    "/usr/share/nginx/html/index.html",
                    "/usr/share/nginx/html/assets",
                    "/app/src/App.jsx",
                    "/app/dist/index.html",
        ]
            elif service in ['backend', 'api', 'server']:
                paths = [
                    "/app/server.js",
                    "/app/package.json",
                    "/app/routes",
                ]
            else:
                paths = ["/app"]
        
        # Get container ID for the service
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "ps", "-q", service],
                cwd=str(self.workspace.root),
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace',
            )
            container_id = result.stdout.strip()
            
            if not container_id:
                return ToolResult.fail(f"No running container for service '{service}'. Run docker_up first.")
            
            # Check each path
            found = []
            missing = []
            file_contents = {}
            
            for path in paths:
                check_result = subprocess.run(
                    ["docker", "exec", container_id, "test", "-e", path],
                    capture_output=True,
                    timeout=10,
                )
                
                if check_result.returncode == 0:
                    found.append(path)
                    
                    # For key files, get first few lines
                    if path.endswith(('.jsx', '.js', '.html', '.json')):
                        head_result = subprocess.run(
                            ["docker", "exec", container_id, "head", "-20", path],
                            capture_output=True,
                            text=True,
                            timeout=10,
                            encoding='utf-8',
                            errors='replace',
                        )
                        if head_result.returncode == 0:
                            file_contents[path] = head_result.stdout[:500]
                else:
                    missing.append(path)
            
            # Check for placeholder indicators
            is_placeholder = False
            placeholder_evidence = []
            
            for path, content in file_contents.items():
                if "scaffold" in content.lower() or "placeholder" in content.lower():
                    is_placeholder = True
                    placeholder_evidence.append(path)
            
            return ToolResult.ok(data={
                "service": service,
                "container_id": container_id[:12],
                "found_paths": found,
                "missing_paths": missing,
                "file_samples": file_contents,
                "is_placeholder": is_placeholder,
                "placeholder_evidence": placeholder_evidence,
                "recommendation": (
                    "REBUILD REQUIRED: Container has placeholder content. Run: docker_build(service='{}', no_cache=True) then docker_up(service='{}', force_recreate=True)".format(service, service)
                    if is_placeholder else
                    "Container appears to have actual source code"
                ),
            })
            
        except subprocess.TimeoutExpired:
            return ToolResult.fail("Command timed out")
        except Exception as e:
            return ToolResult.fail(f"Inspect error: {e}")


class EnvironmentStatusTool(BaseTool):
    """Check and manage environment status cache."""
    
    NAME = "check_environment"
    DESCRIPTION = """Check environment status and optionally reset failure cache.

Use this to:
- See which tools/services are unavailable (Docker, psql, etc.)
- Reset the failure cache to retry a failed operation
- Understand why certain operations are being skipped

Examples:
  check_environment()  # See current status
  check_environment(reset="docker_daemon")  # Force retry Docker operations
  check_environment(reset="all")  # Reset all caches
"""
    
    def __init__(self, **kwargs):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
    
    @property
    def tool_definition(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "type": "object",
                "properties": {
                    "reset": {
                        "type": "string",
                        "description": "Key to reset (e.g., 'docker_daemon', 'psql') or 'all' to reset everything"
                    }
                },
                "required": [],
            },
        )
    
    def execute(self, reset: str = None) -> ToolResult:
        if not env_cache:
            return ToolResult.ok(data={
                "info": "Environment cache not available",
                "status": {}
            })
        
        # Handle reset
        if reset:
            if reset.lower() == "all":
                env_cache.reset()
                return ToolResult.ok(data={
                    "reset": "all",
                    "info": "All environment caches reset. Operations will be retried.",
                    "status": {}
                })
            else:
                env_cache.reset(reset)
                return ToolResult.ok(data={
                    "reset": reset,
                    "info": f"Cache for '{reset}' reset. Will retry on next call.",
                    "status": env_cache.get_status()
                })
        
        # Get current status
        status = env_cache.get_status()
        
        # Build summary
        unavailable = [k for k, v in status.items() if not v.get("available", True)]
        
        return ToolResult.ok(data={
            "status": status,
            "unavailable": unavailable,
            "info": f"{len(unavailable)} services unavailable" if unavailable else "All services available",
            "hint": "Use check_environment(reset='key') to force retry" if unavailable else None
        })


def create_docker_tools(output_dir: str = None, workspace: Workspace = None) -> List[BaseTool]:
    """Create all Docker tools."""
    return [
        DockerBuildTool(output_dir=output_dir, workspace=workspace),
        DockerUpTool(output_dir=output_dir, workspace=workspace),
        DockerDownTool(output_dir=output_dir, workspace=workspace),
        DockerLogsTool(output_dir=output_dir, workspace=workspace),
        DockerStatusTool(output_dir=output_dir, workspace=workspace),
        DockerRestartTool(output_dir=output_dir, workspace=workspace),
        DockerValidateTool(output_dir=output_dir, workspace=workspace),
        DockerInspectImageTool(output_dir=output_dir, workspace=workspace),
        EnvironmentStatusTool(),
    ]

