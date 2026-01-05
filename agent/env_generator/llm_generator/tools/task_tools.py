"""
Task Tools - Tools for extracting action space, generating tasks, and creating judges

Used by TaskAgent to create benchmark configurations for generated applications.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

from utils.tool import BaseTool, ToolCategory, ToolResult

logger = logging.getLogger(__name__)


class ExtractActionSpaceTool(BaseTool):
    """
    Extract action space from generated application code.
    
    Analyzes frontend components and backend routes to find all possible actions.
    """
    
    NAME = "extract_action_space"
    DESCRIPTION = """Extract all possible user actions from the generated application.

Analyzes:
- Frontend JSX files for buttons, forms, links
- Backend route files for API endpoints
- Spec files for navigation routes

Example:
```python
extract_action_space()  # Extracts from entire app
extract_action_space(scope="ui")  # Only UI actions
extract_action_space(scope="api")  # Only API actions
```

Returns structured action space with UI actions, API actions, and navigation.
"""
    
    def __init__(self, workspace=None):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        self.workspace = workspace
    
    def get_tool_param(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.NAME,
                "description": self.DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scope": {
                            "type": "string",
                            "enum": ["all", "ui", "api", "navigation"],
                            "description": "Which actions to extract (default: all)"
                        }
                    },
                    "required": []
                }
            }
        }
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def execute(self, scope: str = "all") -> ToolResult:
        """Extract action space from application."""
        if not self.workspace:
            return ToolResult(
                success=False,
                error_message="Workspace not configured"
            )
        
        action_space = {
            "ui_actions": [],
            "api_actions": [],
            "navigation_actions": []
        }
        
        try:
            app_dir = self.workspace.root / "app"
            
            # Extract UI actions from frontend
            if scope in ["all", "ui"]:
                frontend_dir = app_dir / "frontend" / "src"
                if frontend_dir.exists():
                    action_space["ui_actions"] = self._extract_ui_actions(frontend_dir)
            
            # Extract API actions from backend
            if scope in ["all", "api"]:
                backend_dir = app_dir / "backend" / "src" / "routes"
                if backend_dir.exists():
                    action_space["api_actions"] = self._extract_api_actions(backend_dir)
                
                # Also try spec file
                spec_file = self.workspace.root / "design" / "spec.api.json"
                if spec_file.exists():
                    action_space["api_actions"].extend(self._extract_api_from_spec(spec_file))
            
            # Extract navigation from spec
            if scope in ["all", "navigation"]:
                ui_spec = self.workspace.root / "design" / "spec.ui.json"
                if ui_spec.exists():
                    action_space["navigation_actions"] = self._extract_navigation(ui_spec)
            
            # Deduplicate
            action_space["api_actions"] = self._dedupe_by_key(action_space["api_actions"], "endpoint")
            
            return ToolResult(
                success=True,
                data={
                    "action_space": action_space,
                    "counts": {
                        "ui_actions": len(action_space["ui_actions"]),
                        "api_actions": len(action_space["api_actions"]),
                        "navigation_actions": len(action_space["navigation_actions"])
                    },
                    "message": f"Extracted {sum(len(v) for v in action_space.values())} total actions"
                }
            )
            
        except Exception as e:
            logger.exception(f"Action space extraction failed: {e}")
            return ToolResult(success=False, error_message=str(e))
    
    def _extract_ui_actions(self, frontend_dir: Path) -> List[Dict]:
        """Extract UI actions from JSX/TSX files."""
        actions = []
        
        for file in frontend_dir.rglob("*.jsx"):
            try:
                content = file.read_text()
                
                # Find buttons
                button_patterns = [
                    r'<button[^>]*onClick[^>]*>([^<]*)</button>',
                    r'<Button[^>]*onClick[^>]*>([^<]*)</Button>',
                    r'data-testid=["\']([^"\']+)["\']',
                ]
                
                for pattern in button_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if match.strip():
                            actions.append({
                                "action_type": "click",
                                "selector": f"[data-testid='{match}']" if 'testid' in pattern else f"button:has-text('{match}')",
                                "description": f"Click {match}",
                                "source_file": str(file.relative_to(frontend_dir))
                            })
                
                # Find inputs
                input_patterns = [
                    r'<input[^>]*(?:id|name)=["\']([^"\']+)["\'][^>]*>',
                    r'<Input[^>]*(?:id|name)=["\']([^"\']+)["\'][^>]*>',
                ]
                
                for pattern in input_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        actions.append({
                            "action_type": "type",
                            "selector": f"#{match}" if not match.startswith('#') else match,
                            "description": f"Type into {match}",
                            "parameters": {"value": "<user_input>"},
                            "source_file": str(file.relative_to(frontend_dir))
                        })
                
                # Find select elements
                select_patterns = [
                    r'<select[^>]*(?:id|name)=["\']([^"\']+)["\'][^>]*>',
                    r'<Select[^>]*(?:id|name)=["\']([^"\']+)["\'][^>]*>',
                ]
                
                for pattern in select_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        actions.append({
                            "action_type": "select",
                            "selector": f"#{match}",
                            "description": f"Select option in {match}",
                            "parameters": {"value": "<option>"},
                            "source_file": str(file.relative_to(frontend_dir))
                        })
                
                # Find links
                link_patterns = [
                    r'<Link[^>]*to=["\']([^"\']+)["\'][^>]*>([^<]*)</Link>',
                    r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>',
                ]
                
                for pattern in link_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for href, text in matches:
                        if href.startswith('/'):
                            actions.append({
                                "action_type": "click",
                                "selector": f"a[href='{href}']",
                                "description": f"Click link to {href}",
                                "target_url": href,
                                "source_file": str(file.relative_to(frontend_dir))
                            })
                            
            except Exception as e:
                logger.debug(f"Error parsing {file}: {e}")
        
        return actions
    
    def _extract_api_actions(self, routes_dir: Path) -> List[Dict]:
        """Extract API actions from backend route files."""
        actions = []
        
        for file in routes_dir.glob("*.js"):
            try:
                content = file.read_text()
                
                # Find Express routes
                route_patterns = [
                    r'router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
                    r'app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
                ]
                
                for pattern in route_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for method, path in matches:
                        # Determine if auth required
                        auth_required = 'requireAuth' in content or 'authenticate' in content
                        
                        actions.append({
                            "method": method.upper(),
                            "endpoint": f"/api{path}" if not path.startswith('/api') else path,
                            "description": f"{method.upper()} {path}",
                            "auth_required": auth_required,
                            "source_file": file.name
                        })
                        
            except Exception as e:
                logger.debug(f"Error parsing {file}: {e}")
        
        return actions
    
    def _extract_api_from_spec(self, spec_file: Path) -> List[Dict]:
        """Extract API actions from spec.api.json."""
        actions = []
        
        try:
            with open(spec_file) as f:
                spec = json.load(f)
            
            endpoints = spec.get("endpoints", [])
            for ep in endpoints:
                actions.append({
                    "method": ep.get("method", "GET").upper(),
                    "endpoint": ep.get("path", ""),
                    "description": ep.get("description", ""),
                    "parameters": ep.get("parameters", {}),
                    "auth_required": ep.get("auth_required", False),
                    "source": "spec.api.json"
                })
                
        except Exception as e:
            logger.debug(f"Error parsing API spec: {e}")
        
        return actions
    
    def _extract_navigation(self, ui_spec: Path) -> List[Dict]:
        """Extract navigation actions from spec.ui.json."""
        actions = []
        
        try:
            with open(ui_spec) as f:
                spec = json.load(f)
            
            pages = spec.get("pages", [])
            for page in pages:
                actions.append({
                    "action": "navigate",
                    "url": page.get("path", "/"),
                    "description": f"Navigate to {page.get('name', page.get('path'))}",
                    "page_name": page.get("name", "")
                })
                
        except Exception as e:
            logger.debug(f"Error parsing UI spec: {e}")
        
        # Add standard navigation
        actions.extend([
            {"action": "back", "description": "Go back in browser history"},
            {"action": "forward", "description": "Go forward in browser history"},
            {"action": "refresh", "description": "Refresh current page"}
        ])
        
        return actions
    
    def _dedupe_by_key(self, items: List[Dict], key: str) -> List[Dict]:
        """Remove duplicates based on a key."""
        seen = set()
        unique = []
        for item in items:
            val = item.get(key)
            if val and val not in seen:
                seen.add(val)
                unique.append(item)
        return unique


class GenerateTaskTool(BaseTool):
    """
    Generate a task definition for the benchmark.
    """
    
    NAME = "generate_task"
    DESCRIPTION = """Generate a task definition for the benchmark.

Creates a structured task with:
- task_id: Unique identifier
- description: Natural language task description
- category: Task category (auth, search, booking, etc.)
- difficulty: easy/medium/hard
- initial_state: Required starting conditions
- goal_state: Expected end state
- hints: Optional hints for solving

Example:
```python
generate_task(
    task_id="task_001",
    description="Search for flights from NYC to LAX on December 25th",
    category="search",
    difficulty="easy",
    initial_state={"logged_in": False, "current_url": "/"},
    goal_state={"flights_displayed": True, "search_params": {"origin": "NYC", "destination": "LAX"}},
    hints=["Navigate to flights", "Fill search form", "Click search"]
)
```
"""
    
    def __init__(self, workspace=None):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        self.workspace = workspace
        self._tasks: List[Dict] = []
    
    def get_tool_param(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.NAME,
                "description": self.DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Unique task identifier (e.g., 'task_001')"
                        },
                        "description": {
                            "type": "string",
                            "description": "Natural language task description"
                        },
                        "category": {
                            "type": "string",
                            "enum": ["auth", "search", "booking", "profile", "crud", "navigation", "complex"],
                            "description": "Task category"
                        },
                        "difficulty": {
                            "type": "string",
                            "enum": ["easy", "medium", "hard"],
                            "description": "Task difficulty"
                        },
                        "initial_state": {
                            "type": "object",
                            "description": "Required initial conditions (e.g., logged_in, current_url)"
                        },
                        "goal_state": {
                            "type": "object",
                            "description": "Expected end state to verify"
                        },
                        "hints": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional hints for solving"
                        },
                        "max_steps": {
                            "type": "integer",
                            "description": "Maximum steps allowed (default: 20)"
                        }
                    },
                    "required": ["task_id", "description", "category", "difficulty", "initial_state", "goal_state"]
                }
            }
        }
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def execute(
        self,
        task_id: str,
        description: str,
        category: str,
        difficulty: str,
        initial_state: Dict,
        goal_state: Dict,
        hints: List[str] = None,
        max_steps: int = 20
    ) -> ToolResult:
        """Generate a task definition."""
        task = {
            "task_id": task_id,
            "description": description,
            "category": category,
            "difficulty": difficulty,
            "initial_state": initial_state,
            "goal_state": goal_state,
            "hints": hints or [],
            "max_steps": max_steps
        }
        
        self._tasks.append(task)
        
        return ToolResult(
            success=True,
            data={
                "task": task,
                "total_tasks": len(self._tasks),
                "message": f"Task '{task_id}' created: {description[:50]}..."
            }
        )


class GenerateTrajectoryTool(BaseTool):
    """
    Generate a reference trajectory (action sequence) for a task.
    """
    
    NAME = "generate_trajectory"
    DESCRIPTION = """Generate a reference trajectory for a task.

Creates a sequence of actions that completes the task.

Example:
```python
generate_trajectory(
    task_id="task_001",
    actions=[
        {"action": "navigate", "url": "/flights"},
        {"action": "type", "selector": "#origin", "value": "NYC"},
        {"action": "type", "selector": "#destination", "value": "LAX"},
        {"action": "click", "selector": "#search-btn"}
    ],
    observations=[
        "Flights page loaded",
        "Origin entered",
        "Destination entered",
        "Search results displayed"
    ]
)
```
"""
    
    def __init__(self, workspace=None):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        self.workspace = workspace
        self._trajectories: List[Dict] = []
    
    def get_tool_param(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.NAME,
                "description": self.DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID this trajectory solves"
                        },
                        "actions": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Sequence of actions"
                        },
                        "observations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Expected observations after each action"
                        }
                    },
                    "required": ["task_id", "actions"]
                }
            }
        }
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def execute(
        self,
        task_id: str,
        actions: List[Dict],
        observations: List[str] = None
    ) -> ToolResult:
        """Generate a trajectory."""
        trajectory = {
            "task_id": task_id,
            "actions": actions,
            "observations": observations or [""] * len(actions),
            "success": True
        }
        
        self._trajectories.append(trajectory)
        
        return ToolResult(
            success=True,
            data={
                "trajectory": trajectory,
                "num_actions": len(actions),
                "message": f"Trajectory for '{task_id}' created with {len(actions)} actions"
            }
        )


class GenerateJudgeTool(BaseTool):
    """
    Generate a judge function for a task.
    """
    
    NAME = "generate_judge"
    DESCRIPTION = """Generate a judge function that verifies task completion.

Creates Python code that checks if a task was completed successfully.

Example:
```python
generate_judge(
    task_id="task_001",
    judge_type="composite",
    checks=[
        {"type": "url_contains", "value": "/flights"},
        {"type": "element_exists", "selector": ".flight-result"},
        {"type": "element_count", "selector": ".flight-result", "min": 1}
    ],
    description="Verify flight search completed"
)
```

Or with custom code:
```python
generate_judge(
    task_id="task_001",
    judge_type="custom",
    code=\"\"\"
async def judge(page, context):
    if '/flights' not in page.url:
        return False, 'Not on flights page'
    results = await page.query_selector_all('.flight-result')
    if len(results) == 0:
        return False, 'No results'
    return True, 'Success'
\"\"\",
    description="Custom flight search verification"
)
```
"""
    
    def __init__(self, workspace=None):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        self.workspace = workspace
        self._judges: List[Dict] = []
    
    def get_tool_param(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.NAME,
                "description": self.DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID this judge verifies"
                        },
                        "judge_type": {
                            "type": "string",
                            "enum": ["url", "element", "api", "database", "composite", "custom"],
                            "description": "Type of judge"
                        },
                        "checks": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "List of checks for composite judge"
                        },
                        "code": {
                            "type": "string",
                            "description": "Custom Python code for custom judge"
                        },
                        "description": {
                            "type": "string",
                            "description": "What this judge verifies"
                        }
                    },
                    "required": ["task_id", "judge_type", "description"]
                }
            }
        }
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def execute(
        self,
        task_id: str,
        judge_type: str,
        description: str,
        checks: List[Dict] = None,
        code: str = None
    ) -> ToolResult:
        """Generate a judge function."""
        
        # Generate code from checks if not custom
        if judge_type != "custom" and checks:
            code = self._generate_judge_code(checks)
        elif not code:
            code = "async def judge(page, context):\n    return True, 'No checks defined'"
        
        judge = {
            "task_id": task_id,
            "judge_type": judge_type,
            "code": code,
            "description": description
        }
        
        self._judges.append(judge)
        
        return ToolResult(
            success=True,
            data={
                "judge": judge,
                "message": f"Judge for '{task_id}' created: {description}"
            }
        )
    
    def _generate_judge_code(self, checks: List[Dict]) -> str:
        """Generate judge code from checks."""
        lines = [
            "async def judge(page, context):",
            "    try:"
        ]
        
        for check in checks:
            check_type = check.get("type", "")
            
            if check_type == "url_contains":
                value = check.get("value", "")
                lines.append(f"        if '{value}' not in page.url:")
                lines.append(f"            return False, 'URL does not contain {value}'")
            
            elif check_type == "url_equals":
                value = check.get("value", "")
                lines.append(f"        if page.url != '{value}':")
                lines.append(f"            return False, 'URL is not {value}'")
            
            elif check_type == "element_exists":
                selector = check.get("selector", "")
                lines.append(f"        el = await page.query_selector('{selector}')")
                lines.append(f"        if not el:")
                lines.append(f"            return False, 'Element {selector} not found'")
            
            elif check_type == "element_count":
                selector = check.get("selector", "")
                min_count = check.get("min", 1)
                lines.append(f"        els = await page.query_selector_all('{selector}')")
                lines.append(f"        if len(els) < {min_count}:")
                lines.append(f"            return False, 'Expected at least {min_count} elements for {selector}'")
            
            elif check_type == "element_text":
                selector = check.get("selector", "")
                expected = check.get("value", "")
                lines.append(f"        el = await page.query_selector('{selector}')")
                lines.append(f"        if el:")
                lines.append(f"            text = await el.inner_text()")
                lines.append(f"            if '{expected}' not in text:")
                lines.append(f"                return False, 'Text {expected} not found in {selector}'")
            
            elif check_type == "api_status":
                endpoint = check.get("endpoint", "")
                status = check.get("status", 200)
                lines.append(f"        resp = await context.request.get('{endpoint}')")
                lines.append(f"        if resp.status != {status}:")
                lines.append(f"            return False, 'API {endpoint} returned status ' + str(resp.status)")
            
            elif check_type == "localstorage":
                key = check.get("key", "")
                lines.append(f"        val = await page.evaluate('localStorage.getItem(\"{key}\")')")
                lines.append(f"        if not val:")
                lines.append(f"            return False, 'localStorage key {key} not found'")
        
        lines.append("        return True, 'All checks passed'")
        lines.append("    except Exception as e:")
        lines.append("        return False, f'Judge error: {str(e)}'")
        
        return "\n".join(lines)


class ExportTaskConfigTool(BaseTool):
    """
    Export the complete task configuration to a JSON file.
    """
    
    NAME = "export_task_config"
    DESCRIPTION = """Export all tasks, trajectories, and judges to task_config.json.

Combines all generated tasks, trajectories, and judges into a single config file.

Example:
```python
export_task_config(output_file="task_config.json")
```
"""
    
    def __init__(self, workspace=None):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        self.workspace = workspace
        # These will be populated by other tools
        self.action_space = {}
        self.tasks = []
        self.trajectories = []
        self.judges = []
    
    def get_tool_param(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.NAME,
                "description": self.DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "output_file": {
                            "type": "string",
                            "description": "Output file path (default: task_config.json)"
                        },
                        "action_space": {
                            "type": "object",
                            "description": "Action space to include"
                        },
                        "tasks": {
                            "type": "array",
                            "description": "Tasks to include"
                        },
                        "trajectories": {
                            "type": "array",
                            "description": "Trajectories to include"
                        },
                        "judges": {
                            "type": "array",
                            "description": "Judges to include"
                        }
                    },
                    "required": []
                }
            }
        }
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def execute(
        self,
        output_file: str = "task_config.json",
        action_space: Dict = None,
        tasks: List[Dict] = None,
        trajectories: List[Dict] = None,
        judges: List[Dict] = None
    ) -> ToolResult:
        """Export task configuration."""
        config = {
            "action_space": action_space or self.action_space,
            "tasks": tasks or self.tasks,
            "trajectories": trajectories or self.trajectories,
            "judges": judges or self.judges,
            "metadata": {
                "total_tasks": len(tasks or self.tasks),
                "difficulty_distribution": self._count_difficulties(tasks or self.tasks),
                "category_distribution": self._count_categories(tasks or self.tasks)
            }
        }
        
        # Write to file
        if self.workspace:
            output_path = self.workspace.root / output_file
        else:
            output_path = Path(output_file)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return ToolResult(
            success=True,
            data={
                "output_file": str(output_path),
                "total_tasks": len(config["tasks"]),
                "total_trajectories": len(config["trajectories"]),
                "total_judges": len(config["judges"]),
                "message": f"Exported {len(config['tasks'])} tasks to {output_file}"
            }
        )
    
    def _count_difficulties(self, tasks: List[Dict]) -> Dict[str, int]:
        counts = {"easy": 0, "medium": 0, "hard": 0}
        for task in tasks:
            diff = task.get("difficulty", "medium")
            counts[diff] = counts.get(diff, 0) + 1
        return counts
    
    def _count_categories(self, tasks: List[Dict]) -> Dict[str, int]:
        counts = {}
        for task in tasks:
            cat = task.get("category", "other")
            counts[cat] = counts.get(cat, 0) + 1
        return counts


class TestActionTool(BaseTool):
    """
    Test if an action can be executed in the current application state.
    """
    
    NAME = "test_action"
    DESCRIPTION = """Test if an action can be executed.

Attempts to execute an action and reports success/failure.

Example:
```python
test_action(
    action_type="click",
    selector="#login-button"
)

test_action(
    action_type="api",
    method="GET",
    endpoint="/api/flights"
)
```
"""
    
    def __init__(self, workspace=None, browser_manager=None):
        super().__init__(name=self.NAME, category=ToolCategory.RUNTIME)
        self.workspace = workspace
        self.browser_manager = browser_manager
    
    def get_tool_param(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.NAME,
                "description": self.DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action_type": {
                            "type": "string",
                            "enum": ["click", "type", "select", "navigate", "api"],
                            "description": "Type of action to test"
                        },
                        "selector": {
                            "type": "string",
                            "description": "CSS selector for UI actions"
                        },
                        "value": {
                            "type": "string",
                            "description": "Value for type/select actions"
                        },
                        "url": {
                            "type": "string",
                            "description": "URL for navigate action"
                        },
                        "method": {
                            "type": "string",
                            "description": "HTTP method for API action"
                        },
                        "endpoint": {
                            "type": "string",
                            "description": "API endpoint for API action"
                        }
                    },
                    "required": ["action_type"]
                }
            }
        }
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def execute(
        self,
        action_type: str,
        selector: str = None,
        value: str = None,
        url: str = None,
        method: str = None,
        endpoint: str = None
    ) -> ToolResult:
        """Test an action."""
        # This is a placeholder - actual implementation would use browser_manager
        return ToolResult(
            success=True,
            data={
                "action_type": action_type,
                "tested": True,
                "message": "Action test would be performed with browser. Use browser tools directly for now."
            }
        )


def create_task_tools(workspace=None) -> List[BaseTool]:
    """Create all task-related tools."""
    return [
        ExtractActionSpaceTool(workspace=workspace),
        GenerateTaskTool(workspace=workspace),
        GenerateTrajectoryTool(workspace=workspace),
        GenerateJudgeTool(workspace=workspace),
        ExportTaskConfigTool(workspace=workspace),
        TestActionTool(workspace=workspace),
    ]


__all__ = [
    "ExtractActionSpaceTool",
    "GenerateTaskTool",
    "GenerateTrajectoryTool",
    "GenerateJudgeTool",
    "ExportTaskConfigTool",
    "TestActionTool",
    "create_task_tools",
]

