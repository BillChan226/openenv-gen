"""
Docker-based Runtime Testing

Tests the generated web environment using Docker Compose:
1. Build and start all containers (frontend, backend, database, openenv)
2. Wait for services to be healthy
3. Test API endpoints
4. Test frontend accessibility
5. Capture logs for debugging
6. Report issues for agent to fix

Usage:
    tester = DockerTester(env_dir)
    report = await tester.run_tests()
    
    if not report.success:
        # Agent can use report.issues to fix problems
        for issue in report.issues:
            print(f"Issue: {issue}")
"""

import asyncio
import subprocess
import time
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import httpx


@dataclass
class ServiceStatus:
    """Status of a single service."""
    name: str
    running: bool = False
    healthy: bool = False
    port: Optional[int] = None
    error: str = ""
    logs: str = ""


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    success: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0


@dataclass
class DockerTestReport:
    """Complete test report."""
    success: bool = False
    services: Dict[str, ServiceStatus] = field(default_factory=dict)
    tests: List[TestResult] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    total_duration: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "services": {k: v.__dict__ for k, v in self.services.items()},
            "tests": [t.__dict__ for t in self.tests],
            "issues": self.issues,
            "suggestions": self.suggestions,
            "total_duration": self.total_duration,
        }


class DockerTester:
    """
    Tests generated environment using Docker Compose.
    
    Expected directory structure:
    env_dir/
    ├── app/
    │   ├── frontend/
    │   ├── backend/
    │   └── database/
    ├── env/
    │   └── server/
    └── docker/
        └── docker-compose.yml
    """
    
    def __init__(
        self,
        env_dir: Path,
        compose_file: str = "docker/docker-compose.yml",
        frontend_port: int = 3000,
        backend_port: int = 5000,
        openenv_port: int = 8000,
        timeout: int = 120,
    ):
        self.env_dir = Path(env_dir)
        self.compose_file = self.env_dir / compose_file
        self.frontend_port = frontend_port
        self.backend_port = backend_port
        self.openenv_port = openenv_port
        self.timeout = timeout
        
        self.services = {
            "frontend": ServiceStatus(name="frontend", port=frontend_port),
            "backend": ServiceStatus(name="backend", port=backend_port),
            "database": ServiceStatus(name="database", port=5432),
            "openenv": ServiceStatus(name="openenv", port=openenv_port),
        }
    
    async def run_tests(self) -> DockerTestReport:
        """Run all tests and return report."""
        start_time = time.time()
        report = DockerTestReport()
        
        try:
            # Step 1: Validate docker-compose.yml exists
            if not self.compose_file.exists():
                report.issues.append(f"docker-compose.yml not found at {self.compose_file}")
                report.suggestions.append("Generate docker/docker-compose.yml first")
                return report
            
            # Step 2: Build containers
            build_result = await self._build_containers()
            report.tests.append(build_result)
            if not build_result.success:
                report.issues.append(f"Docker build failed: {build_result.message}")
                report.suggestions.append("Check Dockerfiles for syntax errors")
                return report
            
            # Step 3: Start containers
            start_result = await self._start_containers()
            report.tests.append(start_result)
            if not start_result.success:
                report.issues.append(f"Docker start failed: {start_result.message}")
                await self._capture_logs(report)
                return report
            
            # Step 4: Wait for services to be healthy
            health_result = await self._wait_for_health()
            report.tests.append(health_result)
            report.services = self.services
            
            if not health_result.success:
                report.issues.append("Services failed to become healthy")
                await self._capture_logs(report)
                # Continue with API tests even if not all services are healthy
            
            # Step 5: Test backend API
            api_tests = await self._test_backend_api()
            report.tests.extend(api_tests)
            
            # Step 6: Test frontend accessibility
            frontend_test = await self._test_frontend()
            report.tests.append(frontend_test)
            
            # Step 7: Analyze results
            failed_tests = [t for t in report.tests if not t.success]
            report.success = len(failed_tests) == 0
            
            if not report.success:
                for test in failed_tests:
                    report.issues.append(f"{test.name}: {test.message}")
                await self._capture_logs(report)
                self._generate_suggestions(report)
            
        except Exception as e:
            report.issues.append(f"Unexpected error: {str(e)}")
            
        finally:
            report.total_duration = time.time() - start_time
        
        return report
    
    async def _build_containers(self) -> TestResult:
        """Build Docker containers."""
        start = time.time()
        try:
            result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "build"],
                cwd=self.env_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            if result.returncode != 0:
                # Keep more of the error message for better analysis
                error_msg = result.stderr if len(result.stderr) < 2000 else result.stderr[-2000:]
                return TestResult(
                    name="docker_build",
                    success=False,
                    message=error_msg,
                    details={"stdout": result.stdout, "stderr": result.stderr},
                    duration=time.time() - start,
                )
            
            return TestResult(
                name="docker_build",
                success=True,
                message="All containers built successfully",
                duration=time.time() - start,
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                name="docker_build",
                success=False,
                message="Build timed out after 300 seconds",
                duration=time.time() - start,
            )
        except Exception as e:
            return TestResult(
                name="docker_build",
                success=False,
                message=str(e),
                duration=time.time() - start,
            )
    
    async def _start_containers(self) -> TestResult:
        """Start Docker containers."""
        start = time.time()
        try:
            result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "up", "-d"],
                cwd=self.env_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode != 0:
                return TestResult(
                    name="docker_start",
                    success=False,
                    message=result.stderr[:500],
                    details={"stdout": result.stdout, "stderr": result.stderr},
                    duration=time.time() - start,
                )
            
            return TestResult(
                name="docker_start",
                success=True,
                message="All containers started",
                duration=time.time() - start,
            )
            
        except Exception as e:
            return TestResult(
                name="docker_start",
                success=False,
                message=str(e),
                duration=time.time() - start,
            )
    
    async def _wait_for_health(self, max_wait: int = 60) -> TestResult:
        """Wait for all services to be healthy."""
        start = time.time()
        
        health_checks = {
            "backend": f"http://localhost:{self.backend_port}/api/health",
            "frontend": f"http://localhost:{self.frontend_port}/",
            "openenv": f"http://localhost:{self.openenv_port}/",
        }
        
        healthy_services = set()
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            while time.time() - start < max_wait:
                for service, url in health_checks.items():
                    if service in healthy_services:
                        continue
                    
                    try:
                        response = await client.get(url)
                        if response.status_code < 500:
                            healthy_services.add(service)
                            self.services[service].running = True
                            self.services[service].healthy = True
                    except:
                        pass
                
                if len(healthy_services) >= 2:  # At least backend + frontend
                    break
                
                await asyncio.sleep(2)
        
        all_healthy = len(healthy_services) >= 2
        
        return TestResult(
            name="health_check",
            success=all_healthy,
            message=f"Healthy services: {healthy_services}" if all_healthy else f"Only {healthy_services} became healthy",
            details={"healthy": list(healthy_services), "timeout": max_wait},
            duration=time.time() - start,
        )
    
    async def _test_backend_api(self) -> List[TestResult]:
        """Test backend API endpoints."""
        results = []
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            base_url = f"http://localhost:{self.backend_port}/api"
            
            # Test 1: Health endpoint
            try:
                start = time.time()
                response = await client.get(f"{base_url}/health")
                results.append(TestResult(
                    name="api_health",
                    success=response.status_code == 200,
                    message=f"Status: {response.status_code}",
                    details={"response": response.text[:200]},
                    duration=time.time() - start,
                ))
            except Exception as e:
                results.append(TestResult(
                    name="api_health",
                    success=False,
                    message=str(e),
                ))
            
            # Test 2: Auth register
            try:
                start = time.time()
                response = await client.post(
                    f"{base_url}/auth/register",
                    json={"email": "test@test.com", "password": "test123456", "name": "Test"}
                )
                results.append(TestResult(
                    name="api_register",
                    success=response.status_code in [200, 201, 400],  # 400 = already exists is ok
                    message=f"Status: {response.status_code}",
                    details={"response": response.text[:200]},
                    duration=time.time() - start,
                ))
            except Exception as e:
                results.append(TestResult(
                    name="api_register",
                    success=False,
                    message=str(e),
                ))
            
            # Test 3: Auth login
            try:
                start = time.time()
                response = await client.post(
                    f"{base_url}/auth/login",
                    json={"email": "user@example.com", "password": "user123"}  # Seeded user
                )
                results.append(TestResult(
                    name="api_login",
                    success=response.status_code == 200,
                    message=f"Status: {response.status_code}",
                    details={"response": response.text[:200]},
                    duration=time.time() - start,
                ))
            except Exception as e:
                results.append(TestResult(
                    name="api_login",
                    success=False,
                    message=str(e),
                ))
        
        return results
    
    async def _test_frontend(self) -> TestResult:
        """Test frontend accessibility."""
        start = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"http://localhost:{self.frontend_port}/")
                
                # Check for React app indicators
                is_react = "root" in response.text or "React" in response.text
                
                return TestResult(
                    name="frontend_accessible",
                    success=response.status_code == 200 and is_react,
                    message=f"Status: {response.status_code}, React app: {is_react}",
                    details={"content_length": len(response.text)},
                    duration=time.time() - start,
                )
        except Exception as e:
            return TestResult(
                name="frontend_accessible",
                success=False,
                message=str(e),
                duration=time.time() - start,
            )
    
    async def _capture_logs(self, report: DockerTestReport) -> None:
        """Capture logs from failing containers."""
        try:
            result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "logs", "--tail=50"],
                cwd=self.env_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            # Parse logs by service
            current_service = None
            for line in result.stdout.split("\n"):
                for service in self.services:
                    if line.startswith(f"{service}_") or f"|{service}" in line.lower():
                        current_service = service
                        break
                
                if current_service:
                    self.services[current_service].logs += line + "\n"
                    
                    # Detect common errors
                    if "error" in line.lower() or "Error" in line:
                        self.services[current_service].error = line[:200]
                        
        except Exception as e:
            report.issues.append(f"Failed to capture logs: {str(e)}")
    
    def _generate_suggestions(self, report: DockerTestReport) -> None:
        """Generate fix suggestions based on issues."""
        for service, status in self.services.items():
            if status.error:
                if "ECONNREFUSED" in status.error:
                    report.suggestions.append(f"{service}: Check if the service is listening on the correct port")
                elif "ModuleNotFoundError" in status.error or "Cannot find module" in status.error:
                    report.suggestions.append(f"{service}: Install missing dependencies")
                elif "SyntaxError" in status.error:
                    report.suggestions.append(f"{service}: Fix syntax error in source code")
                elif "ENOENT" in status.error:
                    report.suggestions.append(f"{service}: Check file paths and ensure files exist")
                elif "permission denied" in status.error.lower():
                    report.suggestions.append(f"{service}: Check file permissions")
            
            # Parse detailed SQL errors from logs
            if status.logs:
                sql_fixes = self._parse_sql_errors(status.logs)
                report.suggestions.extend(sql_fixes)
    
    def _parse_sql_errors(self, logs: str) -> List[str]:
        """Parse SQL errors and generate specific fix suggestions."""
        suggestions = []
        
        import re
        
        # Pattern: column "X" of relation "Y" does not exist
        col_pattern = r'column "(\w+)" of relation "(\w+)" does not exist'
        for match in re.finditer(col_pattern, logs):
            col, table = match.groups()
            suggestions.append(
                f"SQL_FIX: Column '{col}' missing in table '{table}'. "
                f"Either add '{col}' to 01_schema.sql CREATE TABLE {table}, "
                f"or remove '{col}' from INSERT statements in 02_seed.sql"
            )
        
        # Pattern: relation "X" does not exist
        rel_pattern = r'relation "(\w+)" does not exist'
        for match in re.finditer(rel_pattern, logs):
            table = match.group(1)
            suggestions.append(
                f"SQL_FIX: Table '{table}' not found. Add CREATE TABLE {table} to 01_schema.sql"
            )
        
        # Pattern: duplicate key value violates unique constraint
        dup_pattern = r'duplicate key value violates unique constraint "(\w+)"'
        for match in re.finditer(dup_pattern, logs):
            constraint = match.group(1)
            suggestions.append(
                f"SQL_FIX: Duplicate key for constraint '{constraint}'. "
                f"Add ON CONFLICT clause to INSERT statements in 02_seed.sql"
            )
        
        # Pattern: function X does not exist
        func_pattern = r'function (\w+)\([^)]*\) does not exist'
        for match in re.finditer(func_pattern, logs):
            func = match.group(1)
            suggestions.append(
                f"SQL_FIX: Function '{func}' not found. Add CREATE FUNCTION {func} to 03_functions.sql"
            )
        
        # Pattern: syntax error at or near "X"
        syntax_pattern = r'syntax error at or near "([^"]+)"'
        for match in re.finditer(syntax_pattern, logs):
            token = match.group(1)
            suggestions.append(
                f"SQL_FIX: SQL syntax error near '{token}'. Check SQL files for typos"
            )
        
        return suggestions
    
    def analyze_and_fix_errors(self, report: DockerTestReport) -> dict:
        """
        Analyze errors and return structured fix instructions.
        
        Returns dict with:
        - file_fixes: List of {file, action, details}
        - regenerate_files: List of files to regenerate
        - manual_review: List of issues requiring manual review
        """
        result = {
            "file_fixes": [],
            "regenerate_files": [],
            "manual_review": [],
        }
        
        for suggestion in report.suggestions:
            if suggestion.startswith("SQL_FIX:"):
                # Parse SQL fix suggestion
                if "missing in table" in suggestion:
                    # Extract column and table
                    import re
                    match = re.search(r"Column '(\w+)' missing in table '(\w+)'", suggestion)
                    if match:
                        col, table = match.groups()
                        result["file_fixes"].append({
                            "file": "app/database/init/02_seed.sql",
                            "action": "remove_column_from_insert",
                            "table": table,
                            "column": col,
                            "description": f"Remove '{col}' from INSERT INTO {table}"
                        })
                elif "Table" in suggestion and "not found" in suggestion:
                    result["regenerate_files"].append("app/database/init/01_schema.sql")
            
            elif "Install missing dependencies" in suggestion:
                if "frontend" in suggestion.lower():
                    result["file_fixes"].append({
                        "file": "app/frontend/package.json",
                        "action": "add_dependency",
                        "description": "Add missing npm dependency"
                    })
                elif "backend" in suggestion.lower():
                    result["file_fixes"].append({
                        "file": "app/backend/package.json", 
                        "action": "add_dependency",
                        "description": "Add missing npm dependency"
                    })
            
            else:
                result["manual_review"].append(suggestion)
        
        return result
    
    async def stop_containers(self) -> None:
        """Stop and remove containers."""
        try:
            subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "down", "-v"],
                cwd=self.env_dir,
                capture_output=True,
                timeout=60,
            )
        except:
            pass
    
    async def get_service_logs(self, service: str) -> str:
        """Get logs for a specific service."""
        try:
            result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "logs", "--tail=100", service],
                cwd=self.env_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout
        except:
            return ""


# Convenience function for orchestrator
async def test_docker_environment(env_dir: Path) -> DockerTestReport:
    """Run Docker-based tests on generated environment."""
    tester = DockerTester(env_dir)
    try:
        report = await tester.run_tests()
        return report
    finally:
        await tester.stop_containers()

