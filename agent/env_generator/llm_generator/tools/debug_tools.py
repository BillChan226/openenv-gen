"""
Debug Tools - Advanced debugging capabilities for cross-layer error tracing

This module provides tools for:
1. Cross-Layer Error Tracing - Trace errors across frontend/backend/database
2. API-Code Alignment Verification - Verify frontend calls match backend routes
3. Runtime Debug Tools - API testing, route checking, etc.
4. Enhanced Error Parsing - Pattern-based error diagnosis
"""

import re
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from workspace import Workspace

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


# ============================================================================
# Cross-Layer Error Tracing
# ============================================================================

@dataclass
class ErrorTrace:
    """Result of cross-layer error tracing."""
    origin_layer: str  # frontend, backend, database, config
    affected_layers: List[str]
    immediate_cause: str
    root_cause: str
    fix_suggestion: str
    affected_files: List[str] = field(default_factory=list)
    confidence: float = 0.0


class CrossLayerDebugger:
    """
    Trace errors across frontend -> backend -> database layers.
    
    This debugger understands common patterns that span multiple layers
    and can identify root causes that may be in a different layer than
    where the error surfaces.
    """
    
    # Pattern definitions: regex -> diagnosis info
    ERROR_PATTERNS = {
        # Database / SQL errors surfacing in backend
        r"invalid input syntax for type uuid[:\s]*['\"]?(\w+)['\"]?": {
            "origin_layer": "database",
            "affected_layers": ["backend_routing", "database"],
            "root_cause": "A specific route (like /search) is being caught by a generic :id route, passing non-UUID string to database",
            "fix_suggestion": "Move specific routes BEFORE parameterized routes in Express router. E.g., router.get('/search', ...) must come before router.get('/:id', ...)",
            "confidence": 0.95,
        },
        r"relation ['\"]?(\w+)['\"]? does not exist": {
            "origin_layer": "database",
            "affected_layers": ["database_schema", "backend_model"],
            "root_cause": "Database table does not exist - schema not applied or table name mismatch",
            "fix_suggestion": "1) Check if init scripts ran (docker-compose down -v && up). 2) Verify table name in schema matches model queries",
            "confidence": 0.9,
        },
        r"column ['\"]?(\w+)['\"]? .*does not exist": {
            "origin_layer": "database",
            "affected_layers": ["database_schema", "backend_model"],
            "root_cause": "Column name mismatch between backend model and database schema",
            "fix_suggestion": "Align column names: check SQL schema vs backend model queries. Common: snake_case in DB vs camelCase in JS",
            "confidence": 0.9,
        },
        r"duplicate key value violates unique constraint": {
            "origin_layer": "database",
            "affected_layers": ["database", "backend_validation"],
            "root_cause": "Attempting to insert duplicate value into unique column",
            "fix_suggestion": "Add existence check before insert, or use UPSERT/ON CONFLICT",
            "confidence": 0.85,
        },
        
        # Backend / Node.js errors
        r"Cannot read propert(?:y|ies) of undefined.*reading ['\"](\w+)['\"]": {
            "origin_layer": "backend",
            "affected_layers": ["backend_config", "backend_model"],
            "root_cause": "Accessing property on undefined object - likely missing config or null data",
            "fix_suggestion": "Add null checks. If config-related, verify env.js exports the expected properties",
            "confidence": 0.8,
        },
        r"Cannot destructure property ['\"](\w+)['\"].*undefined": {
            "origin_layer": "backend",
            "affected_layers": ["backend_controller", "backend_model"],
            "root_cause": "Destructuring from undefined - data not returned as expected",
            "fix_suggestion": "Add default values in destructuring: const { prop = default } = obj || {}",
            "confidence": 0.85,
        },
        r"ECONNREFUSED.*:(\d+)": {
            "origin_layer": "backend",
            "affected_layers": ["backend", "database", "docker"],
            "root_cause": "Cannot connect to service on specified port",
            "fix_suggestion": "Check if database/service is running. Verify docker-compose depends_on and healthcheck",
            "confidence": 0.9,
        },
        r"JWT.*expired|TokenExpiredError": {
            "origin_layer": "backend",
            "affected_layers": ["backend_auth"],
            "root_cause": "JWT token has expired",
            "fix_suggestion": "Check token expiration settings. For testing, increase expiresIn or refresh token",
            "confidence": 0.95,
        },
        r"Error: Route\.(\w+)\(\) requires a callback": {
            "origin_layer": "backend",
            "affected_layers": ["backend_routing"],
            "root_cause": "Route handler is undefined - import or export issue",
            "fix_suggestion": "Check import statements in routes file. Verify controller exports the function",
            "confidence": 0.9,
        },
        r"SyntaxError: The requested module.*does not provide an export named ['\"](\w+)['\"]": {
            "origin_layer": "backend",
            "affected_layers": ["backend_config", "backend_exports"],
            "root_cause": "Named export missing from module",
            "fix_suggestion": "Add the missing export to the module, or change to default export/import",
            "confidence": 0.95,
        },
        r"missing.*authorization|unauthorized|401": {
            "origin_layer": "backend",
            "affected_layers": ["backend_auth", "frontend_api"],
            "root_cause": "Request missing authentication token",
            "fix_suggestion": "Frontend must include Authorization header. Implement login flow and token storage",
            "confidence": 0.85,
        },
        
        # Frontend / React errors
        r"Objects are not valid as a React child": {
            "origin_layer": "frontend",
            "affected_layers": ["frontend_component"],
            "root_cause": "Trying to render an object directly in JSX",
            "fix_suggestion": "Use JSON.stringify() for debugging or extract specific properties to render",
            "confidence": 0.9,
        },
        r"Each child in a list should have a unique ['\"]key['\"] prop": {
            "origin_layer": "frontend",
            "affected_layers": ["frontend_component"],
            "root_cause": "Missing key prop in list rendering",
            "fix_suggestion": "Add key prop to list items in map() calls: items.map(item => <Item key={item.id} />)",
            "confidence": 0.95,
        },
        r"Invalid hook call": {
            "origin_layer": "frontend",
            "affected_layers": ["frontend_component"],
            "root_cause": "Hooks called outside function component or in wrong order",
            "fix_suggestion": "Ensure hooks are only called at top level of function components, not in conditions/loops",
            "confidence": 0.9,
        },
        r"Failed to fetch|NetworkError|ERR_CONNECTION_REFUSED": {
            "origin_layer": "frontend",
            "affected_layers": ["frontend_api", "backend", "docker"],
            "root_cause": "Frontend cannot reach backend API",
            "fix_suggestion": "Check: 1) Backend is running 2) CORS configured 3) API URL correct (use /api not localhost in Docker)",
            "confidence": 0.8,
        },
        r"ERR_NAME_NOT_RESOLVED|getaddrinfo.*ENOTFOUND": {
            "origin_layer": "frontend",
            "affected_layers": ["frontend_config", "docker"],
            "root_cause": "Frontend trying to resolve Docker service hostname from browser",
            "fix_suggestion": "Use /api (same-origin) with nginx proxy, not http://backend:8000 (Docker-only hostname)",
            "confidence": 0.95,
        },
        
        # Docker / Infrastructure errors
        r"No such container": {
            "origin_layer": "docker",
            "affected_layers": ["docker"],
            "root_cause": "Container was removed or never created - often from crashed service",
            "fix_suggestion": "Run: docker-compose down --remove-orphans && docker-compose up -d --build",
            "confidence": 0.85,
        },
        r"port is already allocated|address already in use": {
            "origin_layer": "docker",
            "affected_layers": ["docker", "host_system"],
            "root_cause": "Port conflict with existing process",
            "fix_suggestion": "Change port in docker-compose.yml or stop conflicting process: lsof -i :<port>",
            "confidence": 0.9,
        },
    }
    
    def __init__(self, workspace: Workspace = None):
        self.workspace = workspace
    
    def trace_error(self, error_message: str, context: Dict[str, Any] = None) -> ErrorTrace:
        """
        Trace an error across layers and identify root cause.
        
        Args:
            error_message: The error message to analyze
            context: Optional context (logs, file contents, etc.)
        
        Returns:
            ErrorTrace with diagnosis
        """
        error_lower = error_message.lower()
        
        for pattern, info in self.ERROR_PATTERNS.items():
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                # Extract captured groups for more specific diagnosis
                groups = match.groups()
                
                # Customize fix suggestion with captured values
                fix = info["fix_suggestion"]
                if groups:
                    fix = f"{fix} (Specific value: {groups[0]})"
                
                return ErrorTrace(
                    origin_layer=info["origin_layer"],
                    affected_layers=info["affected_layers"],
                    immediate_cause=f"Pattern matched: {pattern[:50]}...",
                    root_cause=info["root_cause"],
                    fix_suggestion=fix,
                    confidence=info["confidence"],
                )
        
        # No pattern matched - return generic trace
        return ErrorTrace(
            origin_layer="unknown",
            affected_layers=["unknown"],
            immediate_cause=error_message[:200],
            root_cause="Could not automatically determine root cause",
            fix_suggestion="Manual investigation needed. Check logs across all layers.",
            confidence=0.0,
        )
    
    def trace_multiple_errors(self, errors: List[str]) -> List[ErrorTrace]:
        """Trace multiple errors and return sorted by confidence."""
        traces = [self.trace_error(e) for e in errors]
        return sorted(traces, key=lambda t: t.confidence, reverse=True)


# ============================================================================
# API-Code Alignment Verification
# ============================================================================

@dataclass
class APICall:
    """Represents an API call from frontend code."""
    method: str
    path: str
    file: str
    line: int
    has_auth: bool = False


@dataclass
class BackendRoute:
    """Represents a backend route definition."""
    method: str
    path: str
    file: str
    line: int
    requires_auth: bool = False


@dataclass
class AlignmentIssue:
    """An issue found during API alignment verification."""
    issue_type: str  # missing_route, method_mismatch, auth_mismatch, path_mismatch
    frontend_call: Optional[APICall]
    backend_route: Optional[BackendRoute]
    description: str
    suggestion: str
    severity: str = "error"  # error, warning


class APIAlignmentVerifier:
    """
    Verify that frontend API calls match backend routes.
    
    This catches common issues like:
    - Frontend calling endpoints that don't exist
    - Method mismatches (GET vs POST)
    - Auth requirements not met
    - Path parameter mismatches
    """
    
    def __init__(self, workspace: Workspace = None):
        self.workspace = workspace
    
    def parse_frontend_api_calls(self, api_file: Path) -> List[APICall]:
        """
        Parse frontend api.js to extract all API calls.
        
        Looks for patterns like:
        - fetch(`${API_URL}/endpoint`, { method: 'POST' })
        - await api.get('/endpoint')
        """
        if not api_file.exists():
            return []
        
        content = api_file.read_text()
        calls = []
        
        # Pattern for fetch calls
        fetch_pattern = r"fetch\s*\(\s*[`'\"]([^`'\"]+)[`'\"].*?method:\s*['\"](\w+)['\"]"
        for match in re.finditer(fetch_pattern, content, re.DOTALL):
            path = match.group(1)
            method = match.group(2).upper()
            line = content[:match.start()].count('\n') + 1
            
            # Normalize path
            path = re.sub(r'\$\{[^}]+\}', '', path)  # Remove template literals
            path = re.sub(r'\?.*$', '', path)  # Remove query params
            
            calls.append(APICall(
                method=method,
                path=path,
                file=str(api_file),
                line=line,
                has_auth='Authorization' in content[max(0, match.start()-200):match.end()+200],
            ))
        
        # Pattern for simple GET (fetch without method = GET)
        simple_fetch = r"fetch\s*\(\s*[`'\"]([^`'\"]+)[`'\"](?:\s*\)|\s*,\s*\{(?!.*method))"
        for match in re.finditer(simple_fetch, content, re.DOTALL):
            path = match.group(1)
            path = re.sub(r'\$\{[^}]+\}', '', path)
            path = re.sub(r'\?.*$', '', path)
            line = content[:match.start()].count('\n') + 1
            
            calls.append(APICall(
                method="GET",
                path=path,
                file=str(api_file),
                line=line,
            ))
        
        return calls
    
    def parse_backend_routes(self, routes_dir: Path) -> List[BackendRoute]:
        """
        Parse backend routes from Express router files.
        
        Looks for patterns like:
        - router.get('/endpoint', handler)
        - router.post('/endpoint', authRequired, handler)
        """
        if not routes_dir.exists():
            return []
        
        routes = []
        
        for route_file in routes_dir.glob('*.js'):
            content = route_file.read_text()
            
            # Pattern for Express routes
            route_pattern = r"router\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]"
            for match in re.finditer(route_pattern, content, re.IGNORECASE):
                method = match.group(1).upper()
                path = match.group(2)
                line = content[:match.start()].count('\n') + 1
                
                # Check if route requires auth
                line_content = content[match.start():match.end()+200]
                requires_auth = 'authRequired' in line_content or 'authenticate' in line_content
                
                routes.append(BackendRoute(
                    method=method,
                    path=path,
                    file=str(route_file),
                    line=line,
                    requires_auth=requires_auth,
                ))
        
        return routes
    
    def normalize_path(self, path: str) -> str:
        """Normalize path for comparison (replace :params with placeholder)."""
        # Remove /api prefix
        path = re.sub(r'^/api', '', path)
        # Replace :param with {param}
        path = re.sub(r':(\w+)', r'{\1}', path)
        # Remove trailing slash
        path = path.rstrip('/')
        return path or '/'
    
    def paths_match(self, frontend_path: str, backend_path: str) -> bool:
        """Check if frontend and backend paths match (accounting for params)."""
        fp = self.normalize_path(frontend_path)
        bp = self.normalize_path(backend_path)
        
        # Exact match
        if fp == bp:
            return True
        
        # Check with parameter placeholders
        fp_parts = fp.split('/')
        bp_parts = bp.split('/')
        
        if len(fp_parts) != len(bp_parts):
            return False
        
        for fp_part, bp_part in zip(fp_parts, bp_parts):
            # Both are params or both are same literal
            if fp_part.startswith('{') or bp_part.startswith('{'):
                continue  # Param matches anything
            if fp_part != bp_part:
                return False
        
        return True
    
    def verify_alignment(
        self,
        frontend_dir: Path,
        backend_dir: Path,
    ) -> List[AlignmentIssue]:
        """
        Verify that frontend API calls align with backend routes.
        
        Returns list of issues found.
        """
        issues = []
        
        # Parse frontend API calls
        api_file = frontend_dir / "src" / "services" / "api.js"
        if not api_file.exists():
            api_file = frontend_dir / "src" / "api.js"
        
        frontend_calls = self.parse_frontend_api_calls(api_file)
        
        # Parse backend routes
        routes_dir = backend_dir / "src" / "routes"
        backend_routes = self.parse_backend_routes(routes_dir)
        
        # Check each frontend call has a matching backend route
        for call in frontend_calls:
            matching_route = None
            
            for route in backend_routes:
                if self.paths_match(call.path, route.path):
                    if call.method == route.method:
                        matching_route = route
                        break
                    elif matching_route is None:
                        # Path matches but method doesn't - potential issue
                        matching_route = route
            
            if matching_route is None:
                issues.append(AlignmentIssue(
                    issue_type="missing_backend_route",
                    frontend_call=call,
                    backend_route=None,
                    description=f"Frontend calls {call.method} {call.path} but no matching backend route exists",
                    suggestion=f"Add backend route: router.{call.method.lower()}('{call.path}', handler)",
                    severity="error",
                ))
            elif matching_route.method != call.method:
                issues.append(AlignmentIssue(
                    issue_type="method_mismatch",
                    frontend_call=call,
                    backend_route=matching_route,
                    description=f"Frontend uses {call.method} but backend expects {matching_route.method} for {call.path}",
                    suggestion=f"Change frontend to {matching_route.method} or backend to {call.method}",
                    severity="error",
                ))
            elif matching_route.requires_auth and not call.has_auth:
                issues.append(AlignmentIssue(
                    issue_type="auth_mismatch",
                    frontend_call=call,
                    backend_route=matching_route,
                    description=f"Backend route {matching_route.path} requires auth but frontend doesn't send Authorization header",
                    suggestion="Add Authorization header to frontend API call",
                    severity="warning",
                ))
        
        # Check for Express route ordering issues
        route_order_issues = self.check_route_ordering(backend_routes)
        issues.extend(route_order_issues)
        
        return issues
    
    def check_route_ordering(self, routes: List[BackendRoute]) -> List[AlignmentIssue]:
        """
        Check for Express route ordering issues.
        
        In Express, specific routes must come BEFORE parameterized routes,
        otherwise /search would be caught by /:id.
        """
        issues = []
        
        # Group routes by file
        routes_by_file: Dict[str, List[BackendRoute]] = {}
        for route in routes:
            if route.file not in routes_by_file:
                routes_by_file[route.file] = []
            routes_by_file[route.file].append(route)
        
        for file_path, file_routes in routes_by_file.items():
            # Sort by line number to get definition order
            file_routes.sort(key=lambda r: r.line)
            
            for i, route in enumerate(file_routes):
                # Check if this is a parameterized route
                if ':' not in route.path:
                    continue
                
                # Check if any specific routes come after this parameterized route
                for later_route in file_routes[i+1:]:
                    if later_route.method != route.method:
                        continue
                    
                    # Check if later route would be shadowed
                    if ':' not in later_route.path:
                        # Get base paths to compare
                        param_base = re.sub(r':[^/]+', '', route.path).rstrip('/')
                        specific_base = later_route.path.rsplit('/', 1)[0] if '/' in later_route.path else ''
                        
                        if param_base == specific_base or route.path.split('/')[:-1] == later_route.path.split('/')[:-1]:
                            issues.append(AlignmentIssue(
                                issue_type="route_order",
                                frontend_call=None,
                                backend_route=later_route,
                                description=f"Route '{later_route.path}' (line {later_route.line}) comes after parameterized route '{route.path}' (line {route.line}) - will never be reached",
                                suggestion=f"Move '{later_route.path}' BEFORE '{route.path}' in {Path(file_path).name}",
                                severity="error",
                            ))
        
        return issues


# ============================================================================
# Runtime Debug Tools
# ============================================================================

class RuntimeDebugTools:
    """Runtime debugging tools for testing APIs and checking configurations."""
    
    def __init__(self, workspace: Workspace = None):
        self.workspace = workspace
    
    async def test_api_endpoint(
        self,
        method: str,
        url: str,
        body: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Test an API endpoint and return detailed diagnostics.
        
        Returns:
            Dict with success, status_code, response_body, response_headers, timing
        """
        if not HTTPX_AVAILABLE:
            return {
                "success": False,
                "error": "httpx not installed. Run: pip install httpx",
                "error_type": "DependencyError",
            }
        
        import time
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    json=body,
                    headers=headers or {},
                )
                
                elapsed = time.time() - start_time
                
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "response_body": response.text[:2000],
                    "response_headers": dict(response.headers),
                    "timing_ms": round(elapsed * 1000, 2),
                    "request_info": {
                        "method": method.upper(),
                        "url": url,
                        "body": body,
                    },
                }
            except httpx.ConnectError as e:
                return {
                    "success": False,
                    "error": f"Connection refused: {e}",
                    "error_type": "ConnectError",
                    "suggestion": "Check if the server is running and the port is correct",
                }
            except httpx.TimeoutException:
                return {
                    "success": False,
                    "error": f"Request timed out after {timeout}s",
                    "error_type": "TimeoutError",
                    "suggestion": "Server may be overloaded or not responding",
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
    
    async def test_api_with_auth_flow(
        self,
        base_url: str,
        register_payload: Dict = None,
        login_payload: Dict = None,
        protected_endpoints: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Test a complete auth flow: register -> login -> access protected endpoints.
        
        Returns detailed results for each step.
        """
        results = {
            "register": None,
            "login": None,
            "token": None,
            "protected_tests": [],
        }
        
        # Default payloads
        if register_payload is None:
            register_payload = {
                "email": "test@example.com",
                "password": "Test123456!",
                "username": "testuser",
                "name": "Test User",
            }
        
        if login_payload is None:
            login_payload = {
                "email": register_payload.get("email", "test@example.com"),
                "password": register_payload.get("password", "Test123456!"),
            }
        
        # 1. Register
        register_result = await self.test_api_endpoint(
            method="POST",
            url=f"{base_url}/api/auth/register",
            body=register_payload,
        )
        results["register"] = register_result
        
        # 2. Login
        login_result = await self.test_api_endpoint(
            method="POST",
            url=f"{base_url}/api/auth/login",
            body=login_payload,
        )
        results["login"] = login_result
        
        # Extract token
        if login_result.get("success"):
            try:
                body = json.loads(login_result.get("response_body", "{}"))
                token = body.get("token") or body.get("accessToken") or body.get("access_token")
                results["token"] = token
            except json.JSONDecodeError:
                results["token"] = None
        
        # 3. Test protected endpoints
        if results["token"] and protected_endpoints:
            auth_headers = {"Authorization": f"Bearer {results['token']}"}
            
            for endpoint in protected_endpoints:
                method = "GET"
                url = endpoint
                
                # Support dict format for non-GET
                if isinstance(endpoint, dict):
                    method = endpoint.get("method", "GET")
                    url = endpoint.get("url", endpoint)
                
                if not url.startswith("http"):
                    url = f"{base_url}{url}"
                
                test_result = await self.test_api_endpoint(
                    method=method,
                    url=url,
                    headers=auth_headers,
                )
                results["protected_tests"].append({
                    "endpoint": url,
                    "method": method,
                    "result": test_result,
                })
        
        return results
    
    def check_express_route_file(self, route_file: Path) -> List[Dict[str, Any]]:
        """
        Check an Express route file for common issues.
        
        Issues detected:
        - Route ordering problems
        - Missing error handlers
        - Async handlers without try/catch
        """
        if not route_file.exists():
            return [{"type": "file_not_found", "message": f"File not found: {route_file}"}]
        
        content = route_file.read_text()
        issues = []
        
        # 1. Check route ordering (specific before parameterized)
        route_pattern = r"router\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]"
        routes = list(re.finditer(route_pattern, content, re.IGNORECASE))
        
        for i, route in enumerate(routes):
            method, path = route.groups()
            
            # If this is parameterized, check if specific routes come after
            if ':' in path:
                for later in routes[i+1:]:
                    later_method, later_path = later.groups()
                    if later_method.lower() == method.lower() and ':' not in later_path:
                        # Check if they share a base path
                        base = path.split('/:')[0]
                        if later_path.startswith(base):
                            issues.append({
                                "type": "route_order",
                                "line": content[:later.start()].count('\n') + 1,
                                "message": f"'{later_path}' defined after '{path}' - will never be reached",
                                "fix": f"Move router.{later_method}('{later_path}', ...) before router.{method}('{path}', ...)",
                            })
        
        # 2. Check for async handlers without proper error handling
        async_handler_pattern = r"async\s*\([^)]*\)\s*=>\s*\{(?![^}]*try)"
        for match in re.finditer(async_handler_pattern, content):
            line = content[:match.start()].count('\n') + 1
            issues.append({
                "type": "missing_try_catch",
                "line": line,
                "message": "Async handler without try/catch - errors may crash the server",
                "fix": "Wrap handler body in try/catch and call next(error)",
            })
        
        return issues


# ============================================================================
# Enhanced Error Parser
# ============================================================================

class EnhancedErrorParser:
    """
    Enhanced error parsing with layer-specific pattern matching.
    
    Parses frontend, backend, and database errors with actionable suggestions.
    """
    
    @staticmethod
    def parse_frontend_errors(logs: str) -> List[Dict[str, str]]:
        """Parse React/JavaScript errors from frontend logs."""
        suggestions = []
        
        patterns = {
            r"Cannot read propert(?:y|ies) of undefined \(reading '(\w+)'\)":
                lambda m: {
                    "type": "null_reference",
                    "fix": f"FE_FIX: Object accessing '{m.group(1)}' is undefined. Add null check: obj?.{m.group(1)}",
                },
            
            r"Objects are not valid as a React child":
                lambda m: {
                    "type": "render_object",
                    "fix": "FE_FIX: Trying to render an object directly. Use JSON.stringify() or extract specific properties.",
                },
            
            r"Each child in a list should have a unique ['\"]key['\"] prop":
                lambda m: {
                    "type": "missing_key",
                    "fix": "FE_FIX: Add key prop to list items: items.map(item => <Item key={item.id} />)",
                },
            
            r"Invalid hook call":
                lambda m: {
                    "type": "invalid_hook",
                    "fix": "FE_FIX: Hooks can only be called at top level of function components, not in conditions/loops.",
                },
            
            r"Maximum update depth exceeded":
                lambda m: {
                    "type": "infinite_loop",
                    "fix": "FE_FIX: Infinite re-render loop. Check useEffect dependencies and setState calls.",
                },
            
            r"Failed to fetch|NetworkError":
                lambda m: {
                    "type": "network_error",
                    "fix": "FE_FIX: Network request failed. Check: 1) Backend running 2) CORS 3) URL correct",
                },
        }
        
        for pattern, fix_generator in patterns.items():
            for match in re.finditer(pattern, logs, re.IGNORECASE):
                suggestions.append(fix_generator(match))
        
        return suggestions
    
    @staticmethod
    def parse_backend_errors(logs: str) -> List[Dict[str, str]]:
        """Parse Node.js/Express errors from backend logs."""
        suggestions = []
        
        patterns = {
            r"ECONNREFUSED.*:(\d+)":
                lambda m: {
                    "type": "connection_refused",
                    "fix": f"BE_FIX: Cannot connect to port {m.group(1)}. Check if database/service is running.",
                },
            
            r"JWT.*expired|TokenExpiredError":
                lambda m: {
                    "type": "jwt_expired",
                    "fix": "BE_FIX: JWT token expired. Check token expiration settings or implement refresh.",
                },
            
            r"Error: Route\.(\w+)\(\) requires a callback":
                lambda m: {
                    "type": "missing_handler",
                    "fix": f"BE_FIX: Route handler for {m.group(1)} is undefined. Check import/export statements.",
                },
            
            r"ER_ACCESS_DENIED_ERROR|authentication failed":
                lambda m: {
                    "type": "db_auth_failed",
                    "fix": "BE_FIX: Database authentication failed. Check DB_USER, DB_PASSWORD in env config.",
                },
            
            r"ENOENT.*['\"]([^'\"]+)['\"]":
                lambda m: {
                    "type": "file_not_found",
                    "fix": f"BE_FIX: File not found: {m.group(1)}. Check file path and working directory.",
                },
        }
        
        for pattern, fix_generator in patterns.items():
            for match in re.finditer(pattern, logs, re.IGNORECASE):
                suggestions.append(fix_generator(match))
        
        return suggestions
    
    @staticmethod
    def parse_database_errors(logs: str) -> List[Dict[str, str]]:
        """Parse PostgreSQL/database errors."""
        suggestions = []
        
        patterns = {
            r"relation ['\"]?(\w+)['\"]? does not exist":
                lambda m: {
                    "type": "missing_table",
                    "fix": f"DB_FIX: Table '{m.group(1)}' doesn't exist. Run init scripts or check table name.",
                },
            
            r"column ['\"]?(\w+)['\"]? .* does not exist":
                lambda m: {
                    "type": "missing_column",
                    "fix": f"DB_FIX: Column '{m.group(1)}' doesn't exist. Check schema vs model column names.",
                },
            
            r"invalid input syntax for type uuid[:\s]*['\"]?(\w+)['\"]?":
                lambda m: {
                    "type": "invalid_uuid",
                    "fix": f"DB_FIX: '{m.group(1)}' is not a valid UUID. Check route ordering (specific before :id).",
                },
            
            r"duplicate key value violates unique constraint":
                lambda m: {
                    "type": "duplicate_key",
                    "fix": "DB_FIX: Duplicate value. Add existence check or use ON CONFLICT.",
                },
            
            r"null value in column ['\"]?(\w+)['\"]? .*violates not-null":
                lambda m: {
                    "type": "null_violation",
                    "fix": f"DB_FIX: Column '{m.group(1)}' cannot be null. Provide a value or make column nullable.",
                },
        }
        
        for pattern, fix_generator in patterns.items():
            for match in re.finditer(pattern, logs, re.IGNORECASE):
                suggestions.append(fix_generator(match))
        
        return suggestions
    
    @classmethod
    def parse_all_errors(cls, logs: str) -> Dict[str, List[Dict[str, str]]]:
        """Parse errors from all layers."""
        return {
            "frontend": cls.parse_frontend_errors(logs),
            "backend": cls.parse_backend_errors(logs),
            "database": cls.parse_database_errors(logs),
        }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "CrossLayerDebugger",
    "ErrorTrace",
    "APIAlignmentVerifier",
    "APICall",
    "BackendRoute",
    "AlignmentIssue",
    "RuntimeDebugTools",
    "EnhancedErrorParser",
]

