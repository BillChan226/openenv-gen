"""
Design Agent - Project Architecture & Design

Responsibilities:
1. Create project overview (README)
2. Design database schema (spec.database.json)
3. Design API endpoints (spec.api.json)
4. Design frontend structure (spec.ui.json)
5. Answer design questions from other agents

Uses prompts from: prompts/design_agent.j2
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.llm import Message

from .base import EnvGenAgent


class DesignAgent(EnvGenAgent):
    """
    Design Agent - Architect for the project.
    
    Creates design documents that other agents reference.
    Answers questions about design decisions.
    """
    
    agent_id = "design"
    agent_name = "DesignAgent"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Design documents (shared with other agents)
        self._db_schema: Dict = {}
        self._api_spec: Dict = {}
        self._ui_spec: Dict = {}
    
    # ==================== Main Interface ====================
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute design tasks."""
        task_type = task.get("type", "")
        requirements = task.get("requirements", self._requirements)
        
        if task_type == "design_all":
            return await self._design_all(requirements)
        elif task_type == "design_db":
            return await self._design_database(requirements)
        elif task_type == "design_api":
            return await self._design_api(requirements)
        elif task_type == "design_ui":
            return await self._design_ui(requirements)
        else:
            return {"success": False, "error": f"Unknown task type: {task_type}"}
    
    # ==================== Design Methods ====================
    
    async def _design_all(self, requirements: Dict) -> Dict[str, Any]:
        """Create all design documents."""
        self._logger.info("Creating all design documents...")
        files_created = []
        
        # 1. Project README
        readme = await self._create_readme(requirements)
        self.write_file("design/README.md", readme)
        files_created.append("design/README.md")
        
        # 2. Database schema
        db_result = await self._design_database(requirements)
        if db_result["success"]:
            files_created.append("design/spec.database.json")
        
        # 3. API specification
        api_result = await self._design_api(requirements)
        if api_result["success"]:
            files_created.append("design/spec.api.json")
        
        # 4. UI specification
        ui_result = await self._design_ui(requirements)
        if ui_result["success"]:
            files_created.append("design/spec.ui.json")
        
        # LLM can use broadcast tool to notify other agents
        return {
            "success": True,
            "files_created": files_created,
            "design_docs": {
                "db_schema": self._db_schema,
                "api_spec": self._api_spec,
                "ui_spec": self._ui_spec,
            },
            "notify_suggestion": "Consider using broadcast to notify all agents: 'Design phase complete'",
        }
    
    async def _create_readme(self, requirements: Dict) -> str:
        """Create project README using j2 template."""
        try:
            prompt = self.render_macro(
                "design_agent.j2",
                "create_readme",
                project=requirements.get("project", {})
            )
        except Exception as e:
            self._logger.warning(f"Could not load j2 template: {e}")
            project = requirements.get("project", {})
            prompt = f"""Create a professional README.md for:
{json.dumps(project, indent=2)}

Include: title, description, features, tech stack, getting started, development guide.
Output markdown directly.
"""
        
        return await self.think(prompt)
    
    async def _design_database(self, requirements: Dict) -> Dict[str, Any]:
        """Design database schema using j2 template."""
        self._logger.info("Designing database schema...")
        
        try:
            prompt = self.render_macro(
                "design_agent.j2",
                "design_database",
                requirements=requirements,
                features=requirements.get("features", [])
            )
        except Exception as e:
            self._logger.warning(f"Could not load j2 template: {e}")
            prompt = self._get_db_prompt(requirements)
        
        response = await self.think(prompt)
        
        try:
            json_str = self._extract_json(response)
            self._db_schema = json.loads(json_str)
            self.write_file("design/spec.database.json", json.dumps(self._db_schema, indent=2))
            
            # LLM can use tell_agent to notify database agent if needed
            return {"success": True, "schema": self._db_schema}
            
        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse DB schema: {e}")
            return {"success": False, "error": str(e)}
    
    async def _design_api(self, requirements: Dict) -> Dict[str, Any]:
        """Design API specification using j2 template."""
        self._logger.info("Designing API specification...")
        
        try:
            prompt = self.render_macro(
                "design_agent.j2",
                "design_api",
                requirements=requirements,
                db_schema=self._db_schema
            )
        except Exception as e:
            self._logger.warning(f"Could not load j2 template: {e}")
            prompt = self._get_api_prompt(requirements)
        
        response = await self.think(prompt)
        
        try:
            json_str = self._extract_json(response)
            self._api_spec = json.loads(json_str)
            self.write_file("design/spec.api.json", json.dumps(self._api_spec, indent=2))
            
            # LLM can use tell_agent or broadcast to notify agents if needed
            return {"success": True, "api_spec": self._api_spec}
            
        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse API spec: {e}")
            return {"success": False, "error": str(e)}
    
    async def _design_ui(self, requirements: Dict) -> Dict[str, Any]:
        """Design UI specification using j2 template."""
        self._logger.info("Designing UI specification...")
        
        try:
            prompt = self.render_macro(
                "design_agent.j2",
                "design_ui",
                requirements=requirements,
                api_spec=self._api_spec
            )
        except Exception as e:
            self._logger.warning(f"Could not load j2 template: {e}")
            prompt = self._get_ui_prompt(requirements)
        
        response = await self.think(prompt)
        
        try:
            json_str = self._extract_json(response)
            self._ui_spec = json.loads(json_str)
            self.write_file("design/spec.ui.json", json.dumps(self._ui_spec, indent=2))
            
            # LLM can use tell_agent to notify frontend if needed
            return {"success": True, "ui_spec": self._ui_spec}
            
        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse UI spec: {e}")
            return {"success": False, "error": str(e)}
    
    # ==================== Fallback Prompts ====================
    
    def _get_db_prompt(self, requirements: Dict) -> str:
        """Fallback database design prompt."""
        return f"""Design PostgreSQL database schema for:
{json.dumps(requirements, indent=2)}

Output JSON with: tables (columns, types, constraints), relationships, seed_data.
Use UUIDs, timestamps. Include test users with bcrypt hashes.
Output ONLY JSON.
"""
    
    def _get_api_prompt(self, requirements: Dict) -> str:
        """Fallback API design prompt."""
        return f"""Design REST API specification for:
{json.dumps(requirements, indent=2)}

Database schema: {json.dumps(self._db_schema, indent=2)}

Output JSON with:
- conventions (base_url, list_response_wrapper: "items")
- auth endpoints (register, login, me, logout)
- CRUD endpoints for each entity
- Each endpoint must have response_key (items, item, etc.)

CRITICAL: All list endpoints must use "items" as response wrapper.
Output ONLY JSON.
"""
    
    def _get_ui_prompt(self, requirements: Dict) -> str:
        """Fallback UI design prompt."""
        return f"""Design frontend UI specification for:
{json.dumps(requirements, indent=2)}

Output JSON with: theme (colors, typography), layout, pages, components.
Each component should specify api_integration with endpoint and response_key.
Output ONLY JSON.
"""
    
    def _extract_json(self, response: str) -> str:
        """Extract JSON from LLM response."""
        if "```json" in response:
            return response.split("```json")[1].split("```")[0]
        elif "```" in response:
            return response.split("```")[1].split("```")[0]
        return response
    
    # ==================== Communication Handlers ====================
    
    async def _answer_question(self, message) -> str:
        """Answer design questions from other agents."""
        try:
            prompt = self.render_macro(
                "design_agent.j2",
                "answer_question",
                question=message.content,
                context={
                    "db_schema": self._db_schema,
                    "api_spec": self._api_spec,
                    "ui_spec": self._ui_spec,
                }
            )
        except:
            prompt = f"""You are the Design/Architect agent. Another agent ({message.from_agent}) asks:

{message.content}

Design Context:
- Database Schema: {json.dumps(self._db_schema, indent=2)[:500] if self._db_schema else "Not yet designed"}
- API Spec: {json.dumps(self._api_spec, indent=2)[:500] if self._api_spec else "Not yet designed"}

Provide an authoritative answer about the design.
"""
        return await self.think(prompt)
    
    def get_design_docs(self) -> Dict[str, Any]:
        """Get all design documents."""
        return {
            "db_schema": self._db_schema,
            "api_spec": self._api_spec,
            "ui_spec": self._ui_spec,
        }
