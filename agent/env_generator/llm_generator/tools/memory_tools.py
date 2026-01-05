"""
Memory Tools - Tools for agents to manage their memory

These tools allow agents to:
1. Remember important information for later recall
2. Recall previously stored information
3. Share knowledge with other agents
4. Query their operation history

Usage in agent prompts:
- Use remember() to store important decisions, patterns, or learnings
- Use recall() to retrieve relevant past knowledge
- Use share_knowledge() to inform other agents of important info
"""

from typing import Dict, Any, List, Optional
import logging

import sys
from pathlib import Path
_tools_dir = Path(__file__).parent.parent.parent.absolute()
if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))

from utils.tool import BaseTool, ToolResult, ToolCategory, create_tool_param


class RememberTool(BaseTool):
    """
    Tool for agents to remember important information.
    
    Stores knowledge in long-term memory with categorization.
    """
    
    NAME = "remember"
    DESCRIPTION = """Store important information in your memory for later recall.

Use this to remember:
- Key decisions and their rationale
- Bug fixes and how you solved them
- Patterns you've discovered
- Important requirements or constraints
- Learnings that could help with similar tasks

Examples:
- remember(content="User auth requires JWT tokens with 24h expiry", category="requirement")
- remember(content="Fixed CORS error by adding origin header in backend", category="bug_fix")
- remember(content="This project uses PostgreSQL for main data", category="tech_context")

Categories: requirement, decision, bug_fix, pattern, tech_context, warning
"""
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        self.agent = None
        self._logger = logging.getLogger("memory_tools")
    
    def set_agent(self, agent):
        """Set the agent instance for memory access."""
        self.agent = agent
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "content": {
                    "type": "string",
                    "description": "The information to remember (be specific and concise)"
                },
                "category": {
                    "type": "string",
                    "enum": ["requirement", "decision", "bug_fix", "pattern", "tech_context", "warning", "progress"],
                    "description": "Category of the knowledge"
                },
                "importance": {
                    "type": "number",
                    "description": "Importance score from 0.0 (low) to 1.0 (critical). Default: 0.5",
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "share_with": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: List of agent IDs to share this knowledge with (e.g., ['backend', 'frontend'])"
                }
            },
            required=["content", "category"]
        )
    
    def execute(
        self, 
        content: str, 
        category: str,
        importance: float = 0.5,
        share_with: List[str] = None
    ) -> ToolResult:
        if not self.agent or not hasattr(self.agent, 'memory'):
            return ToolResult(
                success=False,
                error_message="Memory system not available"
            )
        
        try:
            knowledge_id = self.agent.memory.add_knowledge(
                content=content,
                category=category,
                importance=importance,
                share_with=share_with
            )
            
            result = {
                "stored": True,
                "knowledge_id": knowledge_id,
                "category": category,
                "importance": importance,
            }
            
            if share_with:
                result["shared_with"] = share_with
            
            self._logger.info(f"[{getattr(self.agent, 'agent_id', 'unknown')}] Remembered: {content[:80]}...")
            
            return ToolResult(success=True, data=result)
            
        except Exception as e:
            return ToolResult(success=False, error_message=str(e))


class RecallTool(BaseTool):
    """
    Tool for agents to recall previously stored information.
    """
    
    NAME = "recall"
    DESCRIPTION = """Search your memory for relevant past knowledge.

Use this to retrieve:
- Previously stored decisions or patterns
- How you fixed similar bugs before
- Technical context about the project
- Important requirements you noted

Examples:
- recall(query="authentication") - Search for auth-related memories
- recall(category="bug_fix") - Get all bug fix memories
- recall(query="database schema", category="tech_context")

Returns up to 5 most relevant memories.
"""
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        self.agent = None
    
    def set_agent(self, agent):
        self.agent = agent
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant memories"
                },
                "category": {
                    "type": "string",
                    "enum": ["requirement", "decision", "bug_fix", "pattern", "tech_context", "warning", "progress"],
                    "description": "Optional: Filter by category"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 5)",
                    "minimum": 1,
                    "maximum": 10
                }
            },
            required=[]
        )
    
    def execute(
        self, 
        query: str = None,
        category: str = None,
        limit: int = 5
    ) -> ToolResult:
        if not self.agent or not hasattr(self.agent, 'memory'):
            return ToolResult(
                success=False,
                error_message="Memory system not available"
            )
        
        try:
            memories = self.agent.memory.recall_knowledge(
                query=query,
                category=category,
                limit=limit
            )
            
            if not memories:
                return ToolResult(
                    success=True,
                    data={
                        "found": 0,
                        "memories": [],
                        "message": "No matching memories found"
                    }
                )
            
            formatted = []
            for m in memories:
                formatted.append({
                    "id": m.get("id"),
                    "content": m.get("content"),
                    "category": m.get("category"),
                    "importance": m.get("importance"),
                    "timestamp": m.get("timestamp"),
                })
            
            return ToolResult(
                success=True,
                data={
                    "found": len(formatted),
                    "memories": formatted
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error_message=str(e))


class ShareKnowledgeTool(BaseTool):
    """
    Tool for agents to share knowledge with other agents.
    """
    
    NAME = "share_knowledge"
    DESCRIPTION = """Share important knowledge with other agents.

Use this to inform other agents about:
- API schemas they need to implement against
- Database structure decisions
- Design patterns to follow
- Important constraints or warnings

The knowledge will be delivered to the target agents' inbox.

Examples:
- share_knowledge(to_agents=["frontend"], content="API uses JWT Bearer tokens", category="tech_context")
- share_knowledge(to_agents=["backend", "frontend"], content="Use snake_case for all API fields", category="pattern")
"""
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        self.agent = None
        self._logger = logging.getLogger("memory_tools")
    
    def set_agent(self, agent):
        self.agent = agent
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "to_agents": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["user", "design", "database", "backend", "frontend"]},
                    "description": "List of agent IDs to share with"
                },
                "content": {
                    "type": "string",
                    "description": "The knowledge to share"
                },
                "category": {
                    "type": "string",
                    "enum": ["tech_context", "pattern", "warning", "requirement", "decision"],
                    "description": "Category of knowledge"
                },
                "importance": {
                    "type": "string",
                    "enum": ["low", "normal", "high"],
                    "description": "How important is this info? Default: normal"
                }
            },
            required=["to_agents", "content", "category"]
        )
    
    def execute(
        self,
        to_agents: List[str],
        content: str,
        category: str,
        importance: str = "normal"
    ) -> ToolResult:
        if not self.agent:
            return ToolResult(success=False, error_message="Agent not available")
        
        try:
            # Store in own memory
            if hasattr(self.agent, 'memory'):
                self.agent.memory.add_knowledge(
                    content=f"[Shared to {', '.join(to_agents)}] {content}",
                    category=category,
                    importance=0.6
                )
            
            # Send via message bus
            bus = getattr(self.agent, '_external_bus', None) or getattr(self.agent, '_message_bus', None)
            if not bus:
                return ToolResult(
                    success=False,
                    error_message="Message bus not available for sharing"
                )
            
            # Queue messages (will be sent by agent's message processing)
            if not hasattr(self.agent, '_pending_knowledge_shares'):
                self.agent._pending_knowledge_shares = []
            
            for target in to_agents:
                self.agent._pending_knowledge_shares.append({
                    "target": target,
                    "content": content,
                    "category": category,
                    "importance": importance,
                })
            
            self._logger.info(f"[{getattr(self.agent, 'agent_id', 'unknown')}] Queued knowledge share to {to_agents}")
            
            return ToolResult(
                success=True,
                data={
                    "shared_to": to_agents,
                    "category": category,
                    "message": "Knowledge queued for delivery"
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error_message=str(e))


class GetOperationHistoryTool(BaseTool):
    """
    Tool to get recent operation history.
    """
    
    NAME = "get_history"
    DESCRIPTION = """Get your recent operation history and statistics.

Useful to:
- Review what you've done so far
- Check file creation/modification stats
- See recent tool calls
- Identify patterns in your actions

Returns: Recent tool calls, file stats, and any warnings.
"""
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        self.agent = None
    
    def set_agent(self, agent):
        self.agent = agent
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={
                "include": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["tools", "files", "errors", "knowledge"]},
                    "description": "What to include in history. Default: all"
                }
            },
            required=[]
        )
    
    def execute(self, include: List[str] = None) -> ToolResult:
        if not self.agent or not hasattr(self.agent, 'memory'):
            return ToolResult(
                success=False,
                error_message="Memory system not available"
            )
        
        include = include or ["tools", "files", "errors", "knowledge"]
        
        try:
            result = {}
            
            if "tools" in include:
                tool_stats = self.agent.memory.get_tool_stats()
                result["tool_stats"] = {
                    "total_calls": tool_stats.get("total_calls", 0),
                    "by_tool": tool_stats.get("by_tool", {}),
                    "last_tool": tool_stats.get("last_tool", ""),
                }
                if tool_stats.get("consecutive_same", 0) > 3:
                    result["tool_stats"]["warning"] = f"Repeated {tool_stats['last_tool']} calls detected"
            
            if "files" in include:
                result["file_stats"] = self.agent.memory.get_file_stats()
                unlinted = self.agent.memory.get_unlinted_files()
                if unlinted:
                    result["file_stats"]["unlinted_files"] = unlinted[:10]
            
            if "errors" in include:
                errors = self.agent.memory._errors[-5:]
                if errors:
                    result["recent_errors"] = [
                        {"error": e["error"][:200], "time": e["time"]}
                        for e in errors
                    ]
            
            if "knowledge" in include:
                knowledge = self.agent.memory._knowledge[-5:]
                if knowledge:
                    result["recent_knowledge"] = [
                        {"content": k["content"][:100], "category": k["category"]}
                        for k in knowledge
                    ]
            
            return ToolResult(success=True, data=result)
            
        except Exception as e:
            return ToolResult(success=False, error_message=str(e))


class GetMemoryContextTool(BaseTool):
    """
    Tool to get formatted memory context.
    """
    
    NAME = "get_memory_context"
    DESCRIPTION = """Get a formatted summary of your memory and context.

Returns a structured overview of:
- Previous context summary (if conversation was condensed)
- Current phase and progress
- File operation stats
- Key learnings
- Recent issues

Use this when you need to refresh your understanding of the current state.
"""
    
    def __init__(self):
        super().__init__(name=self.NAME, category=ToolCategory.AGENT)
        self.agent = None
    
    def set_agent(self, agent):
        self.agent = agent
    
    def tool_definition(self):
        return self.get_tool_param()
    
    def get_tool_param(self):
        return create_tool_param(
            name=self.NAME,
            description=self.DESCRIPTION,
            parameters={},
            required=[]
        )
    
    def execute(self) -> ToolResult:
        if not self.agent or not hasattr(self.agent, 'memory'):
            return ToolResult(
                success=False,
                error_message="Memory system not available"
            )
        
        try:
            context = self.agent.memory.get_memory_context(include_knowledge=True)
            
            return ToolResult(
                success=True,
                data={
                    "context": context,
                    "stats": self.agent.memory.stats()
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error_message=str(e))


# ==================== Tool Creation Helper ====================

def create_memory_tools(agent=None) -> List[BaseTool]:
    """
    Create all memory tools.
    
    Args:
        agent: The agent instance to attach tools to
        
    Returns:
        List of memory tool instances
    """
    tools = [
        RememberTool(),
        RecallTool(),
        ShareKnowledgeTool(),
        GetOperationHistoryTool(),
        GetMemoryContextTool(),
    ]
    
    if agent:
        for tool in tools:
            if hasattr(tool, 'set_agent'):
                tool.set_agent(agent)
    
    return tools


__all__ = [
    "RememberTool",
    "RecallTool",
    "ShareKnowledgeTool",
    "GetOperationHistoryTool",
    "GetMemoryContextTool",
    "create_memory_tools",
]

