"""
Backend Agent - API Code Generation

Responsibilities:
1. Generate Express.js server code
2. Create route handlers for all endpoints
3. Implement authentication middleware
4. Fix backend issues

Uses prompts from: prompts/code_agents.j2
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.llm import Message

from .base import EnvGenAgent


class BackendAgent(EnvGenAgent):
    """
    Backend Agent - Handles all backend/API code.
    
    Has access to:
    - File tools for code generation
    - Runtime tools for testing server
    - API testing tools
    
    Communicates with:
    - DesignAgent: Get API spec
    - DatabaseAgent: Get table info
    - FrontendAgent: Coordinate API contracts
    """
    
    agent_id = "backend"
    agent_name = "BackendAgent"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._api_spec: Dict = {}
        self._files_created: List[str] = []
    
    # ==================== Main Interface ====================
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute backend tasks."""
        task_type = task.get("type", "")
        
        if task_type == "generate":
            return await self._generate()
        elif task_type == "fix":
            return await self._fix_issues(task.get("issues", []))
        else:
            return {"success": False, "error": f"Unknown task type: {task_type}"}
    
    # ==================== Generation ====================
    
    async def _generate(self) -> Dict[str, Any]:
        """Generate backend code from design spec."""
        self._logger.info("Generating backend code...")
        
        # Get API spec
        api_spec = self._design_docs.get("design_api_spec") or self._design_docs.get("api_spec")
        
        if not api_spec:
            content = self.read_file("design/spec.api.json")
            if content:
                api_spec = json.loads(content)
        
        if not api_spec:
            return {
                "success": False, 
                "error": "No API spec found. Use ask_agent tool to request from design agent.",
                "suggestion": "ask_agent(agent_id='design', question='Please provide the API specification JSON.')"
            }
        
        self._api_spec = api_spec
        
        # Get database table info from file or LLM can use ask_agent tool
        db_content = self.read_file("design/spec.database.json")
        db_tables = db_content if db_content else "Tables not yet defined - check with database agent"
        
        try:
            # 1. package.json
            pkg_json = self._generate_package_json()
            self.write_file("app/backend/package.json", pkg_json)
            self._files_created.append("app/backend/package.json")
            
            # 2. server.js
            server_js = await self._generate_server(api_spec, db_tables)
            self.write_file("app/backend/server.js", server_js)
            self._files_created.append("app/backend/server.js")
            
            # 3. Route files
            routes = await self._generate_routes(api_spec, db_tables)
            for route_name, route_code in routes.items():
                path = f"app/backend/routes/{route_name}.js"
                self.write_file(path, route_code)
                self._files_created.append(path)
            
            # 4. Auth middleware
            middleware = await self._generate_middleware()
            self.write_file("app/backend/middleware/auth.js", middleware)
            self._files_created.append("app/backend/middleware/auth.js")
            
            # 5. Dockerfile
            dockerfile = self._generate_dockerfile()
            self.write_file("app/backend/Dockerfile", dockerfile)
            self._files_created.append("app/backend/Dockerfile")
            
            # LLM can use tell_agent/broadcast to notify other agents
            return {
                "success": True,
                "files_created": self._files_created,
                "endpoints": [e.get("path") for e in api_spec.get("endpoints", [])],
                "notify_suggestion": "Consider using tell_agent or broadcast to notify frontend about API completion.",
            }
            
        except Exception as e:
            self._logger.error(f"Backend generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_package_json(self) -> str:
        """Generate package.json."""
        return json.dumps({
            "name": "backend",
            "version": "1.0.0",
            "main": "server.js",
            "scripts": {
                "start": "node server.js",
                "dev": "nodemon server.js"
            },
            "dependencies": {
                "express": "^4.18.2",
                "cors": "^2.8.5",
                "pg": "^8.11.3",
                "bcryptjs": "^2.4.3",
                "jsonwebtoken": "^9.0.2",
                "uuid": "^9.0.0",
                "dotenv": "^16.3.1"
            },
            "devDependencies": {
                "nodemon": "^3.0.2"
            }
        }, indent=2)
    
    async def _generate_server(self, api_spec: Dict, db_tables: str) -> str:
        """Generate server.js using j2 template."""
        try:
            prompt = self.render_macro(
                "code_agents.j2",
                "backend_generate_server",
                api_spec=api_spec,
                db_tables=db_tables
            )
        except Exception as e:
            self._logger.warning(f"Could not load j2 template: {e}")
            prompt = f"""Generate Express server.js.

API Base: {api_spec.get("conventions", {}).get("base_url", "/api")}
Endpoints: {len(api_spec.get("endpoints", []))} total

Requirements:
- Express with CORS, JSON parsing
- PostgreSQL pool connection
- Mount routes from ./routes/
- Error handling middleware
- Health check at /health

Output raw JavaScript only.
"""
        
        return await self.think(prompt)
    
    async def _generate_routes(self, api_spec: Dict, db_tables: str) -> Dict[str, str]:
        """Generate route files grouped by resource."""
        routes = {}
        endpoints = api_spec.get("endpoints", [])
        
        # Group by resource
        by_resource: Dict[str, List] = {}
        for endpoint in endpoints:
            path = endpoint.get("path", "")
            parts = path.strip("/").split("/")
            resource = parts[0] if parts else "index"
            
            if resource not in by_resource:
                by_resource[resource] = []
            by_resource[resource].append(endpoint)
        
        for resource, resource_endpoints in by_resource.items():
            try:
                prompt = self.render_macro(
                    "code_agents.j2",
                    "backend_generate_routes",
                    resource=resource,
                    endpoints=resource_endpoints,
                    db_tables=db_tables
                )
            except:
                prompt = f"""Generate Express routes for: {resource}

Endpoints:
{json.dumps(resource_endpoints, indent=2)}

CRITICAL: Response format must be:
- Lists: {{ items: [...], total: N }}
- Single: {{ item: {{...}} }}
- Errors: {{ error: {{ code, message }} }}

Use parameterized queries. Output raw JavaScript.
"""
            
            route_code = await self.think(prompt)
            routes[resource] = route_code
        
        return routes
    
    async def _generate_middleware(self) -> str:
        """Generate auth middleware."""
        prompt = """Generate Express JWT auth middleware.

Requirements:
- Verify JWT from Authorization header (Bearer token)
- Attach decoded user to req.user
- Handle missing/invalid tokens with 401
- Export as module.exports = auth;

Output raw JavaScript only.
"""
        return await self.think(prompt)
    
    def _generate_dockerfile(self) -> str:
        """Generate Dockerfile."""
        return '''FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
'''
    
    # ==================== Fix Issues ====================
    
    async def _fix_issues(self, issues: List[Dict]) -> Dict[str, Any]:
        """Fix backend issues."""
        self._logger.info(f"Fixing {len(issues)} backend issues...")
        fixed = 0
        
        for issue in issues:
            try:
                result = await self._fix_single_issue(issue)
                if result:
                    fixed += 1
            except Exception as e:
                self._logger.error(f"Failed to fix issue: {e}")
        
        return {
            "success": True,
            "fixed": fixed,
            "total": len(issues),
        }
    
    async def _fix_single_issue(self, issue: Dict) -> bool:
        """Fix a single backend issue."""
        related_files = issue.get("related_files", [])
        
        files_content = {}
        for f in related_files:
            content = self.read_file(f)
            if content:
                files_content[f] = content
        
        if not files_content:
            files_content["server.js"] = self.read_file("app/backend/server.js") or ""
        
        try:
            prompt = self.render_macro(
                "code_agents.j2",
                "backend_fix_issue",
                issue=issue,
                current_files=files_content,
                api_spec=self._api_spec
            )
        except:
            prompt = f"""Fix this backend issue:
Issue: {issue.get('title', '')}
Description: {issue.get('description', '')}

Common fixes:
- 404: Route path mismatch
- 405: Wrong HTTP method
- 400: Request body format
- Response format: Use {{items:[...]}} for lists

Current code:
{json.dumps(files_content, indent=2)[:2000]}

Provide fix as JSON: {{"files": [{{"path": "...", "content": "..."}}]}}
"""
        
        response = await self.think(prompt)
        
        try:
            fix = json.loads(self._extract_json(response))
            
            for file_fix in fix.get("files", []):
                path = file_fix.get("path", "")
                content = file_fix.get("content", "")
                if path and content:
                    self.write_file(path, content)
            
            # LLM can use tell_agent to notify if needed
            self._logger.info(f"Fixed: {issue.get('title', '')}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to parse fix: {e}")
        
        return False
    
    def _extract_json(self, response: str) -> str:
        """Extract JSON from LLM response."""
        if "```json" in response:
            return response.split("```json")[1].split("```")[0]
        elif "```" in response:
            return response.split("```")[1].split("```")[0]
        return response
    
    # ==================== Communication Handlers ====================
    
    async def _answer_question(self, message) -> str:
        """Answer questions about the backend."""
        try:
            prompt = self.render_macro(
                "code_agents.j2",
                "answer_question",
                agent_type="Backend",
                question=message.content,
                context={"api_spec": self._api_spec, "files": self._files_created}
            )
        except:
            prompt = f"""You are the Backend agent. Another agent asks:
{message.content}

API spec: {json.dumps(self._api_spec, indent=2)[:1000] if self._api_spec else "Not generated"}
Files: {self._files_created}

Provide a helpful answer about API endpoints or implementation.
"""
        return await self.think(prompt)
