"""
Validator Agent - Validates and tests generated environments

This agent performs comprehensive validation including:
- Code syntax validation
- Docker build validation
- API endpoint testing
- OpenEnv interface testing
- Integration tests
"""

import asyncio
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
)

from ..context import EnvGenerationContext


@dataclass
class ValidationResult:
    """Result of a validation check"""
    name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class ValidationReport:
    """Complete validation report"""
    environment_name: str
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warnings: int = 0
    results: List[ValidationResult] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return (self.passed_checks / self.total_checks) * 100
    
    @property
    def passed(self) -> bool:
        return self.failed_checks == 0
    
    def to_dict(self) -> Dict:
        return {
            "environment_name": self.environment_name,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warnings": self.warnings,
            "success_rate": f"{self.success_rate:.1f}%",
            "passed": self.passed,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "duration_ms": r.duration_ms,
                }
                for r in self.results
            ],
        }


class ValidatorAgent(PlanningAgent):
    """
    Agent for validating generated environments.
    
    Performs:
    - Static validation (file structure, syntax)
    - Docker validation (build, compose)
    - Runtime validation (API tests, OpenEnv tests)
    
    Usage:
        agent = ValidatorAgent(config)
        await agent.initialize()
        
        report = await agent.validate(context, output_dir)
        print(f"Validation: {report.passed_checks}/{report.total_checks} passed")
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config, role=AgentRole.SPECIALIST, enable_reasoning=True)
        
        self.add_capability(AgentCapability(
            name="environment_validation",
            description="Validate generated environments",
        ))
    
    async def on_initialize(self) -> None:
        """Initialize validator"""
        await super().on_initialize()
        self._logger.info("ValidatorAgent initialized")
    
    async def validate(
        self,
        context: EnvGenerationContext,
        output_dir: Path,
        run_docker: bool = False,
        run_api_tests: bool = False,
    ) -> ValidationReport:
        """
        Validate generated environment.
        
        Args:
            context: Environment generation context
            output_dir: Output directory with generated files
            run_docker: Whether to run Docker validation (requires Docker)
            run_api_tests: Whether to run API tests (requires running services)
            
        Returns:
            ValidationReport with all results
        """
        report = ValidationReport(environment_name=context.name)
        
        # 1. Static validation
        print("\n[Validator] Running static validation...")
        static_results = await self._validate_static(context, output_dir)
        report.results.extend(static_results)
        
        # 2. Python syntax validation
        print("[Validator] Validating Python syntax...")
        python_results = await self._validate_python_syntax(context, output_dir)
        report.results.extend(python_results)
        
        # 3. TypeScript/React validation (if node available)
        print("[Validator] Validating TypeScript...")
        ts_results = await self._validate_typescript(context, output_dir)
        report.results.extend(ts_results)
        
        # 4. Docker validation
        if run_docker:
            print("[Validator] Validating Docker...")
            docker_results = await self._validate_docker(context, output_dir)
            report.results.extend(docker_results)
        
        # 5. API tests
        if run_api_tests:
            print("[Validator] Running API tests...")
            api_results = await self._validate_api(context)
            report.results.extend(api_results)
        
        # 6. OpenEnv interface validation
        print("[Validator] Validating OpenEnv interface...")
        openenv_results = await self._validate_openenv(context, output_dir)
        report.results.extend(openenv_results)
        
        # Calculate totals
        for result in report.results:
            report.total_checks += 1
            if result.passed:
                report.passed_checks += 1
            else:
                report.failed_checks += 1
        
        # Generate test files
        await self._generate_test_files(context, output_dir)
        
        # Save report
        report_path = output_dir / "validation_report.json"
        report_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        
        return report
    
    async def _validate_static(
        self,
        context: EnvGenerationContext,
        output_dir: Path,
    ) -> List[ValidationResult]:
        """Validate file structure and existence"""
        results = []
        
        # Required files
        required_files = [
            f"{context.name}_api/main.py",
            f"{context.name}_api/models.py",
            f"{context.name}_api/schemas.py",
            f"{context.name}_api/database.py",
            f"{context.name}_api/auth.py",
            f"{context.name}_api/requirements.txt",
            "openenv_adapter/models.py",
            "openenv_adapter/client.py",
            "openenv_adapter/server/environment.py",
            "openenv_adapter/server/app.py",
            "docker-compose.yml",
            "README.md",
        ]
        
        # Check frontend if exists
        ui_dir = output_dir / f"{context.name}_ui"
        if ui_dir.exists():
            required_files.extend([
                f"{context.name}_ui/package.json",
                f"{context.name}_ui/src/App.tsx",
                f"{context.name}_ui/src/services/api.ts",
            ])
        
        for file_path in required_files:
            start = time.time()
            full_path = output_dir / file_path
            exists = full_path.exists()
            duration = (time.time() - start) * 1000
            
            results.append(ValidationResult(
                name=f"file_exists:{file_path}",
                passed=exists,
                message=f"File {'exists' if exists else 'missing'}: {file_path}",
                duration_ms=duration,
            ))
        
        # Check directory structure
        required_dirs = [
            f"{context.name}_api",
            f"{context.name}_api/routers",
            "openenv_adapter",
            "openenv_adapter/server",
        ]
        
        for dir_path in required_dirs:
            start = time.time()
            full_path = output_dir / dir_path
            exists = full_path.is_dir()
            duration = (time.time() - start) * 1000
            
            results.append(ValidationResult(
                name=f"dir_exists:{dir_path}",
                passed=exists,
                message=f"Directory {'exists' if exists else 'missing'}: {dir_path}",
                duration_ms=duration,
            ))
        
        return results
    
    async def _validate_python_syntax(
        self,
        context: EnvGenerationContext,
        output_dir: Path,
    ) -> List[ValidationResult]:
        """Validate Python file syntax"""
        results = []
        
        # Find all Python files
        api_dir = output_dir / f"{context.name}_api"
        openenv_dir = output_dir / "openenv_adapter"
        
        python_files = []
        if api_dir.exists():
            python_files.extend(api_dir.rglob("*.py"))
        if openenv_dir.exists():
            python_files.extend(openenv_dir.rglob("*.py"))
        
        for py_file in python_files:
            start = time.time()
            rel_path = py_file.relative_to(output_dir)
            
            try:
                # Try to compile the file
                code = py_file.read_text(encoding="utf-8")
                compile(code, str(py_file), "exec")
                
                duration = (time.time() - start) * 1000
                results.append(ValidationResult(
                    name=f"python_syntax:{rel_path}",
                    passed=True,
                    message=f"Valid Python syntax: {rel_path}",
                    duration_ms=duration,
                ))
            except SyntaxError as e:
                duration = (time.time() - start) * 1000
                results.append(ValidationResult(
                    name=f"python_syntax:{rel_path}",
                    passed=False,
                    message=f"Syntax error in {rel_path}: {e.msg} (line {e.lineno})",
                    details={"line": e.lineno, "error": str(e)},
                    duration_ms=duration,
                ))
            except Exception as e:
                duration = (time.time() - start) * 1000
                results.append(ValidationResult(
                    name=f"python_syntax:{rel_path}",
                    passed=False,
                    message=f"Error validating {rel_path}: {e}",
                    duration_ms=duration,
                ))
        
        return results
    
    async def _validate_typescript(
        self,
        context: EnvGenerationContext,
        output_dir: Path,
    ) -> List[ValidationResult]:
        """Validate TypeScript/React files"""
        results = []
        
        ui_dir = output_dir / f"{context.name}_ui"
        if not ui_dir.exists():
            return results
        
        # Check if package.json has correct structure
        package_json = ui_dir / "package.json"
        if package_json.exists():
            start = time.time()
            try:
                pkg = json.loads(package_json.read_text(encoding="utf-8"))
                
                # Check required fields
                has_name = "name" in pkg
                has_deps = "dependencies" in pkg
                has_react = pkg.get("dependencies", {}).get("react") is not None
                
                valid = has_name and has_deps and has_react
                duration = (time.time() - start) * 1000
                
                results.append(ValidationResult(
                    name="package_json_valid",
                    passed=valid,
                    message="package.json is valid" if valid else "package.json missing required fields",
                    details={"has_name": has_name, "has_deps": has_deps, "has_react": has_react},
                    duration_ms=duration,
                ))
            except json.JSONDecodeError as e:
                duration = (time.time() - start) * 1000
                results.append(ValidationResult(
                    name="package_json_valid",
                    passed=False,
                    message=f"package.json is not valid JSON: {e}",
                    duration_ms=duration,
                ))
        
        # Check TSX files exist and have valid structure
        tsx_files = [
            "src/App.tsx",
            "src/main.tsx",
            "src/contexts/AuthContext.tsx",
            "src/services/api.ts",
        ]
        
        for tsx_file in tsx_files:
            start = time.time()
            file_path = ui_dir / tsx_file
            
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                
                # Basic checks
                has_import = "import" in content
                has_export = "export" in content
                
                valid = has_import and has_export
                duration = (time.time() - start) * 1000
                
                results.append(ValidationResult(
                    name=f"tsx_valid:{tsx_file}",
                    passed=valid,
                    message=f"{tsx_file} has valid structure" if valid else f"{tsx_file} missing imports/exports",
                    duration_ms=duration,
                ))
            else:
                duration = (time.time() - start) * 1000
                results.append(ValidationResult(
                    name=f"tsx_valid:{tsx_file}",
                    passed=False,
                    message=f"{tsx_file} not found",
                    duration_ms=duration,
                ))
        
        return results
    
    async def _validate_docker(
        self,
        context: EnvGenerationContext,
        output_dir: Path,
    ) -> List[ValidationResult]:
        """Validate Docker configuration"""
        results = []
        
        # Check docker-compose.yml syntax
        compose_file = output_dir / "docker-compose.yml"
        if compose_file.exists():
            start = time.time()
            try:
                # Validate docker-compose config
                proc = subprocess.run(
                    ["docker-compose", "-f", str(compose_file), "config"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                
                valid = proc.returncode == 0
                duration = (time.time() - start) * 1000
                
                results.append(ValidationResult(
                    name="docker_compose_valid",
                    passed=valid,
                    message="docker-compose.yml is valid" if valid else f"docker-compose.yml error: {proc.stderr}",
                    duration_ms=duration,
                ))
            except FileNotFoundError:
                duration = (time.time() - start) * 1000
                results.append(ValidationResult(
                    name="docker_compose_valid",
                    passed=True,  # Skip if docker-compose not installed
                    message="docker-compose not installed, skipping validation",
                    duration_ms=duration,
                ))
            except subprocess.TimeoutExpired:
                duration = (time.time() - start) * 1000
                results.append(ValidationResult(
                    name="docker_compose_valid",
                    passed=False,
                    message="docker-compose validation timed out",
                    duration_ms=duration,
                ))
        
        # Check Dockerfiles syntax
        dockerfiles = [
            f"{context.name}_api/Dockerfile",
            "openenv_adapter/Dockerfile",
        ]
        
        ui_dockerfile = output_dir / f"{context.name}_ui" / "Dockerfile"
        if ui_dockerfile.exists():
            dockerfiles.append(f"{context.name}_ui/Dockerfile")
        
        for dockerfile in dockerfiles:
            start = time.time()
            file_path = output_dir / dockerfile
            
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                
                # Basic Dockerfile validation
                has_from = "FROM" in content
                has_cmd_or_entrypoint = "CMD" in content or "ENTRYPOINT" in content
                
                valid = has_from and has_cmd_or_entrypoint
                duration = (time.time() - start) * 1000
                
                results.append(ValidationResult(
                    name=f"dockerfile_valid:{dockerfile}",
                    passed=valid,
                    message=f"{dockerfile} is valid" if valid else f"{dockerfile} missing FROM or CMD",
                    duration_ms=duration,
                ))
        
        return results
    
    async def _validate_api(
        self,
        context: EnvGenerationContext,
    ) -> List[ValidationResult]:
        """Validate API endpoints (requires running server)"""
        results = []
        
        try:
            import requests
        except ImportError:
            results.append(ValidationResult(
                name="api_health",
                passed=True,
                message="requests library not available, skipping API tests",
            ))
            return results
        
        base_url = f"http://localhost:{context.api_port}"
        
        # Test health endpoint
        start = time.time()
        try:
            resp = requests.get(f"{base_url}/health", timeout=5)
            valid = resp.status_code == 200
            duration = (time.time() - start) * 1000
            
            results.append(ValidationResult(
                name="api_health",
                passed=valid,
                message="API health check passed" if valid else f"Health check failed: {resp.status_code}",
                duration_ms=duration,
            ))
        except requests.exceptions.ConnectionError:
            duration = (time.time() - start) * 1000
            results.append(ValidationResult(
                name="api_health",
                passed=False,
                message=f"Cannot connect to API at {base_url}",
                duration_ms=duration,
            ))
        except Exception as e:
            duration = (time.time() - start) * 1000
            results.append(ValidationResult(
                name="api_health",
                passed=False,
                message=f"API health check error: {e}",
                duration_ms=duration,
            ))
        
        # Test root endpoint
        start = time.time()
        try:
            resp = requests.get(f"{base_url}/", timeout=5)
            valid = resp.status_code == 200
            duration = (time.time() - start) * 1000
            
            results.append(ValidationResult(
                name="api_root",
                passed=valid,
                message="API root endpoint accessible" if valid else f"Root endpoint failed: {resp.status_code}",
                duration_ms=duration,
            ))
        except Exception as e:
            duration = (time.time() - start) * 1000
            results.append(ValidationResult(
                name="api_root",
                passed=False,
                message=f"API root endpoint error: {e}",
                duration_ms=duration,
            ))
        
        return results
    
    async def _validate_openenv(
        self,
        context: EnvGenerationContext,
        output_dir: Path,
    ) -> List[ValidationResult]:
        """Validate OpenEnv interface"""
        results = []
        
        # Check OpenEnv models
        models_file = output_dir / "openenv_adapter" / "models.py"
        if models_file.exists():
            start = time.time()
            content = models_file.read_text(encoding="utf-8")
            
            # Check for required classes
            has_action = f"{context.class_name}Action" in content
            has_observation = f"{context.class_name}Observation" in content
            has_state = f"{context.class_name}State" in content
            
            valid = has_action and has_observation and has_state
            duration = (time.time() - start) * 1000
            
            results.append(ValidationResult(
                name="openenv_models",
                passed=valid,
                message="OpenEnv models are complete" if valid else "OpenEnv models missing required classes",
                details={
                    "has_action": has_action,
                    "has_observation": has_observation,
                    "has_state": has_state,
                },
                duration_ms=duration,
            ))
        
        # Check OpenEnv client
        client_file = output_dir / "openenv_adapter" / "client.py"
        if client_file.exists():
            start = time.time()
            content = client_file.read_text(encoding="utf-8")
            
            # Check for required methods
            has_step_payload = "_step_payload" in content
            has_parse_result = "_parse_result" in content
            has_parse_state = "_parse_state" in content
            
            valid = has_step_payload and has_parse_result and has_parse_state
            duration = (time.time() - start) * 1000
            
            results.append(ValidationResult(
                name="openenv_client",
                passed=valid,
                message="OpenEnv client is complete" if valid else "OpenEnv client missing required methods",
                details={
                    "has_step_payload": has_step_payload,
                    "has_parse_result": has_parse_result,
                    "has_parse_state": has_parse_state,
                },
                duration_ms=duration,
            ))
        
        # Check OpenEnv environment
        env_file = output_dir / "openenv_adapter" / "server" / "environment.py"
        if env_file.exists():
            start = time.time()
            content = env_file.read_text(encoding="utf-8")
            
            # Check for required methods
            has_reset = "def reset(" in content
            has_step = "def step(" in content
            has_state = "def state(" in content or "@property" in content
            
            valid = has_reset and has_step and has_state
            duration = (time.time() - start) * 1000
            
            results.append(ValidationResult(
                name="openenv_environment",
                passed=valid,
                message="OpenEnv environment is complete" if valid else "OpenEnv environment missing required methods",
                details={
                    "has_reset": has_reset,
                    "has_step": has_step,
                    "has_state": has_state,
                },
                duration_ms=duration,
            ))
        
        # Check OpenEnv app
        app_file = output_dir / "openenv_adapter" / "server" / "app.py"
        if app_file.exists():
            start = time.time()
            content = app_file.read_text(encoding="utf-8")
            
            # Check for FastAPI app and create_app
            has_app = "app = " in content or "create_app" in content
            has_fastapi = "FastAPI" in content or "create_app" in content
            
            valid = has_app and has_fastapi
            duration = (time.time() - start) * 1000
            
            results.append(ValidationResult(
                name="openenv_app",
                passed=valid,
                message="OpenEnv app is complete" if valid else "OpenEnv app missing FastAPI setup",
                duration_ms=duration,
            ))
        
        return results
    
    async def _generate_test_files(
        self,
        context: EnvGenerationContext,
        output_dir: Path,
    ) -> None:
        """Generate test files for the environment"""
        tests_dir = output_dir / "tests"
        tests_dir.mkdir(exist_ok=True)
        
        # Generate conftest.py
        conftest = self._generate_conftest(context)
        (tests_dir / "conftest.py").write_text(conftest, encoding="utf-8")
        
        # Generate test_api.py
        test_api = self._generate_test_api(context)
        (tests_dir / "test_api.py").write_text(test_api, encoding="utf-8")
        
        # Generate test_openenv.py
        test_openenv = self._generate_test_openenv(context)
        (tests_dir / "test_openenv.py").write_text(test_openenv, encoding="utf-8")
        
        # Generate __init__.py
        (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    
    def _generate_conftest(self, context: EnvGenerationContext) -> str:
        """Generate pytest conftest.py"""
        return f'''"""
Test configuration for {context.display_name}
"""

import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "{context.name}_api"))
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def api_client():
    """Create test client for API"""
    from main import app
    return TestClient(app)


@pytest.fixture
def auth_token(api_client):
    """Get authentication token for tests"""
    # Register test user
    api_client.post("/api/v1/auth/register", json={{
        "email": "test@example.com",
        "password": "testpassword123",
    }})
    
    # Login and get token
    response = api_client.post("/api/v1/auth/login", json={{
        "email": "test@example.com",
        "password": "testpassword123",
    }})
    
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


@pytest.fixture
def auth_headers(auth_token):
    """Get authorization headers"""
    if auth_token:
        return {{"Authorization": f"Bearer {{auth_token}}"}}
    return {{}}
'''
    
    def _generate_test_api(self, context: EnvGenerationContext) -> str:
        """Generate API tests"""
        return f'''"""
API tests for {context.display_name}
"""

import pytest


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self, api_client):
        """Test /health endpoint returns 200"""
        response = api_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_root_endpoint(self, api_client):
        """Test / endpoint returns 200"""
        response = api_client.get("/")
        assert response.status_code == 200


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_register(self, api_client):
        """Test user registration"""
        response = api_client.post("/api/v1/auth/register", json={{
            "email": "newuser@example.com",
            "password": "password123",
        }})
        assert response.status_code in [200, 201, 400]  # 400 if user exists
    
    def test_login_invalid(self, api_client):
        """Test login with invalid credentials"""
        response = api_client.post("/api/v1/auth/login", json={{
            "email": "invalid@example.com",
            "password": "wrongpassword",
        }})
        assert response.status_code == 401
    
    def test_me_unauthorized(self, api_client):
        """Test /auth/me without token"""
        response = api_client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    def test_me_authorized(self, api_client, auth_headers):
        """Test /auth/me with valid token"""
        if auth_headers:
            response = api_client.get("/api/v1/auth/me", headers=auth_headers)
            assert response.status_code == 200
'''
    
    def _generate_test_openenv(self, context: EnvGenerationContext) -> str:
        """Generate OpenEnv tests"""
        return f'''"""
OpenEnv interface tests for {context.display_name}
"""

import pytest
from dataclasses import asdict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openenv_adapter.models import {context.class_name}Action, {context.class_name}Observation, {context.class_name}State
from openenv_adapter.server.environment import {context.class_name}Environment


class TestOpenEnvModels:
    """Test OpenEnv data models"""
    
    def test_action_creation(self):
        """Test creating an action"""
        action = {context.class_name}Action(
            action_type="login",
            params={{"email": "test@example.com", "password": "password"}},
        )
        assert action.action_type == "login"
        assert "email" in action.params
    
    def test_observation_creation(self):
        """Test creating an observation"""
        obs = {context.class_name}Observation(
            success=True,
            data={{"message": "test"}},
        )
        assert obs.success is True
        assert obs.data["message"] == "test"
    
    def test_state_creation(self):
        """Test creating a state"""
        state = {context.class_name}State(
            episode_id="test-episode",
            step_count=0,
        )
        assert state.episode_id == "test-episode"
        assert state.step_count == 0


class TestOpenEnvEnvironment:
    """Test OpenEnv environment implementation"""
    
    @pytest.fixture
    def env(self):
        """Create environment instance"""
        return {context.class_name}Environment(api_base_url="http://localhost:{context.api_port}")
    
    def test_reset(self, env):
        """Test environment reset"""
        obs = env.reset()
        assert isinstance(obs, {context.class_name}Observation)
        assert obs.success is True
        assert env.state.step_count == 0
    
    def test_state_after_reset(self, env):
        """Test state after reset"""
        env.reset()
        state = env.state
        assert isinstance(state, {context.class_name}State)
        assert state.episode_id is not None
    
    def test_step_increases_count(self, env):
        """Test that step increases step count"""
        env.reset()
        initial_count = env.state.step_count
        
        action = {context.class_name}Action(
            action_type="navigate",
            params={{"page": "dashboard"}},
        )
        env.step(action)
        
        assert env.state.step_count == initial_count + 1


class TestOpenEnvIntegration:
    """Integration tests for OpenEnv (requires running API)"""
    
    @pytest.mark.integration
    def test_login_flow(self):
        """Test complete login flow through OpenEnv"""
        env = {context.class_name}Environment()
        
        # Reset
        obs = env.reset()
        assert obs.success
        
        # Try to login
        action = {context.class_name}Action(
            action_type="login",
            params={{"email": "test@example.com", "password": "testpassword123"}},
        )
        obs = env.step(action)
        
        # Check result
        # Note: This will fail if user doesn't exist, which is expected
        assert isinstance(obs, {context.class_name}Observation)
'''
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """Process validation task"""
        params = task.task_params
        context = params.get("context")
        output_dir = Path(params.get("output_dir", "./generated"))
        run_docker = params.get("run_docker", False)
        run_api_tests = params.get("run_api_tests", False)
        
        if not context:
            return create_result_message(
                source_id=self.agent_id,
                target_id=task.header.source_agent_id,
                task_id=task.task_id,
                success=False,
                error_message="Context required",
            )
        
        report = await self.validate(context, output_dir, run_docker, run_api_tests)
        
        return create_result_message(
            source_id=self.agent_id,
            target_id=task.header.source_agent_id,
            task_id=task.task_id,
            success=report.passed,
            result_data=report.to_dict(),
        )

