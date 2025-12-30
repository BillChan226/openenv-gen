"""
Tools Integration for Multi-Agent System

Provides tools to each agent based on their role:
- UserAgent: Browser, Docker, Testing tools
- DesignAgent: File, Analysis tools
- DatabaseAgent: File, Docker tools
- BackendAgent: File, Docker, Runtime tools
- FrontendAgent: File, Runtime tools
"""

from pathlib import Path
from typing import List, Optional

from utils.tool import BaseTool, ToolRegistry

# Import from existing tools module
import sys
_llm_gen_dir = Path(__file__).parent.parent
if str(_llm_gen_dir) not in sys.path:
    sys.path.insert(0, str(_llm_gen_dir))

from tools import (
    # Workspace
    Workspace,
    
    # File Tools
    ViewTool,
    WriteFileTool,
    StrReplaceEditorTool,
    DeleteFileTool,
    GlobTool,
    GrepTool,
    EditFileTool,
    
    # Reasoning Tools
    ThinkTool,
    PlanTool,
    
    # Analysis Tools
    create_analysis_tools,
    
    # Runtime Tools
    ExecuteBashTool,
    FindFreePortTool,
    RunBackgroundTool,
    StopProcessTool,
    ListProcessesTool,
    GetProcessOutputTool,
    TestAPITool,
    InstallDependenciesTool,
    
    # Docker Tools
    create_docker_tools,
    DockerBuildTool,
    DockerUpTool,
    DockerDownTool,
    DockerLogsTool,
    DockerStatusTool,
    
    # Project Tools
    create_project_tools,
    ProjectStructureTool,
    ListGeneratedFilesTool,
    
    # Browser Tools
    BROWSER_TOOLS_AVAILABLE,
    create_browser_tools,
    
    # Vision Tools
    create_vision_tools,
)


def get_all_tools(
    workspace: Workspace,
    include_browser: bool = True,
    include_docker: bool = True,
    include_vision: bool = False,
    llm_client = None,
) -> List[BaseTool]:
    """Get all available tools."""
    tools = []
    
    # File tools
    tools.extend([
        ViewTool(workspace=workspace),
        WriteFileTool(workspace=workspace),
        StrReplaceEditorTool(workspace=workspace),
        DeleteFileTool(workspace=workspace),
        GlobTool(workspace=workspace),
        GrepTool(workspace=workspace),
        EditFileTool(workspace=workspace),
    ])
    
    # Reasoning
    tools.extend([
        ThinkTool(),
        PlanTool(),
    ])
    
    # Analysis
    tools.extend(create_analysis_tools(workspace=workspace))
    
    # Runtime
    tools.extend([
        ExecuteBashTool(workspace=workspace),
        FindFreePortTool(),
        RunBackgroundTool(workspace=workspace),
        StopProcessTool(),
        ListProcessesTool(),
        GetProcessOutputTool(),
        TestAPITool(),
        InstallDependenciesTool(workspace=workspace),
    ])
    
    # Docker
    if include_docker:
        tools.extend(create_docker_tools(workspace=workspace))
    
    # Project
    tools.extend(create_project_tools(workspace=workspace))
    
    # Browser
    if include_browser and BROWSER_TOOLS_AVAILABLE:
        tools.extend(create_browser_tools(workspace.root))
    
    # Vision
    if include_vision and llm_client:
        tools.extend(create_vision_tools(llm_client, workspace=workspace))
    
    return tools


def get_agent_tools(
    agent_type: str,
    workspace: Workspace,
    include_browser: bool = False,
    include_docker: bool = False,
    llm_client = None,
) -> List[BaseTool]:
    """
    Get tools appropriate for a specific agent type.
    
    Tool assignments:
    - user: Browser, Docker, Testing (for verification)
    - design: File, Analysis (for design documents)
    - database: File (for SQL files)
    - backend: File, Runtime (for server code)
    - frontend: File (for React code)
    """
    
    # Base file tools for all agents
    file_tools = [
        ViewTool(workspace=workspace),
        WriteFileTool(workspace=workspace),
        StrReplaceEditorTool(workspace=workspace),
        GlobTool(workspace=workspace),
        GrepTool(workspace=workspace),
    ]
    
    # Reasoning tools for all agents
    reasoning_tools = [
        ThinkTool(),
        PlanTool(),
    ]
    
    # Project tools for all agents
    project_tools = create_project_tools(workspace=workspace)
    
    # Base tools that all agents get
    base_tools = file_tools + reasoning_tools + project_tools
    
    if agent_type == "user":
        # UserAgent: Full testing suite
        tools = base_tools + [
            TestAPITool(),
            ExecuteBashTool(workspace=workspace),
        ]
        
        # Docker for managing containers
        if include_docker:
            tools.extend(create_docker_tools(workspace=workspace))
        
        # Browser for UI testing
        if include_browser and BROWSER_TOOLS_AVAILABLE:
            tools.extend(create_browser_tools(workspace.root))
        
        return tools
    
    elif agent_type == "design":
        # DesignAgent: File + Analysis
        return base_tools + create_analysis_tools(workspace=workspace)
    
    elif agent_type == "database":
        # DatabaseAgent: File only (SQL files)
        return base_tools
    
    elif agent_type == "backend":
        # BackendAgent: File + Runtime (for testing server)
        return base_tools + [
            ExecuteBashTool(workspace=workspace),
            FindFreePortTool(),
            RunBackgroundTool(workspace=workspace),
            StopProcessTool(),
            GetProcessOutputTool(),
            TestAPITool(),
            InstallDependenciesTool(workspace=workspace),
        ]
    
    elif agent_type == "frontend":
        # FrontendAgent: File + npm commands
        return base_tools + [
            ExecuteBashTool(workspace=workspace),
            InstallDependenciesTool(workspace=workspace),
        ]
    
    else:
        # Unknown agent type: basic tools only
        return base_tools


# Re-export Workspace
__all__ = [
    "Workspace",
    "get_all_tools",
    "get_agent_tools",
]

