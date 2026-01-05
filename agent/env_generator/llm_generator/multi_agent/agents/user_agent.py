"""
User Agent - Requirements refinement, testing, project delivery

Works like other agents via agentic loop + tool calls.
No special methods - all behavior driven by prompts and messages.

Uses j2 templates from: prompts/user_agent.j2
"""

import json
import re
from typing import Any, Dict, List, Optional

from .base import EnvGenAgent


class UserAgent(EnvGenAgent):
    """
    User agent - acts as PM/QA.
    
    Phases:
    1. Requirements: Refine raw requirements into structured spec
    2. Testing: Test application after other agents finish, report issues
    3. Delivery: Call deliver_project() when everything is ready
    
    All behavior is driven by prompts - no special hardcoded logic.
    """
    
    agent_id = "user"
    agent_name = "UserAgent"
    allowed_tool_categories = ["browser", "docker", "api", "debug", "reasoning", "file", "progress", "communication"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._project_delivered: bool = False
    
    def _get_system_prompt(self) -> str:
        """Use j2 template for system prompt."""
        workspace_dir = str(self.workspace.base_dir) if self.workspace else "."
        
        prompt = self.render_macro("user_agent.j2", "test_system_prompt", workspace_dir=workspace_dir)
        if prompt:
            return prompt
        
        # Fallback
        return """You are UserAgent, acting as PM and QA Engineer.

Your responsibilities:
1. Refine raw requirements into structured specifications
2. Test the application after other agents complete their work
3. Report issues to the responsible agents
4. Deliver the project when everything is ready

Communication:
- Use check_inbox() to see messages from other agents
- Use send_message() / ask_agent() to communicate
- Use report_issue() to dispatch bugs to responsible agents

Completion:
- Use finish() to end current task (you stay available for more work)
- Use deliver_project() ONLY when the project is 100% ready for users
  - deliver_project() ends the ENTIRE generation process
"""
    
    def _build_task_prompt(self, task: Dict) -> str:
        """Build task prompt based on task type."""
        raw_requirements = task.get("raw_requirements", "")
        workflow = task.get("workflow", "")
        description = task.get("description", "")
        
        # Full workflow: requirements → coordinate → test → deliver
        if workflow == "full" or raw_requirements:
            return self._build_full_workflow_prompt(raw_requirements)
        
        # Testing only (legacy or explicit testing task)
        return self._build_test_prompt(description)
    
    def _build_full_workflow_prompt(self, raw_requirements: str) -> str:
        """Build full workflow prompt - UserAgent coordinates entire generation."""
        api_port = getattr(self.gen_context, 'api_port', 8000) if self.gen_context else 8000
        ui_port = getattr(self.gen_context, 'ui_port', 3000) if self.gen_context else 3000
        
        prompt = self.render_macro(
            "user_agent.j2",
            "full_workflow_prompt",
            raw_requirements=raw_requirements,
            api_port=api_port,
            ui_port=ui_port,
        )
        if prompt:
            return prompt
        
        # Fallback
        return f"""## Full Project Workflow

You are the coordinator for this project. You will guide the entire generation process.

### Raw Requirements
{raw_requirements}

### Your Workflow

**Phase 1: Requirements**
1. think() - analyze the requirements
2. Create structured JSON spec with project_name, features, tech_stack, pages, api_endpoints
3. broadcast() - send requirements to all agents
4. send_message(to_agent="design", content="Requirements ready. Please start design.", msg_type="info")

**Phase 2: Wait for Design**
1. check_inbox() - wait for design agent to complete
2. When design is ready, code agents will be notified by design agent

**Phase 3: Wait for Code**
1. check_inbox() periodically - monitor progress from database, backend, frontend
2. Answer any questions from other agents

**Phase 4: Test**
1. When code agents finish, start testing
2. docker_build(), docker_up() - start services
3. test_api(), browser_navigate() - test functionality
4. report_issue() - send bugs to responsible agents
5. Re-test after fixes

**Phase 5: Deliver**
1. When everything works with NO bugs:
2. deliver_project(confirmation="CONFIRMED", delivery_summary="...", checklist={{...}})

### URLs
- Frontend: http://localhost:{ui_port}
- Backend: http://localhost:{api_port}

Start with plan() to organize your approach, then begin Phase 1.
"""
    
    def _build_refine_prompt(self, raw_requirements: str) -> str:
        """Build requirements refinement prompt."""
        prompt = self.render_macro("user_agent.j2", "refine_requirements", raw_requirements=raw_requirements)
        if prompt:
            return prompt
        
        return f"""## Refine Requirements

Raw requirements:
{raw_requirements}

Create a structured JSON specification with:
- project_name, description
- features (name, description, priority)
- tech_stack (frontend: React, backend: Express, database: PostgreSQL)
- pages, api_endpoints

Steps:
1. think() - analyze the requirements
2. Create the specification
3. finish(outputs={{"requirements": {{...}}}})
"""
    
    def _build_test_prompt(self, description: str = "") -> str:
        """Build testing prompt."""
        api_port = getattr(self.gen_context, 'api_port', 8000) if self.gen_context else 8000
        ui_port = getattr(self.gen_context, 'ui_port', 3000) if self.gen_context else 3000
        
        prompt = self.render_macro(
            "user_agent.j2", 
            "test_task_prompt",
            api_port=api_port,
            ui_port=ui_port,
            description=description,
        )
        if prompt:
            return prompt
        
        return f"""## Task: Test Application and Deliver When Ready

{description}

URLs:
- Frontend: http://localhost:{ui_port}
- Backend: http://localhost:{api_port}

## Your Workflow

1. **Check Status**
   - Use check_inbox() to see if other agents have completed
   - Use docker_status() to check containers

2. **Start Services** (if needed)
   - docker_build() - build containers
   - docker_up() - start containers

3. **Test**
   - test_api() - test API endpoints
   - browser_navigate(), browser_screenshot() - test UI
   - Verify all features from the spec work correctly

4. **Report Issues**
   - Use report_issue(issue="...", assign_to="frontend/backend/database") for bugs
   - Wait for fixes, re-test

5. **Deliver**
   - When EVERYTHING works perfectly with NO bugs:
   - deliver_project(confirmation="CONFIRMED", delivery_summary="...", checklist={{...}})
   - This ends the generation process

Start with plan() to organize your testing approach.
"""
    
    def _process_refine_result(self, result: Dict) -> Dict:
        """Extract requirements from result."""
        if result.get("success"):
            finish_outputs = result.get("finish", {}).get("outputs", {})
            if "requirements" in finish_outputs:
                self._requirements = finish_outputs["requirements"]
                return {"success": True, "requirements": self._requirements}
            
            # Try parse from summary
            summary = result.get("summary", "")
            try:
                json_str = self._extract_json(summary)
                requirements = json.loads(json_str)
                self._requirements = requirements
                return {"success": True, "requirements": requirements}
            except:
                pass
        
        return {"success": False, "error": "Failed to extract requirements", "raw_result": result}
    
    async def execute(self, task: Dict) -> Dict:
        """Execute task - standard agentic loop."""
        result = await super().execute(task)
        
        # Post-process requirements refinement
        if task.get("raw_requirements"):
            return self._process_refine_result(result)
        
        return result
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text."""
        if "```json" in text:
            match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
            if match:
                return match.group(1).strip()
        
        # Find braces
        start = text.find('{')
        if start != -1:
            count = 0
            for i, c in enumerate(text[start:], start):
                if c == '{':
                    count += 1
                elif c == '}':
                    count -= 1
                    if count == 0:
                        return text[start:i+1]
        
        return text.strip()
