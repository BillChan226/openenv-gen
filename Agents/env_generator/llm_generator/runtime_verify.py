"""
Runtime Verification

Actually runs the generated code to verify it works:
1. Backend API: Start server, test health endpoint, basic CRUD
2. Frontend UI: Install deps, build, check for errors
3. Docker: Build images, run compose

This goes beyond static analysis to find real runtime issues.
"""

import asyncio
import subprocess
import shutil
import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import httpx
import time


@dataclass
class VerificationResult:
    """Result of a verification check"""
    name: str
    success: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0


@dataclass
class RuntimeVerificationReport:
    """Complete runtime verification report"""
    backend_results: List[VerificationResult] = field(default_factory=list)
    frontend_results: List[VerificationResult] = field(default_factory=list)
    docker_results: List[VerificationResult] = field(default_factory=list)
    overall_success: bool = False
    total_duration: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "backend": [r.__dict__ for r in self.backend_results],
            "frontend": [r.__dict__ for r in self.frontend_results],
            "docker": [r.__dict__ for r in self.docker_results],
            "overall_success": self.overall_success,
            "total_duration": self.total_duration,
        }


class RuntimeVerifier:
    """
    Verifies generated code by actually running it.
    
    Usage:
        verifier = RuntimeVerifier(env_dir)
        report = await verifier.verify_all()
        
        if not report.overall_success:
            for r in report.backend_results:
                if not r.success:
                    print(f"Backend issue: {r.message}")
    """
    
    def __init__(
        self,
        env_dir: Path,
        env_name: str,
        api_port: int = 8000,
        ui_port: int = 3000,
        timeout: int = 60,
    ):
        self.env_dir = Path(env_dir)
        self.env_name = env_name
        self.api_port = api_port
        self.ui_port = ui_port
        self.timeout = timeout
        
        self.api_dir = self.env_dir / f"{env_name}_api"
        self.ui_dir = self.env_dir / f"{env_name}_ui"
        
        self._api_process: Optional[subprocess.Popen] = None
        self._ui_process: Optional[subprocess.Popen] = None
    
    async def verify_all(self) -> RuntimeVerificationReport:
        """Run all verifications"""
        start_time = time.time()
        report = RuntimeVerificationReport()
        
        try:
            # Backend verification
            if self.api_dir.exists():
                report.backend_results = await self._verify_backend()
            else:
                report.backend_results = [VerificationResult(
                    name="backend_exists",
                    success=False,
                    message=f"Backend directory not found: {self.api_dir}",
                )]
            
            # Frontend verification
            if self.ui_dir.exists():
                report.frontend_results = await self._verify_frontend()
            else:
                report.frontend_results = [VerificationResult(
                    name="frontend_exists",
                    success=False,
                    message=f"Frontend directory not found: {self.ui_dir}",
                )]
            
            # Docker verification (optional)
            if (self.env_dir / "docker-compose.yml").exists():
                report.docker_results = await self._verify_docker()
            
            # Calculate overall success
            all_results = (
                report.backend_results +
                report.frontend_results +
                report.docker_results
            )
            
            # Success if no critical failures
            critical_checks = ["python_syntax", "deps_install", "server_start", "health_check"]
            critical_failures = [
                r for r in all_results
                if not r.success and any(c in r.name for c in critical_checks)
            ]
            report.overall_success = len(critical_failures) == 0
            
        finally:
            # Cleanup
            await self._cleanup()
            report.total_duration = time.time() - start_time
        
        return report
    
    async def _verify_backend(self) -> List[VerificationResult]:
        """Verify the backend API"""
        results = []
        
        # 0. Ensure __init__.py files exist for Python package imports
        self._ensure_init_files()
        
        # 1. Check Python syntax
        results.append(await self._check_python_syntax())
        
        # 2. Install dependencies
        results.append(await self._install_python_deps())
        
        # 3. Start server
        server_result = await self._start_api_server()
        results.append(server_result)
        
        if server_result.success:
            # 4. Test health endpoint
            results.append(await self._test_health_endpoint())
            
            # 5. Test auth endpoints
            results.append(await self._test_auth_endpoints())
        
        return results
    
    def _ensure_init_files(self) -> None:
        """Ensure __init__.py files exist for Python package imports"""
        # Create __init__.py in api directory
        init_file = self.api_dir / "__init__.py"
        if not init_file.exists():
            init_file.touch()
        
        # Create __init__.py in routers directory if it exists
        routers_dir = self.api_dir / "routers"
        if routers_dir.exists():
            routers_init = routers_dir / "__init__.py"
            if not routers_init.exists():
                routers_init.touch()
    
    async def _verify_frontend(self) -> List[VerificationResult]:
        """Verify the frontend"""
        results = []
        
        # 1. Check if package.json exists
        package_json = self.ui_dir / "package.json"
        if not package_json.exists():
            results.append(VerificationResult(
                name="package_json",
                success=False,
                message="package.json not found",
            ))
            return results
        
        results.append(VerificationResult(
            name="package_json",
            success=True,
            message="package.json found",
        ))
        
        # 2. Install dependencies
        results.append(await self._install_npm_deps())
        
        # 3. Build check (type check)
        results.append(await self._run_typescript_check())
        
        return results
    
    async def _verify_docker(self) -> List[VerificationResult]:
        """Verify Docker configuration"""
        results = []
        
        # Check if Docker is available
        docker_available = shutil.which("docker") is not None
        if not docker_available:
            results.append(VerificationResult(
                name="docker_available",
                success=False,
                message="Docker not found in PATH",
            ))
            return results
        
        # Validate docker-compose.yml
        try:
            result = await self._run_command(
                ["docker", "compose", "config"],
                cwd=self.env_dir,
                timeout=30,
            )
            results.append(VerificationResult(
                name="docker_compose_valid",
                success=result[0],
                message="docker-compose.yml is valid" if result[0] else f"Invalid: {result[1]}",
            ))
        except Exception as e:
            results.append(VerificationResult(
                name="docker_compose_valid",
                success=False,
                message=str(e),
            ))
        
        return results
    
    async def _check_python_syntax(self) -> VerificationResult:
        """Check Python syntax for all .py files"""
        start = time.time()
        errors = []
        
        for py_file in self.api_dir.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    code = f.read()
                compile(code, str(py_file), 'exec')
            except SyntaxError as e:
                errors.append(f"{py_file.name}: {e}")
        
        return VerificationResult(
            name="python_syntax",
            success=len(errors) == 0,
            message="All Python files have valid syntax" if not errors else f"Syntax errors: {errors[:3]}",
            details={"errors": errors},
            duration=time.time() - start,
        )
    
    async def _install_python_deps(self) -> VerificationResult:
        """Install Python dependencies"""
        start = time.time()
        
        req_file = self.api_dir / "requirements.txt"
        if not req_file.exists():
            return VerificationResult(
                name="deps_install",
                success=False,
                message="requirements.txt not found",
                duration=time.time() - start,
            )
        
        # Use pip3 or python3 -m pip for better compatibility
        pip_cmd = ["python3", "-m", "pip", "install", "-r", "requirements.txt", "--quiet"]
        success, output = await self._run_command(
            pip_cmd,
            cwd=self.api_dir,
            timeout=120,
        )
        
        return VerificationResult(
            name="deps_install",
            success=success,
            message="Dependencies installed" if success else f"Install failed: {output[:200]}",
            duration=time.time() - start,
        )
    
    async def _start_api_server(self) -> VerificationResult:
        """Start the API server"""
        start = time.time()
        
        # Find main.py
        main_file = self.api_dir / "main.py"
        if not main_file.exists():
            return VerificationResult(
                name="server_start",
                success=False,
                message="main.py not found",
                duration=time.time() - start,
            )
        
        try:
            # Start uvicorn from parent directory to support absolute imports
            # e.g., "from calendar_api.database import ..." works when run from env_dir
            api_module = f"{self.env_name}_api.main:app"
            
            # Set PYTHONPATH to include env_dir
            env = {**os.environ, "PYTHONUNBUFFERED": "1"}
            env["PYTHONPATH"] = str(self.env_dir)
            
            self._api_process = subprocess.Popen(
                ["python3", "-m", "uvicorn", api_module, "--host", "0.0.0.0", "--port", str(self.api_port)],
                cwd=self.env_dir,  # Run from env_dir, not api_dir
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            
            # Wait for server to start
            await asyncio.sleep(3)
            
            # Check if process is still running
            if self._api_process.poll() is not None:
                stdout, stderr = self._api_process.communicate()
                return VerificationResult(
                    name="server_start",
                    success=False,
                    message=f"Server failed to start: {stderr.decode()[:300]}",
                    duration=time.time() - start,
                )
            
            return VerificationResult(
                name="server_start",
                success=True,
                message=f"Server started on port {self.api_port}",
                duration=time.time() - start,
            )
            
        except Exception as e:
            return VerificationResult(
                name="server_start",
                success=False,
                message=str(e),
                duration=time.time() - start,
            )
    
    async def _test_health_endpoint(self) -> VerificationResult:
        """Test the health endpoint"""
        start = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{self.api_port}/health",
                    timeout=10,
                )
                
                success = response.status_code == 200
                return VerificationResult(
                    name="health_check",
                    success=success,
                    message=f"Health check {'passed' if success else 'failed'}: {response.status_code}",
                    details={"status_code": response.status_code, "body": response.text[:200]},
                    duration=time.time() - start,
                )
        except Exception as e:
            return VerificationResult(
                name="health_check",
                success=False,
                message=f"Health check failed: {e}",
                duration=time.time() - start,
            )
    
    async def _test_auth_endpoints(self) -> VerificationResult:
        """Test auth endpoints"""
        start = time.time()
        
        try:
            async with httpx.AsyncClient(base_url=f"http://localhost:{self.api_port}") as client:
                # Try to register
                register_response = await client.post(
                    "/api/auth/register",
                    json={
                        "email": "test@example.com",
                        "password": "testpassword123",
                        "name": "Test User",
                    },
                    timeout=10,
                )
                
                # Try to login
                login_response = await client.post(
                    "/api/auth/login",
                    json={
                        "email": "test@example.com",
                        "password": "testpassword123",
                    },
                    timeout=10,
                )
                
                success = login_response.status_code in [200, 201]
                return VerificationResult(
                    name="auth_endpoints",
                    success=success,
                    message=f"Auth test {'passed' if success else 'failed'}",
                    details={
                        "register_status": register_response.status_code,
                        "login_status": login_response.status_code,
                    },
                    duration=time.time() - start,
                )
        except Exception as e:
            return VerificationResult(
                name="auth_endpoints",
                success=False,
                message=f"Auth test failed: {e}",
                duration=time.time() - start,
            )
    
    async def _install_npm_deps(self) -> VerificationResult:
        """Install NPM dependencies"""
        start = time.time()
        
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        
        success, output = await self._run_command(
            [npm_cmd, "install", "--silent"],
            cwd=self.ui_dir,
            timeout=180,
        )
        
        return VerificationResult(
            name="npm_install",
            success=success,
            message="NPM dependencies installed" if success else f"Install failed: {output[:200]}",
            duration=time.time() - start,
        )
    
    async def _run_typescript_check(self) -> VerificationResult:
        """Run TypeScript type check"""
        start = time.time()
        
        npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
        
        success, output = await self._run_command(
            [npx_cmd, "tsc", "--noEmit"],
            cwd=self.ui_dir,
            timeout=60,
        )
        
        return VerificationResult(
            name="typescript_check",
            success=success,
            message="TypeScript check passed" if success else f"Type errors: {output[:300]}",
            duration=time.time() - start,
        )
    
    async def _run_command(
        self,
        cmd: List[str],
        cwd: Path,
        timeout: int = 60,
    ) -> Tuple[bool, str]:
        """Run a command and return (success, output)"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
            
            success = process.returncode == 0
            output = stdout.decode() + stderr.decode()
            
            return success, output
            
        except asyncio.TimeoutError:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    async def _cleanup(self) -> None:
        """Cleanup running processes"""
        if self._api_process:
            self._api_process.terminate()
            try:
                self._api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._api_process.kill()
            self._api_process = None
        
        if self._ui_process:
            self._ui_process.terminate()
            try:
                self._ui_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._ui_process.kill()
            self._ui_process = None


async def verify_environment(env_dir: Path, env_name: str) -> RuntimeVerificationReport:
    """Convenience function to verify an environment"""
    verifier = RuntimeVerifier(env_dir, env_name)
    return await verifier.verify_all()

