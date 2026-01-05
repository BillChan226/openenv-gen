"""
Frontend Agent - React/Vite UI code generation

Uses j2 templates from: prompts/frontend_agent.j2
"""

from typing import Dict, List

from .base import EnvGenAgent


class FrontendAgent(EnvGenAgent):
    """Frontend agent - generates React + Vite + Tailwind code."""
    
    agent_id = "frontend"
    agent_name = "FrontendAgent"
    allowed_tool_categories = ["file", "reasoning", "runtime", "vision", "communication"]
    
    def _get_system_prompt(self) -> str:
        """Use j2 template for system prompt."""
        workspace_dir = str(self.workspace.base_dir) if self.workspace else "."
        
        prompt = self.render_macro("frontend_agent.j2", "frontend_system_prompt", workspace_dir=workspace_dir)
        if prompt:
            return prompt
        
        # Fallback
        return """You are FrontendAgent, a React frontend developer.
Generate React + Vite + Tailwind code in app/frontend/.
Read design/spec.ui.json first. Check reference images.
Backend returns {items: [...]} for lists - always access data.items.
Use tools. Call finish() when done."""
    
    def _build_task_prompt(self, task: Dict) -> str:
        """Use j2 template for task prompt."""
        description = task.get("description", "")
        
        # If specific task description, use it
        if description:
            # Add API spec context if API-related issue
            enhanced = description
            if any(kw in description.lower() for kw in ["map", "undefined", "api", "fetch", "items"]):
                api_spec = self.read_file("design/spec.api.json")
                if api_spec:
                    enhanced += f"\n\nAPI Spec (for reference):\n{api_spec[:2000]}"
            
            return f"""## Task

{enhanced}

## Instructions

1. Use view() to examine relevant files
2. Use think() to analyze what needs to be done
3. Make changes with write_file() or str_replace_editor()
4. Use lint() to verify syntax
5. Call finish() when done

Remember: Backend returns lists as {{items: [...]}}.

Start now."""
        
        # Default generation task - use j2 template
        backend_port = getattr(self.gen_context, 'backend_internal_port', 8080) if self.gen_context else 8080
        
        prompt = self.render_macro(
            "frontend_agent.j2",
            "frontend_task_prompt",
            backend_port=backend_port
        )
        
        if prompt:
            return prompt
        
        # Fallback
        return f"""Generate React + Vite frontend.

1. list_reference_images() and view_image() to check design references
2. view("design/spec.ui.json") and view("design/spec.api.json")
3. Create app/frontend/src/ with components, pages, services
4. API returns {{items: [...]}} for lists - extract with data.items

Call finish() when done."""
