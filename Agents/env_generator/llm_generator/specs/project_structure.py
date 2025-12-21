"""
Project Structure - Standard structure for generated environments

This defines the canonical structure that User Agent enforces.
"""

from typing import Dict, List, Any
from utils.message import TaskType

# Standard project structure
PROJECT_STRUCTURE = {
    "design": {
        "path": "design/",
        "description": "Design documents and specifications",
        "files": [
            "spec.json",          # Project specification
            "api_contracts.md",   # API definitions
            "components.md",      # Component inventory
        ],
    },
    
    "frontend": {
        "path": "app/frontend/",
        "description": "React frontend application",
        "structure": {
            "public/": "Static assets",
            "src/": {
                "components/": {
                    "ui/": "Basic UI components (Button, Input, Card, Modal)",
                    "features/": "Business components (specific to this app)",
                },
                "layouts/": "Page layouts (MainLayout, Header, Sidebar)",
                "pages/": "Route pages",
                "hooks/": "Custom React hooks",
                "services/": "API client functions",
                "stores/": "State management",
                "styles/": "Global styles and theme",
                "utils/": "Utility functions",
            },
        },
        "root_files": [
            "package.json",
            "vite.config.js",
            "Dockerfile",
            "src/App.jsx",
            "src/main.jsx",
        ],
    },
    
    "backend": {
        "path": "app/backend/",
        "description": "Express.js backend API",
        "structure": {
            "src/": {
                "config/": "Configuration (env, database, auth)",
                "controllers/": "Request handlers",
                "middleware/": "Express middleware",
                "models/": "Database models (Sequelize)",
                "routes/": "Route definitions",
                "services/": "Business logic",
                "utils/": "Utility functions",
            },
        },
        "root_files": [
            "package.json",
            "Dockerfile",
            "src/app.js",
            "src/server.js",
        ],
    },
    
    "database": {
        "path": "app/database/",
        "description": "PostgreSQL database",
        "files": [
            "init/01_schema.sql",   # Table definitions
            "init/02_seed.sql",     # Initial data
            "Dockerfile",
        ],
    },
    
    "env": {
        "path": "env/",
        "description": "OpenEnv adapter",
        "files": [
            "models.py",           # WebAction, WebObservation
            "client.py",           # WebEnvClient
            "openenv.yaml",        # Configuration
            "server/environment.py",
            "server/app.py",
            "server/Dockerfile",
        ],
    },
    
    "docker": {
        "path": "docker/",
        "description": "Docker configuration",
        "files": [
            "docker-compose.yml",
            "docker-compose.dev.yml",
        ],
    },
    
    "config": {
        "path": "",
        "description": "Root configuration",
        "files": [
            "config.yaml",
        ],
    },
}


# Phase definitions - what to generate in each phase
PHASES = [
    {
        "id": "design",
        "type": TaskType.DESIGN,
        "name": "Design",
        "description": "Generate design documents and project specification",
        "target_directory": "design/",
        "depends_on": [],
    },
    {
        "id": "database",
        "type": TaskType.DATABASE,
        "name": "Database",
        "description": "Generate database schema and seed data",
        "target_directory": "app/database/",
        "depends_on": ["design"],
    },
    {
        "id": "backend",
        "type": TaskType.BACKEND,
        "name": "Backend",
        "description": "Generate Express.js backend API",
        "target_directory": "app/backend/",
        "depends_on": ["design", "database"],
    },
    {
        "id": "frontend",
        "type": TaskType.FRONTEND,
        "name": "Frontend",
        "description": """Generate React frontend application with COMPLETE, FUNCTIONAL UI.

REQUIREMENTS:
- All components must be fully functional (no placeholder onClick handlers)
- All pages must display REAL data from the backend API
- Navigation must work between all pages
- Forms must submit data to the backend
- Search must work end-to-end
- Settings must be viewable and savable
- Loading states must show while fetching data
- Error states must show when API fails
- Design must be polished and user-friendly""",
        "target_directory": "app/frontend/",
        "depends_on": ["design", "backend"],
    },
    {
        "id": "integration",
        "type": TaskType.VERIFICATION,
        "name": "Integration",
        "description": """Verify frontend-backend integration is complete.

This phase tests:
1. All frontend pages load with real data from backend
2. No console errors in browser
3. No network errors (failed API calls)
4. All interactive elements work (buttons, forms, links)
5. CRUD operations work end-to-end
6. User can complete all core workflows

Use browser tools to navigate, click, fill forms, and verify results.""",
        "target_directory": "",
        "depends_on": ["backend", "frontend"],
    },
    {
        "id": "env",
        "type": TaskType.ENV,
        "name": "OpenEnv",
        "description": "Generate OpenEnv adapter for agent interaction",
        "target_directory": "env/",
        "depends_on": ["integration"],
    },
    {
        "id": "docker",
        "type": TaskType.DOCKER,
        "name": "Docker",
        "description": "Generate Docker configuration",
        "target_directory": "docker/",
        "depends_on": ["backend", "frontend", "database"],
    },
]


def get_allowed_paths(phase_id: str) -> List[str]:
    """
    Get allowed file paths for a phase.
    
    Args:
        phase_id: Phase identifier (design, backend, frontend, etc.)
    
    Returns:
        List of allowed path prefixes
    """
    spec = PROJECT_STRUCTURE.get(phase_id, {})
    base_path = spec.get("path", "")
    
    if not base_path:
        return spec.get("files", [])
    
    # Collect all allowed paths
    allowed = []
    
    # Root files
    for f in spec.get("root_files", []):
        allowed.append(f"{base_path}{f}")
    
    # Direct files
    for f in spec.get("files", []):
        allowed.append(f"{base_path}{f}")
    
    # Structured directories
    structure = spec.get("structure", {})
    def collect_paths(struct: Dict, prefix: str):
        for key, value in struct.items():
            if isinstance(value, dict):
                collect_paths(value, f"{prefix}{key}")
            else:
                allowed.append(f"{prefix}{key}")
    
    collect_paths(structure, base_path)
    
    return allowed


def get_phase_spec(phase_id: str) -> Dict[str, Any]:
    """
    Get full specification for a phase.
    
    Args:
        phase_id: Phase identifier
    
    Returns:
        Phase specification dict
    """
    for phase in PHASES:
        if phase["id"] == phase_id:
            return {
                **phase,
                "structure": PROJECT_STRUCTURE.get(phase_id, {}),
                "allowed_paths": get_allowed_paths(phase_id),
            }
    return {}


def validate_path(path: str, phase_id: str) -> bool:
    """
    Check if a path is allowed for a phase.
    
    Args:
        path: File path to validate
        phase_id: Current phase
    
    Returns:
        True if path is allowed
    """
    spec = PROJECT_STRUCTURE.get(phase_id, {})
    base_path = spec.get("path", "")
    
    # Must be under the phase's base path
    if base_path and not path.startswith(base_path):
        return False
    
    return True


def format_structure_for_prompt() -> str:
    """
    Format project structure for inclusion in prompts.
    
    Returns:
        Formatted string describing the structure
    """
    lines = ["## Project Structure\n"]
    
    for key, spec in PROJECT_STRUCTURE.items():
        path = spec.get("path", "(root)")
        desc = spec.get("description", "")
        lines.append(f"### {path}")
        lines.append(f"{desc}\n")
        
        # Show structure if available
        structure = spec.get("structure", {})
        if structure:
            def format_struct(s: Dict, indent: int = 0):
                result = []
                for k, v in s.items():
                    prefix = "  " * indent
                    if isinstance(v, dict):
                        result.append(f"{prefix}- {k}")
                        result.extend(format_struct(v, indent + 1))
                    else:
                        result.append(f"{prefix}- {k}  # {v}")
                return result
            
            lines.extend(format_struct(structure))
        
        # Show files if available
        for f in spec.get("files", []):
            lines.append(f"  - {f}")
        for f in spec.get("root_files", []):
            lines.append(f"  - {f}")
        
        lines.append("")
    
    return "\n".join(lines)

