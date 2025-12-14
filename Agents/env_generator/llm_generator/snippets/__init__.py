"""
Code Snippet Library

Pre-defined, high-quality code patterns that:
1. Speed up generation by providing templates
2. Improve consistency across generated code
3. Encode best practices
4. Reduce LLM hallucination errors

Snippets are NOT used as-is, but included in prompts as examples
for the LLM to follow and adapt.
"""

from .backend import BACKEND_SNIPPETS
from .frontend import FRONTEND_SNIPPETS
from .openenv import OPENENV_SNIPPETS

# All snippets organized by category
SNIPPET_LIBRARY = {
    "backend": BACKEND_SNIPPETS,
    "frontend": FRONTEND_SNIPPETS,
    "openenv": OPENENV_SNIPPETS,
}


def get_snippet(category: str, name: str) -> str:
    """Get a specific snippet by category and name"""
    if category in SNIPPET_LIBRARY and name in SNIPPET_LIBRARY[category]:
        return SNIPPET_LIBRARY[category][name]
    return ""


def get_relevant_snippets(file_path: str, purpose: str = "") -> list:
    """
    Get snippets relevant to a file being generated.
    
    Analyzes the file path and purpose to determine which snippets
    would be helpful as examples.
    """
    snippets = []
    path_lower = file_path.lower()
    purpose_lower = purpose.lower()
    
    # Backend snippets
    if "_api/" in path_lower or "backend" in purpose_lower:
        if "models" in path_lower:
            snippets.append(("SQLAlchemy Model", BACKEND_SNIPPETS.get("sqlalchemy_model", "")))
        if "schemas" in path_lower:
            snippets.append(("Pydantic Schema", BACKEND_SNIPPETS.get("pydantic_schema", "")))
        if "auth" in path_lower:
            snippets.append(("JWT Auth", BACKEND_SNIPPETS.get("jwt_auth", "")))
        if "router" in path_lower or "endpoint" in purpose_lower:
            snippets.append(("CRUD Router", BACKEND_SNIPPETS.get("crud_router", "")))
        if "database" in path_lower:
            snippets.append(("Database Config", BACKEND_SNIPPETS.get("database_config", "")))
        if "main" in path_lower:
            snippets.append(("FastAPI Main", BACKEND_SNIPPETS.get("fastapi_main", "")))
    
    # Frontend snippets
    if "_ui/" in path_lower or "frontend" in purpose_lower:
        if "context" in path_lower or "auth" in path_lower:
            snippets.append(("Auth Context", FRONTEND_SNIPPETS.get("auth_context", "")))
        if "login" in path_lower or "register" in path_lower:
            snippets.append(("Auth Form", FRONTEND_SNIPPETS.get("auth_form", "")))
        if "list" in path_lower or "table" in path_lower:
            snippets.append(("Data List", FRONTEND_SNIPPETS.get("data_list", "")))
        if "form" in path_lower or "create" in path_lower or "edit" in path_lower:
            snippets.append(("Entity Form", FRONTEND_SNIPPETS.get("entity_form", "")))
        if "api" in path_lower and ".ts" in path_lower:
            snippets.append(("API Client", FRONTEND_SNIPPETS.get("api_client", "")))
    
    # OpenEnv snippets
    if "openenv" in path_lower or "environment" in path_lower:
        if "environment" in path_lower:
            snippets.append(("OpenEnv Environment", OPENENV_SNIPPETS.get("environment_class", "")))
        if "models" in path_lower:
            snippets.append(("OpenEnv Models", OPENENV_SNIPPETS.get("openenv_models", "")))
    
    return snippets


def format_snippets_for_prompt(snippets: list) -> str:
    """Format snippets for inclusion in LLM prompt"""
    if not snippets:
        return ""
    
    formatted = "\n\n=== CODE EXAMPLES (Follow these patterns) ===\n"
    
    for name, code in snippets:
        if code:
            formatted += f"\n--- {name} ---\n```\n{code}\n```\n"
    
    return formatted

