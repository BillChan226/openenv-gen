"""
SchemaDesigner Agent - Designs database schema

This agent transforms the environment specification into concrete
database models, schemas, and migrations.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from jinja2 import Environment, FileSystemLoader

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

from ..context import EnvGenerationContext, Entity, EntityField


# Type mapping: SQLAlchemy type -> Python type -> TypeScript type
TYPE_MAPPINGS = {
    "Integer": {"python": "int", "ts": "number"},
    "String": {"python": "str", "ts": "string"},
    "Text": {"python": "str", "ts": "string"},
    "Boolean": {"python": "bool", "ts": "boolean"},
    "Float": {"python": "float", "ts": "number"},
    "Decimal": {"python": "float", "ts": "number"},
    "DateTime": {"python": "datetime", "ts": "string"},
    "Date": {"python": "date", "ts": "string"},
    "JSON": {"python": "dict", "ts": "Record<string, any>"},
}


class SchemaDesignerAgent(PlanningAgent):
    """
    Agent for designing database schema.
    
    Takes environment specification and generates:
    - SQLAlchemy models
    - Pydantic schemas
    - Database initialization scripts
    
    Usage:
        agent = SchemaDesignerAgent(config)
        await agent.initialize()
        
        files = await agent.generate_schema(context, output_dir)
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config, role=AgentRole.SPECIALIST, enable_reasoning=True)
        
        self.add_capability(AgentCapability(
            name="schema_design",
            description="Design database schemas from specifications",
        ))
        
        # Initialize Jinja2 environment
        template_dir = Path(__file__).parent.parent / "templates" / "backend"
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    
    async def on_initialize(self) -> None:
        """Initialize schema design tools"""
        await super().on_initialize()
        self._logger.info("SchemaDesignerAgent initialized")
    
    async def generate_schema(
        self,
        context: EnvGenerationContext,
        output_dir: Path,
    ) -> Dict[str, str]:
        """
        Generate database schema files.
        
        Args:
            context: Environment generation context
            output_dir: Output directory
            
        Returns:
            Dict mapping file paths to content
        """
        files = {}
        api_dir = output_dir / f"{context.name}_api"
        api_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare entity data with type mappings
        entities = self._prepare_entities(context.entities)
        
        # Generate models.py
        models_content = self._generate_models(context, entities)
        files[f"{context.name}_api/models.py"] = models_content
        
        # Generate schemas.py
        schemas_content = self._generate_schemas(context, entities)
        files[f"{context.name}_api/schemas.py"] = schemas_content
        
        # Generate database.py
        database_content = self._generate_database(context)
        files[f"{context.name}_api/database.py"] = database_content
        
        # Generate requirements.txt
        requirements_content = self._generate_requirements()
        files[f"{context.name}_api/requirements.txt"] = requirements_content
        
        # Write files
        for path, content in files.items():
            file_path = output_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        
        return files
    
    def _prepare_entities(self, entities: List[Any]) -> List[Dict]:
        """Prepare entity data with type mappings"""
        prepared = []
        
        for entity in entities:
            # Handle both Entity objects and dicts
            if hasattr(entity, "__dict__"):
                entity_dict = {
                    "name": entity.name,
                    "table_name": entity.table_name,
                    "description": entity.description,
                    "fields": [],
                    "relationships": getattr(entity, "relationships", []),
                }
                fields = entity.fields
            else:
                entity_dict = dict(entity)
                entity_dict["relationships"] = entity_dict.get("relationships", [])
                fields = entity.get("fields", [])
            
            # Process fields
            for field in fields:
                if hasattr(field, "__dict__"):
                    field_dict = field.__dict__.copy()
                else:
                    field_dict = dict(field)
                
                # Extract base type for mapping
                sql_type = field_dict.get("type", "String")
                base_type = sql_type.split("(")[0]
                
                # Add Python and TypeScript types
                type_info = TYPE_MAPPINGS.get(base_type, {"python": "str", "ts": "string"})
                field_dict["python_type"] = type_info["python"]
                field_dict["ts_type"] = type_info["ts"]
                
                # Handle nullable types
                if field_dict.get("nullable"):
                    field_dict["python_type"] = f"Optional[{field_dict['python_type']}]"
                    field_dict["ts_type"] = f"{field_dict['ts_type']} | null"
                
                entity_dict["fields"].append(field_dict)
            
            # Check for common patterns
            entity_dict["has_timestamps"] = any(
                f.get("name") in ["created_at", "updated_at"]
                for f in entity_dict["fields"]
            )
            entity_dict["has_user_id"] = any(
                f.get("name") == "user_id"
                for f in entity_dict["fields"]
            )
            
            # Determine ID type
            id_field = next(
                (f for f in entity_dict["fields"] if f.get("primary_key")),
                None
            )
            if id_field:
                entity_dict["id_type"] = id_field.get("python_type", "int")
            
            # Add display fields (for UI)
            entity_dict["display_fields"] = [
                f for f in entity_dict["fields"]
                if not f.get("primary_key")
                and f.get("name") not in ["hashed_password", "created_at", "updated_at"]
            ][:5]  # Limit to 5 fields
            
            prepared.append(entity_dict)
        
        return prepared
    
    def _generate_models(self, context: EnvGenerationContext, entities: List[Dict]) -> str:
        """Generate SQLAlchemy models"""
        try:
            template = self._jinja_env.get_template("models.py.j2")
            return template.render(
                env_name=context.name,
                display_name=context.display_name,
                entities=entities,
            )
        except Exception:
            # Fallback: generate inline
            return self._generate_models_inline(context, entities)
    
    def _generate_models_inline(self, context: EnvGenerationContext, entities: List[Dict]) -> str:
        """Generate models without template"""
        lines = [
            '"""',
            f'SQLAlchemy Models for {context.display_name}',
            '"""',
            '',
            'from datetime import datetime',
            'from typing import Optional',
            'from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float',
            'from sqlalchemy.orm import relationship',
            'from .database import Base',
            '',
        ]
        
        for entity in entities:
            lines.append(f'class {entity["name"]}(Base):')
            lines.append(f'    """{ entity.get("description", entity["name"] + " model")}"""')
            lines.append(f'    __tablename__ = "{entity["table_name"]}"')
            lines.append('')
            
            for field in entity["fields"]:
                col_parts = [field["type"]]
                if field.get("primary_key"):
                    col_parts.append("primary_key=True")
                if field.get("foreign_key"):
                    col_parts.append(f'ForeignKey("{field["foreign_key"]}")')
                if field.get("unique"):
                    col_parts.append("unique=True")
                if field.get("nullable"):
                    col_parts.append("nullable=True")
                if field.get("default") == "now":
                    col_parts.append("default=datetime.utcnow")
                elif field.get("default") is not None:
                    col_parts.append(f'default={field["default"]}')
                
                lines.append(f'    {field["name"]} = Column({", ".join(col_parts)})')
            
            lines.append('')
            lines.append('')
        
        return '\n'.join(lines)
    
    def _generate_schemas(self, context: EnvGenerationContext, entities: List[Dict]) -> str:
        """Generate Pydantic schemas"""
        try:
            template = self._jinja_env.get_template("schemas.py.j2")
            return template.render(
                env_name=context.name,
                display_name=context.display_name,
                entities=entities,
            )
        except Exception:
            # Fallback: generate inline
            return self._generate_schemas_inline(context, entities)
    
    def _generate_schemas_inline(self, context: EnvGenerationContext, entities: List[Dict]) -> str:
        """Generate schemas without template"""
        lines = [
            '"""',
            f'Pydantic Schemas for {context.display_name}',
            '"""',
            '',
            'from datetime import datetime',
            'from typing import Optional, List',
            'from pydantic import BaseModel, EmailStr, Field',
            '',
        ]
        
        for entity in entities:
            name = entity["name"]
            
            # Base schema
            lines.append(f'class {name}Base(BaseModel):')
            for field in entity["fields"]:
                if not field.get("primary_key") and field["name"] not in ["created_at", "updated_at", "hashed_password"]:
                    type_str = field.get("python_type", "str")
                    if field.get("nullable"):
                        lines.append(f'    {field["name"]}: {type_str} = None')
                    else:
                        lines.append(f'    {field["name"]}: {type_str}')
            lines.append('')
            
            # Create schema
            lines.append(f'class {name}Create({name}Base):')
            if name == "User":
                lines.append('    password: str = Field(..., min_length=8)')
            lines.append('    pass')
            lines.append('')
            
            # Response schema
            lines.append(f'class {name}Response({name}Base):')
            id_field = next((f for f in entity["fields"] if f.get("primary_key")), None)
            if id_field:
                lines.append(f'    {id_field["name"]}: {id_field.get("python_type", "int")}')
            lines.append('    class Config:')
            lines.append('        from_attributes = True')
            lines.append('')
            lines.append('')
        
        # Auth schemas
        lines.extend([
            'class Token(BaseModel):',
            '    access_token: str',
            '    token_type: str = "bearer"',
            '',
            'class LoginRequest(BaseModel):',
            '    email: EmailStr',
            '    password: str',
            '',
        ])
        
        return '\n'.join(lines)
    
    def _generate_database(self, context: EnvGenerationContext) -> str:
        """Generate database configuration"""
        return f'''"""
Database configuration for {context.display_name}
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./{context.name}.db"
)

engine = create_engine(
    DATABASE_URL,
    connect_args={{"check_same_thread": False}} if "sqlite" in DATABASE_URL else {{}},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''
    
    def _generate_requirements(self) -> str:
        """Generate requirements.txt"""
        return '''# Backend API dependencies
fastapi>=0.104.0
uvicorn>=0.24.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
python-dotenv>=1.0.0
psycopg2-binary>=2.9.0
'''
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """Process schema design task"""
        params = task.task_params
        context = params.get("context")
        output_dir = Path(params.get("output_dir", "./generated"))
        
        if not context:
            return create_result_message(
                source_id=self.agent_id,
                target_id=task.header.source_agent_id,
                task_id=task.task_id,
                success=False,
                error_message="Context required",
            )
        
        files = await self.generate_schema(context, output_dir)
        
        return create_result_message(
            source_id=self.agent_id,
            target_id=task.header.source_agent_id,
            task_id=task.task_id,
            success=True,
            result_data={"files": list(files.keys())},
        )

