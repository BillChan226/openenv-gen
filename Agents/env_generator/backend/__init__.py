"""
Phase 2: Backend Generation Agents

Agents for generating FastAPI backend code.

Agents:
    - SchemaDesignerAgent: Generates SQLAlchemy models and Pydantic schemas
    - DatabaseBuilderAgent: Creates database connection and auth modules (TODO)
    - APIBuilderAgent: Generates FastAPI routers and business logic
"""

from .schema_designer import SchemaDesignerAgent
from .api_builder import APIBuilderAgent

# TODO: Implement
# from .database_builder import DatabaseBuilderAgent

__all__ = [
    "SchemaDesignerAgent",
    "APIBuilderAgent",
    # "DatabaseBuilderAgent",
]

