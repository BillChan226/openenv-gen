"""
Communication Tools - Enable LLM to communicate with other agents

These tools allow agents to dynamically decide when and how to communicate
with other agents in the multi-agent system.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from utils.tool import BaseTool

if TYPE_CHECKING:
    from .agents.base import EnvGenAgent


class AskAgentTool(BaseTool):
    """
    Ask another agent a question and wait for their response.
    
    Use this when you need information from another agent's domain:
    - Ask 'design' about API specifications or schema
    - Ask 'database' about table structures
    - Ask 'backend' about API endpoints
    - Ask 'frontend' about UI components
    - Ask 'user' about requirements clarification
    """
    
    name = "ask_agent"
    description = """Ask another agent a question and wait for their response.

Use this tool when you need information from another agent's expertise:
- design: API specs, database schema, UI design decisions
- database: Table structures, SQL queries, data relationships
- backend: API endpoints, authentication, server logic
- frontend: UI components, state management, user interactions
- user: Requirements clarification, business logic

Args:
    agent_id: Target agent to ask (design, database, backend, frontend, user)
    question: Your question for the agent

Returns:
    The agent's response to your question
"""
    
    def __init__(self, agent: "EnvGenAgent"):
        super().__init__()
        self.agent = agent
    
    async def execute(self, agent_id: str, question: str) -> str:
        """Ask another agent a question."""
        if not self.agent.can_talk_to(agent_id):
            available = [info["id"] for info in self.agent.get_available_agents()]
            return f"Error: Cannot communicate with '{agent_id}'. Available agents: {available}"
        
        try:
            response = await self.agent.ask(agent_id, question)
            return f"Response from {agent_id}: {response}"
        except Exception as e:
            return f"Error communicating with {agent_id}: {str(e)}"


class TellAgentTool(BaseTool):
    """
    Send a one-way message to another agent (no response expected).
    
    Use this to:
    - Notify other agents of your progress
    - Share information they might need
    - Report completion of tasks
    """
    
    name = "tell_agent"
    description = """Send a one-way notification to another agent.

Use this tool to inform other agents about:
- Progress updates ("Backend API routes are ready")
- Completed work ("Database schema has been created")
- Important information they need ("API uses 'items' as response wrapper")
- Warnings ("Database migration required before testing")

Args:
    agent_id: Target agent (design, database, backend, frontend, user)
    message: The message to send
    msg_type: Type of message (update, complete, warning, info). Default: update

Returns:
    Confirmation that message was sent
"""
    
    def __init__(self, agent: "EnvGenAgent"):
        super().__init__()
        self.agent = agent
    
    async def execute(self, agent_id: str, message: str, msg_type: str = "update") -> str:
        """Send a message to another agent."""
        if not self.agent.can_talk_to(agent_id):
            available = [info["id"] for info in self.agent.get_available_agents()]
            return f"Error: Cannot communicate with '{agent_id}'. Available agents: {available}"
        
        try:
            await self.agent.tell(agent_id, message, msg_type=msg_type)
            return f"Message sent to {agent_id}: '{message}'"
        except Exception as e:
            return f"Error sending message to {agent_id}: {str(e)}"


class BroadcastTool(BaseTool):
    """
    Broadcast a message to all other agents.
    
    Use this for major announcements that all agents should know about:
    - Phase completions
    - Critical changes
    - System-wide updates
    """
    
    name = "broadcast"
    description = """Broadcast a message to all other agents.

Use this tool for important announcements that everyone should know:
- Major milestone completions ("Design phase complete")
- Critical changes ("API response format changed to use 'items' wrapper")
- System-wide updates ("Database schema has been updated, please sync")

Args:
    message: The message to broadcast
    msg_type: Type of message (update, complete, warning, info). Default: update

Returns:
    Confirmation that message was broadcast
"""
    
    def __init__(self, agent: "EnvGenAgent"):
        super().__init__()
        self.agent = agent
    
    async def execute(self, message: str, msg_type: str = "update") -> str:
        """Broadcast message to all agents."""
        try:
            await self.agent.broadcast(message, msg_type=msg_type)
            recipients = [info["id"] for info in self.agent.get_available_agents()]
            return f"Broadcast sent to {len(recipients)} agents: {recipients}"
        except Exception as e:
            return f"Error broadcasting: {str(e)}"


class GetAgentInfoTool(BaseTool):
    """
    Get information about available agents.
    
    Use this to understand who you can communicate with
    and what their responsibilities are.
    """
    
    name = "get_agents"
    description = """Get information about available agents you can communicate with.

Use this to:
- See which agents are available
- Understand each agent's role and responsibilities
- Decide who to ask for specific information

Args:
    agent_id: Optional specific agent ID to get detailed info. If not provided, lists all agents.

Returns:
    Information about available agents
"""
    
    def __init__(self, agent: "EnvGenAgent"):
        super().__init__()
        self.agent = agent
    
    async def execute(self, agent_id: str = None) -> str:
        """Get agent information."""
        if agent_id:
            info = self.agent.get_agent_info(agent_id)
            if info:
                return f"Agent '{agent_id}':\n  Name: {info['name']}\n  Role: {info['role']}\n  Tools: {', '.join(info.get('tools', [])[:5])}..."
            else:
                return f"Agent '{agent_id}' not found"
        
        agents = self.agent.get_available_agents()
        if not agents:
            return "No other agents available"
        
        lines = ["Available agents:"]
        for info in agents:
            lines.append(f"  - {info['id']}: {info['role']}")
        
        return "\n".join(lines)


def create_communication_tools(agent: "EnvGenAgent") -> List[BaseTool]:
    """
    Create all communication tools for an agent.
    
    Args:
        agent: The agent that will use these tools
        
    Returns:
        List of communication tools
    """
    return [
        AskAgentTool(agent),
        TellAgentTool(agent),
        BroadcastTool(agent),
        GetAgentInfoTool(agent),
    ]

