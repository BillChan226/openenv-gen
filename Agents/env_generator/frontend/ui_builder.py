"""
UIBuilder Agent - Generates React frontend

This agent generates the complete React frontend including:
- App component with routing
- Authentication context
- API service layer
- Entity list/detail/form pages
- Reusable UI components
"""

from pathlib import Path
from typing import Any, Dict, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import (
    PlanningAgent,
    AgentConfig,
    AgentRole,
    AgentCapability,
    TaskMessage,
    ResultMessage,
    create_result_message,
)

from ..context import EnvGenerationContext


class UIBuilderAgent(PlanningAgent):
    """
    Agent for generating React frontend.
    
    Generates:
    - App.tsx with routing
    - Authentication context
    - API service layer
    - Entity pages (List, Detail, Form)
    - Reusable components (Layout, Button, Table, etc.)
    - Styles (CSS)
    
    Usage:
        agent = UIBuilderAgent(config)
        await agent.initialize()
        
        files = await agent.generate_frontend(context, output_dir)
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config, role=AgentRole.SPECIALIST, enable_reasoning=True)
        
        self.add_capability(AgentCapability(
            name="frontend_generation",
            description="Generate React frontend code",
        ))
    
    async def on_initialize(self) -> None:
        """Initialize frontend builder"""
        await super().on_initialize()
        self._logger.info("UIBuilderAgent initialized")
    
    async def generate_frontend(
        self,
        context: EnvGenerationContext,
        output_dir: Path,
        entities: List[Dict] = None,
    ) -> Dict[str, str]:
        """
        Generate React frontend files.
        
        Args:
            context: Environment generation context
            output_dir: Output directory
            entities: Prepared entity data
            
        Returns:
            Dict mapping file paths to content
        """
        files = {}
        ui_dir = output_dir / f"{context.name}_ui"
        
        # Prepare entities
        if entities is None:
            entities = self._prepare_entities(context.entities)
        
        # Generate package.json
        files[f"{context.name}_ui/package.json"] = self._generate_package_json(context)
        
        # Generate vite.config.ts
        files[f"{context.name}_ui/vite.config.ts"] = self._generate_vite_config()
        
        # Generate tsconfig.json
        files[f"{context.name}_ui/tsconfig.json"] = self._generate_tsconfig()
        
        # Generate index.html
        files[f"{context.name}_ui/index.html"] = self._generate_index_html(context)
        
        # Generate src/main.tsx
        files[f"{context.name}_ui/src/main.tsx"] = self._generate_main_tsx()
        
        # Generate src/App.tsx
        files[f"{context.name}_ui/src/App.tsx"] = self._generate_app_tsx(context, entities)
        
        # Generate src/App.css
        files[f"{context.name}_ui/src/App.css"] = self._generate_app_css(context)
        
        # Generate contexts
        files[f"{context.name}_ui/src/contexts/AuthContext.tsx"] = self._generate_auth_context(context)
        
        # Generate services/api.ts
        files[f"{context.name}_ui/src/services/api.ts"] = self._generate_api_service(context, entities)
        
        # Generate components
        files[f"{context.name}_ui/src/components/Layout.tsx"] = self._generate_layout_component(context)
        files[f"{context.name}_ui/src/components/Layout.css"] = self._generate_layout_css()
        files[f"{context.name}_ui/src/components/Button.tsx"] = self._generate_button_component()
        files[f"{context.name}_ui/src/components/Table.tsx"] = self._generate_table_component()
        files[f"{context.name}_ui/src/components/Input.tsx"] = self._generate_input_component()
        files[f"{context.name}_ui/src/components/index.ts"] = self._generate_components_index()
        
        # Generate pages
        files[f"{context.name}_ui/src/pages/Login.tsx"] = self._generate_login_page(context)
        files[f"{context.name}_ui/src/pages/Login.css"] = self._generate_login_css()
        files[f"{context.name}_ui/src/pages/Register.tsx"] = self._generate_register_page(context)
        files[f"{context.name}_ui/src/pages/Dashboard.tsx"] = self._generate_dashboard_page(context, entities)
        files[f"{context.name}_ui/src/pages/Dashboard.css"] = self._generate_dashboard_css()
        
        # Generate entity pages
        for entity in entities:
            if entity["name"] != "User":
                name = entity["name"]
                files[f"{context.name}_ui/src/pages/{name}List.tsx"] = self._generate_entity_list_page(context, entity)
                files[f"{context.name}_ui/src/pages/{name}Detail.tsx"] = self._generate_entity_detail_page(context, entity)
                files[f"{context.name}_ui/src/pages/{name}Form.tsx"] = self._generate_entity_form_page(context, entity)
        
        # Generate Dockerfile
        files[f"{context.name}_ui/Dockerfile"] = self._generate_dockerfile(context)
        
        # Generate nginx.conf
        files[f"{context.name}_ui/nginx.conf"] = self._generate_nginx_conf()
        
        # Write files
        for path, content in files.items():
            file_path = output_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        
        return files
    
    def _prepare_entities(self, entities: List[Any]) -> List[Dict]:
        """Prepare entity data for code generation"""
        prepared = []
        
        for entity in entities:
            if hasattr(entity, "__dict__"):
                entity_dict = {
                    "name": entity.name,
                    "table_name": entity.table_name,
                    "description": getattr(entity, "description", ""),
                    "fields": [],
                }
                fields = entity.fields if hasattr(entity, "fields") else []
            else:
                entity_dict = dict(entity)
                fields = entity.get("fields", [])
            
            for field in fields:
                if hasattr(field, "__dict__"):
                    field_dict = field.__dict__.copy()
                else:
                    field_dict = dict(field)
                
                # Add TypeScript type
                sql_type = field_dict.get("type", "String")
                if "Integer" in sql_type or "Float" in sql_type or "Decimal" in sql_type:
                    field_dict["ts_type"] = "number"
                elif "Boolean" in sql_type:
                    field_dict["ts_type"] = "boolean"
                elif "DateTime" in sql_type or "Date" in sql_type:
                    field_dict["ts_type"] = "string"
                else:
                    field_dict["ts_type"] = "string"
                
                entity_dict["fields"].append(field_dict)
            
            # Get ID type
            id_field = next((f for f in entity_dict["fields"] if f.get("primary_key")), None)
            entity_dict["id_type"] = "string" if id_field and "String" in id_field.get("type", "") else "number"
            
            # Display fields (exclude system fields)
            entity_dict["display_fields"] = [
                f for f in entity_dict["fields"]
                if not f.get("primary_key")
                and f.get("name") not in ["hashed_password", "created_at", "updated_at", "user_id"]
            ][:5]
            
            # Form fields (editable)
            entity_dict["form_fields"] = [
                f for f in entity_dict["fields"]
                if not f.get("primary_key")
                and f.get("name") not in ["hashed_password", "created_at", "updated_at", "user_id"]
            ]
            
            prepared.append(entity_dict)
        
        return prepared
    
    def _generate_package_json(self, context: EnvGenerationContext) -> str:
        """Generate package.json"""
        return f'''{{
  "name": "{context.name}-ui",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0"
  }},
  "devDependencies": {{
    "@types/react": "^18.2.37",
    "@types/react-dom": "^18.2.15",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.2.2",
    "vite": "^5.0.0"
  }}
}}
'''
    
    def _generate_vite_config(self) -> str:
        """Generate vite.config.ts"""
        return '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
'''
    
    def _generate_tsconfig(self) -> str:
        """Generate tsconfig.json"""
        return '''{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
'''
    
    def _generate_index_html(self, context: EnvGenerationContext) -> str:
        """Generate index.html"""
        return f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{context.display_name}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
'''
    
    def _generate_main_tsx(self) -> str:
        """Generate main.tsx"""
        return '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './App.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
'''
    
    def _generate_app_tsx(self, context: EnvGenerationContext, entities: List[Dict]) -> str:
        """Generate App.tsx with routing"""
        # Generate imports for entity pages
        entity_imports = []
        entity_routes = []
        
        for entity in entities:
            if entity["name"] != "User":
                name = entity["name"]
                table = entity.get("table_name", name.lower() + "s")
                entity_imports.append(f"import {name}List from './pages/{name}List'")
                entity_imports.append(f"import {name}Detail from './pages/{name}Detail'")
                entity_imports.append(f"import {name}Form from './pages/{name}Form'")
                entity_routes.append(f'          <Route path="/{table}" element={{<ProtectedRoute><{name}List /></ProtectedRoute>}} />')
                entity_routes.append(f'          <Route path="/{table}/:id" element={{<ProtectedRoute><{name}Detail /></ProtectedRoute>}} />')
                entity_routes.append(f'          <Route path="/{table}/new" element={{<ProtectedRoute><{name}Form /></ProtectedRoute>}} />')
                entity_routes.append(f'          <Route path="/{table}/:id/edit" element={{<ProtectedRoute><{name}Form /></ProtectedRoute>}} />')
        
        return f'''/**
 * {context.display_name} - Main App Component
 */

import {{ BrowserRouter, Routes, Route, Navigate }} from 'react-router-dom';
import {{ AuthProvider, useAuth }} from './contexts/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
{chr(10).join(entity_imports)}

function ProtectedRoute({{ children }}: {{ children: React.ReactNode }}) {{
  const {{ isAuthenticated, loading }} = useAuth();
  
  if (loading) {{
    return <div className="loading">Loading...</div>;
  }}
  
  if (!isAuthenticated) {{
    return <Navigate to="/login" replace />;
  }}
  
  return <>{{children}}</>;
}}

function App() {{
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={{<Login />}} />
          <Route path="/register" element={{<Register />}} />
          <Route path="/" element={{<ProtectedRoute><Dashboard /></ProtectedRoute>}} />
{chr(10).join(entity_routes)}
          <Route path="*" element={{<Navigate to="/" replace />}} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}}

export default App;
'''
    
    def _generate_app_css(self, context: EnvGenerationContext) -> str:
        """Generate App.css"""
        return '''/* Global Styles */
:root {
  --primary-color: #3b82f6;
  --primary-hover: #2563eb;
  --secondary-color: #64748b;
  --success-color: #22c55e;
  --danger-color: #ef4444;
  --warning-color: #f59e0b;
  --background-color: #f8fafc;
  --surface-color: #ffffff;
  --text-color: #1e293b;
  --text-secondary: #64748b;
  --border-color: #e2e8f0;
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  --radius: 8px;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
    Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  background-color: var(--background-color);
  color: var(--text-color);
  line-height: 1.5;
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  font-size: 1.25rem;
  color: var(--text-secondary);
}

.error-message {
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  padding: 0.75rem 1rem;
  border-radius: var(--radius);
  margin-bottom: 1rem;
}

.success-message {
  background-color: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #16a34a;
  padding: 0.75rem 1rem;
  border-radius: var(--radius);
  margin-bottom: 1rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: var(--text-secondary);
}

.empty-state p {
  margin-bottom: 1rem;
}

a {
  color: var(--primary-color);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}
'''
    
    def _generate_auth_context(self, context: EnvGenerationContext) -> str:
        """Generate AuthContext.tsx"""
        return f'''/**
 * Authentication Context
 */

import {{ createContext, useContext, useState, useEffect, ReactNode }} from 'react';
import {{ api }} from '../services/api';

interface User {{
  id: number;
  email: string;
  full_name?: string;
}}

interface AuthContextType {{
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({{ children }}: {{ children: ReactNode }}) {{
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {{
    const token = localStorage.getItem('token');
    if (token) {{
      fetchCurrentUser();
    }} else {{
      setLoading(false);
    }}
  }}, []);

  const fetchCurrentUser = async () => {{
    try {{
      const response = await api.get('/auth/me');
      setUser(response.data);
    }} catch (error) {{
      localStorage.removeItem('token');
    }} finally {{
      setLoading(false);
    }}
  }};

  const login = async (email: string, password: string) => {{
    const response = await api.post('/auth/login', {{ email, password }});
    const {{ access_token }} = response.data;
    localStorage.setItem('token', access_token);
    api.defaults.headers.common['Authorization'] = `Bearer ${{access_token}}`;
    await fetchCurrentUser();
  }};

  const register = async (email: string, password: string, fullName?: string) => {{
    await api.post('/auth/register', {{
      email,
      password,
      full_name: fullName,
    }});
    await login(email, password);
  }};

  const logout = () => {{
    localStorage.removeItem('token');
    delete api.defaults.headers.common['Authorization'];
    setUser(null);
  }};

  return (
    <AuthContext.Provider
      value={{{{
        user,
        isAuthenticated: !!user,
        loading,
        login,
        register,
        logout,
      }}}}
    >
      {{children}}
    </AuthContext.Provider>
  );
}}

export function useAuth() {{
  const context = useContext(AuthContext);
  if (context === undefined) {{
    throw new Error('useAuth must be used within an AuthProvider');
  }}
  return context;
}}
'''
    
    def _generate_api_service(self, context: EnvGenerationContext, entities: List[Dict]) -> str:
        """Generate API service"""
        # Generate entity APIs and types
        entity_apis = []
        entity_types = []
        
        for entity in entities:
            name = entity["name"]
            table = entity.get("table_name", name.lower() + "s")
            id_type = entity.get("id_type", "number")
            
            if name != "User":
                entity_apis.append(f'''
// {name} API
export const {name.lower()}Api = {{
  list: () => fetchItems<{name}>('{table}'),
  get: (id: {id_type}) => fetchItem<{name}>('{table}', id),
  create: (data: Partial<{name}>) => createItem<{name}>('{table}', data),
  update: (id: {id_type}, data: Partial<{name}>) => updateItem<{name}>('{table}', id, data),
  delete: (id: {id_type}) => deleteItem('{table}', id),
}};''')
            
            # Generate interface
            fields = []
            for field in entity.get("fields", []):
                ts_type = field.get("ts_type", "string")
                nullable = "?" if field.get("nullable") else ""
                fields.append(f"  {field['name']}{nullable}: {ts_type};")
            
            entity_types.append(f'''
export interface {name} {{
{chr(10).join(fields)}
}}''')
        
        return f'''/**
 * API Service
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:{context.api_port}/api/v1';

export const api = axios.create({{
  baseURL: API_BASE_URL,
  headers: {{
    'Content-Type': 'application/json',
  }},
}});

// Request interceptor
api.interceptors.request.use(
  (config) => {{
    const token = localStorage.getItem('token');
    if (token) {{
      config.headers.Authorization = `Bearer ${{token}}`;
    }}
    return config;
  }},
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {{
    if (error.response?.status === 401) {{
      localStorage.removeItem('token');
      window.location.href = '/login';
    }}
    return Promise.reject(error);
  }}
);

// Generic CRUD functions
async function fetchItems<T>(resource: string): Promise<T[]> {{
  const response = await api.get(`/${{resource}}`);
  return response.data;
}}

async function fetchItem<T>(resource: string, id: string | number): Promise<T> {{
  const response = await api.get(`/${{resource}}/${{id}}`);
  return response.data;
}}

async function createItem<T>(resource: string, data: Partial<T>): Promise<T> {{
  const response = await api.post(`/${{resource}}`, data);
  return response.data;
}}

async function updateItem<T>(resource: string, id: string | number, data: Partial<T>): Promise<T> {{
  const response = await api.put(`/${{resource}}/${{id}}`, data);
  return response.data;
}}

async function deleteItem(resource: string, id: string | number): Promise<void> {{
  await api.delete(`/${{resource}}/${{id}}`);
}}
{chr(10).join(entity_apis)}

// Types
{chr(10).join(entity_types)}
'''
    
    def _generate_layout_component(self, context: EnvGenerationContext) -> str:
        """Generate Layout component"""
        return f'''/**
 * Layout Component
 */

import {{ ReactNode }} from 'react';
import {{ Link, useNavigate }} from 'react-router-dom';
import {{ useAuth }} from '../contexts/AuthContext';
import './Layout.css';

interface LayoutProps {{
  children: ReactNode;
}}

export default function Layout({{ children }}: LayoutProps) {{
  const {{ user, logout }} = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {{
    logout();
    navigate('/login');
  }};

  return (
    <div className="layout">
      <header className="header">
        <div className="header-left">
          <Link to="/" className="logo">{context.display_name}</Link>
        </div>
        <div className="header-right">
          <span className="user-email">{{user?.email}}</span>
          <button onClick={{handleLogout}} className="logout-btn">Logout</button>
        </div>
      </header>
      <div className="layout-body">
        <aside className="sidebar">
          <nav>
            <ul>
              <li><Link to="/">Dashboard</Link></li>
            </ul>
          </nav>
        </aside>
        <main className="main-content">
          {{children}}
        </main>
      </div>
    </div>
  );
}}
'''
    
    def _generate_layout_css(self) -> str:
        """Generate Layout CSS"""
        return '''.layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.5rem;
  background-color: var(--surface-color);
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow);
}

.header-left .logo {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--primary-color);
  text-decoration: none;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-email {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.logout-btn {
  padding: 0.5rem 1rem;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 0.875rem;
}

.logout-btn:hover {
  background-color: var(--background-color);
}

.layout-body {
  display: flex;
  flex: 1;
}

.sidebar {
  width: 240px;
  background-color: var(--surface-color);
  border-right: 1px solid var(--border-color);
  padding: 1rem 0;
}

.sidebar nav ul {
  list-style: none;
}

.sidebar nav li a {
  display: block;
  padding: 0.75rem 1.5rem;
  color: var(--text-color);
  text-decoration: none;
}

.sidebar nav li a:hover {
  background-color: var(--background-color);
  color: var(--primary-color);
}

.main-content {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
}
'''
    
    def _generate_button_component(self) -> str:
        """Generate Button component"""
        return '''/**
 * Button Component
 */

import { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  children: ReactNode;
}

export default function Button({
  variant = 'primary',
  size = 'md',
  children,
  className = '',
  ...props
}: ButtonProps) {
  const baseStyles = `
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 500;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    transition: all 0.2s;
  `;
  
  const variants = {
    primary: 'background-color: var(--primary-color); color: white;',
    secondary: 'background-color: var(--surface-color); color: var(--text-color); border: 1px solid var(--border-color);',
    danger: 'background-color: var(--danger-color); color: white;',
  };
  
  const sizes = {
    sm: 'padding: 0.375rem 0.75rem; font-size: 0.875rem;',
    md: 'padding: 0.5rem 1rem; font-size: 1rem;',
    lg: 'padding: 0.75rem 1.5rem; font-size: 1.125rem;',
  };

  return (
    <button
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 500,
        borderRadius: '6px',
        cursor: 'pointer',
        transition: 'all 0.2s',
        padding: size === 'sm' ? '0.375rem 0.75rem' : size === 'lg' ? '0.75rem 1.5rem' : '0.5rem 1rem',
        fontSize: size === 'sm' ? '0.875rem' : size === 'lg' ? '1.125rem' : '1rem',
        backgroundColor: variant === 'primary' ? 'var(--primary-color)' : variant === 'danger' ? 'var(--danger-color)' : 'var(--surface-color)',
        color: variant === 'secondary' ? 'var(--text-color)' : 'white',
        border: variant === 'secondary' ? '1px solid var(--border-color)' : 'none',
      }}
      {...props}
    >
      {children}
    </button>
  );
}
'''
    
    def _generate_table_component(self) -> str:
        """Generate Table component"""
        return '''/**
 * Table Component
 */

import { ReactNode } from 'react';

interface Column {
  key: string;
  label: string;
}

interface TableProps {
  columns: Column[];
  children: ReactNode;
}

export default function Table({ columns, children }: TableProps) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{
        width: '100%',
        borderCollapse: 'collapse',
        backgroundColor: 'var(--surface-color)',
        borderRadius: 'var(--radius)',
        overflow: 'hidden',
        boxShadow: 'var(--shadow)',
      }}>
        <thead>
          <tr style={{ backgroundColor: 'var(--background-color)' }}>
            {columns.map((col) => (
              <th
                key={col.key}
                style={{
                  padding: '0.75rem 1rem',
                  textAlign: 'left',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  color: 'var(--text-secondary)',
                  borderBottom: '1px solid var(--border-color)',
                }}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function TableRow({ children }: { children: ReactNode }) {
  return (
    <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
      {children}
    </tr>
  );
}

export function TableCell({ children }: { children: ReactNode }) {
  return (
    <td style={{ padding: '0.75rem 1rem' }}>
      {children}
    </td>
  );
}
'''
    
    def _generate_input_component(self) -> str:
        """Generate Input component"""
        return '''/**
 * Input Component
 */

import { InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export default function Input({ label, error, ...props }: InputProps) {
  return (
    <div style={{ marginBottom: '1rem' }}>
      {label && (
        <label style={{
          display: 'block',
          marginBottom: '0.5rem',
          fontWeight: 500,
          fontSize: '0.875rem',
        }}>
          {label}
        </label>
      )}
      <input
        style={{
          width: '100%',
          padding: '0.5rem 0.75rem',
          border: `1px solid ${error ? 'var(--danger-color)' : 'var(--border-color)'}`,
          borderRadius: 'var(--radius)',
          fontSize: '1rem',
          outline: 'none',
        }}
        {...props}
      />
      {error && (
        <p style={{
          marginTop: '0.25rem',
          fontSize: '0.875rem',
          color: 'var(--danger-color)',
        }}>
          {error}
        </p>
      )}
    </div>
  );
}
'''
    
    def _generate_components_index(self) -> str:
        """Generate components index.ts"""
        return '''export { default as Layout } from './Layout';
export { default as Button } from './Button';
export { default as Table, TableRow, TableCell } from './Table';
export { default as Input } from './Input';
'''
    
    def _generate_login_page(self, context: EnvGenerationContext) -> str:
        """Generate Login page"""
        return f'''/**
 * Login Page
 */

import {{ useState }} from 'react';
import {{ Link, useNavigate }} from 'react-router-dom';
import {{ useAuth }} from '../contexts/AuthContext';
import Input from '../components/Input';
import Button from '../components/Button';
import './Login.css';

export default function Login() {{
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const {{ login }} = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {{
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {{
      await login(email, password);
      navigate('/');
    }} catch (err: any) {{
      setError(err.response?.data?.detail || 'Login failed');
    }} finally {{
      setLoading(false);
    }}
  }};

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>{context.display_name}</h1>
        <h2>Sign In</h2>
        
        {{error && <div className="error-message">{{error}}</div>}}
        
        <form onSubmit={{handleSubmit}}>
          <Input
            label="Email"
            type="email"
            value={{email}}
            onChange={{(e) => setEmail(e.target.value)}}
            required
          />
          <Input
            label="Password"
            type="password"
            value={{password}}
            onChange={{(e) => setPassword(e.target.value)}}
            required
          />
          <Button type="submit" disabled={{loading}} style={{{{ width: '100%' }}}}>
            {{loading ? 'Signing in...' : 'Sign In'}}
          </Button>
        </form>
        
        <p className="login-footer">
          Don't have an account? <Link to="/register">Sign up</Link>
        </p>
      </div>
    </div>
  );
}}
'''
    
    def _generate_login_css(self) -> str:
        """Generate Login CSS"""
        return '''.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  background: var(--surface-color);
  padding: 2rem;
  border-radius: var(--radius);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 400px;
}

.login-card h1 {
  text-align: center;
  margin-bottom: 0.5rem;
  color: var(--primary-color);
}

.login-card h2 {
  text-align: center;
  margin-bottom: 1.5rem;
  font-weight: 400;
  color: var(--text-secondary);
}

.login-footer {
  text-align: center;
  margin-top: 1.5rem;
  color: var(--text-secondary);
}
'''
    
    def _generate_register_page(self, context: EnvGenerationContext) -> str:
        """Generate Register page"""
        return f'''/**
 * Register Page
 */

import {{ useState }} from 'react';
import {{ Link, useNavigate }} from 'react-router-dom';
import {{ useAuth }} from '../contexts/AuthContext';
import Input from '../components/Input';
import Button from '../components/Button';
import './Login.css';

export default function Register() {{
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const {{ register }} = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {{
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {{
      await register(email, password, fullName);
      navigate('/');
    }} catch (err: any) {{
      setError(err.response?.data?.detail || 'Registration failed');
    }} finally {{
      setLoading(false);
    }}
  }};

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>{context.display_name}</h1>
        <h2>Create Account</h2>
        
        {{error && <div className="error-message">{{error}}</div>}}
        
        <form onSubmit={{handleSubmit}}>
          <Input
            label="Full Name"
            type="text"
            value={{fullName}}
            onChange={{(e) => setFullName(e.target.value)}}
          />
          <Input
            label="Email"
            type="email"
            value={{email}}
            onChange={{(e) => setEmail(e.target.value)}}
            required
          />
          <Input
            label="Password"
            type="password"
            value={{password}}
            onChange={{(e) => setPassword(e.target.value)}}
            required
            minLength={{8}}
          />
          <Button type="submit" disabled={{loading}} style={{{{ width: '100%' }}}}>
            {{loading ? 'Creating account...' : 'Sign Up'}}
          </Button>
        </form>
        
        <p className="login-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}}
'''
    
    def _generate_dashboard_page(self, context: EnvGenerationContext, entities: List[Dict]) -> str:
        """Generate Dashboard page"""
        # Generate entity links
        entity_cards = []
        for entity in entities:
            if entity["name"] != "User":
                name = entity["name"]
                table = entity.get("table_name", name.lower() + "s")
                entity_cards.append(f'''
          <Link to="/{table}" className="dashboard-card">
            <h3>{name}s</h3>
            <p>Manage {name.lower()}s</p>
          </Link>''')
        
        return f'''/**
 * Dashboard Page
 */

import {{ Link }} from 'react-router-dom';
import Layout from '../components/Layout';
import {{ useAuth }} from '../contexts/AuthContext';
import './Dashboard.css';

export default function Dashboard() {{
  const {{ user }} = useAuth();

  return (
    <Layout>
      <div className="dashboard">
        <h1>Welcome, {{user?.full_name || user?.email}}</h1>
        
        <div className="dashboard-grid">
{chr(10).join(entity_cards)}
        </div>
      </div>
    </Layout>
  );
}}
'''
    
    def _generate_dashboard_css(self) -> str:
        """Generate Dashboard CSS"""
        return '''.dashboard h1 {
  margin-bottom: 1.5rem;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.dashboard-card {
  display: block;
  padding: 1.5rem;
  background-color: var(--surface-color);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  text-decoration: none;
  transition: transform 0.2s, box-shadow 0.2s;
}

.dashboard-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  text-decoration: none;
}

.dashboard-card h3 {
  color: var(--text-color);
  margin-bottom: 0.5rem;
}

.dashboard-card p {
  color: var(--text-secondary);
  font-size: 0.875rem;
}
'''
    
    def _generate_entity_list_page(self, context: EnvGenerationContext, entity: Dict) -> str:
        """Generate entity list page"""
        name = entity["name"]
        name_lower = name.lower()
        table = entity.get("table_name", name_lower + "s")
        id_type = entity.get("id_type", "number")
        
        # Generate columns
        columns = ["{ key: 'id', label: 'ID' }"]
        for field in entity.get("display_fields", [])[:4]:
            label = field.get("name", "").replace("_", " ").title()
            columns.append(f"{{ key: '{field['name']}', label: '{label}' }}")
        columns.append("{ key: 'actions', label: 'Actions' }")
        
        # Generate row cells
        row_cells = ["<td style={{ padding: '0.75rem 1rem' }}>{item.id}</td>"]
        for field in entity.get("display_fields", [])[:4]:
            row_cells.append(f"<td style={{{{{{ padding: '0.75rem 1rem' }}}}}}>{{{{item.{field['name']}}}}}</td>")
        
        return f'''/**
 * {name} List Page
 */

import {{ useState, useEffect }} from 'react';
import {{ Link, useNavigate }} from 'react-router-dom';
import Layout from '../components/Layout';
import Button from '../components/Button';
import Table from '../components/Table';
import {{ {name_lower}Api, {name} }} from '../services/api';

export default function {name}List() {{
  const [items, setItems] = useState<{name}[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {{
    loadItems();
  }}, []);

  const loadItems = async () => {{
    try {{
      setLoading(true);
      const data = await {name_lower}Api.list();
      setItems(data);
      setError(null);
    }} catch (err) {{
      setError('Failed to load {name_lower}s');
      console.error(err);
    }} finally {{
      setLoading(false);
    }}
  }};

  const handleDelete = async (id: {id_type}) => {{
    if (!confirm('Are you sure you want to delete this {name_lower}?')) {{
      return;
    }}
    
    try {{
      await {name_lower}Api.delete(id);
      await loadItems();
    }} catch (err) {{
      setError('Failed to delete {name_lower}');
      console.error(err);
    }}
  }};

  const columns = [
    {', '.join(columns)}
  ];

  if (loading) {{
    return (
      <Layout>
        <div className="loading">Loading...</div>
      </Layout>
    );
  }}

  return (
    <Layout>
      <div>
        <header className="page-header">
          <h1>{name}s</h1>
          <Link to="/{table}/new">
            <Button variant="primary">Add {name}</Button>
          </Link>
        </header>

        {{error && <div className="error-message">{{error}}</div>}}

        {{items.length === 0 ? (
          <div className="empty-state">
            <p>No {name_lower}s found.</p>
            <Link to="/{table}/new">
              <Button variant="primary">Create your first {name_lower}</Button>
            </Link>
          </div>
        ) : (
          <Table columns={{columns}}>
            {{items.map((item) => (
              <tr key={{item.id}} style={{{{ borderBottom: '1px solid var(--border-color)' }}}}>
                {chr(10).join(f'                {cell}' for cell in row_cells)}
                <td style={{{{ padding: '0.75rem 1rem' }}}}>
                  <div style={{{{ display: 'flex', gap: '0.5rem' }}}}>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={{() => navigate(`/{table}/${{item.id}}`)}}
                    >
                      View
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={{() => navigate(`/{table}/${{item.id}}/edit`)}}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={{() => handleDelete(item.id)}}
                    >
                      Delete
                    </Button>
                  </div>
                </td>
              </tr>
            ))}}
          </Table>
        )}}
      </div>
    </Layout>
  );
}}
'''
    
    def _generate_entity_detail_page(self, context: EnvGenerationContext, entity: Dict) -> str:
        """Generate entity detail page"""
        name = entity["name"]
        name_lower = name.lower()
        table = entity.get("table_name", name_lower + "s")
        
        # Generate detail rows
        detail_rows = []
        for field in entity.get("fields", []):
            if field.get("name") not in ["hashed_password"]:
                label = field.get("name", "").replace("_", " ").title()
                detail_rows.append(f'''
            <tr>
              <td style={{{{ fontWeight: 500, padding: '0.5rem 0' }}}}>{label}</td>
              <td style={{{{ padding: '0.5rem 0' }}}}>{{item.{field['name']}}}</td>
            </tr>''')
        
        return f'''/**
 * {name} Detail Page
 */

import {{ useState, useEffect }} from 'react';
import {{ useParams, useNavigate, Link }} from 'react-router-dom';
import Layout from '../components/Layout';
import Button from '../components/Button';
import {{ {name_lower}Api, {name} }} from '../services/api';

export default function {name}Detail() {{
  const {{ id }} = useParams<{{ id: string }}>();
  const [item, setItem] = useState<{name} | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {{
    if (id) {{
      loadItem(id);
    }}
  }}, [id]);

  const loadItem = async (itemId: string) => {{
    try {{
      setLoading(true);
      const data = await {name_lower}Api.get(itemId);
      setItem(data);
      setError(null);
    }} catch (err) {{
      setError('{name} not found');
      console.error(err);
    }} finally {{
      setLoading(false);
    }}
  }};

  const handleDelete = async () => {{
    if (!confirm('Are you sure you want to delete this {name_lower}?')) {{
      return;
    }}
    
    try {{
      await {name_lower}Api.delete(id!);
      navigate('/{table}');
    }} catch (err) {{
      setError('Failed to delete {name_lower}');
      console.error(err);
    }}
  }};

  if (loading) {{
    return (
      <Layout>
        <div className="loading">Loading...</div>
      </Layout>
    );
  }}

  if (error || !item) {{
    return (
      <Layout>
        <div className="error-message">{{error || '{name} not found'}}</div>
        <Link to="/{table}">Back to list</Link>
      </Layout>
    );
  }}

  return (
    <Layout>
      <div>
        <header className="page-header">
          <h1>{name} Details</h1>
          <div style={{{{ display: 'flex', gap: '0.5rem' }}}}>
            <Button variant="secondary" onClick={{() => navigate(`/{table}/${{id}}/edit`)}}>
              Edit
            </Button>
            <Button variant="danger" onClick={{handleDelete}}>
              Delete
            </Button>
          </div>
        </header>

        <div style={{{{
          backgroundColor: 'var(--surface-color)',
          padding: '1.5rem',
          borderRadius: 'var(--radius)',
          boxShadow: 'var(--shadow)',
        }}}}>
          <table style={{{{ width: '100%' }}}}>
            <tbody>
              {chr(10).join(detail_rows)}
            </tbody>
          </table>
        </div>

        <div style={{{{ marginTop: '1rem' }}}}>
          <Link to="/{table}">← Back to list</Link>
        </div>
      </div>
    </Layout>
  );
}}
'''
    
    def _generate_entity_form_page(self, context: EnvGenerationContext, entity: Dict) -> str:
        """Generate entity form page"""
        name = entity["name"]
        name_lower = name.lower()
        table = entity.get("table_name", name_lower + "s")
        
        # Generate form fields
        form_fields = entity.get("form_fields", [])
        state_init = []
        input_fields = []
        
        for field in form_fields:
            field_name = field.get("name", "")
            label = field_name.replace("_", " ").title()
            field_type = "text"
            
            if "email" in field_name.lower():
                field_type = "email"
            elif "password" in field_name.lower():
                field_type = "password"
            elif field.get("ts_type") == "number":
                field_type = "number"
            elif "date" in field_name.lower():
                field_type = "datetime-local"
            
            state_init.append(f"{field_name}: ''")
            input_fields.append(f'''
          <Input
            label="{label}"
            type="{field_type}"
            name="{field_name}"
            value={{formData.{field_name}}}
            onChange={{handleChange}}
            {"required" if not field.get("nullable") else ""}
          />''')
        
        return f'''/**
 * {name} Form Page
 */

import {{ useState, useEffect }} from 'react';
import {{ useParams, useNavigate, Link }} from 'react-router-dom';
import Layout from '../components/Layout';
import Input from '../components/Input';
import Button from '../components/Button';
import {{ {name_lower}Api }} from '../services/api';

export default function {name}Form() {{
  const {{ id }} = useParams<{{ id: string }}>();
  const isEdit = !!id;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({{
    {', '.join(state_init)}
  }});
  const navigate = useNavigate();

  useEffect(() => {{
    if (isEdit && id) {{
      loadItem(id);
    }}
  }}, [id, isEdit]);

  const loadItem = async (itemId: string) => {{
    try {{
      const data = await {name_lower}Api.get(itemId);
      setFormData(data as any);
    }} catch (err) {{
      setError('Failed to load {name_lower}');
      console.error(err);
    }}
  }};

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {{
    const {{ name, value }} = e.target;
    setFormData((prev) => ({{ ...prev, [name]: value }}));
  }};

  const handleSubmit = async (e: React.FormEvent) => {{
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {{
      if (isEdit) {{
        await {name_lower}Api.update(id!, formData);
      }} else {{
        await {name_lower}Api.create(formData);
      }}
      navigate('/{table}');
    }} catch (err: any) {{
      setError(err.response?.data?.detail || 'Failed to save {name_lower}');
    }} finally {{
      setLoading(false);
    }}
  }};

  return (
    <Layout>
      <div>
        <header className="page-header">
          <h1>{{isEdit ? 'Edit' : 'Create'}} {name}</h1>
        </header>

        {{error && <div className="error-message">{{error}}</div>}}

        <div style={{{{
          backgroundColor: 'var(--surface-color)',
          padding: '1.5rem',
          borderRadius: 'var(--radius)',
          boxShadow: 'var(--shadow)',
          maxWidth: '600px',
        }}}}>
          <form onSubmit={{handleSubmit}}>
{chr(10).join(input_fields)}

            <div style={{{{ display: 'flex', gap: '0.5rem', marginTop: '1.5rem' }}}}>
              <Button type="submit" disabled={{loading}}>
                {{loading ? 'Saving...' : (isEdit ? 'Update' : 'Create')}}
              </Button>
              <Button type="button" variant="secondary" onClick={{() => navigate('/{table}')}}>
                Cancel
              </Button>
            </div>
          </form>
        </div>

        <div style={{{{ marginTop: '1rem' }}}}>
          <Link to="/{table}">← Back to list</Link>
        </div>
      </div>
    </Layout>
  );
}}
'''
    
    def _generate_dockerfile(self, context: EnvGenerationContext) -> str:
        """Generate Dockerfile for frontend"""
        return f'''# {context.display_name} UI Dockerfile

# Build stage
FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
'''
    
    def _generate_nginx_conf(self) -> str:
        """Generate nginx.conf"""
        return '''server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
'''
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """Process frontend generation task"""
        params = task.task_params
        context = params.get("context")
        output_dir = Path(params.get("output_dir", "./generated"))
        entities = params.get("entities")
        
        if not context:
            return create_result_message(
                source_id=self.agent_id,
                target_id=task.header.source_agent_id,
                task_id=task.task_id,
                success=False,
                error_message="Context required",
            )
        
        files = await self.generate_frontend(context, output_dir, entities)
        
        return create_result_message(
            source_id=self.agent_id,
            target_id=task.header.source_agent_id,
            task_id=task.task_id,
            success=True,
            result_data={"files": list(files.keys())},
        )

