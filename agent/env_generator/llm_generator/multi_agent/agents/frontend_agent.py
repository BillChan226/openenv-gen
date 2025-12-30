"""
Frontend Agent - UI Code Generation

Responsibilities:
1. Generate React application
2. Create components and pages
3. Implement API service with correct response handling
4. Fix frontend issues

Uses prompts from: prompts/code_agents.j2
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.llm import Message

from .base import EnvGenAgent


class FrontendAgent(EnvGenAgent):
    """
    Frontend Agent - Handles all frontend/UI code.
    
    Has access to:
    - File tools for code generation
    - Runtime tools for npm commands
    
    Communicates with:
    - DesignAgent: Get UI spec
    - BackendAgent: Get API endpoints
    """
    
    agent_id = "frontend"
    agent_name = "FrontendAgent"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ui_spec: Dict = {}
        self._api_spec: Dict = {}
        self._files_created: List[str] = []
    
    # ==================== Main Interface ====================
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute frontend tasks."""
        task_type = task.get("type", "")
        
        if task_type == "generate":
            return await self._generate()
        elif task_type == "fix":
            return await self._fix_issues(task.get("issues", []))
        else:
            return {"success": False, "error": f"Unknown task type: {task_type}"}
    
    # ==================== Generation ====================
    
    async def _generate(self) -> Dict[str, Any]:
        """Generate frontend code from design spec."""
        self._logger.info("Generating frontend code...")
        
        # Get specs
        ui_spec = self._design_docs.get("design_ui_spec") or self._design_docs.get("ui_spec")
        api_spec = self._design_docs.get("design_api_spec") or self._design_docs.get("api_spec")
        
        if not ui_spec:
            content = self.read_file("design/spec.ui.json")
            if content:
                ui_spec = json.loads(content)
        
        if not api_spec:
            content = self.read_file("design/spec.api.json")
            if content:
                api_spec = json.loads(content)
        
        if not ui_spec:
            return {"success": False, "error": "No UI spec available"}
        
        self._ui_spec = ui_spec
        self._api_spec = api_spec or {}
        
        # Ask backend about endpoints
        api_info = await self.ask("backend", "What API endpoints are available?")
        
        try:
            # 1. package.json
            pkg_json = self._generate_package_json()
            self.write_file("app/frontend/package.json", pkg_json)
            self._files_created.append("app/frontend/package.json")
            
            # 2. Vite config
            vite_config = self._generate_vite_config()
            self.write_file("app/frontend/vite.config.js", vite_config)
            self._files_created.append("app/frontend/vite.config.js")
            
            # 3. Index HTML
            index_html = self._generate_index_html()
            self.write_file("app/frontend/index.html", index_html)
            self._files_created.append("app/frontend/index.html")
            
            # 4. Main entry
            main_jsx = self._generate_main()
            self.write_file("app/frontend/src/main.jsx", main_jsx)
            self._files_created.append("app/frontend/src/main.jsx")
            
            # 5. API service (CRITICAL - must match backend response format)
            api_js = await self._generate_api_service(self._api_spec)
            self.write_file("app/frontend/src/services/api.js", api_js)
            self._files_created.append("app/frontend/src/services/api.js")
            
            # 6. App component
            app_jsx = await self._generate_app(ui_spec)
            self.write_file("app/frontend/src/App.jsx", app_jsx)
            self._files_created.append("app/frontend/src/App.jsx")
            
            # 7. Pages
            pages = await self._generate_pages(ui_spec)
            for page_name, page_code in pages.items():
                path = f"app/frontend/src/pages/{page_name}.jsx"
                self.write_file(path, page_code)
                self._files_created.append(path)
            
            # 8. Components
            components = await self._generate_components(ui_spec)
            for comp_name, comp_code in components.items():
                path = f"app/frontend/src/components/{comp_name}.jsx"
                self.write_file(path, comp_code)
                self._files_created.append(path)
            
            # 9. Global styles
            styles = await self._generate_styles(ui_spec.get("theme", {}))
            self.write_file("app/frontend/src/index.css", styles)
            self._files_created.append("app/frontend/src/index.css")
            
            # 10. Dockerfile + nginx
            self.write_file("app/frontend/Dockerfile", self._generate_dockerfile())
            self.write_file("app/frontend/nginx.conf", self._generate_nginx_config())
            self._files_created.extend(["app/frontend/Dockerfile", "app/frontend/nginx.conf"])
            
            return {
                "success": True,
                "files_created": self._files_created,
            }
            
        except Exception as e:
            self._logger.error(f"Frontend generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_package_json(self) -> str:
        """Generate package.json."""
        return json.dumps({
            "name": "frontend",
            "version": "1.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "preview": "vite preview"
            },
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-router-dom": "^6.20.1"
            },
            "devDependencies": {
                "@vitejs/plugin-react": "^4.2.1",
                "vite": "^5.0.8"
            }
        }, indent=2)
    
    def _generate_vite_config(self) -> str:
        return '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://backend:3000',
        changeOrigin: true
      }
    }
  }
})
'''
    
    def _generate_index_html(self) -> str:
        return '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
'''
    
    def _generate_main(self) -> str:
        return '''import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
'''
    
    async def _generate_api_service(self, api_spec: Dict) -> str:
        """Generate API service - CRITICAL for correct response handling."""
        try:
            prompt = self.render_macro(
                "code_agents.j2",
                "frontend_generate_api_service",
                api_spec=api_spec
            )
        except Exception as e:
            self._logger.warning(f"Could not load j2 template: {e}")
            # Get response wrapper from spec
            conventions = api_spec.get("conventions", {})
            list_wrapper = conventions.get("list_response_wrapper", "items")
            
            prompt = f"""Generate frontend API service.

CRITICAL: Backend returns data wrapped in '{list_wrapper}' key for lists.

Example:
- GET /api/items returns {{ items: [...], total: N }}
- GET /api/items/123 returns {{ item: {{...}} }}

Generate service that:
1. Has base request() function with auth header
2. Extracts data correctly from response
3. Functions for ALL endpoints in spec

Endpoints:
{json.dumps(api_spec.get("endpoints", [])[:10], indent=2)}

Output raw JavaScript only.
"""
        
        return await self.think(prompt)
    
    async def _generate_app(self, ui_spec: Dict) -> str:
        """Generate App.jsx with routing."""
        pages = ui_spec.get("pages", [])
        
        try:
            prompt = self.render_macro(
                "code_agents.j2",
                "frontend_generate_app",
                ui_spec=ui_spec,
                pages=pages
            )
        except:
            prompt = f"""Generate React App.jsx with routing.

Pages: {json.dumps(pages, indent=2)}

Use React Router v6. Include:
- Auth context
- Protected routes
- Layout wrapper

Output raw JSX only.
"""
        
        return await self.think(prompt)
    
    async def _generate_pages(self, ui_spec: Dict) -> Dict[str, str]:
        """Generate page components."""
        pages = {}
        page_specs = ui_spec.get("pages", [])
        
        for page_spec in page_specs:
            name = page_spec.get("name", "Page")
            
            try:
                prompt = self.render_macro(
                    "code_agents.j2",
                    "frontend_generate_page",
                    page_spec=page_spec,
                    api_endpoints=self._api_spec.get("endpoints", [])[:5]
                )
            except:
                prompt = f"""Generate React page: {name}

Spec: {json.dumps(page_spec, indent=2)}

IMPORTANT: When fetching lists, API returns {{items: [...]}}
Use: const data = await api.getItems(); // Already extracts .items

Output raw JSX only.
"""
            
            page_code = await self.think(prompt)
            pages[name] = page_code
        
        return pages
    
    async def _generate_components(self, ui_spec: Dict) -> Dict[str, str]:
        """Generate reusable components."""
        components = {}
        comp_specs = ui_spec.get("components", [])
        
        for comp_spec in comp_specs:
            name = comp_spec.get("name", "Component")
            
            prompt = f"""Generate React component: {name}

Spec: {json.dumps(comp_spec, indent=2)}

Functional component with proper props. Output raw JSX only.
"""
            
            comp_code = await self.think(prompt)
            components[name] = comp_code
        
        return components
    
    async def _generate_styles(self, theme: Dict) -> str:
        """Generate global CSS."""
        prompt = f"""Generate global CSS styles.

Theme: {json.dumps(theme, indent=2)}

Include:
- CSS variables for theme colors
- Reset/normalize
- Typography
- Utility classes

Output raw CSS only.
"""
        return await self.think(prompt)
    
    def _generate_dockerfile(self) -> str:
        return '''FROM node:20-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
'''
    
    def _generate_nginx_config(self) -> str:
        return '''server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
'''
    
    # ==================== Fix Issues ====================
    
    async def _fix_issues(self, issues: List[Dict]) -> Dict[str, Any]:
        """Fix frontend issues."""
        self._logger.info(f"Fixing {len(issues)} frontend issues...")
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
        """Fix a single frontend issue."""
        description = issue.get("description", "")
        
        # Check if API-related issue
        if "map" in description.lower() or "undefined" in description.lower():
            api_info = await self.ask(
                "backend",
                f"What is the response format for: {description}"
            )
            description += f"\n\nBackend says: {api_info}"
        
        related_files = issue.get("related_files", [])
        files_content = {}
        
        for f in related_files:
            content = self.read_file(f)
            if content:
                files_content[f] = content
        
        if not files_content:
            for f in ["app/frontend/src/services/api.js", "app/frontend/src/App.jsx"]:
                content = self.read_file(f)
                if content:
                    files_content[f] = content
        
        try:
            prompt = self.render_macro(
                "code_agents.j2",
                "frontend_fix_issue",
                issue={**issue, "description": description},
                current_files=files_content,
                api_spec=self._api_spec
            )
        except:
            prompt = f"""Fix this frontend issue:
Issue: {issue.get('title', '')}
Description: {description}

Common causes:
- "x.map is not a function": API returns {{items:[...]}} but code expects array
- Wrong response key extraction

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
        """Answer questions about the frontend."""
        try:
            prompt = self.render_macro(
                "code_agents.j2",
                "answer_question",
                agent_type="Frontend",
                question=message.content,
                context={"ui_spec": self._ui_spec, "files": self._files_created}
            )
        except:
            prompt = f"""You are the Frontend agent. Another agent asks:
{message.content}

UI spec: {json.dumps(self._ui_spec, indent=2)[:1000] if self._ui_spec else "Not generated"}
Files: {self._files_created}

Provide a helpful answer about UI components or styling.
"""
        return await self.think(prompt)
