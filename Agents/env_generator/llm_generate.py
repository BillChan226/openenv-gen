#!/usr/bin/env python
"""
LLM-Powered Environment Generator

Uses LLM (GPT-4) as the core code generator with templates as guidance.

Usage:
    python llm_generate.py --name calendar --domain calendar
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Set API key from environment variable
# Usage: export OPENAI_API_KEY=your-api-key
if not os.environ.get("OPENAI_API_KEY"):
    print("Warning: OPENAI_API_KEY environment variable not set")
    print("Please set it: export OPENAI_API_KEY=your-api-key")

try:
    from openai import AsyncOpenAI
except ImportError:
    print("Please install openai: pip install openai")
    sys.exit(1)


@dataclass
class GenerationContext:
    """Context for environment generation"""
    name: str
    display_name: str = ""
    description: str = ""
    domain_type: str = "custom"
    entities: List[Dict] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    api_port: int = 8000
    ui_port: int = 3000
    openenv_port: int = 8080
    
    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.name.replace("_", " ").title()
    
    @property
    def class_name(self) -> str:
        return "".join(word.capitalize() for word in self.name.split("_"))


class LLMCodeGenerator:
    """LLM-powered code generator for OpenEnv environments"""
    
    def __init__(self, model: str = "gpt-4-turbo-preview"):
        self.client = AsyncOpenAI()
        self.model = model
        
        # Load reference docs
        self.openenv_docs = self._load_openenv_docs()
        self.project_structure = self._get_project_structure()
    
    def _load_openenv_docs(self) -> str:
        """Load OpenEnv documentation as context"""
        docs_path = Path(__file__).parent.parent.parent.parent / "openenv-gen-main" / "README.md"
        if docs_path.exists():
            return docs_path.read_text()[:8000]  # Truncate for context window
        return """
OpenEnv is a framework for creating RL training environments with:
- Environment class with reset(), step(), state() methods
- HTTPEnvClient for remote environment access
- Action, Observation, State dataclasses
- FastAPI server for HTTP interface
"""
    
    def _get_project_structure(self) -> str:
        """Get the expected project structure"""
        return """
Generated Environment Structure:
{env_name}/
├── {env_name}_api/              # FastAPI backend
│   ├── main.py                  # FastAPI app entry
│   ├── models.py                # SQLAlchemy models
│   ├── schemas.py               # Pydantic schemas
│   ├── database.py              # DB configuration
│   ├── auth.py                  # JWT authentication
│   ├── routers/                 # API routers
│   │   ├── __init__.py
│   │   ├── auth.py              # Auth endpoints
│   │   └── {entity}.py          # Entity CRUD endpoints
│   ├── requirements.txt
│   └── Dockerfile
├── {env_name}_ui/               # React frontend (TypeScript)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── services/api.ts
│   │   ├── contexts/AuthContext.tsx
│   │   ├── components/
│   │   └── pages/
│   ├── package.json
│   └── Dockerfile
├── openenv_adapter/             # OpenEnv integration
│   ├── models.py                # Action, Observation, State
│   ├── client.py                # HTTPEnvClient
│   └── server/
│       ├── environment.py       # Environment class
│       └── app.py               # OpenEnv HTTP server
├── docker-compose.yml
└── README.md
"""
    
    async def generate(
        self,
        context: GenerationContext,
        output_dir: Path,
    ) -> Dict[str, str]:
        """Generate complete environment using LLM"""
        output_dir.mkdir(parents=True, exist_ok=True)
        files = {}
        
        print(f"\nGenerating {context.display_name} environment...")
        print(f"Using model: {self.model}")
        print("-" * 50)
        
        # Phase 1: Design environment spec
        print("\n[1/6] Designing environment specification...")
        spec = await self._design_spec(context)
        context.entities = spec.get("entities", [])
        context.features = spec.get("features", [])
        
        spec_file = output_dir / "env_spec.json"
        spec_file.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        files["env_spec.json"] = json.dumps(spec, indent=2)
        print(f"  ✓ Generated spec with {len(context.entities)} entities")
        
        # Phase 2: Generate backend
        print("\n[2/6] Generating FastAPI backend...")
        backend_files = await self._generate_backend(context, output_dir)
        files.update(backend_files)
        print(f"  ✓ Generated {len(backend_files)} backend files")
        
        # Phase 3: Generate frontend
        print("\n[3/6] Generating React frontend...")
        frontend_files = await self._generate_frontend(context, output_dir)
        files.update(frontend_files)
        print(f"  ✓ Generated {len(frontend_files)} frontend files")
        
        # Phase 4: Generate OpenEnv adapter
        print("\n[4/6] Generating OpenEnv adapter...")
        openenv_files = await self._generate_openenv(context, output_dir)
        files.update(openenv_files)
        print(f"  ✓ Generated {len(openenv_files)} OpenEnv files")
        
        # Phase 5: Generate Docker configuration
        print("\n[5/6] Generating Docker configuration...")
        docker_files = await self._generate_docker(context, output_dir)
        files.update(docker_files)
        print(f"  ✓ Generated {len(docker_files)} Docker files")
        
        # Phase 6: Generate README
        print("\n[6/6] Generating documentation...")
        readme = await self._generate_readme(context, spec)
        readme_file = output_dir / "README.md"
        readme_file.write_text(readme, encoding="utf-8")
        files["README.md"] = readme
        print("  ✓ Generated README.md")
        
        return files
    
    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call LLM with prompts"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=4000,
        )
        return response.choices[0].message.content
    
    async def _design_spec(self, context: GenerationContext) -> Dict:
        """Design environment specification using LLM"""
        system_prompt = """You are an expert software architect. Design a complete environment specification.
Output ONLY valid JSON with this structure:
{
    "name": "env_name",
    "description": "description",
    "entities": [
        {
            "name": "EntityName",
            "table_name": "table_names",
            "description": "description",
            "fields": [
                {"name": "id", "type": "Integer", "primary_key": true},
                {"name": "field_name", "type": "String(255)", "nullable": true}
            ]
        }
    ],
    "features": ["Feature1", "Feature2"],
    "user_roles": [{"name": "admin", "permissions": ["create", "read", "update", "delete"]}]
}

Field types: Integer, String(n), Text, Boolean, DateTime, Float, JSON
Always include a User entity with id, email, hashed_password, full_name, created_at, is_active fields."""
        
        user_prompt = f"""Design a specification for: {context.display_name}
Description: {context.description}
Domain: {context.domain_type}

Include appropriate entities, fields, and features for this domain."""
        
        response = await self._call_llm(system_prompt, user_prompt)
        
        # Extract JSON from response
        try:
            # Try to find JSON in response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response
            
            return json.loads(json_str.strip())
        except json.JSONDecodeError:
            # Fallback to basic spec
            return {
                "name": context.name,
                "description": context.description,
                "entities": [
                    {
                        "name": "User",
                        "table_name": "users",
                        "fields": [
                            {"name": "id", "type": "Integer", "primary_key": True},
                            {"name": "email", "type": "String(255)", "unique": True},
                            {"name": "hashed_password", "type": "String(255)"},
                            {"name": "created_at", "type": "DateTime", "default": "now"},
                        ],
                    }
                ],
                "features": ["Authentication", "CRUD Operations"],
            }
    
    async def _generate_backend(self, context: GenerationContext, output_dir: Path) -> Dict[str, str]:
        """Generate FastAPI backend using LLM"""
        files = {}
        api_dir = output_dir / f"{context.name}_api"
        api_dir.mkdir(parents=True, exist_ok=True)
        (api_dir / "routers").mkdir(exist_ok=True)
        
        # Generate models.py
        models_code = await self._generate_file(
            context,
            "models.py",
            "SQLAlchemy models for database entities",
            """Generate SQLAlchemy models for all entities.
Use declarative_base, include relationships, and add to_dict() method.
Import datetime, use correct column types."""
        )
        (api_dir / "models.py").write_text(models_code, encoding="utf-8")
        files[f"{context.name}_api/models.py"] = models_code
        
        # Generate schemas.py
        schemas_code = await self._generate_file(
            context,
            "schemas.py",
            "Pydantic schemas for request/response validation",
            """Generate Pydantic v2 schemas with Base, Create, Update, Response variants.
Use from_attributes=True in Config. Include Token and LoginRequest schemas."""
        )
        (api_dir / "schemas.py").write_text(schemas_code, encoding="utf-8")
        files[f"{context.name}_api/schemas.py"] = schemas_code
        
        # Generate database.py
        database_code = await self._generate_file(
            context,
            "database.py",
            "Database configuration with SQLAlchemy",
            """Create engine, SessionLocal, Base, and get_db dependency.
Support both SQLite and PostgreSQL via DATABASE_URL env var."""
        )
        (api_dir / "database.py").write_text(database_code, encoding="utf-8")
        files[f"{context.name}_api/database.py"] = database_code
        
        # Generate auth.py
        auth_code = await self._generate_file(
            context,
            "auth.py",
            "JWT authentication module",
            """Implement JWT auth with jose, passlib for password hashing.
Include verify_password, get_password_hash, create_access_token, get_current_user."""
        )
        (api_dir / "auth.py").write_text(auth_code, encoding="utf-8")
        files[f"{context.name}_api/auth.py"] = auth_code
        
        # Generate auth router
        auth_router_code = await self._generate_file(
            context,
            "routers/auth.py",
            "Authentication API endpoints",
            """Create router with /register, /login, /me endpoints.
Use Depends for database and auth. Return Token on login."""
        )
        (api_dir / "routers" / "auth.py").write_text(auth_router_code, encoding="utf-8")
        files[f"{context.name}_api/routers/auth.py"] = auth_router_code
        
        # Generate entity routers
        for entity in context.entities:
            if entity.get("name") != "User":
                entity_name = entity.get("name", "Item")
                router_code = await self._generate_file(
                    context,
                    f"routers/{entity_name.lower()}.py",
                    f"CRUD API endpoints for {entity_name}",
                    f"""Create FastAPI router for {entity_name} with:
- GET / (list), POST / (create), GET /{{id}}, PUT /{{id}}, DELETE /{{id}}
- Use Depends for db and auth. Handle 404 errors."""
                )
                (api_dir / "routers" / f"{entity_name.lower()}.py").write_text(router_code, encoding="utf-8")
                files[f"{context.name}_api/routers/{entity_name.lower()}.py"] = router_code
        
        # Generate routers __init__.py
        entity_names = [e.get("name", "").lower() for e in context.entities if e.get("name") != "User"]
        router_imports = ["from .auth import router as auth_router"]
        router_imports.extend([f"from .{name} import router as {name}_router" for name in entity_names])
        router_init = "\n".join(router_imports) + "\n"
        (api_dir / "routers" / "__init__.py").write_text(router_init, encoding="utf-8")
        files[f"{context.name}_api/routers/__init__.py"] = router_init
        
        # Generate main.py
        main_code = await self._generate_file(
            context,
            "main.py",
            "FastAPI application entry point",
            f"""Create FastAPI app with CORS, include all routers with /api/v1 prefix.
Create tables on startup. Add health check endpoint.
Entities: {', '.join(e.get('name', '') for e in context.entities)}"""
        )
        (api_dir / "main.py").write_text(main_code, encoding="utf-8")
        files[f"{context.name}_api/main.py"] = main_code
        
        # Generate __init__.py
        (api_dir / "__init__.py").write_text(f'"""{context.display_name} API"""\n', encoding="utf-8")
        files[f"{context.name}_api/__init__.py"] = f'"""{context.display_name} API"""\n'
        
        # Generate requirements.txt
        requirements = """fastapi>=0.104.0
uvicorn>=0.24.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
python-dotenv>=1.0.0
psycopg2-binary>=2.9.0
"""
        (api_dir / "requirements.txt").write_text(requirements, encoding="utf-8")
        files[f"{context.name}_api/requirements.txt"] = requirements
        
        return files
    
    async def _generate_frontend(self, context: GenerationContext, output_dir: Path) -> Dict[str, str]:
        """Generate React frontend using LLM"""
        files = {}
        ui_dir = output_dir / f"{context.name}_ui"
        ui_dir.mkdir(parents=True, exist_ok=True)
        (ui_dir / "src").mkdir(exist_ok=True)
        (ui_dir / "src" / "components").mkdir(exist_ok=True)
        (ui_dir / "src" / "pages").mkdir(exist_ok=True)
        (ui_dir / "src" / "contexts").mkdir(exist_ok=True)
        (ui_dir / "src" / "services").mkdir(exist_ok=True)
        
        # Generate package.json
        package_json = {
            "name": f"{context.name}-ui",
            "version": "1.0.0",
            "type": "module",
            "scripts": {
                "dev": "vite",
                "build": "tsc && vite build",
                "preview": "vite preview"
            },
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-router-dom": "^6.20.0",
                "axios": "^1.6.0"
            },
            "devDependencies": {
                "@types/react": "^18.2.37",
                "@types/react-dom": "^18.2.15",
                "@vitejs/plugin-react": "^4.2.0",
                "typescript": "^5.2.2",
                "vite": "^5.0.0"
            }
        }
        (ui_dir / "package.json").write_text(json.dumps(package_json, indent=2), encoding="utf-8")
        files[f"{context.name}_ui/package.json"] = json.dumps(package_json, indent=2)
        
        # Generate index.html
        index_html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{context.display_name}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""
        (ui_dir / "index.html").write_text(index_html, encoding="utf-8")
        files[f"{context.name}_ui/index.html"] = index_html
        
        # Generate main.tsx
        main_tsx = await self._generate_file(
            context,
            "src/main.tsx",
            "React entry point",
            "Create React root and render App component. Import App.css."
        )
        (ui_dir / "src" / "main.tsx").write_text(main_tsx, encoding="utf-8")
        files[f"{context.name}_ui/src/main.tsx"] = main_tsx
        
        # Generate App.tsx
        app_tsx = await self._generate_file(
            context,
            "src/App.tsx",
            "Main React App component with routing",
            f"""Create App with BrowserRouter, AuthProvider, Routes.
Include protected routes for: Dashboard, {', '.join(e.get('name', '') + 'List' for e in context.entities if e.get('name') != 'User')}
Public routes: Login, Register."""
        )
        (ui_dir / "src" / "App.tsx").write_text(app_tsx, encoding="utf-8")
        files[f"{context.name}_ui/src/App.tsx"] = app_tsx
        
        # Generate App.css
        app_css = await self._generate_file(
            context,
            "src/App.css",
            "Global CSS styles",
            "Create modern CSS with CSS variables for colors, nice typography, card styles."
        )
        (ui_dir / "src" / "App.css").write_text(app_css, encoding="utf-8")
        files[f"{context.name}_ui/src/App.css"] = app_css
        
        # Generate AuthContext.tsx
        auth_context = await self._generate_file(
            context,
            "src/contexts/AuthContext.tsx",
            "React authentication context",
            "Create AuthContext with user state, login, logout, register functions. Use localStorage for token."
        )
        (ui_dir / "src" / "contexts" / "AuthContext.tsx").write_text(auth_context, encoding="utf-8")
        files[f"{context.name}_ui/src/contexts/AuthContext.tsx"] = auth_context
        
        # Generate api.ts
        api_ts = await self._generate_file(
            context,
            "src/services/api.ts",
            "API service with axios",
            f"""Create axios instance with interceptors for auth token.
Add CRUD functions for: {', '.join(e.get('name', '') for e in context.entities if e.get('name') != 'User')}
Add TypeScript interfaces for each entity."""
        )
        (ui_dir / "src" / "services" / "api.ts").write_text(api_ts, encoding="utf-8")
        files[f"{context.name}_ui/src/services/api.ts"] = api_ts
        
        # Generate Login page
        login_tsx = await self._generate_file(
            context,
            "src/pages/Login.tsx",
            "Login page component",
            "Create login form with email/password, error handling, redirect to dashboard on success."
        )
        (ui_dir / "src" / "pages" / "Login.tsx").write_text(login_tsx, encoding="utf-8")
        files[f"{context.name}_ui/src/pages/Login.tsx"] = login_tsx
        
        # Generate Dashboard page
        dashboard_tsx = await self._generate_file(
            context,
            "src/pages/Dashboard.tsx",
            "Dashboard page component",
            f"Create dashboard with navigation cards to: {', '.join(e.get('name', '') for e in context.entities if e.get('name') != 'User')}"
        )
        (ui_dir / "src" / "pages" / "Dashboard.tsx").write_text(dashboard_tsx, encoding="utf-8")
        files[f"{context.name}_ui/src/pages/Dashboard.tsx"] = dashboard_tsx
        
        # Generate vite.config.ts
        vite_config = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
"""
        (ui_dir / "vite.config.ts").write_text(vite_config, encoding="utf-8")
        files[f"{context.name}_ui/vite.config.ts"] = vite_config
        
        # Generate tsconfig.json
        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "useDefineForClassFields": True,
                "lib": ["ES2020", "DOM", "DOM.Iterable"],
                "module": "ESNext",
                "skipLibCheck": True,
                "moduleResolution": "bundler",
                "allowImportingTsExtensions": True,
                "resolveJsonModule": True,
                "isolatedModules": True,
                "noEmit": True,
                "jsx": "react-jsx",
                "strict": True
            },
            "include": ["src"]
        }
        (ui_dir / "tsconfig.json").write_text(json.dumps(tsconfig, indent=2), encoding="utf-8")
        files[f"{context.name}_ui/tsconfig.json"] = json.dumps(tsconfig, indent=2)
        
        return files
    
    async def _generate_openenv(self, context: GenerationContext, output_dir: Path) -> Dict[str, str]:
        """Generate OpenEnv adapter using LLM"""
        files = {}
        openenv_dir = output_dir / "openenv_adapter"
        openenv_dir.mkdir(parents=True, exist_ok=True)
        (openenv_dir / "server").mkdir(exist_ok=True)
        
        # Generate models.py
        models_code = await self._generate_file(
            context,
            "openenv_adapter/models.py",
            "OpenEnv Action, Observation, State dataclasses",
            f"""Create dataclasses for OpenEnv interface:
- {context.class_name}Action: action_type (str), resource (str), resource_id (str), params (dict)
- {context.class_name}Observation: success (bool), data (Any), error_message (str), available_actions (list)
- {context.class_name}State: episode_id (str), step_count (int), current_user (str), current_page (str)
Use dataclass(kw_only=True) and field(default_factory=dict) for dicts."""
        )
        (openenv_dir / "models.py").write_text(models_code, encoding="utf-8")
        files["openenv_adapter/models.py"] = models_code
        
        # Generate client.py
        client_code = await self._generate_file(
            context,
            "openenv_adapter/client.py",
            "OpenEnv HTTP client",
            f"""Create {context.class_name}Env class that wraps HTTP calls to environment server.
Include reset(), step(action), state() methods.
Add from_docker_image() class method."""
        )
        (openenv_dir / "client.py").write_text(client_code, encoding="utf-8")
        files["openenv_adapter/client.py"] = client_code
        
        # Generate server/environment.py
        env_code = await self._generate_file(
            context,
            "openenv_adapter/server/environment.py",
            "OpenEnv Environment implementation",
            f"""Create {context.class_name}Environment class with:
- __init__(api_base_url): initialize state and requests session
- reset() -> Observation: reset state, return initial observation
- step(action) -> Observation: execute action via API, return result
- state property -> State: return current state
Handle login, logout, CRUD actions for all entities."""
        )
        (openenv_dir / "server" / "environment.py").write_text(env_code, encoding="utf-8")
        files["openenv_adapter/server/environment.py"] = env_code
        
        # Generate server/app.py
        app_code = await self._generate_file(
            context,
            "openenv_adapter/server/app.py",
            "OpenEnv FastAPI server",
            f"""Create FastAPI app with /reset, /step, /state, /health endpoints.
Instantiate {context.class_name}Environment and handle requests."""
        )
        (openenv_dir / "server" / "app.py").write_text(app_code, encoding="utf-8")
        files["openenv_adapter/server/app.py"] = app_code
        
        # Generate __init__.py files
        init_code = f'"""{context.display_name} OpenEnv Adapter"""\nfrom .models import {context.class_name}Action, {context.class_name}Observation, {context.class_name}State\nfrom .client import {context.class_name}Env\n'
        (openenv_dir / "__init__.py").write_text(init_code, encoding="utf-8")
        files["openenv_adapter/__init__.py"] = init_code
        
        (openenv_dir / "server" / "__init__.py").write_text("", encoding="utf-8")
        files["openenv_adapter/server/__init__.py"] = ""
        
        return files
    
    async def _generate_docker(self, context: GenerationContext, output_dir: Path) -> Dict[str, str]:
        """Generate Docker configuration"""
        files = {}
        
        # docker-compose.yml
        docker_compose = f"""version: "3.8"

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: {context.name}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build: ./{context.name}_api
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/{context.name}
      SECRET_KEY: change-me-in-production
    ports:
      - "{context.api_port}:{context.api_port}"
    depends_on:
      db:
        condition: service_healthy

  ui:
    build: ./{context.name}_ui
    ports:
      - "{context.ui_port}:80"
    depends_on:
      - api

  openenv:
    build:
      context: .
      dockerfile: openenv_adapter/Dockerfile
    environment:
      API_BASE_URL: http://api:{context.api_port}
    ports:
      - "{context.openenv_port}:{context.openenv_port}"
    depends_on:
      - api

volumes:
  postgres_data:
"""
        (output_dir / "docker-compose.yml").write_text(docker_compose, encoding="utf-8")
        files["docker-compose.yml"] = docker_compose
        
        # API Dockerfile
        api_dockerfile = f"""FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE {context.api_port}
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{context.api_port}"]
"""
        api_dir = output_dir / f"{context.name}_api"
        api_dir.mkdir(exist_ok=True)
        (api_dir / "Dockerfile").write_text(api_dockerfile, encoding="utf-8")
        files[f"{context.name}_api/Dockerfile"] = api_dockerfile
        
        # UI Dockerfile
        ui_dockerfile = """FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
"""
        ui_dir = output_dir / f"{context.name}_ui"
        ui_dir.mkdir(exist_ok=True)
        (ui_dir / "Dockerfile").write_text(ui_dockerfile, encoding="utf-8")
        files[f"{context.name}_ui/Dockerfile"] = ui_dockerfile
        
        # OpenEnv Dockerfile
        openenv_dockerfile = f"""FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn requests pydantic
COPY openenv_adapter ./openenv_adapter
EXPOSE {context.openenv_port}
CMD ["uvicorn", "openenv_adapter.server.app:app", "--host", "0.0.0.0", "--port", "{context.openenv_port}"]
"""
        openenv_dir = output_dir / "openenv_adapter"
        openenv_dir.mkdir(exist_ok=True)
        (openenv_dir / "Dockerfile").write_text(openenv_dockerfile, encoding="utf-8")
        files["openenv_adapter/Dockerfile"] = openenv_dockerfile
        
        return files
    
    async def _generate_readme(self, context: GenerationContext, spec: Dict) -> str:
        """Generate README documentation"""
        system_prompt = "You are a technical writer. Generate a clear, professional README.md for a software project."
        
        user_prompt = f"""Generate README.md for {context.display_name}

Description: {context.description}
Entities: {json.dumps([e.get('name') for e in spec.get('entities', [])], indent=2)}
Features: {json.dumps(spec.get('features', []), indent=2)}

Include:
1. Project description
2. Quick start (docker-compose)
3. API endpoints
4. OpenEnv usage example
5. Project structure
6. Development setup"""
        
        return await self._call_llm(system_prompt, user_prompt)
    
    async def _generate_file(
        self,
        context: GenerationContext,
        filename: str,
        description: str,
        instructions: str,
    ) -> str:
        """Generate a single file using LLM"""
        system_prompt = f"""You are an expert programmer. Generate production-ready code.
Output ONLY the code, no explanations or markdown fences.

Project: {context.display_name}
File: {filename}
Description: {description}

Entities: {json.dumps([e.get('name') for e in context.entities], indent=2)}

Guidelines:
- Write clean, well-commented code
- Use type hints for Python, TypeScript types for TS
- Handle errors properly
- Follow best practices"""
        
        user_prompt = f"Generate {filename}:\n{instructions}"
        
        response = await self._call_llm(system_prompt, user_prompt)
        
        # Clean up response - remove markdown fences if present
        if response.startswith("```"):
            lines = response.split("\n")
            # Remove first and last lines (``` markers)
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)
        
        return response


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="LLM-powered environment generator")
    parser.add_argument("--name", required=True, help="Environment name")
    parser.add_argument("--domain", default="custom", help="Domain type")
    parser.add_argument("--description", default="", help="Environment description")
    parser.add_argument("--output", default="./generated", help="Output directory")
    parser.add_argument("--model", default="gpt-4-turbo-preview", help="OpenAI model")
    
    args = parser.parse_args()
    
    context = GenerationContext(
        name=args.name,
        description=args.description or f"A {args.domain} application",
        domain_type=args.domain,
    )
    
    generator = LLMCodeGenerator(model=args.model)
    output_dir = Path(args.output) / args.name
    
    files = await generator.generate(context, output_dir)
    
    print("\n" + "=" * 50)
    print(f"✓ Generated {len(files)} files")
    print(f"✓ Output: {output_dir}")
    print("\nNext steps:")
    print(f"  cd {output_dir}")
    print("  docker-compose up --build")


if __name__ == "__main__":
    asyncio.run(main())

