"""
Task Agent - Generates action space, tasks, trajectories, and judge functions

Uses LLM + Tool + Message pattern like other agents.
Analyzes the generated application and creates benchmark tasks.
"""

import logging
from typing import Dict, List, Any, Optional

from env_generator.llm_generator.multi_agent.agents.base import EnvGenAgent

logger = logging.getLogger(__name__)


class TaskAgent(EnvGenAgent):
    """
    Task Agent - Creates benchmark tasks for generated applications.
    
    Works like other agents using:
    - LLM for reasoning and planning
    - Tools for action space extraction, task generation, etc.
    - Messages to coordinate with UserAgent for validation
    
    Workflow (driven by prompt):
    1. Wait for message from UserAgent that app is ready
    2. Analyze specs and code to extract action space
    3. Generate tasks covering all features
    4. Create trajectories (reference solutions)
    5. Write judge functions
    6. Export task_config.json
    7. Notify UserAgent to validate tasks
    """
    
    # Override class attributes for proper identification
    agent_id: str = "task"
    agent_name: str = "TaskAgent"
    allowed_tool_categories: list = ["file", "reasoning", "browser", "task"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Storage for generated content (accessible by tools)
        self.action_space: Dict = {}
        self.tasks: List[Dict] = []
        self.trajectories: List[Dict] = []
        self.judges: List[Dict] = []
