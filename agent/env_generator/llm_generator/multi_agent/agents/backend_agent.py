"""
Backend Agent - Express.js API code generation

Uses j2 templates from: prompts/backend_agent.j2
"""

from typing import Dict, List

from .base import EnvGenAgent


class BackendAgent(EnvGenAgent):
    """Backend agent - generates Express.js API code."""
    
    agent_id = "backend"
    agent_name = "BackendAgent"
    allowed_tool_categories = ["file", "reasoning", "runtime", "docker", "communication"]
    
    def _get_system_prompt(self) -> str:
        """Use j2 template for system prompt."""
        workspace_dir = str(self.workspace.base_dir) if self.workspace else "."
        
        prompt = self.render_macro("backend_agent.j2", "backend_system_prompt", workspace_dir=workspace_dir)
        if prompt:
            return prompt
        
        # Fallback
        return """You are BackendAgent, an Express.js backend developer.
Generate API code in app/backend/. Read design/spec.api.json first.
All list responses must use {items: [...], total: N} format.
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
4. Use lint() to verify syntax
5. Call finish() when done

Start now."""
        
        # Default generation task - use j2 template
        backend_port = getattr(self.gen_context, 'backend_internal_port', 8080) if self.gen_context else 8080
        api_port = getattr(self.gen_context, 'api_port', 8080) if self.gen_context else 8080
        db_port = getattr(self.gen_context, 'db_port', 5432) if self.gen_context else 5432
        
        prompt = self.render_macro(
            "backend_agent.j2",
            "backend_task_prompt",
            backend_port=backend_port,
            api_port=api_port,
            db_port=db_port
        )
        
        if prompt:
            return prompt
        
        # Fallback
        return f"""Generate Express.js backend API.

1. view("design/spec.api.json") and view("design/spec.database.json") first
2. Create server.js, routes, middleware in app/backend/
3. Port: {backend_port} (env: PORT)
4. Response format: {{items: [...], total: N}} for lists

Call finish() when done."""
