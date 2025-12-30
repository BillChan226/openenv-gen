"""
User Agent - Requirements Refinement & Testing

Responsibilities:
1. Refine user requirements into detailed specs
2. Test the generated application (browser + API)
3. Create issues for bugs found
4. Approve when everything works

Tools:
- Browser: Navigate, screenshot, click, fill, etc.
- Docker: Status, logs
- API: Test endpoints
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.llm import Message

from .base import EnvGenAgent


class UserAgent(EnvGenAgent):
    """
    User Agent - Acts as PM/QA.
    
    Has access to:
    - Browser tools for UI testing
    - Docker tools for container management
    - API testing tools
    
    Uses prompts from: prompts/user_agent.j2
    """
    
    agent_id = "user"
    agent_name = "UserAgent"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._test_results: List[Dict] = []
    
    # ==================== Main Interface ====================
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute user agent tasks."""
        task_type = task.get("type", "")
        
        if task_type == "refine":
            return await self._refine_requirements(task.get("raw_requirements", ""))
        elif task_type == "test":
            return await self.test_application()
        else:
            return {"success": False, "error": f"Unknown task type: {task_type}"}
    
    # ==================== Requirements Refinement ====================
    
    async def refine_requirements(self, raw_requirements: str) -> Dict[str, Any]:
        """
        Refine raw requirements into detailed specs.
        
        Uses j2 template: user_agent.j2 -> refine_requirements macro
        """
        self._logger.info("Refining requirements...")
        
        # Render prompt from j2 template
        try:
            prompt = self.render_macro(
                "user_agent.j2",
                "refine_requirements",
                raw_requirements=raw_requirements
            )
        except Exception as e:
            self._logger.warning(f"Could not load j2 template, using inline prompt: {e}")
            prompt = self._get_refine_prompt(raw_requirements)
        
        response = await self.think(prompt)
        
        try:
            # Extract JSON from response
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            requirements = json.loads(json_str)
            self._requirements = requirements
            
            return {
                "success": True,
                "requirements": requirements,
            }
        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse requirements: {e}")
            return {
                "success": False,
                "error": str(e),
                "raw_response": response,
            }
    
    def _get_refine_prompt(self, raw_requirements: str) -> str:
        """Fallback prompt if j2 template not available."""
        return f"""You are a senior project manager refining user requirements.

Raw User Requirements:
{raw_requirements}

Create a detailed JSON specification with:
- project: name, description, target_users, value_proposition
- features: list with name, description, user_stories, acceptance_criteria, priority
- tech_stack: frontend (React), backend (Express), database (PostgreSQL)
- ui_style: theme, colors, key_pages
- data_model: entities with fields and relationships
- api_requirements: response_format with list_wrapper: "items"

Output ONLY valid JSON, no markdown.
"""
    
    async def _refine_requirements(self, raw: str) -> Dict[str, Any]:
        """Internal wrapper for execute()."""
        return await self.refine_requirements(raw)
    
    # ==================== Testing ====================
    
    async def test_application(self) -> Dict[str, Any]:
        """
        Test the generated application using browser and API tools.
        
        Full testing flow:
        1. Check Docker containers
        2. Test API health
        3. Browser-based UI testing
        4. Report issues found
        """
        self._logger.info("Starting application testing...")
        
        issues = []
        
        # Phase 1: Check Docker status
        docker_ok = await self._check_docker()
        if not docker_ok:
            return {
                "success": False,
                "overall_status": "blocked",
                "issues": [{"title": "Docker not running", "module": "docker", "severity": "critical"}],
            }
        
        # Phase 2: Test API health
        api_ok, api_issues = await self._test_api()
        issues.extend(api_issues)
        
        # Phase 3: Browser testing
        if api_ok:
            browser_issues = await self._test_browser()
            issues.extend(browser_issues)
        
        # Determine overall status
        if not issues:
            overall_status = "pass"
        elif any(i.get("severity") == "critical" for i in issues):
            overall_status = "fail"
        else:
            overall_status = "fail"
        
        self._test_results.append({
            "issues": issues,
            "status": overall_status,
        })
        
        return {
            "success": True,
            "overall_status": overall_status,
            "issues": issues,
        }
    
    async def _check_docker(self) -> bool:
        """Check if Docker containers are running."""
        result = await self.call_tool("docker_status")
        if result and "running" in str(result).lower():
            self._logger.info("Docker containers are running")
            return True
        
        self._logger.warning("Docker containers not running, attempting to start...")
        await self.call_tool("docker_up")
        await asyncio.sleep(10)  # Wait for containers
        
        result = await self.call_tool("docker_status")
        return result and "running" in str(result).lower()
    
    def _get_test_credentials(self) -> tuple[str, str]:
        """Get test credentials from context or return defaults."""
        if self.context:
            email = getattr(self.context, 'test_email', 'admin@example.com')
            password = getattr(self.context, 'test_password', 'admin123')
            return email, password
        return 'admin@example.com', 'admin123'
    
    async def _test_api(self) -> tuple[bool, List[Dict]]:
        """Test API endpoints using dynamic port."""
        issues = []
        
        # Get port from context (dynamic, not hardcoded)
        api_port = getattr(self.context, 'api_port', 8000) if self.context else 8000
        
        # Test health endpoint
        result = await self.call_tool("test_api", method="GET", url=f"http://localhost:{api_port}/health")
        if not result or "error" in str(result).lower():
            issues.append({
                "title": "API health check failed",
                "description": f"GET /health returned: {result}",
                "module": "backend",
                "severity": "critical",
            })
            return False, issues
        
        # Test auth endpoints - get credentials from context or use defaults
        test_email, test_password = self._get_test_credentials()
        auth_endpoints = [
            ("POST", "/api/auth/login", {"email": test_email, "password": test_password}),
        ]
        
        for method, path, body in auth_endpoints:
            result = await self.call_tool(
                "test_api",
                method=method,
                url=f"http://localhost:{api_port}{path}",
                body=body
            )
            
            if not result or "error" in str(result).lower():
                issues.append({
                    "title": f"API {method} {path} failed",
                    "description": f"Response: {result}",
                    "module": "backend",
                    "severity": "major",
                })
        
        return len(issues) == 0, issues
    
    async def _test_browser(self) -> List[Dict]:
        """Test UI with browser tools using dynamic port."""
        issues = []
        
        # Get port from context (dynamic, not hardcoded)
        ui_port = getattr(self.context, 'ui_port', 3000) if self.context else 3000
        
        # Navigate to app
        result = await self.call_tool("browser_navigate", url=f"http://localhost:{ui_port}")
        if not result:
            issues.append({
                "title": "Frontend not accessible",
                "description": f"Could not navigate to http://localhost:{ui_port}",
                "module": "frontend",
                "severity": "critical",
            })
            return issues
        
        # Take screenshot
        await self.call_tool("browser_screenshot", save_path="screenshots/initial.png")
        
        # Check for console errors
        console_errors = await self.call_tool("browser_console", filter_type="error")
        if console_errors and len(console_errors) > 0:
            issues.append({
                "title": "JavaScript console errors",
                "description": f"Errors found: {console_errors[:3]}",
                "module": "frontend",
                "severity": "major",
            })
        
        # Check for network errors
        network_errors = await self.call_tool("browser_network_errors")
        if network_errors and len(network_errors) > 0:
            for error in network_errors[:5]:
                issues.append({
                    "title": f"API error: {error.get('status', 'unknown')}",
                    "description": f"URL: {error.get('url', 'unknown')}",
                    "module": "backend" if "/api/" in str(error.get('url', '')) else "frontend",
                    "severity": "major",
                })
        
        # Get accessibility tree to find elements
        a11y_tree = await self.call_tool("browser_a11y_tree", selector="body", max_nodes=200)
        
        # Test login if present
        if "login" in str(a11y_tree).lower() or "email" in str(a11y_tree).lower():
            login_issues = await self._test_login()
            issues.extend(login_issues)
        
        # Take final screenshot
        await self.call_tool("browser_screenshot", save_path="screenshots/final.png", full_page=True)
        
        # Close browser
        await self.call_tool("browser_close")
        
        return issues
    
    async def _test_login(self) -> List[Dict]:
        """Test login functionality."""
        issues = []
        
        # Get test credentials from context or use defaults
        test_email, test_password = self._get_test_credentials()
        
        # Fill email
        await self.call_tool("browser_fill", selector="input[type='email'], input[name='email']", value=test_email)
        
        # Fill password
        await self.call_tool("browser_fill", selector="input[type='password'], input[name='password']", value=test_password)
        
        # Click submit
        await self.call_tool("browser_click", selector="button[type='submit'], button:has-text('Login'), button:has-text('Sign in')")
        
        # Wait for navigation
        await asyncio.sleep(2)
        
        # Check for errors
        network_errors = await self.call_tool("browser_network_errors")
        if network_errors:
            for error in network_errors:
                if error.get("status") in [401, 403]:
                    issues.append({
                        "title": "Login failed",
                        "description": f"Auth error: {error}",
                        "module": "backend",
                        "severity": "critical",
                    })
        
        return issues
    
    # ==================== Communication Handlers ====================
    
    async def _answer_question(self, message) -> str:
        """Answer questions from other agents."""
        try:
            prompt = self.render_macro(
                "user_agent.j2",
                "answer_question",
                question=message.content,
                context=self._requirements
            )
        except:
            prompt = f"""You are the User/PM agent. Another agent asks:

{message.content}

Requirements context:
{json.dumps(self._requirements, indent=2) if self._requirements else "Not yet refined"}

Provide clear guidance based on the project requirements.
"""
        return await self.think(prompt)
    
    async def _process_message(self, message):
        """Process updates from other agents."""
        if message.msg_type == "update":
            self._logger.info(f"Progress from {message.from_agent}: {message.content[:100]}")
        elif message.msg_type == "complete":
            self._logger.info(f"{message.from_agent} completed: {message.content}")
