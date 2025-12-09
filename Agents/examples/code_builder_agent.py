"""
Code Builder Agent - An intelligent agent that can build code projects

Features:
- Planning: Breaks down coding tasks into steps
- Reasoning: Uses ReAct for problem-solving
- Memory: Remembers context and past actions
- Tools: File operations and code execution

Usage:
    python code_builder_agent.py
    
    Or import and use:
    from code_builder_agent import CodeBuilderAgent
    
    agent = CodeBuilderAgent(api_key="your-openai-key")
    await agent.initialize()
    await agent.build("Create a Python calculator with add, subtract, multiply, divide")
"""

import asyncio
import subprocess
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (
    # Agent
    PlanningAgent,
    AgentConfig,
    AgentRole,
    # Config
    LLMConfig,
    LLMProvider,
    ExecutionConfig,
    MemoryConfig,
    # Planning
    PlanStep,
    # Tools
    BaseTool,
    ToolDefinition,
    ToolParameter,
    ToolResult,
    ToolCategory,
    tool,
    # Messages
    TaskMessage,
    ResultMessage,
    create_task_message,
)


# ============================================================
# Tool Definitions
# ============================================================

class CreateFileTool(BaseTool):
    """Tool to create a new file"""
    
    def __init__(self, workspace: str = "./workspace"):
        super().__init__()
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="create_file",
            description="Create a new file at the specified path. Creates parent directories if needed.",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="File path relative to workspace (e.g., 'src/main.py')",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    param_type=str,
                    description="Initial content of the file (optional)",
                    required=False,
                    default="",
                ),
            ],
            returns="Success message with file path",
            examples=[
                {"input": {"path": "hello.py", "content": "print('Hello')"}, "output": "Created: hello.py"},
            ],
        )
    
    async def execute(self, path: str, content: str = "", **kwargs) -> ToolResult:
        try:
            file_path = self.workspace / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return ToolResult.ok(f"Created file: {path}")
        except Exception as e:
            return ToolResult.fail(f"Failed to create file: {e}")


class WriteFileTool(BaseTool):
    """Tool to write/update file content"""
    
    def __init__(self, workspace: str = "./workspace"):
        super().__init__()
        self.workspace = Path(workspace)
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write_file",
            description="Write or overwrite content to an existing file",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="File path relative to workspace",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    param_type=str,
                    description="Content to write to the file",
                    required=True,
                ),
                ToolParameter(
                    name="append",
                    param_type=bool,
                    description="If True, append to file instead of overwriting",
                    required=False,
                    default=False,
                ),
            ],
            returns="Success message",
        )
    
    async def execute(self, path: str, content: str, append: bool = False, **kwargs) -> ToolResult:
        try:
            file_path = self.workspace / path
            
            if not file_path.exists():
                return ToolResult.fail(f"File not found: {path}. Use create_file first.")
            
            mode = "a" if append else "w"
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(content)
            
            action = "Appended to" if append else "Wrote to"
            return ToolResult.ok(f"{action} file: {path}")
        except Exception as e:
            return ToolResult.fail(f"Failed to write file: {e}")


class ReadFileTool(BaseTool):
    """Tool to read file content"""
    
    def __init__(self, workspace: str = "./workspace"):
        super().__init__()
        self.workspace = Path(workspace)
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_file",
            description="Read content from a file",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="File path relative to workspace",
                    required=True,
                ),
            ],
            returns="File content as string",
        )
    
    async def execute(self, path: str, **kwargs) -> ToolResult:
        try:
            file_path = self.workspace / path
            
            if not file_path.exists():
                return ToolResult.fail(f"File not found: {path}")
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            return ToolResult.ok(content)
        except Exception as e:
            return ToolResult.fail(f"Failed to read file: {e}")


class DeleteFileTool(BaseTool):
    """Tool to delete a file"""
    
    def __init__(self, workspace: str = "./workspace"):
        super().__init__()
        self.workspace = Path(workspace)
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="delete_file",
            description="Delete a file from the workspace",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="File path relative to workspace",
                    required=True,
                ),
            ],
            returns="Success message",
        )
    
    async def execute(self, path: str, **kwargs) -> ToolResult:
        try:
            file_path = self.workspace / path
            
            if not file_path.exists():
                return ToolResult.fail(f"File not found: {path}")
            
            file_path.unlink()
            return ToolResult.ok(f"Deleted file: {path}")
        except Exception as e:
            return ToolResult.fail(f"Failed to delete file: {e}")


class RunCodeTool(BaseTool):
    """Tool to run Python code"""
    
    def __init__(self, workspace: str = "./workspace", timeout: int = 30):
        super().__init__()
        self.workspace = Path(workspace)
        self.timeout = timeout
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="run_code",
            description="Execute a Python file or code snippet",
            category=ToolCategory.CODE,
            parameters=[
                ToolParameter(
                    name="path",
                    param_type=str,
                    description="Python file path to run (relative to workspace), or None to run code directly",
                    required=False,
                    default=None,
                ),
                ToolParameter(
                    name="code",
                    param_type=str,
                    description="Python code to execute directly (used if path is None)",
                    required=False,
                    default=None,
                ),
            ],
            returns="Execution output (stdout + stderr)",
        )
    
    async def execute(self, path: str = None, code: str = None, **kwargs) -> ToolResult:
        try:
            if path:
                # Run file
                file_path = self.workspace / path
                if not file_path.exists():
                    return ToolResult.fail(f"File not found: {path}")
                
                result = subprocess.run(
                    [sys.executable, str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=str(self.workspace),
                )
            elif code:
                # Run code directly
                result = subprocess.run(
                    [sys.executable, "-c", code],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=str(self.workspace),
                )
            else:
                return ToolResult.fail("Either 'path' or 'code' must be provided")
            
            output = ""
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
            if result.returncode != 0:
                output += f"\nReturn code: {result.returncode}"
            
            if not output.strip():
                output = "Code executed successfully (no output)"
            
            return ToolResult.ok(output.strip())
            
        except subprocess.TimeoutExpired:
            return ToolResult.fail(f"Execution timed out after {self.timeout} seconds")
        except Exception as e:
            return ToolResult.fail(f"Execution error: {e}")


class ListFilesTool(BaseTool):
    """Tool to list files in workspace"""
    
    def __init__(self, workspace: str = "./workspace"):
        super().__init__()
        self.workspace = Path(workspace)
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_files",
            description="List all files in the workspace or a subdirectory",
            category=ToolCategory.FILE_SYSTEM,
            parameters=[
                ToolParameter(
                    name="directory",
                    param_type=str,
                    description="Directory path relative to workspace (default: root)",
                    required=False,
                    default=".",
                ),
            ],
            returns="List of files and directories",
        )
    
    async def execute(self, directory: str = ".", **kwargs) -> ToolResult:
        try:
            dir_path = self.workspace / directory
            
            if not dir_path.exists():
                return ToolResult.fail(f"Directory not found: {directory}")
            
            items = []
            for item in sorted(dir_path.iterdir()):
                prefix = "[DIR] " if item.is_dir() else "[FILE]"
                rel_path = item.relative_to(self.workspace)
                items.append(f"{prefix} {rel_path}")
            
            if not items:
                return ToolResult.ok("Directory is empty")
            
            return ToolResult.ok("\n".join(items))
        except Exception as e:
            return ToolResult.fail(f"Failed to list files: {e}")


# ============================================================
# Code Builder Agent
# ============================================================

class CodeBuilderAgent(PlanningAgent):
    """
    Intelligent code builder agent
    
    Capabilities:
    - Plans coding tasks step by step
    - Uses reasoning to solve problems
    - Remembers context and past actions
    - Can create, read, write, delete files
    - Can execute Python code
    """
    
    def __init__(
        self,
        api_key: str = None,
        model: str = "gpt-4",  # Change to "gpt-5" when available
        workspace: str = "./workspace",
    ):
        # Create configuration
        config = AgentConfig(
            agent_id="code_builder",
            agent_name="CodeBuilder",
            agent_type="code_builder",
            description="An intelligent agent that builds code projects",
            llm=LLMConfig(
                provider=LLMProvider.OPENAI,
                model_name=model,
                api_key=api_key or os.getenv("OPENAI_API_KEY"),
                temperature=0.3,  # Lower temperature for code generation
                max_tokens=4096,
            ),
            execution=ExecutionConfig(
                max_concurrent_tasks=1,
                task_timeout=300,
                max_retries=2,
            ),
            memory=MemoryConfig(
                short_term_memory_size=20,
                long_term_memory_enabled=True,
            ),
        )
        
        super().__init__(config, role=AgentRole.SPECIALIST, enable_reasoning=True)
        
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
    
    async def on_initialize(self) -> None:
        """Initialize with coding tools"""
        await super().on_initialize()
        
        # Register tools
        self.register_tool(CreateFileTool(str(self.workspace)))
        self.register_tool(WriteFileTool(str(self.workspace)))
        self.register_tool(ReadFileTool(str(self.workspace)))
        self.register_tool(DeleteFileTool(str(self.workspace)))
        self.register_tool(RunCodeTool(str(self.workspace)))
        self.register_tool(ListFilesTool(str(self.workspace)))
        
        # Customize planner for coding tasks
        self.planner.system_prompt = """You are an expert software developer and code architect.

When creating a plan:
1. Break down coding tasks into clear, actionable steps
2. Consider file structure and organization
3. Include testing steps when appropriate
4. Think about error handling
5. Use the available tools effectively

Available tools:
- create_file: Create new files
- write_file: Update existing files
- read_file: Read file contents
- delete_file: Remove files
- run_code: Execute Python code
- list_files: List workspace contents

Always ensure code is complete and runnable."""
        
        # Customize reasoner for coding
        self.reasoner.system_prompt = """You are an expert Python developer solving coding problems.

Follow the ReAct pattern:
1. Thought: Analyze what needs to be done
2. Action: Use a tool (create_file, write_file, read_file, run_code, etc.)
3. Observation: See the result
4. Repeat until the task is complete

When writing code:
- Write clean, well-documented code
- Include proper error handling
- Follow Python best practices
- Test your code when possible

When you have completed the task, use Action: finish"""
        
        self._logger.info(f"CodeBuilder initialized with workspace: {self.workspace}")
    
    async def execute_step(self, step: PlanStep) -> Any:
        """Execute a plan step using tools or reasoning"""
        action = step.action.lower()
        
        # Direct tool execution
        tool = self._tools.get(action)
        if tool:
            kwargs = step.action_input if isinstance(step.action_input, dict) else {}
            result = await tool(**kwargs)
            return result.data if result.success else f"Error: {result.error_message}"
        
        # For complex steps, use reasoning
        if self._reasoner:
            context = f"""
Current task step: {step.description}
Expected output: {step.expected_output}
Workspace: {self.workspace}
"""
            result = await self._reasoner.run(
                task=step.description,
                context=context,
            )
            return result.answer if result.success else f"Reasoning failed: {result.error}"
        
        return f"Executed: {step.description}"
    
    async def build(
        self,
        task: str,
        constraints: list[str] = None,
        context: str = None,
    ) -> dict:
        """
        Build code based on a task description
        
        Args:
            task: What to build (e.g., "Create a Python calculator")
            constraints: Requirements (e.g., ["Use classes", "Add tests"])
            context: Additional context
            
        Returns:
            Build result with plan details
        """
        default_constraints = [
            "Write clean, readable Python code",
            "Include docstrings and comments",
            "Handle potential errors",
        ]
        
        all_constraints = (constraints or []) + default_constraints
        
        print(f"\n{'='*60}")
        print(f"🔨 CodeBuilder Agent")
        print(f"{'='*60}")
        print(f"Task: {task}")
        print(f"Workspace: {self.workspace}")
        print(f"{'='*60}\n")
        
        # Create plan
        print("📋 Creating plan...")
        plan = await self.create_plan(
            task=task,
            constraints=all_constraints,
            context=context,
        )
        
        print(f"\n{self.print_plan()}\n")
        
        # Execute plan
        print("🚀 Executing plan...\n")
        success = await self.execute_plan()
        
        # Print final status
        print(f"\n{'='*60}")
        if success:
            print("✅ Build completed successfully!")
        else:
            print("❌ Build failed")
        
        status = self.get_plan_status()
        print(f"Progress: {status['progress_percent']}")
        print(f"Steps completed: {status['completed_steps']}/{status['total_steps']}")
        print(f"{'='*60}\n")
        
        # List created files
        print("📁 Files in workspace:")
        list_tool = self._tools.get("list_files")
        if list_tool:
            result = await list_tool()
            print(result.data if result.success else "Could not list files")
        
        return {
            "success": success,
            "plan": plan.to_dict(),
            "status": status,
            "workspace": str(self.workspace),
        }
    
    async def quick_code(self, description: str) -> str:
        """
        Quickly generate and run code without full planning
        
        Args:
            description: What the code should do
            
        Returns:
            Generated code and execution result
        """
        if not self._reasoner:
            return "Reasoner not available"
        
        result = await self._reasoner.run(
            task=f"Write Python code that: {description}. Then create the file and run it.",
        )
        
        return result.answer if result.success else f"Error: {result.error}"


# ============================================================
# Main - Demo
# ============================================================

async def main():
    """Demo the CodeBuilder agent"""
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  Warning: OPENAI_API_KEY not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        print("\nRunning in demo mode (will fail on LLM calls)...\n")
    
    # Create agent
    agent = CodeBuilderAgent(
        api_key=api_key,
        model="gpt-4",  # Change to gpt-4-turbo or gpt-5 when available
        workspace="./workspace",
    )
    
    # Initialize
    await agent.initialize()
    
    print("\n" + "="*60)
    print("CodeBuilder Agent Demo")
    print("="*60)
    print("\nThis agent can:")
    print("  📋 Plan coding tasks")
    print("  🧠 Reason through problems")
    print("  💾 Remember context")
    print("  📁 Create/read/write/delete files")
    print("  ▶️  Execute Python code")
    print("\nTools available:")
    for tool in agent.tools.get_all():
        print(f"  - {tool.name}: {tool.description[:50]}...")
    print("="*60 + "\n")
    
    # Example task
    task = """
    Create a simple Python calculator with the following features:
    1. A Calculator class with methods for add, subtract, multiply, divide
    2. Error handling for division by zero
    3. A main.py file that demonstrates usage
    4. Run the code to verify it works
    """
    
    # Build
    result = await agent.build(
        task=task,
        constraints=[
            "Use a class-based design",
            "Include type hints",
            "Add a __main__ block",
        ],
    )
    
    # Show memory stats
    print("\n📊 Agent Memory Stats:")
    print(agent.memory.stats())
    
    # Show plan history
    print(f"\n📜 Plan History: {len(agent.plan_history)} plans executed")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())

