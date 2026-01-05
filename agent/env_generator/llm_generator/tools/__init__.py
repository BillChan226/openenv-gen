"""
Tools Package - Comprehensive tools for code generation

Tool Categories:
================

File Tools:
    ViewTool, StrReplaceEditorTool, WriteFileTool, DeleteFileTool,
    ViewImageTool, ListReferenceImagesTool, CopyReferenceImageTool, GlobTool

Image Tools:
    IconSearchTool (search_icons) - Icons/SVGs from Iconify
    PhotoSearchTool (search_photos) - Photos/screenshots via Google
    LogoSearchTool (search_logos) - Company/brand logos
    SaveImageTool (save_image) - Download images
    CaptureWebpageTool (capture_webpage) - Screenshot webpages

Code Tools:
    GrepTool, EditFileTool, LintTool, ThinkTool, PlanTool, VerifyPlanTool,
    ReadMemoryBankTool, FinishTool

Analysis Tools:
    FindDefinitionTool, FindReferencesTool, GetSymbolsTool

Dependency Tools:
    CheckImportsTool, MissingDependenciesTool

Runtime Tools (Unified Process Management):
    ExecuteBashTool, ExecuteIPythonTool, FindFreePortTool,
    RunBackgroundTool (unified server/background), StopProcessTool, InterruptProcessTool,
    ListProcessesTool, GetProcessOutputTool, WaitForProcessTool,
    CleanupPortsTool, TestAPITool, InstallDependenciesTool
    ProcessManager, ProcessInfo, ProcessType, ProcessStatus

Docker Tools:
    DockerBuildTool, DockerUpTool, DockerDownTool, DockerLogsTool,
    DockerStatusTool, DockerRestartTool

Project Tools:
    ProjectStructureTool, ListGeneratedFilesTool, CheckDuplicatesTool

Browser Tools:
    BrowserNavigateTool, BrowserScreenshotTool, BrowserGetConsoleTool,
    BrowserClickTool, BrowserFillTool, BrowserGetElementsTool,
    BrowserEvaluateTool, BrowserCloseTool, BrowserFindTool,
    BrowserGetUrlTool, BrowserWaitForUrlTool, BrowserA11yTreeTool

Vision Tools:
    AnalyzeScreenshotTool, CompareWithScreenshotTool, ExtractComponentsTool

Debug Tools:
    CrossLayerDebugger, APIAlignmentVerifier, EnhancedErrorParser,
    ReasoningDebugger, IterativeDebugger
"""

# Use centralized base imports
from ._base import Path, Workspace

# Path Utilities (legacy compatibility)
from .path_utils import (
    resolve_path,
    resolve_output_dir,
    normalize_path_for_tracking,
)

# File Tools
from .file_tools import (
    ViewTool,
    StrReplaceEditorTool,
    WriteFileTool,
    DeleteFileTool,
    ViewImageTool,
    ListReferenceImagesTool,
    CopyReferenceImageTool,
    GlobTool,
    FileHistory,
)

# Image Tools (search, download, screenshot)
from .image_search_tools import (
    IconSearchTool,      # search_icons - Icons/SVGs from Iconify
    PhotoSearchTool,     # search_photos - Photos/screenshots via Google
    LogoSearchTool,      # search_logos - Company/brand logos
    SaveImageTool,       # save_image - Download images
    CaptureWebpageTool,  # capture_webpage - Screenshot webpages
    create_image_search_tools,
)

# Code Tools (search, edit, lint)
from .code_tools import (
    GrepTool,
    EditFileTool,
    LintTool,
)

# Reasoning Tools (think, plan)
from .reasoning_tools import (
    ThinkTool,
    GetTimeTool,
    WaitTool,
    PlanTool,
    VerifyPlanTool,
)

# Agent Interaction Tools (memory, finish, deliver)
from .agent_interaction_tools import (
    ReadMemoryBankTool,
    FinishTool,
    DeliverProjectTool,
)

# Communication Tools (message-driven inter-agent communication)
from .communication_tools import (
    SendMessageTool,
    AskAgentTool,
    BroadcastTool,
    CheckInboxTool,
    ListAgentsTool,
    SubscribeMessagesTool,
    UnsubscribeMessagesTool,
    PublishMessageTool,
    # Message status tracking
    GetMessageStatusTool,
    GetPendingRepliesTool,
    AcknowledgeMessageTool,
    MarkProcessingTool,
    create_communication_tools,
)

# Memory Tools (agent memory management)
from .memory_tools import (
    RememberTool,
    RecallTool,
    ShareKnowledgeTool,
    GetOperationHistoryTool,
    GetMemoryContextTool,
    create_memory_tools,
)

# Progress Reporting Tools
from .progress_tools import (
    ReportProgressTool,
    ReportCompletionTool,
    ReportIssueTool,
    GetProgressTool,
)

# Analysis Tools
from .analysis_tools import (
    create_analysis_tools,
    FindDefinitionTool,
    FindReferencesTool,
    GetSymbolsTool,
)

# Dependency Tools
from .dependency_tools import (
    create_dependency_tools,
    CheckImportsTool,
    MissingDependenciesTool,
)

# Runtime Tools (Unified Process Management)
from .runtime_tools import (
    # Core Process Manager
    ProcessManager,
    ProcessInfo,
    ProcessType,
    ProcessStatus,
    get_process_manager,
    
    # Primary Tools
    ExecuteBashTool,
    ExecuteIPythonTool,
    FindFreePortTool,
    RunBackgroundTool,        # NEW: Unified background/server tool
    StopProcessTool,          # NEW: Stop any process
    InterruptProcessTool,     # NEW: Send Ctrl+C to process
    ListProcessesTool,        # NEW: List all processes
    GetProcessOutputTool,     # NEW: Get process output
    WaitForProcessTool,       # NEW: Wait for process to complete
    CleanupPortsTool,
    TestAPITool,
    InstallDependenciesTool,
    
    # Legacy Aliases (backward compatibility)
    StartServerTool,
    StopServerTool,
    ListServersTool,
    GetServerLogsTool,
    KillProcessTool,
    ListBackgroundProcessesTool,
    CheckProcessStatusTool,
    ServerRegistry,
    BackgroundProcessRegistry,
)

# Docker Tools
from .docker_tools import (
    create_docker_tools,
    DockerBuildTool,
    DockerUpTool,
    DockerDownTool,
    DockerLogsTool,
    DockerStatusTool,
    DockerRestartTool,
    DockerValidateTool,
    DockerInspectImageTool,
)

# Project Tools
from .project_tools import (
    create_project_tools,
    ProjectStructureTool,
    ListGeneratedFilesTool,
    CheckDuplicatesTool,
)

# Browser Tools (from browser/ package)
try:
    from .browser import (
        create_browser_tools,
        BrowserManager,
        BrowserState,
        PLAYWRIGHT_AVAILABLE,
        # Core
        BrowserNavigateTool,
        BrowserScreenshotTool,
        BrowserGetConsoleTool,
        BrowserGetNetworkErrorsTool,
        BrowserCloseTool,
        # Interaction
        BrowserClickTool,
        BrowserFillTool,
        BrowserSelectTool,
        BrowserHoverTool,
        BrowserPressKeyTool,
        BrowserScrollTool,
        BrowserWaitTool,
        # Inspection
        BrowserGetElementsTool,
        BrowserEvaluateTool,
        BrowserGetUrlTool,
        BrowserWaitForUrlTool,
        BrowserFindTool,
        BrowserGetAttributeTool,
        BrowserGetTextTool,
        BrowserCheckVisibleTool,
        BrowserCheckAccessibilityTool,
        BrowserAccessibilityTreeTool,
    )
    BROWSER_TOOLS_AVAILABLE = True
except ImportError:
    BROWSER_TOOLS_AVAILABLE = False
    PLAYWRIGHT_AVAILABLE = False
    create_browser_tools = lambda *args, **kwargs: []

# Vision Tools
from .vision_tools import (
    create_vision_tools,
    AnalyzeImageTool,
    CompareWithScreenshotTool,
    ExtractComponentsTool,
    ListReferenceImagesTool as VisionListReferenceImagesTool,
    DesignAnalysis,
)
# Alias for backward compatibility
AnalyzeScreenshotTool = AnalyzeImageTool

# Debug Tools
from .debug_tools import (
    CrossLayerDebugger,
    ErrorTrace,
    APIAlignmentVerifier,
    APICall,
    BackendRoute,
    AlignmentIssue,
    RuntimeDebugTools,
    EnhancedErrorParser,
)

# Reasoning Debugger
from .reasoning_debugger import (
    ReasoningDebugger,
    IterativeDebugger,
    DebugDiagnosis,
    CodeChange,
)

# Database Tools
from .database_tools import (
    DatabaseQueryTool,
    DatabaseSchemaTool,
    DatabaseTestTool,
    create_database_tools,
)

# Data Engine Tools (HuggingFace dataset discovery and loading)
from .data_engine_tools import (
    DiscoverDatasetsTool,
    PreviewDatasetTool,
    GenerateSeedSQLTool,
    create_data_engine_tools,
)

# Log Tools
from .log_tools import (
    LogParser,
    LogEntry,
    LogParseTool,
    LogAnalyzeTool,
    LogSearchTool,
    create_log_tools,
)

# Task Tools (for benchmark generation)
from .task_tools import (
    ExtractActionSpaceTool,
    GenerateTaskTool,
    GenerateTrajectoryTool,
    GenerateJudgeTool,
    ExportTaskConfigTool,
    TestActionTool,
    create_task_tools,
)


def get_all_tools(
    output_dir: str = None, 
    work_dir: str = None, 
    workspace: Workspace = None,
    include_browser: bool = True,
    include_vision: bool = True,
    llm_client = None
):
    """
    Get all available tools.
    
    Args:
        output_dir: Directory for file operations (legacy, use workspace instead)
        work_dir: Working directory for runtime operations (legacy, use workspace instead)
        workspace: Workspace object for centralized path management
        include_browser: Include browser tools (requires Playwright)
        
    Returns:
        List of tool instances
    """
    # Create workspace if not provided
    if workspace is None:
        if output_dir:
            workspace = Workspace(output_dir)
        elif work_dir:
            workspace = Workspace(work_dir)
        else:
            workspace = Workspace(Path.cwd())
    
    tools = [
        # File tools
        ViewTool(workspace=workspace),
        StrReplaceEditorTool(workspace=workspace),
        WriteFileTool(workspace=workspace),
        DeleteFileTool(workspace=workspace),
        ViewImageTool(workspace=workspace),
        ListReferenceImagesTool(workspace=workspace),
        CopyReferenceImageTool(workspace=workspace),
        GlobTool(workspace=workspace),
        
        # Image tools
        IconSearchTool(workspace=workspace),
        PhotoSearchTool(workspace=workspace),
        LogoSearchTool(workspace=workspace),
        SaveImageTool(workspace=workspace),
        CaptureWebpageTool(workspace=workspace),
        
        # Code tools
        GrepTool(workspace=workspace),
        EditFileTool(workspace=workspace),
        LintTool(workspace=workspace),
        ThinkTool(),
        PlanTool(agent_id="default"),  # Use default for get_all_tools
        VerifyPlanTool(),
        ReadMemoryBankTool(workspace=workspace),
        FinishTool(agent_id="default"),  # Use default for get_all_tools
        
        # Communication tools (message-based inter-agent communication)
        *create_communication_tools(),
        
        # Progress Reporting Tools
        ReportProgressTool(),
        ReportCompletionTool(),
        ReportIssueTool(),
        GetProgressTool(),
        
        
        # Analysis tools
        *create_analysis_tools(workspace=workspace),
        
        # Dependency tools
        *create_dependency_tools(workspace=workspace),
        
        # Runtime tools (Unified Process Management)
        ExecuteBashTool(workspace=workspace),
        ExecuteIPythonTool(workspace=workspace),
        FindFreePortTool(),
        RunBackgroundTool(workspace=workspace),   # Unified background/server tool
        StopProcessTool(),                        # Stop any process
        InterruptProcessTool(),                   # Send Ctrl+C to process
        ListProcessesTool(),                      # List all processes
        GetProcessOutputTool(),                   # Get process output
        WaitForProcessTool(),                     # Wait for process to complete
        CleanupPortsTool(),
        TestAPITool(),
        InstallDependenciesTool(workspace=workspace),
        
        # Docker tools
        *create_docker_tools(workspace=workspace),
        
        # Project tools
        *create_project_tools(workspace=workspace),
        
        # Database tools
        *create_database_tools(workspace=workspace),
        
        # Data Engine tools (HuggingFace datasets)
        *create_data_engine_tools(workspace=workspace),
        
        # Log tools
        *create_log_tools(workspace=workspace),
    ]
    
    # Browser tools (optional, requires Playwright)
    if include_browser and BROWSER_TOOLS_AVAILABLE:
        # Pass workspace root - browser tools will save files within it
        tools.extend(create_browser_tools(workspace.root))
    
    # Vision tools (optional, requires multimodal LLM)
    if include_vision:
        vision_tools = create_vision_tools(llm_client, workspace=workspace)
        tools.extend(vision_tools)
    
    return tools


def get_vision_tools(llm_client=None) -> list:
    """Get vision tools for screenshot-based generation"""
    return create_vision_tools(llm_client)


def get_tool_params(tools=None, output_dir: str = None, work_dir: str = None, workspace: Workspace = None):
    """
    Get tool parameters for LLM function calling.
    """
    if tools is None:
        tools = get_all_tools(output_dir=output_dir, work_dir=work_dir, workspace=workspace)
    
    return [tool.get_tool_param() for tool in tools]


__all__ = [
    # Workspace
    "Workspace",
    
    # Path Utilities (legacy)
    "resolve_path",
    "resolve_output_dir",
    "normalize_path_for_tracking",
    
    # File Tools
    "ViewTool",
    "StrReplaceEditorTool",
    "WriteFileTool",
    "DeleteFileTool",
    "ViewImageTool",
    "ListReferenceImagesTool",
    "CopyReferenceImageTool",
    "GlobTool",
    "FileHistory",
    
    # Image Tools
    "IconSearchTool",
    "PhotoSearchTool",
    "LogoSearchTool",
    "SaveImageTool",
    "CaptureWebpageTool",
    "create_image_search_tools",
    
    # Code Tools
    "GrepTool",
    "EditFileTool",
    "LintTool",
    "ThinkTool",
    "GetTimeTool",
    "WaitTool",
    "PlanTool",
    "VerifyPlanTool",
    "ReadMemoryBankTool",
    "FinishTool",
    "DeliverProjectTool",
    
    # Communication Tools
    "SendMessageTool",
    "AskAgentTool",
    "BroadcastTool",
    "CheckInboxTool",
    "ListAgentsTool",
    "SubscribeMessagesTool",
    "UnsubscribeMessagesTool",
    "PublishMessageTool",
    # Message status tracking
    "GetMessageStatusTool",
    "GetPendingRepliesTool",
    "AcknowledgeMessageTool",
    "MarkProcessingTool",
    "create_communication_tools",
    
    # Memory Tools
    "RememberTool",
    "RecallTool",
    "ShareKnowledgeTool",
    "GetOperationHistoryTool",
    "GetMemoryContextTool",
    "create_memory_tools",
    
    # Progress Reporting Tools
    "ReportProgressTool",
    "ReportCompletionTool",
    "ReportIssueTool",
    "GetProgressTool",
    
    
    # Analysis Tools
    "create_analysis_tools",
    "FindDefinitionTool",
    "FindReferencesTool",
    "GetSymbolsTool",
    
    # Dependency Tools
    "create_dependency_tools",
    "CheckImportsTool",
    "MissingDependenciesTool",
    
    # Runtime Tools (Unified Process Management)
    "ProcessManager",
    "ProcessInfo",
    "ProcessType",
    "ProcessStatus",
    "get_process_manager",
    "ExecuteBashTool",
    "ExecuteIPythonTool",
    "FindFreePortTool",
    "RunBackgroundTool",
    "StopProcessTool",
    "InterruptProcessTool",
    "ListProcessesTool",
    "GetProcessOutputTool",
    "WaitForProcessTool",
    "CleanupPortsTool",
    "TestAPITool",
    "InstallDependenciesTool",
    # Legacy Aliases
    "StartServerTool",
    "StopServerTool",
    "ListServersTool",
    "GetServerLogsTool",
    "KillProcessTool",
    "ListBackgroundProcessesTool",
    "CheckProcessStatusTool",
    "ServerRegistry",
    "BackgroundProcessRegistry",
    
    # Docker Tools
    "create_docker_tools",
    "DockerBuildTool",
    "DockerUpTool",
    "DockerDownTool",
    "DockerLogsTool",
    "DockerStatusTool",
    "DockerRestartTool",
    
    # Project Tools
    "create_project_tools",
    "ProjectStructureTool",
    "ListGeneratedFilesTool",
    "CheckDuplicatesTool",
    
    # Browser Tools
    "create_browser_tools",
    "BrowserManager",
    "BrowserState",
    "PLAYWRIGHT_AVAILABLE",
    "BROWSER_TOOLS_AVAILABLE",
    # Core
    "BrowserNavigateTool",
    "BrowserScreenshotTool",
    "BrowserGetConsoleTool",
    "BrowserGetNetworkErrorsTool",
    "BrowserCloseTool",
    # Interaction
    "BrowserClickTool",
    "BrowserFillTool",
    "BrowserSelectTool",
    "BrowserHoverTool",
    "BrowserPressKeyTool",
    "BrowserScrollTool",
    "BrowserWaitTool",
    # Inspection
    "BrowserGetElementsTool",
    "BrowserEvaluateTool",
    "BrowserGetUrlTool",
    "BrowserWaitForUrlTool",
    "BrowserFindTool",
    "BrowserGetAttributeTool",
    "BrowserGetTextTool",
    "BrowserCheckVisibleTool",
    "BrowserCheckAccessibilityTool",
    "BrowserAccessibilityTreeTool",
    
    # Vision Tools
    "create_vision_tools",
    "get_vision_tools",
    "AnalyzeScreenshotTool",
    "CompareWithScreenshotTool",
    "ExtractComponentsTool",
    "DesignAnalysis",
    
    # Debug Tools
    "CrossLayerDebugger",
    "ErrorTrace",
    "APIAlignmentVerifier",
    "APICall",
    "BackendRoute",
    "AlignmentIssue",
    "RuntimeDebugTools",
    "EnhancedErrorParser",
    
    # Reasoning Debugger
    "ReasoningDebugger",
    "IterativeDebugger",
    "DebugDiagnosis",
    "CodeChange",
    
    # Database Tools
    "DatabaseQueryTool",
    "DatabaseSchemaTool",
    "DatabaseTestTool",
    "create_database_tools",
    
    # Data Engine Tools
    "DiscoverDatasetsTool",
    "PreviewDatasetTool",
    "GenerateSeedSQLTool",
    "create_data_engine_tools",
    
    # Log Tools
    "LogParser",
    "LogEntry",
    "LogParseTool",
    "LogAnalyzeTool",
    "LogSearchTool",
    "create_log_tools",
    
    # Task Tools
    "ExtractActionSpaceTool",
    "GenerateTaskTool",
    "GenerateTrajectoryTool",
    "GenerateJudgeTool",
    "ExportTaskConfigTool",
    "TestActionTool",
    "create_task_tools",
    
    # Helpers
    "get_all_tools",
    "get_tool_params",
]
