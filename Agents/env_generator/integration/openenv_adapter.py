"""
OpenEnvAdapter Agent - Generates OpenEnv-compatible wrapper

This agent generates the OpenEnv adapter files that make the generated
environment compatible with the OpenEnv specification for RL training.

Generated files:
- models.py: Action, Observation, State dataclasses
- client.py: HTTPEnvClient implementation
- server/environment.py: Environment implementation
- server/app.py: FastAPI server with OpenEnv endpoints
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import (
    PlanningAgent,
    AgentConfig,
    AgentRole,
    AgentCapability,
    TaskMessage,
    ResultMessage,
    create_result_message,
    BaseTool,
    ToolDefinition,
    ToolParameter,
    ToolResult,
    ToolCategory,
)

from ..context import EnvGenerationContext


class OpenEnvAdapterAgent(PlanningAgent):
    """
    Agent for generating OpenEnv-compatible adapter.
    
    Generates:
    - models.py: Action, Observation, State dataclasses
    - client.py: HTTPEnvClient implementation  
    - server/environment.py: Environment implementation
    - server/app.py: FastAPI server
    - openenv.yaml: Environment manifest
    
    Usage:
        agent = OpenEnvAdapterAgent(config)
        await agent.initialize()
        
        files = await agent.generate_adapter(context)
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config, role=AgentRole.SPECIALIST, enable_reasoning=True)
        
        self.add_capability(AgentCapability(
            name="openenv_generation",
            description="Generate OpenEnv-compatible adapters",
        ))
    
    async def on_initialize(self) -> None:
        """Initialize adapter tools"""
        await super().on_initialize()
        
        self._logger.info("OpenEnvAdapterAgent initialized")
    
    async def generate_adapter(
        self,
        context: EnvGenerationContext,
        output_dir: Path,
    ) -> Dict[str, str]:
        """
        Generate OpenEnv adapter files.
        
        Args:
            context: Environment generation context
            output_dir: Output directory for adapter files
            
        Returns:
            Dict mapping file paths to content
        """
        files = {}
        
        # Create adapter directory
        adapter_dir = output_dir / "openenv_adapter"
        adapter_dir.mkdir(parents=True, exist_ok=True)
        (adapter_dir / "server").mkdir(exist_ok=True)
        
        # Generate models.py
        models_content = self._generate_models(context)
        files["openenv_adapter/models.py"] = models_content
        
        # Generate client.py
        client_content = self._generate_client(context)
        files["openenv_adapter/client.py"] = client_content
        
        # Generate server/environment.py
        env_content = self._generate_environment(context)
        files["openenv_adapter/server/environment.py"] = env_content
        
        # Generate server/app.py
        app_content = self._generate_app(context)
        files["openenv_adapter/server/app.py"] = app_content
        
        # Generate __init__.py files
        files["openenv_adapter/__init__.py"] = self._generate_adapter_init(context)
        files["openenv_adapter/server/__init__.py"] = '"""OpenEnv server module"""\n'
        
        # Generate openenv.yaml
        files["openenv_adapter/openenv.yaml"] = self._generate_manifest(context)
        
        # Generate pyproject.toml
        files["openenv_adapter/pyproject.toml"] = self._generate_pyproject(context)
        
        # Write files
        for path, content in files.items():
            file_path = output_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        
        return files
    
    def _generate_models(self, context: EnvGenerationContext) -> str:
        """Generate OpenEnv models (Action, Observation, State)"""
        env_name = context.name
        class_name = context.class_name
        
        # Determine available actions from entities
        actions = []
        for entity in context.entities:
            name = entity.name if hasattr(entity, 'name') else entity.get('name', 'Item')
            actions.extend([
                f"create_{name.lower()}",
                f"get_{name.lower()}",
                f"update_{name.lower()}",
                f"delete_{name.lower()}",
                f"list_{name.lower()}s",
            ])
        
        return f'''"""
OpenEnv Models for {context.display_name} Environment

Defines Action, Observation, and State dataclasses for the environment.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

# Support both in-repo and standalone imports
try:
    from core.env_server.types import Action, Observation, State
except ImportError:
    try:
        from openenv_core.env_server.types import Action, Observation, State
    except ImportError:
        # Fallback: define base classes locally
        @dataclass(kw_only=True)
        class Action:
            metadata: Dict[str, Any] = field(default_factory=dict)
        
        @dataclass(kw_only=True)
        class Observation:
            done: bool = False
            reward: Union[bool, int, float, None] = None
            metadata: Dict[str, Any] = field(default_factory=dict)
        
        @dataclass
        class State:
            episode_id: Optional[str] = None
            step_count: int = 0


# Available action types
ACTION_TYPES = [
    "login",
    "logout",
    "navigate",
    "query",
{chr(10).join(f'    "{a}",' for a in actions[:20])}
]


@dataclass(kw_only=True)
class {class_name}Action(Action):
    """
    Action for {context.display_name} environment.
    
    Attributes:
        action_type: Type of action to perform
        resource: Target resource (entity type)
        resource_id: ID of specific resource (for get/update/delete)
        params: Additional parameters for the action
    """
    action_type: str  # One of ACTION_TYPES
    resource: Optional[str] = None  # Entity type (e.g., "event", "calendar")
    resource_id: Optional[str] = None  # Specific resource ID
    params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.action_type not in ACTION_TYPES:
            # Allow custom actions but warn
            pass


@dataclass(kw_only=True)
class {class_name}Observation(Observation):
    """
    Observation from {context.display_name} environment.
    
    Attributes:
        success: Whether the action was successful
        data: Result data from the action
        error_message: Error message if action failed
        available_actions: List of currently available actions
        current_page: Current UI page/view
        visible_elements: Elements visible on current page
    """
    success: bool = True
    data: Any = None
    error_message: Optional[str] = None
    available_actions: List[str] = field(default_factory=list)
    current_page: str = "login"
    visible_elements: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class {class_name}State(State):
    """
    State for {context.display_name} environment.
    
    Attributes:
        episode_id: Unique episode identifier
        step_count: Number of steps taken
        current_user: Currently logged in user (email or None)
        current_page: Current UI page
        session_token: Authentication token
        session_data: Additional session data
    """
    episode_id: Optional[str] = None
    step_count: int = 0
    current_user: Optional[str] = None
    current_page: str = "login"
    session_token: Optional[str] = None
    session_data: Dict[str, Any] = field(default_factory=dict)
'''
    
    def _generate_client(self, context: EnvGenerationContext) -> str:
        """Generate HTTPEnvClient implementation"""
        class_name = context.class_name
        
        return f'''"""
OpenEnv HTTP Client for {context.display_name} Environment

Provides client-side interface for connecting to the environment server.
"""

from typing import Any, Dict

# Support both in-repo and standalone imports
try:
    from core.client_types import StepResult
    from core.env_server.types import State
    from core.http_env_client import HTTPEnvClient
except ImportError:
    try:
        from openenv_core.client_types import StepResult
        from openenv_core.env_server.types import State
        from openenv_core.http_env_client import HTTPEnvClient
    except ImportError:
        raise ImportError("Please install openenv-core: pip install openenv-core")

from .models import {class_name}Action, {class_name}Observation, {class_name}State


class {class_name}Env(HTTPEnvClient[{class_name}Action, {class_name}Observation]):
    """
    HTTP client for {context.display_name} environment.
    
    Example:
        # Connect to running server
        client = {class_name}Env(base_url="http://localhost:{context.openenv_port}")
        result = client.reset()
        print(result.observation)
        
        # Take action
        result = client.step({class_name}Action(
            action_type="login",
            params={{"email": "user@example.com", "password": "secret"}}
        ))
        
        # From Docker image
        client = {class_name}Env.from_docker_image("{context.name}-env:latest")
    """
    
    def _step_payload(self, action: {class_name}Action) -> Dict:
        """Convert action to JSON payload"""
        return {{
            "action_type": action.action_type,
            "resource": action.resource,
            "resource_id": action.resource_id,
            "params": action.params,
        }}
    
    def _parse_result(self, payload: Dict) -> StepResult[{class_name}Observation]:
        """Parse server response into StepResult"""
        obs_data = payload.get("observation", {{}})
        
        observation = {class_name}Observation(
            success=obs_data.get("success", True),
            data=obs_data.get("data"),
            error_message=obs_data.get("error_message"),
            available_actions=obs_data.get("available_actions", []),
            current_page=obs_data.get("current_page", "unknown"),
            visible_elements=obs_data.get("visible_elements", []),
            done=payload.get("done", False),
            reward=payload.get("reward"),
        )
        
        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )
    
    def _parse_state(self, payload: Dict) -> {class_name}State:
        """Parse state response"""
        return {class_name}State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            current_user=payload.get("current_user"),
            current_page=payload.get("current_page", "unknown"),
            session_token=payload.get("session_token"),
            session_data=payload.get("session_data", {{}}),
        )
'''
    
    def _generate_environment(self, context: EnvGenerationContext) -> str:
        """Generate Environment implementation"""
        class_name = context.class_name
        
        return f'''"""
{context.display_name} Environment Implementation

Server-side environment that wraps the backend API for RL training.
"""

import requests
from uuid import uuid4
from typing import Any, Dict, List, Optional

# Support both in-repo and standalone imports
try:
    from core.env_server.interfaces import Environment
    from core.env_server.types import State
except ImportError:
    try:
        from openenv_core.env_server.interfaces import Environment
        from openenv_core.env_server.types import State
    except ImportError:
        from abc import ABC, abstractmethod
        class Environment(ABC):
            @abstractmethod
            def reset(self): pass
            @abstractmethod
            def step(self, action): pass
            @property
            @abstractmethod
            def state(self): pass

from ..models import {class_name}Action, {class_name}Observation, {class_name}State, ACTION_TYPES


class {class_name}Environment(Environment):
    """
    {context.display_name} Environment for RL training.
    
    This environment wraps the backend API and provides:
    - State management for episodes
    - Action execution via API calls
    - Reward computation based on task success
    
    Args:
        api_base_url: Base URL of the backend API
        
    Example:
        env = {class_name}Environment(api_base_url="http://localhost:{context.api_port}")
        obs = env.reset()
        obs = env.step({class_name}Action(action_type="login", params={{...}}))
    """
    
    def __init__(self, api_base_url: str = "http://localhost:{context.api_port}"):
        self.api_base_url = api_base_url.rstrip("/")
        self._state = {class_name}State()
        self._session = requests.Session()
        self._reset_count = 0
    
    def reset(self) -> {class_name}Observation:
        """
        Reset environment to initial state.
        
        Returns:
            Initial observation with available actions
        """
        # Clear session
        self._session = requests.Session()
        
        # Initialize state
        self._state = {class_name}State(
            episode_id=str(uuid4()),
            step_count=0,
            current_page="login",
        )
        self._reset_count += 1
        
        return {class_name}Observation(
            success=True,
            data={{"message": "Environment ready"}},
            available_actions=["login", "register", "navigate"],
            current_page="login",
            done=False,
            reward=0.0,
        )
    
    def step(self, action: {class_name}Action) -> {class_name}Observation:
        """
        Execute action and return observation.
        
        Args:
            action: Action to execute
            
        Returns:
            Observation with result, reward, and new state
        """
        self._state.step_count += 1
        
        try:
            # Route action to appropriate handler
            if action.action_type == "login":
                return self._handle_login(action)
            elif action.action_type == "logout":
                return self._handle_logout(action)
            elif action.action_type == "navigate":
                return self._handle_navigate(action)
            elif action.action_type.startswith("create_"):
                return self._handle_create(action)
            elif action.action_type.startswith("get_"):
                return self._handle_get(action)
            elif action.action_type.startswith("list_"):
                return self._handle_list(action)
            elif action.action_type.startswith("update_"):
                return self._handle_update(action)
            elif action.action_type.startswith("delete_"):
                return self._handle_delete(action)
            else:
                return {class_name}Observation(
                    success=False,
                    error_message=f"Unknown action type: {{action.action_type}}",
                    reward=-0.1,
                )
                
        except Exception as e:
            return {class_name}Observation(
                success=False,
                error_message=str(e),
                reward=-1.0,
            )
    
    @property
    def state(self) -> {class_name}State:
        """Get current environment state"""
        return self._state
    
    # =========================================================================
    # Action Handlers
    # =========================================================================
    
    def _handle_login(self, action: {class_name}Action) -> {class_name}Observation:
        """Handle login action"""
        params = action.params
        email = params.get("email")
        password = params.get("password")
        
        if not email or not password:
            return {class_name}Observation(
                success=False,
                error_message="Email and password required",
                reward=-0.5,
            )
        
        try:
            response = self._session.post(
                f"{{self.api_base_url}}/api/v1/auth/login",
                json={{"email": email, "password": password}},
            )
            
            if response.status_code == 200:
                data = response.json()
                self._state.current_user = email
                self._state.session_token = data.get("access_token")
                self._state.current_page = "dashboard"
                
                # Set auth header for future requests
                self._session.headers["Authorization"] = f"Bearer {{self._state.session_token}}"
                
                return {class_name}Observation(
                    success=True,
                    data=data,
                    current_page="dashboard",
                    available_actions=self._get_available_actions(),
                    reward=1.0,
                )
            else:
                return {class_name}Observation(
                    success=False,
                    error_message=response.json().get("detail", "Login failed"),
                    reward=-0.5,
                )
                
        except requests.RequestException as e:
            return {class_name}Observation(
                success=False,
                error_message=f"API error: {{e}}",
                reward=-1.0,
            )
    
    def _handle_logout(self, action: {class_name}Action) -> {class_name}Observation:
        """Handle logout action"""
        self._state.current_user = None
        self._state.session_token = None
        self._state.current_page = "login"
        self._session.headers.pop("Authorization", None)
        
        return {class_name}Observation(
            success=True,
            data={{"message": "Logged out"}},
            current_page="login",
            available_actions=["login", "register"],
            reward=0.0,
        )
    
    def _handle_navigate(self, action: {class_name}Action) -> {class_name}Observation:
        """Handle navigation action"""
        page = action.params.get("page", "dashboard")
        self._state.current_page = page
        
        return {class_name}Observation(
            success=True,
            current_page=page,
            available_actions=self._get_available_actions(),
            reward=0.0,
        )
    
    def _handle_create(self, action: {class_name}Action) -> {class_name}Observation:
        """Handle create action"""
        resource = action.resource or action.action_type.replace("create_", "")
        
        try:
            response = self._session.post(
                f"{{self.api_base_url}}/api/v1/{{resource}}s",
                json=action.params,
            )
            
            if response.status_code in (200, 201):
                return {class_name}Observation(
                    success=True,
                    data=response.json(),
                    available_actions=self._get_available_actions(),
                    reward=1.0,
                )
            else:
                return {class_name}Observation(
                    success=False,
                    error_message=response.json().get("detail", "Create failed"),
                    reward=-0.5,
                )
                
        except requests.RequestException as e:
            return {class_name}Observation(
                success=False,
                error_message=str(e),
                reward=-1.0,
            )
    
    def _handle_get(self, action: {class_name}Action) -> {class_name}Observation:
        """Handle get action"""
        resource = action.resource or action.action_type.replace("get_", "")
        resource_id = action.resource_id or action.params.get("id")
        
        try:
            response = self._session.get(
                f"{{self.api_base_url}}/api/v1/{{resource}}s/{{resource_id}}",
            )
            
            if response.status_code == 200:
                return {class_name}Observation(
                    success=True,
                    data=response.json(),
                    reward=0.5,
                )
            else:
                return {class_name}Observation(
                    success=False,
                    error_message="Not found",
                    reward=-0.2,
                )
                
        except requests.RequestException as e:
            return {class_name}Observation(
                success=False,
                error_message=str(e),
                reward=-1.0,
            )
    
    def _handle_list(self, action: {class_name}Action) -> {class_name}Observation:
        """Handle list action"""
        resource = action.resource or action.action_type.replace("list_", "").rstrip("s")
        
        try:
            response = self._session.get(
                f"{{self.api_base_url}}/api/v1/{{resource}}s",
                params=action.params,
            )
            
            if response.status_code == 200:
                return {class_name}Observation(
                    success=True,
                    data=response.json(),
                    reward=0.5,
                )
            else:
                return {class_name}Observation(
                    success=False,
                    error_message="List failed",
                    reward=-0.2,
                )
                
        except requests.RequestException as e:
            return {class_name}Observation(
                success=False,
                error_message=str(e),
                reward=-1.0,
            )
    
    def _handle_update(self, action: {class_name}Action) -> {class_name}Observation:
        """Handle update action"""
        resource = action.resource or action.action_type.replace("update_", "")
        resource_id = action.resource_id or action.params.pop("id", None)
        
        try:
            response = self._session.put(
                f"{{self.api_base_url}}/api/v1/{{resource}}s/{{resource_id}}",
                json=action.params,
            )
            
            if response.status_code == 200:
                return {class_name}Observation(
                    success=True,
                    data=response.json(),
                    reward=1.0,
                )
            else:
                return {class_name}Observation(
                    success=False,
                    error_message="Update failed",
                    reward=-0.5,
                )
                
        except requests.RequestException as e:
            return {class_name}Observation(
                success=False,
                error_message=str(e),
                reward=-1.0,
            )
    
    def _handle_delete(self, action: {class_name}Action) -> {class_name}Observation:
        """Handle delete action"""
        resource = action.resource or action.action_type.replace("delete_", "")
        resource_id = action.resource_id or action.params.get("id")
        
        try:
            response = self._session.delete(
                f"{{self.api_base_url}}/api/v1/{{resource}}s/{{resource_id}}",
            )
            
            if response.status_code in (200, 204):
                return {class_name}Observation(
                    success=True,
                    data={{"deleted": True}},
                    reward=0.5,
                )
            else:
                return {class_name}Observation(
                    success=False,
                    error_message="Delete failed",
                    reward=-0.5,
                )
                
        except requests.RequestException as e:
            return {class_name}Observation(
                success=False,
                error_message=str(e),
                reward=-1.0,
            )
    
    def _get_available_actions(self) -> List[str]:
        """Get list of currently available actions"""
        if not self._state.current_user:
            return ["login", "register"]
        
        return ACTION_TYPES
'''
    
    def _generate_app(self, context: EnvGenerationContext) -> str:
        """Generate FastAPI app with OpenEnv endpoints"""
        class_name = context.class_name
        
        return f'''"""
FastAPI application for {context.display_name} OpenEnv Environment

Exposes OpenEnv HTTP endpoints: /reset, /step, /state, /health
"""

# Support both in-repo and standalone imports
try:
    from core.env_server.http_server import create_app
except ImportError:
    try:
        from openenv_core.env_server.http_server import create_app
    except ImportError:
        # Fallback: create app manually
        from fastapi import FastAPI, Body
        from dataclasses import asdict
        from typing import Dict, Any
        
        def create_app(env, action_cls, observation_cls, env_name=None):
            app = FastAPI(title=f"{{env_name or 'OpenEnv'}} HTTP Server")
            
            @app.post("/reset")
            async def reset(request: Dict[str, Any] = Body(default={{}})):
                obs = env.reset()
                return {{"observation": asdict(obs), "reward": obs.reward, "done": obs.done}}
            
            @app.post("/step")
            async def step(request: Dict[str, Any]):
                action_data = request.get("action", request)
                action = action_cls(**action_data)
                obs = env.step(action)
                return {{"observation": asdict(obs), "reward": obs.reward, "done": obs.done}}
            
            @app.get("/state")
            async def get_state():
                return asdict(env.state)
            
            @app.get("/health")
            async def health():
                return {{"status": "healthy"}}
            
            return app

from ..models import {class_name}Action, {class_name}Observation
from .environment import {class_name}Environment


# Create environment instance
env = {class_name}Environment()

# Create FastAPI app with OpenEnv routes
app = create_app(env, {class_name}Action, {class_name}Observation, env_name="{context.name}")


def main():
    """Run server directly"""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port={context.openenv_port})


if __name__ == "__main__":
    main()
'''
    
    def _generate_adapter_init(self, context: EnvGenerationContext) -> str:
        """Generate adapter __init__.py"""
        class_name = context.class_name
        
        return f'''"""
{context.display_name} OpenEnv Adapter

Provides OpenEnv-compatible interface for RL training.
"""

from .models import {class_name}Action, {class_name}Observation, {class_name}State
from .client import {class_name}Env

__all__ = [
    "{class_name}Action",
    "{class_name}Observation",
    "{class_name}State",
    "{class_name}Env",
]
'''
    
    def _generate_manifest(self, context: EnvGenerationContext) -> str:
        """Generate openenv.yaml manifest"""
        return f'''# OpenEnv Environment Manifest
name: {context.name}
version: "1.0.0"
description: "{context.description}"

# Environment configuration
environment:
  class: openenv_adapter.server.environment.{context.class_name}Environment
  api_base_url: "http://localhost:{context.api_port}"

# Client configuration
client:
  class: openenv_adapter.client.{context.class_name}Env
  default_port: {context.openenv_port}

# Docker configuration
docker:
  image: {context.name}-env
  port: {context.openenv_port}
  health_check: /health

# Action space
actions:
  - login
  - logout
  - navigate
  - create_*
  - get_*
  - list_*
  - update_*
  - delete_*

# Observation space
observation:
  success: bool
  data: any
  error_message: string
  available_actions: list
  current_page: string
'''
    
    def _generate_pyproject(self, context: EnvGenerationContext) -> str:
        """Generate pyproject.toml"""
        return f'''[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{context.name}-openenv"
version = "1.0.0"
description = "{context.description}"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "requests>=2.25.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "httpx>=0.24.0",
]

[tool.setuptools]
packages = ["openenv_adapter", "openenv_adapter.server"]
'''
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """Process adapter generation task"""
        params = task.task_params
        context = params.get("context")
        output_dir = Path(params.get("output_dir", "./generated"))
        
        if not context:
            return create_result_message(
                source_id=self.agent_id,
                target_id=task.header.source_agent_id,
                task_id=task.task_id,
                success=False,
                error_message="Context required",
            )
        
        files = await self.generate_adapter(context, output_dir)
        
        return create_result_message(
            source_id=self.agent_id,
            target_id=task.header.source_agent_id,
            task_id=task.task_id,
            success=True,
            result_data={"files": list(files.keys())},
        )

