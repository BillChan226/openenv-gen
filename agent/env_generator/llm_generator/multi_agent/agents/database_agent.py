"""
Database Agent - PostgreSQL database code generation

Uses j2 templates from: prompts/database_agent.j2
"""

from typing import Dict, List

from .base import EnvGenAgent


class DatabaseAgent(EnvGenAgent):
    """Database agent - generates SQL schema and seed data."""
    
    agent_id = "database"
    agent_name = "DatabaseAgent"
    allowed_tool_categories = ["file", "reasoning", "database", "communication"]
    
    def _get_system_prompt(self) -> str:
        """Use j2 template for system prompt."""
        workspace_dir = str(self.workspace.base_dir) if self.workspace else "."
        
        prompt = self.render_macro("database_agent.j2", "database_system_prompt", workspace_dir=workspace_dir)
        if prompt:
            return prompt
        
        # Fallback
        return """You are DatabaseAgent, a PostgreSQL database developer.
Generate SQL files in app/database/init/. Read design/spec.database.json first.
Use tools. Call finish() when done."""
    
    def _build_task_prompt(self, task: Dict) -> str:
        """Use j2 template for task prompt."""
        description = task.get("description", "")
        
        # If specific task description, use it
        if description:
            return f"""## Task

{description}

## Instructions

1. Use view() to examine relevant files
2. Use think() to analyze what needs to be done
3. Make changes with write_file() or str_replace_editor()
4. Call finish() when done

Start now."""
        
        # Default generation task - use j2 template
        db_port = getattr(self.gen_context, 'db_port', 5432) if self.gen_context else 5432
        test_credentials = "admin@example.com (admin123), user@example.com (password123)"
        
        prompt = self.render_macro(
            "database_agent.j2", 
            "database_task_prompt",
            db_port=db_port,
            test_credentials=test_credentials
        )
        
        if prompt:
            return prompt
        
        # Fallback
        return f"""Generate PostgreSQL database setup.

1. view("design/spec.database.json") first
2. Create app/database/init/01_schema.sql
3. Create app/database/init/02_seed.sql with test users: {test_credentials}
4. Create app/database/Dockerfile

Call finish() when done."""

