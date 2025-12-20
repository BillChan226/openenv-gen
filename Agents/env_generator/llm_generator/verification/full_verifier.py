"""
Full Verifier - Comprehensive environment verification
Combines API, Browser, and Docker health checks
"""
import asyncio
import subprocess
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from .api_verifier import APIVerifier, APIVerificationReport
from .browser_verifier import BrowserVerifier, BrowserVerificationReport


@dataclass
class DockerHealthReport:
    """Docker container health status"""
    containers: Dict[str, str] = field(default_factory=dict)  # name -> status
    all_healthy: bool = False
    errors: List[str] = field(default_factory=list)
    
    def summary(self) -> str:
        lines = ["Docker Health:"]
        for name, status in self.containers.items():
            indicator = "✓" if "running" in status.lower() or "healthy" in status.lower() else "✗"
            lines.append(f"  {indicator} {name}: {status}")
        if self.errors:
            lines.append("  Errors:")
            for err in self.errors:
                lines.append(f"    - {err}")
        return "\n".join(lines)


@dataclass
class FullVerificationReport:
    """Complete verification report"""
    project_dir: str
    docker: Optional[DockerHealthReport] = None
    api: Optional[APIVerificationReport] = None
    browser: Optional[BrowserVerificationReport] = None
    overall_success: bool = False
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def summary(self) -> str:
        lines = [
            "=" * 60,
            "FULL VERIFICATION REPORT",
            "=" * 60,
            f"Project: {self.project_dir}",
            f"Overall: {'✓ PASSED' if self.overall_success else '✗ FAILED'}",
            "",
        ]
        
        if self.docker:
            lines.append(self.docker.summary())
            lines.append("")
        
        if self.api:
            lines.append(self.api.summary())
            lines.append("")
        
        if self.browser:
            lines.append(self.browser.summary())
            lines.append("")
        
        if self.issues:
            lines.append("Issues Found:")
            for issue in self.issues:
                lines.append(f"  ✗ {issue}")
            lines.append("")
        
        if self.suggestions:
            lines.append("Suggestions:")
            for sug in self.suggestions:
                lines.append(f"  → {sug}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


class FullVerifier:
    """Comprehensive environment verifier"""
    
    def __init__(
        self,
        project_dir: Path,
        backend_port: int = 5001,
        frontend_port: int = 3000,
        logger: Optional[logging.Logger] = None,
    ):
        self.project_dir = Path(project_dir)
        self.backend_url = f"http://localhost:{backend_port}"
        self.frontend_url = f"http://localhost:{frontend_port}"
        self._logger = logger or logging.getLogger(__name__)
        
        self.api_verifier = APIVerifier(
            base_url=self.backend_url,
            logger=self._logger,
        )
        self.browser_verifier = BrowserVerifier(
            base_url=self.frontend_url,
            logger=self._logger,
            screenshot_dir=self.project_dir / "verification_screenshots",
        )
    
    async def verify_all(
        self,
        skip_docker: bool = False,
        skip_api: bool = False,
        skip_browser: bool = False,
        browser_pages: Optional[List[str]] = None,
    ) -> FullVerificationReport:
        """
        Run all verification checks.
        
        Args:
            skip_docker: Skip Docker health checks
            skip_api: Skip API endpoint tests
            skip_browser: Skip browser tests
            browser_pages: List of page paths to test in browser
        """
        report = FullVerificationReport(project_dir=str(self.project_dir))
        
        # 1. Docker Health Check
        if not skip_docker:
            self._logger.info("Checking Docker health...")
            report.docker = await self._check_docker_health()
            
            if not report.docker.all_healthy:
                report.issues.append("Docker containers not healthy")
                for err in report.docker.errors:
                    report.issues.append(f"Docker: {err}")
        
        # 2. API Verification
        if not skip_api:
            self._logger.info("Verifying API endpoints...")
            report.api = await self.api_verifier.verify_all(project_dir=self.project_dir)
            
            if not report.api.all_passed:
                report.issues.append(f"API: {report.api.failed}/{report.api.total_tests} tests failed")
                
                # Add specific API issues
                for result in report.api.results:
                    if not result.success:
                        report.issues.append(f"API: {result.method} {result.endpoint} - {result.error}")
                        
                        # Add suggestions
                        if "404" in str(result.error):
                            report.suggestions.append(
                                f"Endpoint {result.endpoint} not found. Check routes/index.js to ensure it's mounted."
                            )
        
        # 3. Browser Verification
        if not skip_browser:
            self._logger.info("Verifying browser functionality...")
            report.browser = await self.browser_verifier.verify_all(pages=browser_pages)
            
            if not report.browser.all_passed:
                report.issues.append(f"Browser: {report.browser.failed}/{report.browser.total_pages} pages failed")
                
                # Add specific browser issues
                for result in report.browser.results:
                    if result.console_errors:
                        for err in result.console_errors[:3]:
                            if not self.browser_verifier._is_extension_error(err.text):
                                report.issues.append(f"JS Error on {result.url}: {err.text[:100]}")
                    
                    if result.network_errors:
                        for err in result.network_errors[:3]:
                            if "localhost" in err:
                                report.issues.append(f"Network error: {err}")
                                
                                # Add suggestions for 404s
                                if "404" in err:
                                    report.suggestions.append(
                                        f"Resource not found: {err}. Check if the API endpoint exists."
                                    )
        
        # Determine overall success
        docker_ok = report.docker is None or report.docker.all_healthy
        api_ok = report.api is None or report.api.all_passed
        browser_ok = report.browser is None or report.browser.all_passed
        
        report.overall_success = docker_ok and api_ok and browser_ok
        
        # Add general suggestions if failed
        if not report.overall_success:
            if not api_ok and report.api:
                # Check for common issues
                failed_endpoints = [r.endpoint for r in report.api.results if not r.success and "404" in str(r.error)]
                if failed_endpoints:
                    report.suggestions.append(
                        "Check app/backend/src/routes/index.js - some routes may be commented out."
                    )
        
        return report
    
    async def _check_docker_health(self) -> DockerHealthReport:
        """Check Docker container health"""
        report = DockerHealthReport()
        
        try:
            # Get container status
            result = subprocess.run(
                ["docker-compose", "-f", str(self.project_dir / "docker" / "docker-compose.yml"), "ps"],
                capture_output=True,
                text=True,
                cwd=str(self.project_dir),
            )
            
            if result.returncode != 0:
                report.errors.append(f"docker-compose ps failed: {result.stderr}")
                return report
            
            # Parse output
            lines = result.stdout.strip().split("\n")
            for line in lines[1:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[0]
                        # Find status in line
                        if "Up" in line:
                            status = "running"
                            if "healthy" in line.lower():
                                status = "healthy"
                            elif "unhealthy" in line.lower():
                                status = "unhealthy"
                        elif "Exit" in line:
                            status = "exited"
                        else:
                            status = "unknown"
                        
                        report.containers[name] = status
            
            # Check if all are healthy/running
            report.all_healthy = all(
                s in ["running", "healthy"] 
                for s in report.containers.values()
            ) and len(report.containers) > 0
            
            # Check for exited containers
            exited = [n for n, s in report.containers.items() if s == "exited"]
            if exited:
                report.errors.append(f"Containers exited: {', '.join(exited)}")
                
                # Get logs for exited containers
                for name in exited[:2]:  # Limit to 2
                    logs = subprocess.run(
                        ["docker", "logs", name, "--tail", "10"],
                        capture_output=True,
                        text=True,
                    )
                    if logs.stdout or logs.stderr:
                        report.errors.append(f"Logs for {name}: {(logs.stdout + logs.stderr)[:200]}")
                        
        except FileNotFoundError:
            report.errors.append("docker-compose not found")
        except Exception as e:
            report.errors.append(f"Error checking Docker: {str(e)}")
        
        return report


# Convenience function
async def verify_environment(
    project_dir: Path,
    backend_port: int = 5001,
    frontend_port: int = 3000,
) -> FullVerificationReport:
    """Quick full verification"""
    verifier = FullVerifier(
        project_dir=project_dir,
        backend_port=backend_port,
        frontend_port=frontend_port,
    )
    return await verifier.verify_all()

