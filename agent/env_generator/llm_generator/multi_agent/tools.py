"""
Tools Integration for Multi-Agent System

Provides tools to each agent based on their role:
- UserAgent: Browser, Docker, Testing tools
- DesignAgent: File, Analysis tools
- DatabaseAgent: File, Docker, Data Engine tools
- BackendAgent: File, Docker, Runtime tools
- FrontendAgent: File, Runtime, Image Search tools
- TaskAgent: File, Browser, Task generation tools
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
    ViewImageTool,
    ListReferenceImagesTool,
    CopyReferenceImageTool,
    # FileHistory is a singleton helper, not a tool
    
    # Image Tools
    IconSearchTool,      # search_icons
    PhotoSearchTool,     # search_photos
    LogoSearchTool,      # search_logos
    SaveImageTool,       # save_image
    CaptureWebpageTool,  # capture_webpage
    create_image_search_tools,
    
    # Code Tools
    LintTool,
    
    # Reasoning Tools
    ThinkTool,
    GetTimeTool,
    WaitTool,
    PlanTool,
    VerifyPlanTool,
    
    # Analysis Tools
    create_analysis_tools,
    FindDefinitionTool,
    FindReferencesTool,
    GetSymbolsTool,
    
    # Runtime Tools
    ExecuteBashTool,
    ExecuteIPythonTool,
    FindFreePortTool,
    RunBackgroundTool,
    StopProcessTool,
    InterruptProcessTool,
    ListProcessesTool,
    GetProcessOutputTool,
    WaitForProcessTool,
    CleanupPortsTool,
    TestAPITool,
    InstallDependenciesTool,
    
    # Docker Tools
    create_docker_tools,
    DockerBuildTool,
    DockerUpTool,
    DockerDownTool,
    DockerLogsTool,
    DockerStatusTool,
    DockerRestartTool,
    DockerValidateTool,
    DockerInspectImageTool,
    
    # Database Tools
    create_database_tools,
    DatabaseQueryTool,
    DatabaseSchemaTool,
    DatabaseTestTool,
    
    # Data Engine Tools (HuggingFace dataset discovery)
    create_data_engine_tools,
    DiscoverDatasetsTool,
    PreviewDatasetTool,
    GenerateSeedSQLTool,
    
    # Log Tools
    create_log_tools,
    LogParseTool,
    LogAnalyzeTool,
    LogSearchTool,
    
    # Task Tools (benchmark generation)
    create_task_tools,
    ExtractActionSpaceTool,
    GenerateTaskTool,
    GenerateTrajectoryTool,
    GenerateJudgeTool,
    ExportTaskConfigTool,
    TestActionTool,
    
    # Project Tools
    create_project_tools,
    ProjectStructureTool,
    ListGeneratedFilesTool,
    CheckDuplicatesTool,
    
    # Browser Tools
    BROWSER_TOOLS_AVAILABLE,
    create_browser_tools,
    
    # Vision Tools
    create_vision_tools,
    AnalyzeScreenshotTool,
    CompareWithScreenshotTool,
    ExtractComponentsTool,
    
    # Progress Reporting Tools
    ReportProgressTool,
    ReportCompletionTool,
    ReportIssueTool,
    GetProgressTool,
    
    # Agent Interaction Tools
    FinishTool,
    ReadMemoryBankTool,
    DeliverProjectTool,
    
    # Communication Tools
    SendMessageTool,
    AskAgentTool,
    BroadcastTool,
    CheckInboxTool,
    ListAgentsTool,
    SubscribeMessagesTool,
    create_communication_tools,
    
    # Memory Tools
    RememberTool,
    RecallTool,
    ShareKnowledgeTool,
    GetOperationHistoryTool,
    GetMemoryContextTool,
    create_memory_tools,
    
    # Dependency Tools
    create_dependency_tools,
    CheckImportsTool,
    MissingDependenciesTool,
    
    # Note: Debug classes (CrossLayerDebugger, APIAlignmentVerifier, etc.) 
    # are helper classes, not tools - they're used internally by agents
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
        PlanTool(agent_id="default"),  # Use default for get_all_tools
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
    
    # Database
    tools.extend(create_database_tools(workspace=workspace))
    
    # Log
    tools.extend(create_log_tools(workspace=workspace))
    
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
    include_vision: bool = False,
    llm_client = None,
) -> List[BaseTool]:
    """
    Get tools appropriate for a specific agent type.
    
    Tool assignments:
    - user: Browser, Docker, Testing (for verification)
    - design: File, Analysis, Vision (for design documents and reference images)
    - database: File (for SQL files)
    - backend: File, Runtime (for server code)
    - frontend: File, Vision (for React code with reference images)
    """
    
    # Base file tools for all agents
    file_tools = [
        ViewTool(workspace=workspace),
        WriteFileTool(workspace=workspace),
        StrReplaceEditorTool(workspace=workspace),
        DeleteFileTool(workspace=workspace),
        GlobTool(workspace=workspace),
        GrepTool(workspace=workspace),
        LintTool(workspace=workspace),
        ViewImageTool(workspace=workspace),
        # Note: FileHistory is a singleton helper, not a tool
    ]
    
    # Reasoning tools for all agents (each agent gets its own PlanTool instance)
    reasoning_tools = [
        ThinkTool(),
        GetTimeTool(),
        WaitTool(),
        PlanTool(agent_id=agent_type),  # Pass agent_type so each agent has independent plan state
        VerifyPlanTool(),
    ]
    
    # Memory tools for all agents - each agent gets its own instances
    memory_tools = create_memory_tools()  # Agent reference will be set later
    
    # Progress reporting tools for all agents - each agent gets its own instance
    progress_tools = [
        ReportProgressTool(agent_id=agent_type),
        ReportCompletionTool(agent_id=agent_type),
        ReportIssueTool(agent_id=agent_type),
        GetProgressTool(agent_id=agent_type),
    ]
    
    # Core agent tools (finish, etc.) - each agent gets its own FinishTool instance
    agent_tools = [
        FinishTool(agent_id=agent_type),  # Pass agent_type so FinishTool checks the correct plan
        ReadMemoryBankTool(workspace=workspace),
        # Communication tools (will be configured with agent reference later)
        *create_communication_tools(),
    ]
    
    # Project tools for all agents
    project_tools = create_project_tools(workspace=workspace)
    
    # Analysis tools for code understanding
    analysis_tools = create_analysis_tools(workspace=workspace)
    
    # Base tools that all agents get
    base_tools = file_tools + reasoning_tools + memory_tools + progress_tools + agent_tools + project_tools + analysis_tools
    
    if agent_type == "user":
        # UserAgent: Full testing suite + DeliverProjectTool (for ending generation)
        tools = base_tools + [
            TestAPITool(),
            ExecuteBashTool(workspace=workspace),
            ExecuteIPythonTool(workspace=workspace),
            FindFreePortTool(),
            CleanupPortsTool(),
            RunBackgroundTool(workspace=workspace),
            StopProcessTool(),
            InterruptProcessTool(),
            ListProcessesTool(),
            GetProcessOutputTool(),
            WaitForProcessTool(),
            DeliverProjectTool(),  # Only UserAgent can deliver the project (triggers shutdown)
        ]
        
        # Note: Debug classes are helpers used internally, not direct tools
        
        # Docker for managing containers
        if include_docker:
            tools.extend(create_docker_tools(workspace=workspace))
            tools.append(DockerRestartTool(workspace=workspace))
        
        # Database tools for data verification
        tools.extend(create_database_tools(workspace=workspace))
        
        # Log tools for debugging
        tools.extend(create_log_tools(workspace=workspace))
        
        # Browser for UI testing
        if include_browser and BROWSER_TOOLS_AVAILABLE:
            tools.extend(create_browser_tools(workspace.root))
        
        # Vision for comparing screenshots
        if include_vision and llm_client:
            tools.extend(create_vision_tools(llm_client, workspace=workspace))
        
        # Image search tools (for finding reference images)
        tools.extend(create_image_search_tools(workspace=workspace))
        
        return tools
    
    elif agent_type == "design":
        # DesignAgent: File + Analysis + Vision (for analyzing reference screenshots)
        tools = base_tools[:]  # base_tools already includes analysis_tools
        
        # Image viewing tools for reference images
        tools.extend([
            ListReferenceImagesTool(workspace=workspace),
            CopyReferenceImageTool(workspace=workspace),
        ])
        
        # Image search tools
        tools.extend(create_image_search_tools(workspace=workspace))
        
        # Vision tools for analyzing reference images
        if include_vision and llm_client:
            tools.extend(create_vision_tools(llm_client, workspace=workspace))
        
        return tools
    
    elif agent_type == "database":
        # DatabaseAgent: File + Database inspection + Data Engine + Image Search
        tools = base_tools + create_database_tools(workspace=workspace)
        # Add Data Engine tools for HuggingFace dataset discovery and loading
        tools.extend(create_data_engine_tools(workspace=workspace))
        # Add Image Search tools for finding images for seed data (restaurant photos, etc.)
        tools.extend(create_image_search_tools(workspace=workspace))
        return tools
    
    elif agent_type == "backend":
        # BackendAgent: File + Runtime + Database + Debug
        tools = base_tools + [
            ExecuteBashTool(workspace=workspace),
            ExecuteIPythonTool(workspace=workspace),
            FindFreePortTool(),
            CleanupPortsTool(),
            RunBackgroundTool(workspace=workspace),
            StopProcessTool(),
            InterruptProcessTool(),
            ListProcessesTool(),
            GetProcessOutputTool(),
            WaitForProcessTool(),
            TestAPITool(),
            InstallDependenciesTool(workspace=workspace),
        ]
        # Database tools for data verification
        tools.extend(create_database_tools(workspace=workspace))
        # Dependency checking
        tools.extend(create_dependency_tools(workspace=workspace))
        return tools
    
    elif agent_type == "frontend":
        # FrontendAgent: File + npm commands + Vision + Debug
        tools = base_tools + [
            ExecuteBashTool(workspace=workspace),
            InstallDependenciesTool(workspace=workspace),
        ]
        
        # Image tools for reference screenshots
        tools.extend([
            ListReferenceImagesTool(workspace=workspace),
            CopyReferenceImageTool(workspace=workspace),
        ])
        
        # Image search tools
        tools.extend(create_image_search_tools(workspace=workspace))
        
        # Dependency checking for frontend
        tools.extend(create_dependency_tools(workspace=workspace))
        
        # Vision tools for implementing from reference images
        if include_vision and llm_client:
            tools.extend(create_vision_tools(llm_client, workspace=workspace))
        
        return tools
    
    elif agent_type == "task":
        # TaskAgent: File + Project + Browser + Task generation tools
        tools = base_tools + [
            ProjectStructureTool(workspace=workspace),
            ListGeneratedFilesTool(workspace=workspace),
        ]
        
        # Task-specific tools
        tools.extend(create_task_tools(workspace=workspace))
        
        # Browser tools for testing actions
        if BROWSER_TOOLS_AVAILABLE:
            tools.extend(create_browser_tools(workspace.root if workspace else None))
        
        # Database tools for judge functions that check DB state
        tools.extend(create_database_tools(workspace=workspace))
        
        return tools
    
    else:
        # Unknown agent type: basic tools only
        return base_tools


# Re-export Workspace
__all__ = [
    "Workspace",
    "get_all_tools",
    "get_agent_tools",
    "PlanTool",  # Exposed for plan status checking
]

