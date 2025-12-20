"""
API Verifier - Tests backend API endpoints
"""
import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import re
import json


@dataclass
class APITestResult:
    """Result of a single API test"""
    endpoint: str
    method: str
    expected_status: int
    actual_status: Optional[int] = None
    success: bool = False
    error: Optional[str] = None
    response_body: Optional[str] = None
    response_time_ms: float = 0


@dataclass
class APIVerificationReport:
    """Complete API verification report"""
    base_url: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    results: List[APITestResult] = field(default_factory=list)
    discovered_routes: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        return (self.passed / self.total_tests * 100) if self.total_tests > 0 else 0
    
    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.total_tests > 0
    
    def summary(self) -> str:
        lines = [
            f"API Verification Report ({self.base_url})",
            f"  Total: {self.total_tests}, Passed: {self.passed}, Failed: {self.failed}",
            f"  Success Rate: {self.success_rate:.1f}%",
        ]
        if self.results:
            lines.append("  Results:")
            for r in self.results:
                status = "✓" if r.success else "✗"
                lines.append(f"    {status} {r.method} {r.endpoint} -> {r.actual_status} (expected {r.expected_status})")
                if r.error:
                    lines.append(f"      Error: {r.error}")
        return "\n".join(lines)


class APIVerifier:
    """Verifies backend API endpoints"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:5001",
        timeout: int = 10,
        logger: Optional[logging.Logger] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._logger = logger or logging.getLogger(__name__)
        
        # Standard endpoints to test
        self._standard_tests = [
            # Health checks
            {"method": "GET", "path": "/health", "expected": 200},
            {"method": "GET", "path": "/", "expected": 200},
            # Auth endpoints (should return 400/401 without proper data, not 404)
            {"method": "POST", "path": "/auth/login", "expected": [400, 401], "body": {}},
            {"method": "POST", "path": "/auth/register", "expected": [400, 409], "body": {}},
        ]
    
    async def verify_all(
        self,
        project_dir: Optional[Path] = None,
        custom_tests: Optional[List[Dict]] = None,
    ) -> APIVerificationReport:
        """
        Run all API verification tests.
        
        Args:
            project_dir: Project directory to discover routes from
            custom_tests: Additional custom tests to run
        """
        report = APIVerificationReport(base_url=self.base_url)
        
        # Discover routes if project_dir provided
        if project_dir:
            discovered = await self._discover_routes(project_dir)
            report.discovered_routes = discovered
            self._logger.info(f"Discovered {len(discovered)} routes")
        
        # Build test list
        tests = list(self._standard_tests)
        if custom_tests:
            tests.extend(custom_tests)
        
        # Add discovered routes as tests
        for route in report.discovered_routes:
            # Parse route info
            method, path = self._parse_route(route)
            if method and path:
                # Check if not already in tests
                if not any(t["path"] == path and t["method"] == method for t in tests):
                    # GET endpoints should return 200 or 401 (auth required)
                    # POST endpoints should not return 404
                    expected = [200, 401, 403] if method == "GET" else [200, 201, 400, 401, 403]
                    tests.append({"method": method, "path": path, "expected": expected})
        
        # Run tests
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            for test in tests:
                result = await self._run_test(session, test)
                report.results.append(result)
                report.total_tests += 1
                if result.success:
                    report.passed += 1
                else:
                    report.failed += 1
        
        return report
    
    async def _run_test(
        self,
        session: aiohttp.ClientSession,
        test: Dict[str, Any],
    ) -> APITestResult:
        """Run a single API test"""
        method = test["method"]
        path = test["path"]
        expected = test.get("expected", 200)
        body = test.get("body")
        
        # Normalize expected to list
        if isinstance(expected, int):
            expected = [expected]
        
        result = APITestResult(
            endpoint=path,
            method=method,
            expected_status=expected[0],  # Primary expected
        )
        
        try:
            url = f"{self.base_url}{path}"
            
            import time
            start = time.time()
            
            kwargs = {}
            if body is not None:
                kwargs["json"] = body
            
            async with session.request(method, url, **kwargs) as response:
                result.response_time_ms = (time.time() - start) * 1000
                result.actual_status = response.status
                
                try:
                    result.response_body = await response.text()
                except Exception:
                    pass
                
                # Check if status is in expected list
                # 404 is always a failure (endpoint doesn't exist)
                if response.status == 404:
                    result.success = False
                    result.error = f"Endpoint not found (404)"
                elif response.status in expected:
                    result.success = True
                else:
                    result.success = False
                    result.error = f"Unexpected status {response.status}, expected one of {expected}"
                    
        except asyncio.TimeoutError:
            result.error = "Request timed out"
        except aiohttp.ClientError as e:
            result.error = f"Connection error: {str(e)}"
        except Exception as e:
            result.error = f"Error: {str(e)}"
        
        return result
    
    async def _discover_routes(self, project_dir: Path) -> List[str]:
        """Discover API routes from backend source code"""
        routes = []
        
        # Look for route files
        routes_dir = project_dir / "app" / "backend" / "src" / "routes"
        if not routes_dir.exists():
            return routes
        
        # Parse route files
        for route_file in routes_dir.glob("*.js"):
            try:
                content = route_file.read_text()
                
                # Find router method calls
                # router.get('/path', ...) or router.post('/path', ...)
                pattern = r"router\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]"
                matches = re.findall(pattern, content, re.IGNORECASE)
                
                for method, path in matches:
                    routes.append(f"{method.upper()} {path}")
                    
            except Exception as e:
                self._logger.warning(f"Error parsing {route_file}: {e}")
        
        return routes
    
    def _parse_route(self, route: str) -> tuple:
        """Parse route string like 'GET /path' into (method, path)"""
        parts = route.strip().split(maxsplit=1)
        if len(parts) == 2:
            return parts[0].upper(), parts[1]
        return None, None


# Convenience function
async def verify_api(
    base_url: str = "http://localhost:5001",
    project_dir: Optional[Path] = None,
) -> APIVerificationReport:
    """Quick API verification"""
    verifier = APIVerifier(base_url=base_url)
    return await verifier.verify_all(project_dir=project_dir)

