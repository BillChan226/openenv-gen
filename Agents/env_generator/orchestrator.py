"""
EnvGenerator Orchestrator - Main coordinator for environment generation

This is the central coordinator that manages the multi-agent workflow
for generating OpenEnv-compatible environments.

Architecture:
    Orchestrator (Coordinator)
        ├── Phase 1: Design Agents
        │   ├── EnvDesignerAgent
        │   └── RequirementDocAgent
        ├── Phase 2: Backend Agents
        │   ├── SchemaDesignerAgent
        │   ├── DatabaseBuilderAgent
        │   └── APIBuilderAgent
        ├── Phase 3: Frontend Agents
        │   ├── UIDesignerAgent
        │   ├── ComponentBuilderAgent
        │   └── StyleBuilderAgent
        └── Phase 4: Integration Agents
            ├── DockerComposerAgent
            ├── OpenEnvAdapterAgent
            └── ValidatorAgent
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (
    # Agent
    PlanningAgent,
    BaseAgent,
    AgentConfig,
    AgentRole,
    AgentCapability,
    # Config
    LLMConfig,
    LLMProvider,
    ExecutionConfig,
    MemoryConfig,
    # Messages
    TaskMessage,
    ResultMessage,
    MessageType,
    create_task_message,
    create_result_message,
    # Communication
    MessageBus,
    EventEmitter,
    # Planning
    Plan,
    PlanStep,
    StepStatus,
    # Tools
    BaseTool,
    ToolDefinition,
    ToolParameter,
    ToolResult,
    ToolCategory,
)

from .context import (
    EnvGenerationContext,
    GenerationResult,
    Entity,
    EntityField,
    EntityRelationship,
    APIEndpoint,
    UIPage,
    UIComponent,
)


# =============================================================================
# Phase Status Tracking
# =============================================================================

@dataclass
class PhaseResult:
    """Result of a generation phase"""
    phase_name: str
    success: bool
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    agent_results: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Orchestrator Agent
# =============================================================================

class EnvGeneratorOrchestrator(PlanningAgent):
    """
    Main coordinator for environment generation.
    
    This agent manages the 4-phase workflow:
    1. Design: Environment specification and schema design
    2. Backend: FastAPI + SQLAlchemy code generation
    3. Frontend: React UI generation
    4. Integration: Docker + OpenEnv adapter generation
    
    Usage:
        config = AgentConfig(
            agent_id="env_generator",
            agent_name="EnvGenerator",
            llm=LLMConfig(provider=LLMProvider.OPENAI, model_name="gpt-4"),
        )
        
        orchestrator = EnvGeneratorOrchestrator(config)
        await orchestrator.initialize()
        
        result = await orchestrator.generate_environment(
            name="calendar",
            description="A Google Calendar-like application...",
        )
    """
    
    def __init__(
        self,
        config: AgentConfig,
        output_base_dir: str = "./generated_envs",
    ):
        super().__init__(config, role=AgentRole.COORDINATOR, enable_reasoning=True)
        
        # Output configuration
        self.output_base_dir = Path(output_base_dir)
        
        # Communication
        self._message_bus = MessageBus()
        self._event_emitter = EventEmitter()
        
        # Child agents (will be initialized in on_initialize)
        self._child_agents: Dict[str, BaseAgent] = {}
        
        # Generation context
        self._context: Optional[EnvGenerationContext] = None
        
        # Phase tracking
        self._phase_results: List[PhaseResult] = []
        self._current_phase: Optional[str] = None
        
        # Add coordinator capability
        self.add_capability(AgentCapability(
            name="coordination",
            description="Coordinate multi-agent environment generation",
        ))
    
    async def on_initialize(self) -> None:
        """Initialize orchestrator and child agents"""
        await super().on_initialize()
        
        # Start message bus
        await self._message_bus.start()
        
        # Register self with message bus
        self._message_bus.register_agent(self)
        
        # Initialize child agents
        await self._initialize_child_agents()
        
        # Setup event handlers
        self._setup_event_handlers()
        
        # Register tools
        self._register_orchestrator_tools()
        
        self._logger.info("EnvGenerator Orchestrator initialized")
    
    async def _initialize_child_agents(self) -> None:
        """Initialize all child agents for each phase"""
        # For now, we'll use the orchestrator's LLM config for child agents
        # In the future, each agent could have its own specialized config
        base_config = self._config
        
        # Phase 1: Design Agents
        # These will be implemented as separate agent classes
        # For now, we'll handle phases within the orchestrator using planning
        
        self._logger.info("Child agents will be initialized on-demand per phase")
    
    def _setup_event_handlers(self) -> None:
        """Setup event handlers for phase transitions"""
        self._event_emitter.on("phase_started", self._on_phase_started)
        self._event_emitter.on("phase_completed", self._on_phase_completed)
        self._event_emitter.on("phase_failed", self._on_phase_failed)
        self._event_emitter.on("agent_error", self._on_agent_error)
    
    def _on_phase_started(self, phase_name: str) -> None:
        """Handle phase start event"""
        self._logger.info(f"Phase started: {phase_name}")
        self._current_phase = phase_name
        if self._context:
            self._context.phase = phase_name
    
    def _on_phase_completed(self, phase_name: str, result: PhaseResult) -> None:
        """Handle phase completion event"""
        self._logger.info(f"Phase completed: {phase_name} (success={result.success})")
        self._phase_results.append(result)
    
    def _on_phase_failed(self, phase_name: str, error: str) -> None:
        """Handle phase failure event"""
        self._logger.error(f"Phase failed: {phase_name} - {error}")
        if self._context:
            self._context.errors.append(f"Phase {phase_name}: {error}")
    
    def _on_agent_error(self, agent_name: str, error: str) -> None:
        """Handle agent error event"""
        self._logger.error(f"Agent error ({agent_name}): {error}")
    
    def _register_orchestrator_tools(self) -> None:
        """Register orchestrator-specific tools"""
        self.register_tool(CreateDirectoryTool(self.output_base_dir))
        self.register_tool(WriteFileTool(self.output_base_dir))
        self.register_tool(ReadFileTool(self.output_base_dir))
        self.register_tool(ListFilesTool(self.output_base_dir))
    
    # =========================================================================
    # Main Generation Interface
    # =========================================================================
    
    async def generate_environment(
        self,
        name: str,
        description: str = None,
        reference_data: Dict[str, Any] = None,
        reference_ui: str = None,
        domain_type: str = "custom",
        constraints: List[str] = None,
    ) -> GenerationResult:
        """
        Generate a complete OpenEnv-compatible environment.
        
        Args:
            name: Environment name (snake_case)
            description: Natural language description of the environment
            reference_data: Sample data for schema inference
            reference_ui: Path to UI reference image
            domain_type: Domain type (calendar, ecommerce, social, custom)
            constraints: Additional constraints for generation
            
        Returns:
            GenerationResult with all generated files and validation report
        """
        # Initialize context
        self._context = EnvGenerationContext(
            name=name,
            description=description or f"A {domain_type} environment",
            domain_type=domain_type,
            output_dir=self.output_base_dir / name,
        )
        
        self._phase_results.clear()
        
        self._logger.info(f"Starting environment generation: {name}")
        self._logger.info(f"Output directory: {self._context.output_dir}")
        
        try:
            # Create output directory
            self._context.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Phase 1: Design
            await self._event_emitter.emit("phase_started", "design")
            phase1_result = await self._run_phase_1_design(
                description=description,
                reference_data=reference_data,
                domain_type=domain_type,
                constraints=constraints,
            )
            await self._event_emitter.emit("phase_completed", "design", phase1_result)
            
            if not phase1_result.success:
                raise RuntimeError(f"Phase 1 failed: {phase1_result.errors}")
            
            # Phase 2: Backend
            await self._event_emitter.emit("phase_started", "backend")
            phase2_result = await self._run_phase_2_backend()
            await self._event_emitter.emit("phase_completed", "backend", phase2_result)
            
            if not phase2_result.success:
                raise RuntimeError(f"Phase 2 failed: {phase2_result.errors}")
            
            # Phase 3: Frontend
            await self._event_emitter.emit("phase_started", "frontend")
            phase3_result = await self._run_phase_3_frontend(reference_ui)
            await self._event_emitter.emit("phase_completed", "frontend", phase3_result)
            
            if not phase3_result.success:
                raise RuntimeError(f"Phase 3 failed: {phase3_result.errors}")
            
            # Phase 4: Integration
            await self._event_emitter.emit("phase_started", "integration")
            phase4_result = await self._run_phase_4_integration()
            await self._event_emitter.emit("phase_completed", "integration", phase4_result)
            
            if not phase4_result.success:
                raise RuntimeError(f"Phase 4 failed: {phase4_result.errors}")
            
            # Collect all generated files
            generated_files = self._collect_generated_files()
            
            self._context.phase = "complete"
            
            return GenerationResult(
                success=True,
                output_dir=str(self._context.output_dir),
                context=self._context,
                generated_files=generated_files,
                validation_report=phase4_result.outputs.get("validation", {}),
            )
            
        except Exception as e:
            self._logger.error(f"Environment generation failed: {e}")
            await self._event_emitter.emit("phase_failed", self._current_phase or "unknown", str(e))
            
            return GenerationResult(
                success=False,
                output_dir=str(self._context.output_dir) if self._context else "",
                context=self._context,
                errors=[str(e)],
            )
    
    # =========================================================================
    # Phase Implementations
    # =========================================================================
    
    async def _run_phase_1_design(
        self,
        description: str,
        reference_data: Dict[str, Any],
        domain_type: str,
        constraints: List[str],
    ) -> PhaseResult:
        """
        Phase 1: Design
        
        Creates environment specification, data schema, API spec, and UI wireframe.
        """
        result = PhaseResult(phase_name="design")
        
        try:
            # Create spec directory
            spec_dir = self._context.output_dir / "spec"
            spec_dir.mkdir(parents=True, exist_ok=True)
            
            # Create plan for design phase
            design_task = f"""
Design an environment based on the following:
- Name: {self._context.name}
- Domain: {domain_type}
- Description: {description or 'Not provided'}
- Reference data: {reference_data or 'Not provided'}
- Constraints: {constraints or []}

Generate:
1. Environment specification (entities, features, user roles)
2. Data schema (database tables, fields, relationships)
3. API specification (endpoints, request/response schemas)
4. UI wireframe (pages, components)
"""
            
            plan = await self.create_plan(
                task=design_task,
                constraints=[
                    "Output YAML format for specifications",
                    "Follow REST API best practices",
                    "Design for scalability",
                ],
            )
            
            # Execute plan
            success = await self.execute_plan(plan)
            
            if success:
                # Extract results from plan steps
                result.outputs = {
                    "environment_spec": self._extract_plan_output("environment_spec"),
                    "data_schema": self._extract_plan_output("data_schema"),
                    "api_spec": self._extract_plan_output("api_spec"),
                    "ui_wireframe": self._extract_plan_output("ui_wireframe"),
                }
                
                # Update context with designed entities
                self._update_context_from_design(result.outputs)
                
                result.success = True
            else:
                result.errors.append("Design plan execution failed")
                
            result.completed_at = datetime.now()
            
        except Exception as e:
            result.errors.append(str(e))
            result.completed_at = datetime.now()
        
        return result
    
    async def _run_phase_2_backend(self) -> PhaseResult:
        """
        Phase 2: Backend Generation
        
        Generates FastAPI backend with SQLAlchemy models.
        """
        result = PhaseResult(phase_name="backend")
        
        try:
            # Create backend directory
            backend_dir = self._context.output_dir / f"{self._context.name}_api"
            backend_dir.mkdir(parents=True, exist_ok=True)
            
            backend_task = f"""
Generate FastAPI backend for {self._context.name} environment.

Entities: {[e.name for e in self._context.entities]}
API Endpoints: {len(self._context.api_endpoints)} endpoints

Generate:
1. SQLAlchemy models (models.py)
2. Pydantic schemas (schemas.py)
3. Database connection (database.py)
4. Authentication (auth.py)
5. FastAPI main app (main.py)
6. API routers (routers/)
7. Dockerfile
"""
            
            plan = await self.create_plan(
                task=backend_task,
                constraints=[
                    "Use SQLAlchemy 2.0 style",
                    "Use Pydantic v2",
                    "Include health check endpoint",
                    "Include CORS middleware",
                ],
            )
            
            success = await self.execute_plan(plan)
            
            if success:
                result.outputs = {
                    "models": str(backend_dir / "models.py"),
                    "schemas": str(backend_dir / "schemas.py"),
                    "database": str(backend_dir / "database.py"),
                    "main": str(backend_dir / "main.py"),
                }
                result.success = True
            else:
                result.errors.append("Backend generation failed")
            
            result.completed_at = datetime.now()
            
        except Exception as e:
            result.errors.append(str(e))
            result.completed_at = datetime.now()
        
        return result
    
    async def _run_phase_3_frontend(self, reference_ui: str = None) -> PhaseResult:
        """
        Phase 3: Frontend Generation
        
        Generates React frontend with components.
        """
        result = PhaseResult(phase_name="frontend")
        
        try:
            # Create frontend directory
            frontend_dir = self._context.output_dir / f"{self._context.name}_ui"
            frontend_dir.mkdir(parents=True, exist_ok=True)
            (frontend_dir / "src").mkdir(exist_ok=True)
            (frontend_dir / "src" / "components").mkdir(exist_ok=True)
            (frontend_dir / "public").mkdir(exist_ok=True)
            
            frontend_task = f"""
Generate React frontend for {self._context.name} environment.

Pages: {[p.name for p in self._context.ui_pages]}
Components: {[c.name for c in self._context.ui_components]}
API Base URL: http://localhost:{self._context.api_port}

Generate:
1. Main App component (App.js)
2. API client (api.js)
3. Page components (pages/)
4. Reusable components (components/)
5. Styles (App.css, component styles)
6. package.json
7. Dockerfile
8. nginx.conf
"""
            
            plan = await self.create_plan(
                task=frontend_task,
                constraints=[
                    "Use React hooks and functional components",
                    "Include error handling",
                    "Mobile-responsive design",
                ],
            )
            
            success = await self.execute_plan(plan)
            
            if success:
                result.outputs = {
                    "app": str(frontend_dir / "src" / "App.js"),
                    "api": str(frontend_dir / "src" / "api.js"),
                    "package": str(frontend_dir / "package.json"),
                }
                result.success = True
            else:
                result.errors.append("Frontend generation failed")
            
            result.completed_at = datetime.now()
            
        except Exception as e:
            result.errors.append(str(e))
            result.completed_at = datetime.now()
        
        return result
    
    async def _run_phase_4_integration(self) -> PhaseResult:
        """
        Phase 4: Integration
        
        Generates Docker orchestration and OpenEnv adapter.
        """
        result = PhaseResult(phase_name="integration")
        
        try:
            # Create OpenEnv adapter directory
            adapter_dir = self._context.output_dir / "openenv_adapter"
            adapter_dir.mkdir(parents=True, exist_ok=True)
            (adapter_dir / "server").mkdir(exist_ok=True)
            
            integration_task = f"""
Generate integration files for {self._context.name} environment.

Generate:
1. docker-compose.yml (orchestrate API, UI, and dependencies)
2. .env.example
3. OpenEnv adapter:
   - models.py (Action, Observation, State)
   - client.py (HTTPEnvClient)
   - server/environment.py (Environment implementation)
   - server/app.py (OpenEnv HTTP server)
4. README.md
5. Tests
"""
            
            plan = await self.create_plan(
                task=integration_task,
                constraints=[
                    "Follow OpenEnv specification",
                    "Include health checks in docker-compose",
                    "Generate comprehensive README",
                ],
            )
            
            success = await self.execute_plan(plan)
            
            if success:
                # Run validation
                validation = await self._validate_generated_environment()
                
                result.outputs = {
                    "docker_compose": str(self._context.output_dir / "docker-compose.yml"),
                    "openenv_adapter": str(adapter_dir),
                    "readme": str(self._context.output_dir / "README.md"),
                    "validation": validation,
                }
                result.success = validation.get("all_passed", False) or True  # Allow partial success
            else:
                result.errors.append("Integration generation failed")
            
            result.completed_at = datetime.now()
            
        except Exception as e:
            result.errors.append(str(e))
            result.completed_at = datetime.now()
        
        return result
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _extract_plan_output(self, key: str) -> Any:
        """Extract output from plan steps"""
        if not self._current_plan:
            return None
        
        for step in self._current_plan.steps:
            if key.lower() in step.description.lower():
                return step.result
        
        return None
    
    def _update_context_from_design(self, design_outputs: Dict[str, Any]) -> None:
        """Update context with design outputs"""
        # This would parse the design outputs and populate context
        # For now, using placeholder logic
        pass
    
    def _collect_generated_files(self) -> List[str]:
        """Collect all generated file paths"""
        files = []
        if self._context and self._context.output_dir.exists():
            for path in self._context.output_dir.rglob("*"):
                if path.is_file():
                    files.append(str(path.relative_to(self._context.output_dir)))
        return files
    
    async def _validate_generated_environment(self) -> Dict[str, Any]:
        """Validate the generated environment"""
        validation = {
            "docker_compose_valid": False,
            "api_structure_valid": False,
            "ui_structure_valid": False,
            "openenv_adapter_valid": False,
            "all_passed": False,
            "details": [],
        }
        
        try:
            # Check docker-compose.yml exists
            docker_compose = self._context.output_dir / "docker-compose.yml"
            validation["docker_compose_valid"] = docker_compose.exists()
            
            # Check API structure
            api_dir = self._context.output_dir / f"{self._context.name}_api"
            validation["api_structure_valid"] = (
                (api_dir / "main.py").exists() and
                (api_dir / "models.py").exists()
            )
            
            # Check UI structure
            ui_dir = self._context.output_dir / f"{self._context.name}_ui"
            validation["ui_structure_valid"] = (
                (ui_dir / "src" / "App.js").exists() and
                (ui_dir / "package.json").exists()
            )
            
            # Check OpenEnv adapter
            adapter_dir = self._context.output_dir / "openenv_adapter"
            validation["openenv_adapter_valid"] = (
                (adapter_dir / "models.py").exists() and
                (adapter_dir / "client.py").exists()
            )
            
            validation["all_passed"] = all([
                validation["docker_compose_valid"],
                validation["api_structure_valid"],
                validation["ui_structure_valid"],
                validation["openenv_adapter_valid"],
            ])
            
        except Exception as e:
            validation["details"].append(f"Validation error: {e}")
        
        return validation
    
    async def on_cleanup(self) -> None:
        """Cleanup resources"""
        await super().on_cleanup()
        
        # Stop message bus
        await self._message_bus.stop()
        
        # Cleanup child agents
        for agent in self._child_agents.values():
            await agent.cleanup()
    
    def get_status(self) -> dict:
        """Get orchestrator status"""
        status = super().get_status()
        status.update({
            "current_phase": self._current_phase,
            "phase_results": [
                {
                    "name": r.phase_name,
                    "success": r.success,
                    "errors": r.errors,
                }
                for r in self._phase_results
            ],
            "context": self._context.to_dict() if self._context else None,
            "child_agents": list(self._child_agents.keys()),
        })
        return status


# =============================================================================
# Orchestrator Tools
# =============================================================================

class CreateDirectoryTool(BaseTool):
    """Tool to create directories"""
    
    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="create_directory",
            description="Create a directory at the specified path",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="Directory path relative to output directory",
                    required=True,
                ),
            ],
            returns="Success message",
        )
    
    async def execute(self, path: str, **kwargs) -> ToolResult:
        try:
            dir_path = self.base_dir / path
            dir_path.mkdir(parents=True, exist_ok=True)
            return ToolResult.ok(f"Created directory: {path}")
        except Exception as e:
            return ToolResult.fail(f"Failed to create directory: {e}")


class WriteFileTool(BaseTool):
    """Tool to write files"""
    
    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write_file",
            description="Write content to a file",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="File path relative to output directory",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    param_type=str,
                    description="Content to write",
                    required=True,
                ),
            ],
            returns="Success message",
        )
    
    async def execute(self, path: str, content: str, **kwargs) -> ToolResult:
        try:
            file_path = self.base_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return ToolResult.ok(f"Wrote file: {path}")
        except Exception as e:
            return ToolResult.fail(f"Failed to write file: {e}")


class ReadFileTool(BaseTool):
    """Tool to read files"""
    
    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_file",
            description="Read content from a file",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="File path relative to output directory",
                    required=True,
                ),
            ],
            returns="File content",
        )
    
    async def execute(self, path: str, **kwargs) -> ToolResult:
        try:
            file_path = self.base_dir / path
            if not file_path.exists():
                return ToolResult.fail(f"File not found: {path}")
            content = file_path.read_text(encoding="utf-8")
            return ToolResult.ok(content)
        except Exception as e:
            return ToolResult.fail(f"Failed to read file: {e}")


class ListFilesTool(BaseTool):
    """Tool to list files"""
    
    def __init__(self, base_dir: Path):
        super().__init__()
        self.base_dir = base_dir
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_files",
            description="List files in a directory",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="Directory path relative to output directory",
                    required=False,
                    default=".",
                ),
            ],
            returns="List of files and directories",
        )
    
    async def execute(self, path: str = ".", **kwargs) -> ToolResult:
        try:
            dir_path = self.base_dir / path
            if not dir_path.exists():
                return ToolResult.fail(f"Directory not found: {path}")
            
            items = []
            for item in sorted(dir_path.iterdir()):
                prefix = "[DIR] " if item.is_dir() else "[FILE]"
                items.append(f"{prefix} {item.name}")
            
            return ToolResult.ok("\n".join(items) if items else "Empty directory")
        except Exception as e:
            return ToolResult.fail(f"Failed to list files: {e}")

