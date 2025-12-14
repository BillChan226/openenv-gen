"""
Shared Context for Environment Generation

This module defines the shared context that is passed between agents
during environment generation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class EntityField:
    """Database entity field definition"""
    name: str
    type: str
    nullable: bool = True
    default: Any = None
    primary_key: bool = False
    constraints: List[str] = field(default_factory=list)


@dataclass
class EntityRelationship:
    """Database entity relationship definition"""
    type: str  # "one-to-one", "one-to-many", "many-to-many"
    target: str
    foreign_key: Optional[str] = None
    back_populates: Optional[str] = None


@dataclass
class Entity:
    """Database entity definition"""
    name: str
    table_name: str
    description: str = ""
    fields: List[EntityField] = field(default_factory=list)
    relationships: List[EntityRelationship] = field(default_factory=list)
    indexes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class APIEndpoint:
    """API endpoint definition"""
    path: str
    method: str  # "GET", "POST", "PUT", "PATCH", "DELETE"
    operation_id: str
    summary: str
    request_schema: Optional[str] = None
    response_schema: Optional[str] = None
    auth_required: bool = True


@dataclass
class UIComponent:
    """UI component definition"""
    name: str
    type: str  # "page", "component", "layout"
    path: str
    props: List[Dict[str, Any]] = field(default_factory=list)
    api_dependencies: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)


@dataclass
class UIPage:
    """UI page definition"""
    name: str
    route: str
    description: str = ""
    components: List[str] = field(default_factory=list)
    api_dependencies: List[str] = field(default_factory=list)


@dataclass
class UserRole:
    """User role definition"""
    name: str
    permissions: List[str] = field(default_factory=list)


@dataclass
class Feature:
    """Environment feature definition"""
    name: str
    description: str
    user_stories: List[str] = field(default_factory=list)


@dataclass
class EnvGenerationContext:
    """
    Shared context for environment generation.
    
    This context is passed between agents and updated as the
    generation progresses through phases.
    """
    
    # Basic info
    name: str = ""
    display_name: str = ""
    class_name: str = ""
    description: str = ""
    domain_type: str = "custom"
    
    # Paths
    output_dir: Path = field(default_factory=lambda: Path("./generated_envs"))
    
    # Ports
    api_port: int = 8032
    ui_port: int = 8026
    openenv_port: int = 8000
    
    # Design artifacts
    entities: List[Entity] = field(default_factory=list)
    user_roles: List[UserRole] = field(default_factory=list)
    features: List[Feature] = field(default_factory=list)
    
    # API artifacts
    api_endpoints: List[APIEndpoint] = field(default_factory=list)
    
    # UI artifacts
    ui_pages: List[UIPage] = field(default_factory=list)
    ui_components: List[UIComponent] = field(default_factory=list)
    
    # Generation state
    phase: str = "init"  # init, design, backend, frontend, integration, complete
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize derived fields"""
        if self.name and not self.display_name:
            self.display_name = self.name.replace("_", " ").title()
        if self.name and not self.class_name:
            self.class_name = "".join(word.capitalize() for word in self.name.split("_"))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "class_name": self.class_name,
            "description": self.description,
            "domain_type": self.domain_type,
            "output_dir": str(self.output_dir),
            "api_port": self.api_port,
            "ui_port": self.ui_port,
            "openenv_port": self.openenv_port,
            "entities": [e.__dict__ for e in self.entities],
            "api_endpoints": [e.__dict__ for e in self.api_endpoints],
            "ui_pages": [p.__dict__ for p in self.ui_pages],
            "phase": self.phase,
            "errors": self.errors,
            "warnings": self.warnings,
        }
    
    def get_template_vars(self) -> Dict[str, Any]:
        """Get variables for template rendering"""
        return {
            "env_name": self.name,
            "env_display_name": self.display_name,
            "env_class_name": self.class_name,
            "description": self.description,
            "api_port": self.api_port,
            "ui_port": self.ui_port,
            "openenv_port": self.openenv_port,
            "entities": self.entities,
            "api_endpoints": self.api_endpoints,
            "ui_pages": self.ui_pages,
            "ui_components": self.ui_components,
        }


@dataclass
class GenerationResult:
    """Result of environment generation"""
    success: bool
    output_dir: str
    context: EnvGenerationContext
    generated_files: List[str] = field(default_factory=list)
    validation_report: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

