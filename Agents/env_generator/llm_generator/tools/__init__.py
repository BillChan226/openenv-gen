"""
Tools Package - Comprehensive tools for code generation

File Tools:
- ViewTool: View files with line numbers, list directories
- StrReplaceEditorTool: Create, edit, insert, undo files
- WriteFileTool: Simple file write
- GlobTool: Find files by pattern

Code Tools:
- GrepTool: Regex content search
- EditFileTool: LLM-friendly editing with partial content
- LintTool: Syntax checking
- ThinkTool: Reasoning without action
- FinishTool: Signal task completion

Analysis Tools:
- FindDefinitionTool: Find where a symbol is defined
- FindReferencesTool: Find all usages of a symbol
- GetSymbolsTool: List functions/classes in a file

Dependency Tools:
- CheckImportsTool: List imports in a file
- MissingDependenciesTool: Find missing npm/pip packages

Runtime Tools:
- ExecuteBashTool: Run shell commands with timeout
- ExecuteIPythonTool: Run Python code
- StartServerTool: Start background server
- StopServerTool: Stop server
- ListServersTool: List all servers
- GetServerLogsTool: Get server logs
- TestAPITool: HTTP endpoint testing
- InstallDependenciesTool: Install dependencies

Docker Tools:
- DockerBuildTool: Build images
- DockerUpTool: Start containers
- DockerDownTool: Stop containers
- DockerLogsTool: View logs
- DockerStatusTool: Container status
- DockerRestartTool: Restart services

Project Tools:
- ProjectStructureTool: View project tree
- ListGeneratedFilesTool: List generated files
- CheckDuplicatesTool: Check for duplicates

Browser Tools:
- BrowserNavigateTool: Navigate to URL and capture errors
- BrowserScreenshotTool: Take screenshots
- BrowserGetConsoleTool: Get console logs
- BrowserClickTool: Click elements
- BrowserFillTool: Fill form inputs
- BrowserGetElementsTool: Query page elements
- BrowserEvaluateTool: Execute JavaScript
- BrowserCloseTool: Close browser

Vision Tools:
- AnalyzeScreenshotTool: Extract design info from screenshots
- CompareWithScreenshotTool: Compare generated UI with reference
- ExtractComponentsTool: Extract specific UI component specs
"""

# Path Utilities (shared across all tools)
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
    GlobTool,
    FileHistory,
)

# Code Tools
from .code_tools import (
    GrepTool,
    EditFileTool,
    LintTool,
    ThinkTool,
    FinishTool,
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

# Runtime Tools
from .runtime_tools import (
    ExecuteBashTool,
    ExecuteIPythonTool,
    StartServerTool,
    StopServerTool,
    ListServersTool,
    GetServerLogsTool,
    TestAPITool,
    InstallDependenciesTool,
    ServerRegistry,
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
)

# Project Tools
from .project_tools import (
    create_project_tools,
    ProjectStructureTool,
    ListGeneratedFilesTool,
    CheckDuplicatesTool,
)

# Browser Tools
try:
    from .browser_tools import (
        create_browser_tools,
        BrowserManager,
        BrowserNavigateTool,
        BrowserScreenshotTool,
        BrowserGetConsoleTool,
        BrowserClickTool,
        BrowserFillTool,
        BrowserGetElementsTool,
        BrowserEvaluateTool,
        BrowserCloseTool,
    )
    BROWSER_TOOLS_AVAILABLE = True
except ImportError:
    BROWSER_TOOLS_AVAILABLE = False
    create_browser_tools = lambda *args, **kwargs: []

# Vision Tools
from .vision_tools import (
    create_vision_tools,
    AnalyzeScreenshotTool,
    CompareWithScreenshotTool,
    ExtractComponentsTool,
    DesignAnalysis,
)


def get_all_tools(output_dir: str = None, work_dir: str = None, include_browser: bool = True):
    """
    Get all available tools.
    
    Args:
        output_dir: Directory for file operations
        work_dir: Working directory for runtime operations
        include_browser: Include browser tools (requires Playwright)
        
    Returns:
        List of tool instances
    """
    tools = [
        # File tools
        ViewTool(output_dir=output_dir),
        StrReplaceEditorTool(output_dir=output_dir),
        WriteFileTool(output_dir=output_dir),
        GlobTool(output_dir=output_dir),
        
        # Code tools
        GrepTool(output_dir=output_dir),
        EditFileTool(output_dir=output_dir),
        LintTool(output_dir=output_dir),
        ThinkTool(),
        FinishTool(),
        
        # Analysis tools
        *create_analysis_tools(output_dir=output_dir),
        
        # Dependency tools
        *create_dependency_tools(output_dir=output_dir),
        
        # Runtime tools
        ExecuteBashTool(work_dir=work_dir),
        ExecuteIPythonTool(work_dir=work_dir),
        StartServerTool(work_dir=work_dir),
        StopServerTool(),
        ListServersTool(),
        GetServerLogsTool(),
        TestAPITool(),
        InstallDependenciesTool(work_dir=work_dir),
        
        # Docker tools
        *create_docker_tools(output_dir=output_dir),
        
        # Project tools
        *create_project_tools(output_dir=output_dir),
    ]
    
    # Browser tools (optional, requires Playwright)
    if include_browser and BROWSER_TOOLS_AVAILABLE:
        from pathlib import Path
        screenshot_dir = Path(output_dir) / "screenshots" if output_dir else None
        tools.extend(create_browser_tools(screenshot_dir))
    
    return tools


def get_vision_tools(llm_client=None) -> list:
    """Get vision tools for screenshot-based generation"""
    return create_vision_tools(llm_client)


def get_tool_params(tools=None, output_dir: str = None, work_dir: str = None):
    """
    Get tool parameters for LLM function calling.
    """
    if tools is None:
        tools = get_all_tools(output_dir=output_dir, work_dir=work_dir)
    
    return [tool.get_tool_param() for tool in tools]


__all__ = [
    # Path Utilities
    "resolve_path",
    "resolve_output_dir",
    "normalize_path_for_tracking",
    
    # File Tools
    "ViewTool",
    "StrReplaceEditorTool",
    "WriteFileTool",
    "GlobTool",
    "FileHistory",
    
    # Code Tools
    "GrepTool",
    "EditFileTool",
    "LintTool",
    "ThinkTool",
    "FinishTool",
    
    # Analysis Tools
    "create_analysis_tools",
    "FindDefinitionTool",
    "FindReferencesTool",
    "GetSymbolsTool",
    
    # Dependency Tools
    "create_dependency_tools",
    "CheckImportsTool",
    "MissingDependenciesTool",
    
    # Runtime Tools
    "ExecuteBashTool",
    "ExecuteIPythonTool",
    "StartServerTool",
    "StopServerTool",
    "ListServersTool",
    "GetServerLogsTool",
    "TestAPITool",
    "InstallDependenciesTool",
    "ServerRegistry",
    
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
    "BrowserNavigateTool",
    "BrowserScreenshotTool",
    "BrowserGetConsoleTool",
    "BrowserClickTool",
    "BrowserFillTool",
    "BrowserGetElementsTool",
    "BrowserEvaluateTool",
    "BrowserCloseTool",
    "BROWSER_TOOLS_AVAILABLE",
    
    # Vision Tools
    "create_vision_tools",
    "get_vision_tools",
    "AnalyzeScreenshotTool",
    "CompareWithScreenshotTool",
    "ExtractComponentsTool",
    "DesignAnalysis",
    
    # Helpers
    "get_all_tools",
    "get_tool_params",
]
