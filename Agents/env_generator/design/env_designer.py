"""
EnvDesigner Agent - Designs environment specification from user input

This agent analyzes user requirements (description, reference data, or domain type)
and generates a comprehensive environment specification.
"""

import json
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

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
    BaseTool,
    ToolDefinition,
    ToolParameter,
    ToolResult,
    ToolCategory,
    LLM,
)

from ..context import (
    EnvGenerationContext,
    Entity,
    EntityField,
    EntityRelationship,
    APIEndpoint,
    UIPage,
    UIComponent,
    UserRole,
    Feature,
)


# Domain templates for common environment types
DOMAIN_TEMPLATES = {
    "calendar": {
        "entities": ["User", "Calendar", "Event", "Attendee", "Reminder"],
        "features": ["Authentication", "Calendar CRUD", "Event CRUD", "Invitations", "Recurring Events"],
        "user_roles": ["owner", "editor", "viewer"],
    },
    "ecommerce": {
        "entities": ["User", "Product", "Category", "Order", "OrderItem", "Cart", "Review"],
        "features": ["Authentication", "Product Catalog", "Shopping Cart", "Checkout", "Order History"],
        "user_roles": ["admin", "customer", "guest"],
    },
    "social": {
        "entities": ["User", "Profile", "Post", "Comment", "Like", "Follow", "Message"],
        "features": ["Authentication", "Profile Management", "Posts", "Comments", "Messaging"],
        "user_roles": ["admin", "user"],
    },
    "inventory": {
        "entities": ["User", "Product", "Category", "Warehouse", "Stock", "Transaction"],
        "features": ["Authentication", "Product Management", "Stock Tracking", "Reports"],
        "user_roles": ["admin", "manager", "staff"],
    },
}


class EnvDesignerAgent(PlanningAgent):
    """
    Agent for designing environment specifications.
    
    Analyzes user requirements and generates:
    - Entity definitions (database models)
    - Feature list
    - User roles and permissions
    - Initial API endpoint design
    - UI page structure
    
    Usage:
        agent = EnvDesignerAgent(config)
        await agent.initialize()
        
        spec = await agent.design_environment(
            name="calendar",
            description="A calendar app...",
            domain_type="calendar",
        )
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config, role=AgentRole.SPECIALIST, enable_reasoning=True)
        
        self.add_capability(AgentCapability(
            name="environment_design",
            description="Design environment specifications from requirements",
        ))
    
    async def on_initialize(self) -> None:
        """Initialize design tools"""
        await super().on_initialize()
        
        # Register design tools
        self.register_tool(AnalyzeRequirementsTool())
        self.register_tool(InferEntitiesFromDataTool())
        self.register_tool(GenerateSpecificationTool())
        
        # Customize planner for design tasks
        self.planner.system_prompt = """You are an expert software architect specializing in designing web applications.

When designing an environment:
1. Analyze the requirements thoroughly
2. Identify core entities and their relationships
3. Define user roles and permissions
4. Plan API endpoints following REST conventions
5. Design UI pages and components

Always consider:
- Scalability and maintainability
- Security best practices
- User experience
- Data integrity constraints
"""
        
        self._logger.info("EnvDesignerAgent initialized")
    
    async def design_environment(
        self,
        name: str,
        description: str = None,
        reference_data: Dict[str, Any] = None,
        domain_type: str = "custom",
        constraints: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Design environment specification.
        
        Args:
            name: Environment name
            description: Natural language description
            reference_data: Sample data for inference
            domain_type: Domain type for templates
            constraints: Additional constraints
            
        Returns:
            Environment specification dict
        """
        spec = {
            "name": name,
            "display_name": name.replace("_", " ").title(),
            "description": description or f"A {domain_type} environment",
            "domain": domain_type,
            "entities": [],
            "features": [],
            "user_roles": [],
            "api_endpoints": [],
            "ui_pages": [],
        }
        
        # Use domain template if available
        if domain_type in DOMAIN_TEMPLATES:
            template = DOMAIN_TEMPLATES[domain_type]
            spec["entities"] = self._expand_template_entities(template["entities"], domain_type)
            spec["features"] = self._create_features(template["features"])
            spec["user_roles"] = self._create_user_roles(template["user_roles"])
        
        # Infer from reference data if provided
        if reference_data:
            inferred = await self._infer_from_data(reference_data)
            spec["entities"].extend(inferred.get("entities", []))
        
        # Use LLM to enhance specification if description provided
        if description and self._reasoner:
            enhanced = await self._enhance_with_llm(spec, description, constraints)
            spec.update(enhanced)
        
        # Generate API endpoints from entities
        spec["api_endpoints"] = self._generate_api_endpoints(spec["entities"])
        
        # Generate UI pages
        spec["ui_pages"] = self._generate_ui_pages(spec["entities"], spec["features"])
        
        return spec
    
    def _expand_template_entities(self, entity_names: List[str], domain: str) -> List[Dict]:
        """Expand entity names into full definitions"""
        entities = []
        
        entity_templates = {
            "User": {
                "fields": [
                    {"name": "id", "type": "Integer", "primary_key": True},
                    {"name": "email", "type": "String(255)", "unique": True},
                    {"name": "hashed_password", "type": "String(255)"},
                    {"name": "full_name", "type": "String(255)", "nullable": True},
                    {"name": "created_at", "type": "DateTime", "default": "now"},
                    {"name": "is_active", "type": "Boolean", "default": True},
                ],
            },
            "Calendar": {
                "fields": [
                    {"name": "id", "type": "String(36)", "primary_key": True},
                    {"name": "user_id", "type": "Integer", "foreign_key": "users.id"},
                    {"name": "summary", "type": "String(255)"},
                    {"name": "description", "type": "Text", "nullable": True},
                    {"name": "time_zone", "type": "String(50)", "default": "UTC"},
                    {"name": "primary", "type": "Boolean", "default": False},
                ],
            },
            "Event": {
                "fields": [
                    {"name": "id", "type": "String(36)", "primary_key": True},
                    {"name": "calendar_id", "type": "String(36)", "foreign_key": "calendars.id"},
                    {"name": "summary", "type": "String(255)"},
                    {"name": "description", "type": "Text", "nullable": True},
                    {"name": "location", "type": "String(255)", "nullable": True},
                    {"name": "start_datetime", "type": "DateTime"},
                    {"name": "end_datetime", "type": "DateTime"},
                    {"name": "status", "type": "String(20)", "default": "confirmed"},
                    {"name": "created_at", "type": "DateTime", "default": "now"},
                ],
            },
            "Product": {
                "fields": [
                    {"name": "id", "type": "Integer", "primary_key": True},
                    {"name": "name", "type": "String(255)"},
                    {"name": "description", "type": "Text", "nullable": True},
                    {"name": "price", "type": "Decimal(10,2)"},
                    {"name": "stock", "type": "Integer", "default": 0},
                    {"name": "category_id", "type": "Integer", "foreign_key": "categories.id", "nullable": True},
                    {"name": "created_at", "type": "DateTime", "default": "now"},
                ],
            },
            "Order": {
                "fields": [
                    {"name": "id", "type": "Integer", "primary_key": True},
                    {"name": "user_id", "type": "Integer", "foreign_key": "users.id"},
                    {"name": "status", "type": "String(20)", "default": "pending"},
                    {"name": "total_amount", "type": "Decimal(10,2)"},
                    {"name": "created_at", "type": "DateTime", "default": "now"},
                ],
            },
        }
        
        for name in entity_names:
            template = entity_templates.get(name, {
                "fields": [
                    {"name": "id", "type": "Integer", "primary_key": True},
                    {"name": "name", "type": "String(255)"},
                    {"name": "created_at", "type": "DateTime", "default": "now"},
                ],
            })
            
            entities.append({
                "name": name,
                "table_name": name.lower() + "s",
                "description": f"{name} entity for {domain}",
                **template,
            })
        
        return entities
    
    def _create_features(self, feature_names: List[str]) -> List[Dict]:
        """Create feature definitions"""
        return [
            {"name": name, "description": f"{name} functionality"}
            for name in feature_names
        ]
    
    def _create_user_roles(self, role_names: List[str]) -> List[Dict]:
        """Create user role definitions"""
        permissions_map = {
            "admin": ["create", "read", "update", "delete", "manage_users"],
            "owner": ["create", "read", "update", "delete", "share"],
            "editor": ["create", "read", "update"],
            "viewer": ["read"],
            "manager": ["create", "read", "update", "delete", "view_reports"],
            "staff": ["read", "update"],
            "customer": ["read", "create_order", "view_own"],
            "user": ["create", "read", "update_own", "delete_own"],
            "guest": ["read"],
        }
        
        return [
            {
                "name": name,
                "permissions": permissions_map.get(name, ["read"]),
            }
            for name in role_names
        ]
    
    async def _infer_from_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Infer entities from reference data"""
        entities = []
        
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0:
                sample = value[0]
                if isinstance(sample, dict):
                    fields = []
                    for field_name, field_value in sample.items():
                        field_type = self._infer_field_type(field_value)
                        fields.append({
                            "name": field_name,
                            "type": field_type,
                            "primary_key": field_name == "id",
                        })
                    
                    entities.append({
                        "name": key.title().rstrip("s"),
                        "table_name": key.lower(),
                        "description": f"Inferred from data",
                        "fields": fields,
                    })
        
        return {"entities": entities}
    
    def _infer_field_type(self, value: Any) -> str:
        """Infer SQL type from Python value"""
        if isinstance(value, bool):
            return "Boolean"
        elif isinstance(value, int):
            return "Integer"
        elif isinstance(value, float):
            return "Float"
        elif isinstance(value, str):
            if len(value) > 255:
                return "Text"
            return "String(255)"
        else:
            return "JSON"
    
    async def _enhance_with_llm(
        self,
        spec: Dict,
        description: str,
        constraints: List[str],
    ) -> Dict[str, Any]:
        """Use LLM to enhance specification"""
        if not self._reasoner:
            return {}
        
        prompt = f"""
Enhance this environment specification based on the description.

Current spec:
{json.dumps(spec, indent=2)}

Description:
{description}

Constraints:
{constraints or 'None'}

Suggest additional entities, features, or modifications.
Output as JSON with keys: additional_entities, additional_features, modifications
"""
        
        result = await self._reasoner.run(prompt)
        
        if result.success:
            try:
                # Try to parse JSON from response
                enhanced = json.loads(result.answer)
                return enhanced
            except json.JSONDecodeError:
                pass
        
        return {}
    
    def _generate_api_endpoints(self, entities: List[Dict]) -> List[Dict]:
        """Generate REST API endpoints from entities"""
        endpoints = []
        
        for entity in entities:
            name = entity["name"]
            name_lower = name.lower()
            name_plural = name_lower + "s"
            
            # Standard CRUD endpoints
            endpoints.extend([
                {
                    "path": f"/{name_plural}",
                    "method": "GET",
                    "operation_id": f"list_{name_plural}",
                    "summary": f"List all {name_plural}",
                    "auth_required": True,
                },
                {
                    "path": f"/{name_plural}",
                    "method": "POST",
                    "operation_id": f"create_{name_lower}",
                    "summary": f"Create a new {name_lower}",
                    "auth_required": True,
                },
                {
                    "path": f"/{name_plural}/{{{name_lower}_id}}",
                    "method": "GET",
                    "operation_id": f"get_{name_lower}",
                    "summary": f"Get a {name_lower} by ID",
                    "auth_required": True,
                },
                {
                    "path": f"/{name_plural}/{{{name_lower}_id}}",
                    "method": "PUT",
                    "operation_id": f"update_{name_lower}",
                    "summary": f"Update a {name_lower}",
                    "auth_required": True,
                },
                {
                    "path": f"/{name_plural}/{{{name_lower}_id}}",
                    "method": "DELETE",
                    "operation_id": f"delete_{name_lower}",
                    "summary": f"Delete a {name_lower}",
                    "auth_required": True,
                },
            ])
        
        # Add auth endpoints
        endpoints.extend([
            {
                "path": "/auth/register",
                "method": "POST",
                "operation_id": "register",
                "summary": "Register a new user",
                "auth_required": False,
            },
            {
                "path": "/auth/login",
                "method": "POST",
                "operation_id": "login",
                "summary": "Login user",
                "auth_required": False,
            },
            {
                "path": "/auth/me",
                "method": "GET",
                "operation_id": "get_current_user",
                "summary": "Get current user info",
                "auth_required": True,
            },
        ])
        
        return endpoints
    
    def _generate_ui_pages(self, entities: List[Dict], features: List[Dict]) -> List[Dict]:
        """Generate UI page structure"""
        pages = [
            {
                "name": "Login",
                "route": "/login",
                "description": "User login page",
                "components": ["LoginForm"],
            },
            {
                "name": "Register",
                "route": "/register",
                "description": "User registration page",
                "components": ["RegisterForm"],
            },
            {
                "name": "Dashboard",
                "route": "/",
                "description": "Main dashboard",
                "components": ["Header", "Sidebar", "MainContent"],
            },
        ]
        
        # Add pages for each entity
        for entity in entities:
            name = entity["name"]
            name_lower = name.lower()
            
            if name == "User":
                continue  # Skip user entity
            
            pages.extend([
                {
                    "name": f"{name}List",
                    "route": f"/{name_lower}s",
                    "description": f"List of {name_lower}s",
                    "components": [f"{name}Table", "Pagination", "SearchBar"],
                },
                {
                    "name": f"{name}Detail",
                    "route": f"/{name_lower}s/:id",
                    "description": f"{name} detail view",
                    "components": [f"{name}View", f"{name}Actions"],
                },
                {
                    "name": f"{name}Form",
                    "route": f"/{name_lower}s/new",
                    "description": f"Create/edit {name_lower}",
                    "components": [f"{name}Form"],
                },
            ])
        
        return pages
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """Process design task"""
        params = task.task_params
        
        spec = await self.design_environment(
            name=params.get("name", "environment"),
            description=params.get("description"),
            reference_data=params.get("reference_data"),
            domain_type=params.get("domain_type", "custom"),
            constraints=params.get("constraints"),
        )
        
        return create_result_message(
            source_id=self.agent_id,
            target_id=task.header.source_agent_id,
            task_id=task.task_id,
            success=True,
            result_data=spec,
        )


# =============================================================================
# Design Tools
# =============================================================================

class AnalyzeRequirementsTool(BaseTool):
    """Tool to analyze requirements from description"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="analyze_requirements",
            description="Analyze requirements from natural language description",
            category=ToolCategory.DATA,
            parameters=[
                ToolParameter(
                    name="description",
                    param_type=str,
                    description="Natural language description",
                    required=True,
                ),
            ],
            returns="Extracted requirements",
        )
    
    async def execute(self, description: str, **kwargs) -> ToolResult:
        # Extract key concepts from description
        keywords = {
            "auth": ["login", "register", "authentication", "user", "password"],
            "crud": ["create", "read", "update", "delete", "manage"],
            "calendar": ["event", "calendar", "schedule", "appointment"],
            "ecommerce": ["product", "order", "cart", "payment", "checkout"],
        }
        
        found_features = []
        description_lower = description.lower()
        
        for feature, words in keywords.items():
            if any(word in description_lower for word in words):
                found_features.append(feature)
        
        return ToolResult.ok({
            "features": found_features,
            "description": description,
        })


class InferEntitiesFromDataTool(BaseTool):
    """Tool to infer entities from sample data"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="infer_entities",
            description="Infer database entities from sample data",
            category=ToolCategory.DATA,
            parameters=[
                ToolParameter(
                    name="data",
                    param_type=dict,
                    description="Sample data as JSON",
                    required=True,
                ),
            ],
            returns="Inferred entity definitions",
        )
    
    async def execute(self, data: dict, **kwargs) -> ToolResult:
        entities = []
        
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                entities.append({
                    "name": key.title().rstrip("s"),
                    "sample_fields": list(value[0].keys()),
                })
        
        return ToolResult.ok({"entities": entities})


class GenerateSpecificationTool(BaseTool):
    """Tool to generate specification YAML"""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="generate_specification",
            description="Generate environment specification YAML",
            category=ToolCategory.DATA,
            parameters=[
                ToolParameter(
                    name="spec",
                    param_type=dict,
                    description="Specification dictionary",
                    required=True,
                ),
            ],
            returns="YAML formatted specification",
        )
    
    async def execute(self, spec: dict, **kwargs) -> ToolResult:
        yaml_output = yaml.dump(spec, default_flow_style=False, sort_keys=False)
        return ToolResult.ok(yaml_output)

