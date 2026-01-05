"""
Design Agent - Architecture and specification generation

Uses j2 templates from: prompts/design_agent.j2
"""

import json
from typing import Any, Dict, List, Optional

from .base import EnvGenAgent, safe_json_dumps


class DesignAgent(EnvGenAgent):
    """Design agent - creates design documents and specifications."""
    
    agent_id = "design"
    agent_name = "DesignAgent"
    allowed_tool_categories = ["file", "reasoning", "vision", "communication"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._db_schema: Dict = {}
        self._api_spec: Dict = {}
        self._ui_spec: Dict = {}
    
    def _get_system_prompt(self) -> str:
        """Use j2 template for system prompt."""
        workspace_dir = str(self.workspace.base_dir) if self.workspace else "."
        
        prompt = self.render_macro("design_agent.j2", "design_system_prompt", workspace_dir=workspace_dir)
        if prompt:
            return prompt
        
        # Fallback
        return """You are DesignAgent, a senior software architect.
Create design documents in design/. 
Files: README.md, spec.database.json, spec.api.json, spec.ui.json.
All list endpoints must return {items: [...]} format in spec.api.json.
Use tools. Call finish() when done."""
    
    def _build_task_prompt(self, task: Dict) -> str:
        """Use j2 template for task prompt."""
        description = task.get("description", "")
        requirements = task.get("requirements", self._requirements)
        reference_images = task.get("reference_images", [])
        
        # If specific task description, use it
        if description:
            return f"""## Task

{description}

## Instructions

1. Use view() to examine relevant files
2. Use think() to analyze what needs to be done
3. Make changes with write_file() or str_replace_editor()
4. Ensure consistency across all design documents
5. Call finish() when done

Start now."""
        
        # Default design task
        prompt_parts = [
            "## Task: Create Design Documents",
            "",
            "## Requirements",
            safe_json_dumps(requirements),
        ]
        
        if reference_images:
            prompt_parts.extend([
                "",
                "## Reference Images",
                "Use analyze_image() to study these:",
                *[f"- {img}" for img in reference_images],
            ])
        
        prompt_parts.extend([
            "",
            "## Files to Create",
            "1. design/README.md - Project overview",
            "2. design/spec.database.json - Database schema",
            "3. design/spec.api.json - API spec (list responses: {items: [...]})",
            "4. design/spec.ui.json - UI specification",
            "",
            "Use plan() first, then create each file with write_file().",
            "Call finish() when done.",
        ])
        
        return "\n".join(prompt_parts)
    
    async def execute(self, task: Dict) -> Dict:
        """Execute and load design docs after."""
        result = await super().execute(task)
        if result.get("success"):
            self._load_design_docs()
        return result
    
    def _load_design_docs(self):
        """Load design documents into memory."""
        for name, attr in [("spec.database", "_db_schema"), ("spec.api", "_api_spec"), ("spec.ui", "_ui_spec")]:
            content = self.read_file(f"design/{name}.json")
            if content:
                try:
                    setattr(self, attr, json.loads(content))
                except:
                    pass
    
    def get_design_docs(self) -> Dict[str, Any]:
        """Get all design documents."""
        return {"db_schema": self._db_schema, "api_spec": self._api_spec, "ui_spec": self._ui_spec}
