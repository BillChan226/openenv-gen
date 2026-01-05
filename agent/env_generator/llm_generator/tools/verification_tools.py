"""
Verification Tools - Automated verification for generated applications

1. CompareScreenshotsTool - Compare reference images with generated UI screenshots
2. VerifyAPIContractTool - Verify frontend API calls match backend routes
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from utils.tool import BaseTool, ToolCategory, ToolResult
from workspace import Workspace

logger = logging.getLogger(__name__)


# =============================================================================
# 1. SCREENSHOT COMPARISON TOOL
# =============================================================================

class CompareScreenshotsTool(BaseTool):
    """Compare reference screenshots with generated UI screenshots."""
    
    NAME = "compare_screenshots"
    DESCRIPTION = """Compare reference images with generated screenshots.

Calculates visual similarity score between reference design and actual UI.

Examples:
    compare_screenshots("screenshots/reference/home.png", "screenshots/generated/home.png")
    compare_screenshots()  # Auto-compare all matching pairs

Returns:
- similarity_score: 0.0-1.0 (1.0 = identical)
- differences: List of regions that differ
- recommendation: Pass/Fail with suggestions

Requires: pip install pillow scikit-image
"""
    
    def __init__(self, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        self.workspace = workspace
        self._logger = logging.getLogger(__name__)
    
    @property
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return {
            "type": "function",
            "function": {
                "name": self.NAME,
                "description": self.DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reference": {
                            "type": "string",
                            "description": "Path to reference image (optional, auto-detects if not provided)"
                        },
                        "generated": {
                            "type": "string",
                            "description": "Path to generated screenshot (optional, auto-detects if not provided)"
                        },
                        "threshold": {
                            "type": "number",
                            "description": "Minimum similarity score to pass (default: 0.7)"
                        }
                    },
                    "required": []
                }
            }
        }
    
    async def execute(
        self, 
        reference: str = None, 
        generated: str = None,
        threshold: float = 0.7
    ) -> ToolResult:
        """Compare screenshots and return similarity analysis."""
        
        # Check dependencies
        try:
            from PIL import Image
            import numpy as np
        except ImportError:
            return ToolResult(
                success=False,
                error_message="Missing dependencies. Run: pip install pillow numpy"
            )
        
        try:
            from skimage.metrics import structural_similarity as ssim
            HAS_SKIMAGE = True
        except ImportError:
            HAS_SKIMAGE = False
            self._logger.warning("scikit-image not installed, using basic comparison")
        
        if not self.workspace:
            return ToolResult(success=False, error_message="Workspace not configured")
        
        # Auto-detect image pairs if not specified
        if not reference or not generated:
            pairs = self._find_image_pairs()
            if not pairs:
                return ToolResult(
                    success=True,
                    data={
                        "status": "no_pairs",
                        "message": "No matching reference/generated image pairs found.",
                        "hint": "Place reference images in 'screenshots/' and generated ones will be compared automatically."
                    }
                )
        else:
            pairs = [(reference, generated)]
        
        results = []
        overall_score = 0.0
        
        for ref_path, gen_path in pairs:
            try:
                ref_full = self.workspace.resolve(ref_path)
                gen_full = self.workspace.resolve(gen_path)
                
                if not ref_full.exists():
                    results.append({
                        "reference": ref_path,
                        "generated": gen_path,
                        "error": f"Reference not found: {ref_path}"
                    })
                    continue
                
                if not gen_full.exists():
                    results.append({
                        "reference": ref_path,
                        "generated": gen_path,
                        "error": f"Generated not found: {gen_path}"
                    })
                    continue
                
                # Load images
                ref_img = Image.open(ref_full).convert('RGB')
                gen_img = Image.open(gen_full).convert('RGB')
                
                # Resize to same dimensions for comparison
                if ref_img.size != gen_img.size:
                    gen_img = gen_img.resize(ref_img.size, Image.Resampling.LANCZOS)
                
                # Convert to numpy arrays
                ref_arr = np.array(ref_img)
                gen_arr = np.array(gen_img)
                
                # Calculate similarity
                if HAS_SKIMAGE:
                    # Use SSIM (Structural Similarity Index)
                    score, diff_map = ssim(ref_arr, gen_arr, multichannel=True, full=True, channel_axis=2)
                    
                    # Find regions with low similarity
                    diff_regions = self._find_diff_regions(diff_map, threshold=0.5)
                else:
                    # Basic pixel-wise comparison
                    diff = np.abs(ref_arr.astype(float) - gen_arr.astype(float))
                    score = 1.0 - (np.mean(diff) / 255.0)
                    diff_regions = []
                
                overall_score += score
                
                # Determine pass/fail
                passed = score >= threshold
                
                result = {
                    "reference": ref_path,
                    "generated": gen_path,
                    "similarity_score": round(score, 3),
                    "passed": passed,
                    "threshold": threshold,
                    "diff_regions": diff_regions[:5] if diff_regions else [],  # Top 5 differences
                }
                
                if not passed:
                    result["suggestions"] = self._get_suggestions(score, diff_regions)
                
                results.append(result)
                
            except Exception as e:
                results.append({
                    "reference": ref_path,
                    "generated": gen_path,
                    "error": str(e)
                })
        
        # Calculate overall results
        valid_results = [r for r in results if "similarity_score" in r]
        avg_score = overall_score / len(valid_results) if valid_results else 0.0
        all_passed = all(r.get("passed", False) for r in valid_results)
        
        return ToolResult(
            success=True,
            data={
                "overall_score": round(avg_score, 3),
                "overall_passed": all_passed,
                "threshold": threshold,
                "comparisons": results,
                "summary": f"Compared {len(pairs)} image pairs. Average similarity: {avg_score:.1%}. {'PASSED' if all_passed else 'NEEDS IMPROVEMENT'}"
            }
        )
    
    def _find_image_pairs(self) -> List[Tuple[str, str]]:
        """Find matching reference and generated image pairs."""
        pairs = []
        
        # Look for reference images
        ref_dirs = [
            self.workspace.root / "screenshots",
            self.workspace.root / "design" / "screenshots",
            self.workspace.root / "reference",
        ]
        
        # Look for generated screenshots
        gen_dirs = [
            self.workspace.root / "screenshots" / "generated",
            self.workspace.root / "screenshots" / "test",
            self.workspace.root / "app" / "screenshots",
        ]
        
        ref_images = {}
        for ref_dir in ref_dirs:
            if ref_dir.exists():
                for img in ref_dir.glob("*.png"):
                    # Skip if in 'generated' or 'test' subdirectory
                    if "generated" not in str(img) and "test" not in str(img):
                        name = img.stem.lower()
                        ref_images[name] = str(img.relative_to(self.workspace.root))
        
        # Match with generated images
        for gen_dir in gen_dirs:
            if gen_dir.exists():
                for img in gen_dir.glob("*.png"):
                    name = img.stem.lower()
                    # Try to match by name
                    for ref_name, ref_path in ref_images.items():
                        if name in ref_name or ref_name in name:
                            gen_path = str(img.relative_to(self.workspace.root))
                            pairs.append((ref_path, gen_path))
                            break
        
        return pairs
    
    def _find_diff_regions(self, diff_map: 'np.ndarray', threshold: float) -> List[Dict]:
        """Find regions with significant differences."""
        import numpy as np
        
        # Convert to grayscale if needed
        if len(diff_map.shape) == 3:
            diff_gray = np.mean(diff_map, axis=2)
        else:
            diff_gray = diff_map
        
        # Find low-similarity regions
        low_sim = diff_gray < threshold
        
        # Simple region detection (divide into grid)
        h, w = diff_gray.shape
        grid_size = 4
        regions = []
        
        for i in range(grid_size):
            for j in range(grid_size):
                y1, y2 = i * h // grid_size, (i + 1) * h // grid_size
                x1, x2 = j * w // grid_size, (j + 1) * w // grid_size
                
                region_diff = 1.0 - np.mean(diff_gray[y1:y2, x1:x2])
                if region_diff > 0.1:  # More than 10% difference
                    regions.append({
                        "location": f"Row {i+1}, Col {j+1}",
                        "area": f"({x1},{y1}) to ({x2},{y2})",
                        "difference": round(region_diff, 2)
                    })
        
        # Sort by difference (most different first)
        regions.sort(key=lambda r: r["difference"], reverse=True)
        return regions
    
    def _get_suggestions(self, score: float, diff_regions: List[Dict]) -> List[str]:
        """Get improvement suggestions based on comparison results."""
        suggestions = []
        
        if score < 0.3:
            suggestions.append("Layout is very different - check component structure and positioning")
            suggestions.append("Verify correct page is being rendered")
        elif score < 0.5:
            suggestions.append("Significant differences - check colors, fonts, and spacing")
            suggestions.append("Compare component hierarchy with reference")
        elif score < 0.7:
            suggestions.append("Minor differences - fine-tune padding, margins, colors")
            suggestions.append("Check responsive breakpoints")
        
        if diff_regions:
            top_region = diff_regions[0]
            suggestions.append(f"Largest difference at {top_region['location']} - focus there first")
        
        return suggestions


# =============================================================================
# 2. API CONTRACT VERIFICATION TOOL
# =============================================================================

class VerifyAPIContractTool(BaseTool):
    """Verify frontend API calls match backend routes."""
    
    NAME = "verify_api_contract"
    DESCRIPTION = """Verify that frontend API calls match backend routes.

Analyzes:
- Backend: Express routes from src/routes/*.js
- Frontend: API calls from src/services/api.js
- Spec: Expected endpoints from design/spec.api.json

Returns:
- matched: APIs that exist in both frontend and backend
- missing_in_backend: Frontend calls routes that don't exist
- missing_in_frontend: Backend routes not used by frontend
- mismatched: Routes with different methods or paths

Example:
    verify_api_contract()  # Auto-detect and verify
"""
    
    def __init__(self, workspace: Workspace = None):
        super().__init__(name=self.NAME, category=ToolCategory.FILE)
        self.workspace = workspace
        self._logger = logging.getLogger(__name__)
    
    @property
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return {
            "type": "function",
            "function": {
                "name": self.NAME,
                "description": self.DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "backend_dir": {
                            "type": "string",
                            "description": "Backend routes directory (default: app/backend/src/routes)"
                        },
                        "frontend_api": {
                            "type": "string",
                            "description": "Frontend API file (default: app/frontend/src/services/api.js)"
                        },
                        "spec_file": {
                            "type": "string",
                            "description": "API spec file (default: design/spec.api.json)"
                        }
                    },
                    "required": []
                }
            }
        }
    
    async def execute(
        self,
        backend_dir: str = "app/backend/src/routes",
        frontend_api: str = "app/frontend/src/services/api.js",
        spec_file: str = "design/spec.api.json"
    ) -> ToolResult:
        """Verify API contract between frontend and backend."""
        
        if not self.workspace:
            return ToolResult(success=False, error_message="Workspace not configured")
        
        # Extract backend routes
        backend_routes = self._extract_backend_routes(backend_dir)
        
        # Extract frontend API calls
        frontend_calls = self._extract_frontend_calls(frontend_api)
        
        # Extract spec (if exists)
        spec_endpoints = self._extract_spec_endpoints(spec_file)
        
        # Compare and analyze
        analysis = self._analyze_contract(backend_routes, frontend_calls, spec_endpoints)
        
        # Generate report
        issues = []
        
        # Missing in backend (critical)
        for call in analysis["missing_in_backend"]:
            issues.append({
                "severity": "critical",
                "type": "missing_backend_route",
                "frontend_call": call,
                "message": f"Frontend calls {call['method']} {call['path']} but backend has no matching route",
                "fix": f"Add route in backend: router.{call['method'].lower()}('{call['path']}', ...)"
            })
        
        # Missing in frontend (warning)
        for route in analysis["missing_in_frontend"]:
            issues.append({
                "severity": "warning",
                "type": "unused_backend_route",
                "backend_route": route,
                "message": f"Backend has {route['method']} {route['path']} but frontend doesn't use it",
                "fix": "Consider if this route is needed, or add frontend function to use it"
            })
        
        # Method mismatches (critical)
        for mismatch in analysis["method_mismatches"]:
            issues.append({
                "severity": "critical",
                "type": "method_mismatch",
                "path": mismatch["path"],
                "frontend_method": mismatch["frontend_method"],
                "backend_method": mismatch["backend_method"],
                "message": f"Method mismatch for {mismatch['path']}: frontend uses {mismatch['frontend_method']}, backend expects {mismatch['backend_method']}",
                "fix": f"Change frontend to use {mismatch['backend_method']} or update backend route"
            })
        
        # Calculate health score
        total_calls = len(frontend_calls)
        matched = len(analysis["matched"])
        critical_issues = len([i for i in issues if i["severity"] == "critical"])
        
        if total_calls == 0:
            health_score = 0.0
            status = "NO_API_CALLS"
        elif critical_issues == 0:
            health_score = 1.0
            status = "HEALTHY"
        else:
            health_score = matched / total_calls if total_calls > 0 else 0.0
            status = "ISSUES_FOUND"
        
        return ToolResult(
            success=True,
            data={
                "status": status,
                "health_score": round(health_score, 2),
                "summary": {
                    "backend_routes": len(backend_routes),
                    "frontend_calls": len(frontend_calls),
                    "matched": matched,
                    "missing_in_backend": len(analysis["missing_in_backend"]),
                    "missing_in_frontend": len(analysis["missing_in_frontend"]),
                    "method_mismatches": len(analysis["method_mismatches"])
                },
                "matched_endpoints": analysis["matched"],
                "issues": issues,
                "recommendation": self._get_recommendation(status, issues)
            }
        )
    
    def _extract_backend_routes(self, backend_dir: str) -> List[Dict]:
        """Extract routes from Express backend."""
        routes = []
        
        dir_path = self.workspace.root / backend_dir
        if not dir_path.exists():
            # Try alternative paths
            alt_paths = [
                self.workspace.root / "app" / "backend" / "routes",
                self.workspace.root / "backend" / "src" / "routes",
                self.workspace.root / "backend" / "routes",
            ]
            for alt in alt_paths:
                if alt.exists():
                    dir_path = alt
                    break
            else:
                self._logger.warning(f"Backend routes directory not found: {backend_dir}")
                return routes
        
        # Parse route files
        route_pattern = re.compile(
            r'router\.(get|post|put|patch|delete)\s*\(\s*[\'"]([^\'"]+)[\'"]',
            re.IGNORECASE
        )
        
        for js_file in dir_path.glob("*.js"):
            try:
                content = js_file.read_text(encoding='utf-8', errors='replace')
                
                # Determine route prefix from filename
                prefix = "/" + js_file.stem if js_file.stem != "index" else ""
                if prefix == "/auth":
                    prefix = "/auth"
                elif prefix == "/users":
                    prefix = "/users"
                # Usually routes are mounted at /api/<filename>
                
                for match in route_pattern.finditer(content):
                    method = match.group(1).upper()
                    path = match.group(2)
                    
                    # Normalize path
                    full_path = f"/api{prefix}{path}" if not path.startswith("/api") else path
                    full_path = full_path.replace("//", "/")
                    
                    routes.append({
                        "method": method,
                        "path": full_path,
                        "file": js_file.name,
                        "normalized": self._normalize_path(full_path)
                    })
                    
            except Exception as e:
                self._logger.debug(f"Error parsing {js_file}: {e}")
        
        return routes
    
    def _extract_frontend_calls(self, frontend_api: str) -> List[Dict]:
        """Extract API calls from frontend service."""
        calls = []
        
        api_path = self.workspace.root / frontend_api
        if not api_path.exists():
            # Try alternative paths
            alt_paths = [
                self.workspace.root / "app" / "frontend" / "src" / "api.js",
                self.workspace.root / "app" / "frontend" / "src" / "lib" / "api.js",
                self.workspace.root / "frontend" / "src" / "services" / "api.js",
            ]
            for alt in alt_paths:
                if alt.exists():
                    api_path = alt
                    break
            else:
                self._logger.warning(f"Frontend API file not found: {frontend_api}")
                return calls
        
        try:
            content = api_path.read_text(encoding='utf-8', errors='replace')
            
            # Pattern 1: Axios-style http.method() calls
            # e.g., http.get('/api/users'), http.post('/api/login', payload)
            axios_pattern = re.compile(
                r'(?:http|axios|api|client)\s*\.\s*(get|post|put|patch|delete)\s*\(\s*[`\'"]([^`\'"]+)[`\'"]',
                re.IGNORECASE
            )
            
            # Pattern 2: fetch() with method
            fetch_pattern = re.compile(
                r'fetch\s*\(\s*[`\'"]([^`\'"]+)[`\'"].*?method:\s*[\'"](\w+)[\'"]',
                re.IGNORECASE | re.DOTALL
            )
            
            # Pattern 3: request() helper with method option
            request_pattern = re.compile(
                r'request\s*\(\s*[`\'"]([^`\'"]+)[`\'"].*?method:\s*[\'"](\w+)[\'"]',
                re.IGNORECASE | re.DOTALL
            )
            
            # Pattern 4: Simple GET requests
            simple_get = re.compile(
                r'(?:return\s+)?(?:await\s+)?(?:http|axios|api|client)\s*\.\s*get\s*\(\s*[`\'"]([^`\'"]+)[`\'"]',
                re.IGNORECASE
            )
            
            # Pattern 5: fetch without explicit method (defaults to GET)
            simple_fetch = re.compile(
                r'fetch\s*\(\s*[`\'"]([^`\'"]+)[`\'"](?:\s*\)|\s*,\s*\{(?![^}]*method:))',
                re.IGNORECASE
            )
            
            seen_paths = set()
            
            # Extract axios-style calls (most common pattern)
            for match in axios_pattern.finditer(content):
                method = match.group(1).upper()
                path = match.group(2)
                key = (path, method)
                if key not in seen_paths:
                    seen_paths.add(key)
                    calls.append(self._create_call_entry(path, method))
            
            # Extract fetch calls with method
            for match in fetch_pattern.finditer(content):
                path = match.group(1)
                method = match.group(2).upper()
                key = (path, method)
                if key not in seen_paths:
                    seen_paths.add(key)
                    calls.append(self._create_call_entry(path, method))
            
            # Extract request helper calls
            for match in request_pattern.finditer(content):
                path = match.group(1)
                method = match.group(2).upper()
                key = (path, method)
                if key not in seen_paths:
                    seen_paths.add(key)
                    calls.append(self._create_call_entry(path, method))
            
            # Extract simple fetch (GET)
            for match in simple_fetch.finditer(content):
                path = match.group(1)
                key = (path, "GET")
                if key not in seen_paths:
                    seen_paths.add(key)
                    calls.append(self._create_call_entry(path, "GET"))
                    
        except Exception as e:
            self._logger.debug(f"Error parsing frontend API: {e}")
        
        return calls
    
    def _create_call_entry(self, path: str, method: str) -> Dict:
        """Create standardized call entry."""
        # Handle template literals
        path = re.sub(r'\$\{[^}]+\}', ':id', path)
        path = path.replace('${', ':').replace('}', '')
        
        # Normalize
        if not path.startswith("/"):
            path = "/" + path
        
        return {
            "method": method.upper(),
            "path": path,
            "normalized": self._normalize_path(path)
        }
    
    def _extract_spec_endpoints(self, spec_file: str) -> List[Dict]:
        """Extract endpoints from API spec."""
        endpoints = []
        
        spec_path = self.workspace.root / spec_file
        if not spec_path.exists():
            return endpoints
        
        try:
            spec = json.loads(spec_path.read_text(encoding='utf-8'))
            
            for endpoint in spec.get("endpoints", []):
                endpoints.append({
                    "method": endpoint.get("method", "GET").upper(),
                    "path": endpoint.get("path", ""),
                    "normalized": self._normalize_path(endpoint.get("path", ""))
                })
                
        except Exception as e:
            self._logger.debug(f"Error parsing spec: {e}")
        
        return endpoints
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for comparison (replace params with :param)."""
        # Replace UUIDs and numbers with :id
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/:id', path)
        path = re.sub(r'/\d+', '/:id', path)
        # Replace path params
        path = re.sub(r'/:[\w]+', '/:id', path)
        # Remove trailing slash
        path = path.rstrip('/')
        # Lowercase
        return path.lower()
    
    def _analyze_contract(
        self,
        backend_routes: List[Dict],
        frontend_calls: List[Dict],
        spec_endpoints: List[Dict]
    ) -> Dict:
        """Analyze the API contract."""
        
        # Create lookup sets
        backend_set = {(r["normalized"], r["method"]) for r in backend_routes}
        frontend_set = {(c["normalized"], c["method"]) for c in frontend_calls}
        
        # Find matches
        matched = []
        for call in frontend_calls:
            key = (call["normalized"], call["method"])
            if key in backend_set:
                matched.append({
                    "method": call["method"],
                    "path": call["path"]
                })
        
        # Find missing in backend
        missing_in_backend = []
        for call in frontend_calls:
            key = (call["normalized"], call["method"])
            if key not in backend_set:
                # Check if path exists with different method
                path_exists = any(r["normalized"] == call["normalized"] for r in backend_routes)
                if not path_exists:
                    missing_in_backend.append(call)
        
        # Find missing in frontend
        missing_in_frontend = []
        for route in backend_routes:
            key = (route["normalized"], route["method"])
            if key not in frontend_set:
                # Skip common utility routes
                if not any(skip in route["path"] for skip in ["/health", "/status", "/metrics"]):
                    missing_in_frontend.append(route)
        
        # Find method mismatches
        method_mismatches = []
        for call in frontend_calls:
            for route in backend_routes:
                if call["normalized"] == route["normalized"] and call["method"] != route["method"]:
                    method_mismatches.append({
                        "path": call["path"],
                        "frontend_method": call["method"],
                        "backend_method": route["method"]
                    })
        
        return {
            "matched": matched,
            "missing_in_backend": missing_in_backend,
            "missing_in_frontend": missing_in_frontend,
            "method_mismatches": method_mismatches
        }
    
    def _infer_from_function_name(self, func_name: str) -> Optional[str]:
        """Infer API path from function name."""
        # Common patterns
        patterns = {
            r'^get(\w+)s$': ('GET', '/api/{0}s'),           # getUsers -> GET /api/users
            r'^get(\w+)ById$': ('GET', '/api/{0}s/:id'),    # getUserById -> GET /api/users/:id
            r'^create(\w+)$': ('POST', '/api/{0}s'),        # createUser -> POST /api/users
            r'^update(\w+)$': ('PUT', '/api/{0}s/:id'),     # updateUser -> PUT /api/users/:id
            r'^delete(\w+)$': ('DELETE', '/api/{0}s/:id'),  # deleteUser -> DELETE /api/users/:id
            r'^search(\w+)s$': ('GET', '/api/{0}s/search'), # searchUsers -> GET /api/users/search
        }
        
        for pattern, (method, path_template) in patterns.items():
            match = re.match(pattern, func_name, re.IGNORECASE)
            if match:
                resource = match.group(1).lower()
                return path_template.format(resource)
        
        return None
    
    def _get_recommendation(self, status: str, issues: List[Dict]) -> str:
        """Get recommendation based on analysis."""
        if status == "HEALTHY":
            return "API contract is healthy. All frontend calls have matching backend routes."
        
        if status == "NO_API_CALLS":
            return "No API calls detected in frontend. Check if api.js exists and contains fetch/request calls."
        
        critical = [i for i in issues if i["severity"] == "critical"]
        warnings = [i for i in issues if i["severity"] == "warning"]
        
        if critical:
            return f"Found {len(critical)} critical issues. Fix these first - frontend will fail without matching backend routes."
        
        if warnings:
            return f"Found {len(warnings)} warnings. Backend has routes that frontend doesn't use - consider cleanup or future use."
        
        return "Review the issues above and fix as needed."


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_verification_tools(workspace: Workspace = None) -> List[BaseTool]:
    """Create all verification tools."""
    return [
        CompareScreenshotsTool(workspace=workspace),
        VerifyAPIContractTool(workspace=workspace),
    ]

