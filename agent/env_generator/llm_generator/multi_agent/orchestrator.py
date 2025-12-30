"""
Orchestrator - Event-Driven Multi-Agent Coordination

Features from previous implementation:
- Checkpoint system for save/resume
- Event emitter for real-time progress
- Dynamic port allocation (no hardcoded ports)
- Spec validation before code generation
"""

import asyncio
import json
import logging
import socket
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from utils.communication import MessageBus, EventEmitter
from utils.message import (
    BaseMessage,
    MessageType,
)
from utils.config import LLMConfig, AgentConfig
from utils.llm import LLM

from .workspace_manager import WorkspaceManager
from .agents import (
    UserAgent,
    DesignAgent,
    DatabaseAgent,
    BackendAgent,
    FrontendAgent,
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
    messages_exchanged: int = 0
    issues_found: int = 0
    issues_fixed: int = 0
    duration: float = 0.0
    summary: str = ""


def find_free_port(preferred: List[int] = None, range_start: int = 8000, range_end: int = 9000) -> int:
    """Find an available port, checking preferred ports first."""
    preferred = preferred or []
    
    def is_free(port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    # Try preferred ports first
    for port in preferred:
        if is_free(port):
            return port
    
    # Search in range
    for port in range(range_start, range_end):
        if is_free(port):
            return port
    
    raise RuntimeError(f"No free port found in range {range_start}-{range_end}")


class Orchestrator:
    """
    Event-Driven Multi-Agent Orchestrator with advanced features.
    
    Features:
    - Checkpoint: Save/resume generation progress
    - Dynamic Ports: No hardcoded ports, auto-find available
    - Progress Events: Real-time status streaming
    - Spec Validation: Validate designs before code generation
    """
    
    def __init__(
        self,
        llm_config: LLMConfig,
        output_dir: Path,
        verbose: bool = False,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._logger = logging.getLogger("Orchestrator")
        self._verbose = verbose
        
        # Core infrastructure
        self.workspace = WorkspaceManager(self.output_dir)
        self.message_bus = MessageBus()
        
        # Checkpoint system
        self.checkpoint = CheckpointManager(self.output_dir / ".checkpoint.json")
        
        # Progress events
        self.progress = ProgressEmitter()
        if verbose:
            self.progress.on_all(ConsoleListener(verbose=True))
        
        # Generation context with DYNAMIC ports
        self.context = GenerationContext(
            name=self.output_dir.name,
            output_dir=self.output_dir,
            api_port=find_free_port([8000, 8001, 8002, 8080]),
            ui_port=find_free_port([3000, 3001, 3002, 5173]),
            openenv_port=find_free_port([8080, 8081, 8082]),
        )
        
        self._logger.info(f"Allocated ports: API={self.context.api_port}, UI={self.context.ui_port}")
        
        # Store config
        self._llm_config = llm_config
        
        # Agents
        self._agents: Dict[str, Any] = {}
        
        # Tracking
        self._messages_exchanged = 0
        self._issues_found = 0
        self._issues_fixed = 0
    
    # ==================== Setup ====================
    
    def _create_agents(self) -> Dict[str, Any]:
        """Create all agents with shared MessageBus."""
        agents = {}
        
        agent_specs = [
            ("user", UserAgent, "UserAgent"),
            ("design", DesignAgent, "DesignAgent"),
            ("database", DatabaseAgent, "DatabaseAgent"),
            ("backend", BackendAgent, "BackendAgent"),
            ("frontend", FrontendAgent, "FrontendAgent"),
        ]
        
        for agent_id, agent_class, agent_name in agent_specs:
            llm = LLM(self._llm_config)
            config = AgentConfig(agent_id=agent_id, agent_name=agent_name)
            
            agent = agent_class(
                config=config,
                llm=llm,
                workspace_manager=self.workspace,
            )
            
            # Share context (ports, etc.)
            agent.context = self.context
            
            agents[agent_id] = agent
            self._logger.info(f"Created agent: {agent_name}")
        
        # Connect agents for direct communication
        for agent_id, agent in agents.items():
            other_agents = {k: v for k, v in agents.items() if k != agent_id}
            agent.set_other_agents(other_agents)
            agent.set_message_bus(self.message_bus)
        
        return agents
    
    # ==================== Main Entry Point ====================
    
    async def run(
        self,
        goal: str,
        requirements: List[str] = None,
        resume: bool = False,
    ) -> GenerationResult:
        """
        Run event-driven environment generation.
        
        Args:
            goal: Project description
            requirements: Additional requirements
            resume: Whether to resume from checkpoint
        """
        start_time = datetime.now()
        phases_completed = []
        
        # Emit start event
        self.progress.emit(EventType.GENERATION_START, f"Starting generation: {goal[:50]}...", {
            "name": self.context.name,
            "ports": {"api": self.context.api_port, "ui": self.context.ui_port},
        })
        
        # Check for resume
        if resume and self.checkpoint.load():
            self._logger.info(f"Resuming from checkpoint: {self.checkpoint.get_status()}")
            self.checkpoint.print_status()
        else:
            self.checkpoint.start_generation(
                name=self.context.name,
                description=goal,
                domain_type="web_app",
            )
        
        # Create agents
        self._agents = self._create_agents()
        await self.message_bus.start()
        
        try:
            # Phase 1: Refine requirements
            if not self.checkpoint.is_phase_complete("requirements"):
                self.progress.emit(EventType.PHASE_START, "Refining Requirements", {})
                self.checkpoint.start_phase("requirements")
                
                raw_req = goal + ("\n" + "\n".join(requirements) if requirements else "")
                refined = await self._agents["user"].refine_requirements(raw_req)
                
                if refined.get("success"):
                    self.context.features = [f["name"] for f in refined.get("requirements", {}).get("features", [])]
                    await self._broadcast_requirements(refined.get("requirements", {}))
                    self.checkpoint.complete_phase("requirements")
                    phases_completed.append("requirements")
                    self.progress.emit(EventType.PHASE_COMPLETE, "Requirements refined", {"features": len(self.context.features)})
                else:
                    raise RuntimeError("Requirements refinement failed")
            
            # Phase 2: Design
            if not self.checkpoint.is_phase_complete("design"):
                self.progress.emit(EventType.PHASE_START, "Creating Design", {})
                self.checkpoint.start_phase("design")
                
                design_result = await self._agents["design"].execute({
                    "type": "design_all",
                    "requirements": self._agents["user"]._requirements,
                })
                
                if design_result.get("success"):
                    # Validate specs
                    from verification.spec_validator import validate_specs
                    validation = validate_specs(str(self.output_dir))
                    
                    if not validation.valid:
                        self._logger.warning(f"Spec validation issues: {len(validation.issues)}")
                        for issue in validation.issues[:5]:
                            self._logger.warning(f"  {issue.severity}: {issue.message}")
                    
                    self.checkpoint.complete_phase("design")
                    phases_completed.append("design")
                    self.progress.emit(EventType.PHASE_COMPLETE, "Design complete", {"files": len(design_result.get("files_created", []))})
                else:
                    raise RuntimeError("Design failed")
            
            # Phase 3: Parallel code generation
            if not self.checkpoint.is_phase_complete("code"):
                self.progress.emit(EventType.PHASE_START, "Generating Code (Parallel)", {})
                self.checkpoint.start_phase("code")
                
                await self._parallel_code_generation()
                
                self.checkpoint.complete_phase("code")
                phases_completed.append("code")
                self.progress.emit(EventType.PHASE_COMPLETE, "Code generation complete", {})
            
            # Phase 4: Docker configuration
            if not self.checkpoint.is_phase_complete("docker"):
                self.progress.emit(EventType.PHASE_START, "Creating Docker Config", {})
                self.checkpoint.start_phase("docker")
                
                await self._generate_docker()
                
                self.checkpoint.complete_phase("docker")
                phases_completed.append("docker")
                self.progress.emit(EventType.PHASE_COMPLETE, "Docker config complete", {})
            
            # Phase 5: Test and fix loop
            self.progress.emit(EventType.PHASE_START, "Testing & Fixing", {})
            await self._test_and_fix_loop()
            phases_completed.append("testing")
            
            # Complete
            self.checkpoint.complete_generation(success=True)
            success = True
            
        except Exception as e:
            self._logger.error(f"Generation failed: {e}")
            self.progress.emit(EventType.GENERATION_ERROR, str(e), {"error": str(e)})
            success = False
        finally:
            await self.message_bus.stop()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        self.progress.emit(EventType.GENERATION_COMPLETE, "Generation finished", {
            "duration": duration,
            "total_files": len(self.context.files),
            "success": success,
        })
        
        return GenerationResult(
            success=success,
            project_path=str(self.output_dir),
            phases_completed=phases_completed,
            messages_exchanged=self._messages_exchanged,
            issues_found=self._issues_found,
            issues_fixed=self._issues_fixed,
            duration=duration,
            summary=f"Generated {len(self.context.files)} files in {duration:.1f}s",
        )
    
    async def _broadcast_requirements(self, requirements: Dict):
        """Broadcast requirements to all agents."""
        for agent_id, agent in self._agents.items():
            if hasattr(agent, 'receive_requirements'):
                await agent.receive_requirements(requirements)
    
    async def _parallel_code_generation(self):
        """Run code generation in parallel."""
        self.progress.emit(EventType.FILE_PLAN, "Planning parallel generation", {
            "agents": ["database", "backend", "frontend"]
        })
        
        async def generate_with_progress(agent_id: str):
            self.progress.emit(EventType.FILE_START, f"Starting {agent_id}", {"agent": agent_id})
            
            agent = self._agents[agent_id]
            result = await agent.execute({"type": "generate"})
            
            files = result.get("files_created", [])
            self.progress.emit(EventType.FILE_COMPLETE, f"{agent_id} complete", {
                "agent": agent_id,
                "files": len(files),
            })
            
            # Track files in context
            for f in files:
                self.context.add_file(f, "", agent_id)
            
            return agent_id, result
        
        tasks = [
            generate_with_progress("database"),
            generate_with_progress("backend"),
            generate_with_progress("frontend"),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                self._logger.error(f"Agent error: {result}")
    
    async def _generate_docker(self):
        """Generate Docker configuration with DYNAMIC ports."""
        docker_compose = f'''version: '3.8'

services:
  database:
    build:
      context: ./app/database
      dockerfile: Dockerfile
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./app/backend
      dockerfile: Dockerfile
    environment:
      DB_HOST: database
      DB_PORT: 5432
      DB_NAME: app
      DB_USER: postgres
      DB_PASSWORD: postgres
      JWT_SECRET: change-in-production
      PORT: 3000
    ports:
      - "{self.context.api_port}:3000"
    depends_on:
      database:
        condition: service_healthy

  frontend:
    build:
      context: ./app/frontend
      dockerfile: Dockerfile
    ports:
      - "{self.context.ui_port}:80"
    depends_on:
      - backend

volumes:
  postgres_data:
'''
        
        self.workspace.write_file("docker/docker-compose.yml", docker_compose, "orchestrator")
        self.context.add_file("docker/docker-compose.yml", docker_compose, "docker")
        
        self.progress.emit(EventType.FILE_COMPLETE, "docker-compose.yml", {
            "path": "docker/docker-compose.yml",
            "ports": {"api": self.context.api_port, "ui": self.context.ui_port},
        })
    
    async def _test_and_fix_loop(self, max_iterations: int = 5):
        """Test application and fix issues in parallel."""
        for iteration in range(max_iterations):
            self.progress.emit(EventType.VERIFICATION_START, f"Test iteration {iteration + 1}", {})
            
            # UserAgent tests
            test_result = await self._agents["user"].test_application()
            
            if test_result.get("overall_status") == "pass":
                self.progress.emit(EventType.VERIFICATION_PASS, "All tests passed", {})
                return
            
            issues = test_result.get("issues", [])
            if not issues:
                return
            
            self._issues_found += len(issues)
            self.progress.emit(EventType.VERIFICATION_ERROR, f"Found {len(issues)} issues", {
                "issues": len(issues)
            })
            
            # Fix issues in parallel
            self.progress.emit(EventType.FIX_START, "Fixing issues in parallel", {"issues": len(issues)})
            fixed = await self._parallel_fix(issues)
            self._issues_fixed += fixed
            
            self.progress.emit(EventType.FIX_APPLIED, f"Fixed {fixed} issues", {"fixed": fixed})
    
    async def _parallel_fix(self, issues: List[Dict]) -> int:
        """Fix issues in parallel by module."""
        by_module = {"database": [], "backend": [], "frontend": []}
        
        for issue in issues:
            module = issue.get("module", "backend").lower()
            if module in by_module:
                by_module[module].append(issue)
        
        async def fix_module(agent_id: str, module_issues: List[Dict]) -> int:
            if not module_issues:
                return 0
            
            agent = self._agents[agent_id]
            result = await agent.execute({
                "type": "fix",
                "issues": module_issues,
            })
            return result.get("fixed", 0)
        
        tasks = [
            fix_module("database", by_module["database"]),
            fix_module("backend", by_module["backend"]),
            fix_module("frontend", by_module["frontend"]),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_fixed = 0
        for result in results:
            if isinstance(result, int):
                total_fixed += result
        
        return total_fixed
    
    # ==================== Status ====================
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            "name": self.context.name,
            "ports": {
                "api": self.context.api_port,
                "ui": self.context.ui_port,
            },
            "agents": list(self._agents.keys()),
            "checkpoint": self.checkpoint.get_summary(),
            "files_generated": len(self.context.files),
            "issues_found": self._issues_found,
            "issues_fixed": self._issues_fixed,
        }
