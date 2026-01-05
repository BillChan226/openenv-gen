"""
Orchestrator - Multi-Agent Coordination

Coordinates agents via MessageBus:
1. Creates agents
2. Starts their message loops
3. Sends tasks to coordinate phases
4. Waits for completion
"""

import asyncio
import json
import logging
import socket
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.communication import MessageBus
from utils.config import LLMConfig, AgentConfig, ExecutionConfig
from utils.llm import LLM

from .workspace_manager import WorkspaceManager
from .agents import (
    DatabaseAgent,
    BackendAgent,
    FrontendAgent,
    DesignAgent,
    UserAgent,
    TaskAgent,
)

# Import existing systems
import sys
_llm_gen_dir = Path(__file__).parent.parent
if str(_llm_gen_dir) not in sys.path:
    sys.path.insert(0, str(_llm_gen_dir))

from checkpoint import CheckpointManager
from context import GenerationContext
from progress import EventEmitter as ProgressEmitter, EventType, ConsoleListener


@dataclass
class GenerationResult:
    """Result of environment generation."""
    success: bool
    project_path: str
    phases_completed: List[str] = field(default_factory=list)
    issues_found: int = 0
    issues_fixed: int = 0
    duration: float = 0.0
    summary: str = ""


# Track allocated ports to avoid duplicates
_allocated_ports: set = set()

def find_free_port(preferred: List[int] = None, range_start: int = 8000, range_end: int = 9000) -> int:
    """Find an available port that hasn't been allocated yet."""
    global _allocated_ports
    preferred = preferred or []
    
    for port in preferred:
        if port in _allocated_ports:
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                _allocated_ports.add(port)
                return port
        except OSError:
            pass
    
    for port in range(range_start, range_end):
        if port in _allocated_ports:
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                _allocated_ports.add(port)
                return port
        except OSError:
            pass
    
    raise RuntimeError(f"No free port found in range {range_start}-{range_end}")

def reset_allocated_ports():
    """Reset allocated ports (call at start of new generation)."""
    global _allocated_ports
    _allocated_ports = set()


class Orchestrator:
    """Multi-Agent Orchestrator."""
    
    def __init__(
        self,
        llm_config: LLMConfig,
        output_dir: Path,
        name: str = "generated_app",
        reference_images: List[str] = None,
        verbose: bool = False,
    ):
        self._logger = logging.getLogger("Orchestrator")
        if verbose:
            self._logger.setLevel(logging.DEBUG)
        
        # LLM
        self.llm_config = llm_config
        self.llm = LLM(llm_config)
        
        # Output
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._reference_images = reference_images or []
        # Copy reference images into workspace screenshots/ for agents to use
        try:
            screenshots_dir = self.output_dir / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            for ref in self._reference_images:
                src = Path(ref)
                if src.exists():
                    dest = screenshots_dir / src.name
                    if not dest.exists():
                        dest.write_bytes(src.read_bytes())
        except Exception as copy_err:
            self._logger.warning(f"Failed to copy reference images: {copy_err}")
        
        # Dynamic ports - reset allocation tracking first
        reset_allocated_ports()
        self.context = GenerationContext(
            name=name,
            api_port=find_free_port([3000, 3001]),
            ui_port=find_free_port([8080, 8081]),
        )
        self.context.db_port = find_free_port([5432, 5433])
        self.context.backend_internal_port = find_free_port([8080], range_start=8080, range_end=8100)
        
        self._logger.info(f"Ports: API={self.context.api_port}, UI={self.context.ui_port}, DB={self.context.db_port}")
        
        # Infrastructure
        self.workspace = WorkspaceManager(self.output_dir)
        self.message_bus = MessageBus()
        self.progress = ProgressEmitter()
        self.progress.on_all(ConsoleListener())
        self.checkpoint = CheckpointManager(self.output_dir / ".checkpoint")
        
        # Agents
        self._agents: Dict[str, Any] = {}
        self._agent_tasks: Dict[str, asyncio.Task] = {}
        
        # Tracking
        self._issues_found = 0
        self._issues_fixed = 0
    
    def _create_agents(self):
        """Create all agents."""
        agent_classes = {
            "user": UserAgent,
            "design": DesignAgent,
            "database": DatabaseAgent,
            "backend": BackendAgent,
            "frontend": FrontendAgent,
            "task": TaskAgent,
        }
        
        # Task timeout settings (in seconds)
        # UserAgent needs longer timeout as it coordinates entire project
        task_timeouts = {
            "user": 7200,      # 2 hours - coordinates whole project
            "design": 3600,    # 1 hour - generates large spec files
            "database": 1800,  # 30 min
            "backend": 3600,   # 1 hour - generates many files
            "frontend": 3600,  # 1 hour - generates many files
            "task": 3600,      # 1 hour - generates tasks/trajectories/judges
        }
        
        for agent_id, cls in agent_classes.items():
            # Create ExecutionConfig with appropriate timeout
            exec_config = ExecutionConfig(
                task_timeout=task_timeouts.get(agent_id, 1800),
                max_retries=2,
            )
            config = AgentConfig(
                agent_id=agent_id, 
                agent_name=f"{agent_id.title()} Agent",
                execution=exec_config,
            )
            include_vision = agent_id in ["user", "frontend"]
            
            agent = cls(
                config=config,
                llm=self.llm,
                workspace_manager=self.workspace,
                include_vision=include_vision,
            )
            agent.set_gen_context(self.context)
            agent.set_message_bus(self.message_bus)
            self._agents[agent_id] = agent
            self._logger.info(f"Created agent: {agent_id}")
    
    async def _start_agents(self):
        """Start all agent message loops and wait until they're ready."""
        # Start all agents
        for agent_id, agent in self._agents.items():
            self._agent_tasks[agent_id] = asyncio.create_task(agent.run_loop())
        
        # Wait for all agents to be ready
        for agent_id, agent in self._agents.items():
            if not await agent.wait_ready(timeout=30.0):
                self._logger.error(f"Agent {agent_id} failed to start")
                raise RuntimeError(f"Agent {agent_id} failed to start")
            self._logger.info(f"Agent {agent_id} is ready")
    
    async def _stop_agents(self):
        """Stop all agents."""
        for agent in self._agents.values():
            agent.request_shutdown()
        
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._agent_tasks.values(), return_exceptions=True),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            for task in self._agent_tasks.values():
                task.cancel()
    
    async def _preflight_check(self) -> Dict[str, Any]:
        """Pre-flight environment check before generation."""
        import subprocess
        import shutil
        
        results = {
            "docker": {"available": False, "message": ""},
            "node": {"available": False, "message": ""},
            "ports": {"available": True, "blocked": []},
        }
        
        # Check Docker
        try:
            docker_result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=10,
            )
            if docker_result.returncode == 0:
                results["docker"]["available"] = True
                results["docker"]["message"] = "Docker daemon running"
            else:
                results["docker"]["message"] = "Docker daemon not running"
        except FileNotFoundError:
            results["docker"]["message"] = "Docker not installed"
        except subprocess.TimeoutExpired:
            results["docker"]["message"] = "Docker check timed out"
        except Exception as e:
            results["docker"]["message"] = f"Docker check failed: {e}"
        
        # Check Node.js
        try:
            node_result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if node_result.returncode == 0:
                results["node"]["available"] = True
                results["node"]["message"] = f"Node.js {node_result.stdout.strip()}"
        except FileNotFoundError:
            results["node"]["message"] = "Node.js not installed"
        except Exception as e:
            results["node"]["message"] = f"Node check failed: {e}"
        
        # Check common ports
        common_ports = [
            self.context.api_port, 
            self.context.ui_port, 
            self.context.db_port,
            3000, 5432, 8080, 8083
        ]
        
        for port in set(common_ports):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.bind(('localhost', port))
            except OSError:
                results["ports"]["blocked"].append(port)
        
        if results["ports"]["blocked"]:
            results["ports"]["available"] = False
        
        return results
    
    async def run(
        self,
        goal: str,
        requirements: List[str] = None,
        resume: bool = False,
    ) -> GenerationResult:
        """Run environment generation."""
        start_time = datetime.now()
        phases_completed = []
        
        # Pre-flight environment check
        self._logger.info("Running pre-flight environment check...")
        preflight = await self._preflight_check()
        
        # Log results
        for check, result in preflight.items():
            if isinstance(result, dict):
                available = result.get("available", False)
                msg = result.get("message", "")
                status = "OK" if available else "WARN"
                self._logger.info(f"  [{status}] {check}: {msg}")
                if check == "ports" and result.get("blocked"):
                    self._logger.warning(f"  Blocked ports: {result['blocked']}")
        
        # Store preflight results in context for agents to access
        self.context.preflight = preflight
        
        # Warn if Docker is not available
        if not preflight["docker"]["available"]:
            self._logger.warning(
                "Docker is not available. Docker-based testing will fail.\n"
                "  → Start Docker Desktop or docker daemon before testing.\n"
                "  → Agents will use docker_compose_reset() to clean up stale state."
            )
        
        await self.message_bus.start()
        self._create_agents()
        
        agents_started = False
        try:
            await self._start_agents()
            agents_started = True
        except Exception as start_err:
            self._logger.error(f"Failed to start agents: {start_err}")
            await self._stop_agents()
            await self.message_bus.stop()
            raise
        
        self.progress.emit(
            EventType.GENERATION_START,
            f"Starting: {goal[:50]}...",
            {"name": self.context.name, "goal": goal},
        )
        
        if not (resume and self.checkpoint.load()):
            self.checkpoint.start_generation(name=self.context.name, description=goal, domain_type="web_app")
        
        try:
            # ============================================================
            # AGENT-DRIVEN WORKFLOW
            # ============================================================
            # All phases are coordinated by agents via messages.
            # Orchestrator just:
            # 1. Sends initial task to UserAgent with raw requirements
            # 2. Waits for UserAgent to call deliver_project()
            #
            # Workflow (defined in agent prompts):
            # - UserAgent: refine requirements → broadcast → notify design
            # - DesignAgent: create design → broadcast → notify code agents
            # - Code Agents: wait for design → develop → notify completion
            # - UserAgent: monitor → test → deliver_project()
            # ============================================================
            
            self.progress.emit(EventType.PHASE_START, "Agent Workflow", {})
            
            # Prepare initial context for UserAgent
            raw_req = goal + ("\n" + "\n".join(requirements) if requirements else "")
            
            # Set reference images on all agents that might need them
            for agent_id in ["design", "frontend"]:
                if agent_id in self._agents:
                    self._agents[agent_id]._reference_images = self._reference_images
            
            # Generate docker-compose.yml upfront (agents can modify if needed)
            await self._generate_docker()
            
            # Send initial task to UserAgent - it coordinates everything
            self._logger.info("Starting agent-driven workflow...")
            await self._agents["user"].send_task({
                "raw_requirements": raw_req,
                    "reference_images": self._reference_images,
                "workflow": "full",  # Signal to run full workflow
            })
            
            # Wait for UserAgent to call deliver_project() (NOT finish()!)
            # Max 2 hours for full generation
            # deliver_project() sets _project_delivered_event
            user_agent = self._agents["user"]
            await asyncio.wait_for(
                user_agent._project_delivered_event.wait(), 
                timeout=7200.0
            )
            
            phases_completed = ["requirements", "design", "code", "docker", "testing"]
            self.checkpoint.complete_generation(success=True)
            success = True
            
        except Exception as e:
            self._logger.error(f"Generation failed: {e}")
            import traceback
            self._logger.error(traceback.format_exc())
            self.progress.emit(EventType.GENERATION_ERROR, str(e), {})
            success = False
        finally:
            if agents_started:
                await self._stop_agents()
            await self.message_bus.stop()
        
        duration = (datetime.now() - start_time).total_seconds()
        self.progress.emit(EventType.GENERATION_COMPLETE, f"Done in {duration:.1f}s", {"success": success})
        
        return GenerationResult(
            success=success,
            project_path=str(self.output_dir),
            phases_completed=phases_completed,
            issues_found=self._issues_found,
            issues_fixed=self._issues_fixed,
            duration=duration,
            summary=f"Generated {self.context.name} in {duration:.1f}s",
        )
    
    async def _distribute_design_docs(self):
        """Send design docs to code agents."""
        design_dir = self.output_dir / "design"
        if not design_dir.exists():
            return
        
        docs = {}
        for spec_file in design_dir.glob("*.json"):
            try:
                docs[spec_file.stem] = spec_file.read_text()
            except:
                pass
        
        for agent_id in ["database", "backend", "frontend"]:
            self._agents[agent_id].set_design_docs(docs)
    
    async def _generate_docker(self):
        """Generate docker-compose.yml."""
        db_port = self.context.db_port
        backend_port = self.context.backend_internal_port
        api_port = self.context.api_port
        ui_port = self.context.ui_port
        
        docker_compose = f'''version: '3.8'

services:
  database:
    build: ./app/database
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app
      PGPORT: {db_port}
    ports:
      - "{db_port}:{db_port}"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -p {db_port}"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./app/backend
    environment:
      DB_HOST: database
      DB_PORT: {db_port}
      DATABASE_URL: postgres://postgres:postgres@database:{db_port}/app
      PORT: {backend_port}
    ports:
      - "{api_port}:{backend_port}"
    depends_on:
      database:
        condition: service_healthy

  frontend:
    build: ./app/frontend
    environment:
      VITE_API_PROXY_TARGET: http://backend:{backend_port}
    ports:
      - "{ui_port}:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
'''
        
        docker_dir = self.output_dir / "docker"
        docker_dir.mkdir(exist_ok=True)
        (docker_dir / "docker-compose.yml").write_text(docker_compose)
    
    
    def get_status(self) -> Dict:
        """Get current status."""
        return {
            "name": self.context.name,
            "ports": {"api": self.context.api_port, "ui": self.context.ui_port, "db": self.context.db_port},
            "issues_found": self._issues_found,
            "issues_fixed": self._issues_fixed,
        }
