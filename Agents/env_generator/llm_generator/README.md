# LLM Generator

A multi-agent system for generating OpenEnv-compatible environments, built on the AgentForge framework.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    GeneratorOrchestrator                        │
│              (Coordinator - manages phases)                     │
└───────────────┬──────────────┬──────────────┬─────────────────┘
                │              │              │
        ┌───────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐
        │BackendAgent  │ │Frontend  │ │OpenEnv     │
        │              │ │Agent     │ │Agent       │
        └───────┬──────┘ └────┬─────┘ └─────┬──────┘
                │              │              │
                └──────────────┴──────────────┘
                               │
              ┌────────────────▼────────────────┐
              │       CodeGeneratorAgent        │
              │   (Base class with tools)       │
              │                                 │
              │  Tools:                         │
              │  - read_file   - write_file     │
              │  - grep        - search_replace │
              │  - lint        - syntax_check   │
              └─────────────────────────────────┘
```

## Key Features

### 1. Iterative Generation (Not One-Shot)

Unlike simple generators, this system generates code iteratively:

```
THINK → PLAN → GENERATE → REFLECT → FIX → (repeat if needed)
```

Each phase:
1. **THINK**: Analyze what needs to be done
2. **PLAN**: Break down into steps, identify dependencies
3. **GENERATE**: Create files one by one
4. **REFLECT**: Check for syntax errors, import issues
5. **FIX**: If issues found, analyze and fix

### 2. Tool-Augmented Generation

Agents have access to developer tools:

| Tool | Description | Use Case |
|------|-------------|----------|
| `read_file` | Read file contents | Understand existing code |
| `write_file` | Create/overwrite files | Generate new code |
| `grep` | Search for patterns | Find definitions, usages |
| `search_replace` | Targeted modifications | Fix specific issues |
| `lint` | Check code quality | Verify syntax |
| `syntax_check` | Quick syntax verification | Before writing |

### 3. Cross-Phase Consistency

The orchestrator verifies that:
- Backend endpoints match frontend API calls
- Imports reference existing files
- Database models match schemas

### 4. Self-Healing

When issues are detected:
1. Agent analyzes the error
2. Proposes a fix
3. Applies the fix
4. Re-verifies

## Usage

```bash
# Set API key
export OPENAI_API_KEY=sk-...

# Generate a calendar app
python -m llm_generator.main --name calendar --domain calendar --description "A calendar app"

# Generate with verbose logging
python -m llm_generator.main --name shop --domain ecommerce --verbose
```

## Directory Structure

```
llm_generator/
├── __init__.py
├── README.md
├── main.py                 # CLI entry point
├── context.py              # Shared generation context
├── agents/
│   ├── __init__.py
│   ├── code_agent.py       # Base code generator agent
│   └── orchestrator.py     # Multi-agent coordinator
└── tools/
    ├── __init__.py
    ├── file_tools.py       # File operations
    └── code_tools.py       # Code operations
```

## How It Mimics Human Developers

### Thinking Before Acting
```python
# Agent thinks about the task
analysis = await agent.think(
    task="Generate authentication endpoints",
    context="We need JWT-based auth with login/register"
)
```

### Using Tools to Understand Context
```python
# Agent reads existing files to understand structure
result = await agent.call_tool("read_file", path="models.py")
```

### Iterative Refinement
```python
# Agent reflects on generated code
issues = await agent.reflect_on_generation(generated_files)

# If issues found, fix them
if issues:
    fixes = await agent.fix_issues(issues)
```

### Cross-File Consistency
```python
# Orchestrator verifies across phases
cross_issues = await orchestrator._verify_cross_phase()
```

## Extending

### Add a New Tool

```python
from utils.tool import BaseTool, ToolDefinition, ToolParameter, ToolResult

class MyTool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="my_tool",
            description="Does something useful",
            parameters=[
                ToolParameter(name="input", param_type=str, required=True),
            ],
        )
    
    async def execute(self, input: str, **kwargs) -> ToolResult:
        # Do something
        return ToolResult.ok(result)
```

### Add a New Phase

```python
# In orchestrator.py
PHASES = [
    "design",
    "backend",
    "frontend",
    "openenv",
    "docker",
    "my_new_phase",  # Add here
]

# Define phase spec
def _get_phase_spec(self, phase: str):
    if phase == "my_new_phase":
        return {
            "description": "My new phase",
            "files": [
                {"path": "my_file.py", "purpose": "...", "instructions": "..."},
            ],
        }
```

## Comparison with Old Generator

| Feature | Old (llm_generate.py) | New (llm_generator/) |
|---------|----------------------|---------------------|
| Structure | Single 2500+ line file | Modular, separated concerns |
| Generation | One-shot per file | Iterative with reflection |
| Tools | None | Full tool support (grep, etc.) |
| Planning | Hardcoded phases | Dynamic, agent-driven |
| Fixing | Limited auto-fix | Full analysis + fix loop |
| Extensibility | Difficult | Easy to add tools/phases |

## Based On

Built on the AgentForge framework (`utils/`):
- `BaseAgent` - Agent lifecycle management
- `PlanningAgent` - Planning and reasoning capabilities
- `ReActEngine` - THINK-ACTION-OBSERVATION loop
- `ToolRegistry` - Tool management
- `LLM` - LLM client wrapper

