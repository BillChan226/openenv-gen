# LLM Generator - Intelligent Environment Code Generator

An AI-powered code generation system that automatically creates complete, runnable OpenEnv-compatible environments using Large Language Models.

## Architecture Overview

```
llm_generator/
├── main.py                    # CLI entry point
├── __init__.py                # Package exports
│
├── agents/                    # Agent implementations
│   ├── orchestrator.py        # Main coordinator (phases, memory)
│   └── code_agent.py          # Code generation agent
│
├── controller/                # Execution control (OpenHands-inspired)
│   ├── agent_controller.py    # Main agent loop
│   └── stuck.py               # Stuck detection (5 scenarios)
│
├── runtime/                   # Code execution environment
│   ├── bash.py                # Persistent bash shell
│   ├── ipython.py             # Python/IPython execution
│   └── manager.py             # Runtime manager
│
├── events/                    # Agent communication (Action/Observation)
│   ├── action.py              # Agent actions
│   └── observation.py         # Execution results
│
├── progress.py                # Progress streaming (UI, logs)
│   └── EventEmitter           # Real-time event system
│
├── tools/                     # Agent tools (LiteLLM format)
│   ├── file_tools.py          # view, str_replace_editor, write_file, glob
│   ├── code_tools.py          # grep, lint, search_code, think, finish
│   └── runtime_tools.py       # execute_bash, execute_ipython, start_server
│
├── skills/                    # IPython callable functions
│   ├── file_ops.py            # open_file, goto_line, scroll_*, edit_*
│   └── search_ops.py          # search_dir, search_file, find_file, grep
│
├── prompts/                   # Jinja2 prompt templates
│   ├── system_prompt.j2       # System prompt
│   ├── think.j2               # Thinking prompt
│   ├── generate_file.j2       # File generation
│   ├── fix_issue.j2           # Issue fixing
│   └── ... (18 more)
│
├── snippets/                  # Code reference snippets
│   ├── backend.py             # FastAPI patterns
│   ├── frontend.py            # React/TypeScript patterns
│   └── openenv.py             # OpenEnv adapter patterns
│
├── context.py                 # Generation context (shared state)
├── checkpoint.py              # Progress persistence (resume)
├── parallel.py                # Parallel file generation
└── runtime_verify.py          # Runtime testing
```

## Key Components

### 1. Event Systems (Two Types)

| System | Purpose | Location |
|--------|---------|----------|
| **Progress Events** | UI updates, logging, streaming | `progress.py` |
| **Agent Events** | Action/Observation communication | `events/` |

```python
# Progress events (for UI/logs)
from llm_generator.progress import EventEmitter, EventType
emitter.emit(EventType.FILE_START, "Generating main.py")

# Agent events (internal communication)
from llm_generator.events import CmdRunAction, CmdOutputObservation
action = CmdRunAction(command="python test.py")
observation = CmdOutputObservation(output="OK", exit_code=0)
```

### 2. Controller (OpenHands-inspired)

```python
from llm_generator.controller import AgentController, StuckDetector

# StuckDetector detects 5 scenarios:
# 1. Identical action repeated
# 2. Same file edit failed multiple times
# 3. Agent monologuing (no progress)
# 4. Hard stuck (repeated think without action)
# 5. Soft stuck (low progress score)
```

### 3. Runtime (Code Execution)

```python
from llm_generator.runtime import RuntimeManager

runtime = RuntimeManager(work_dir="/path/to/project")
await runtime.initialize()

# Execute bash command
result = await runtime.execute_bash("pip install fastapi")

# Execute Python code
result = await runtime.execute_python("print('Hello')")

# Start a server
await runtime.start_server("api", "uvicorn main:app", port=8000)
```

### 4. Tools (LiteLLM Format)

All tools follow LiteLLM standard format:

```python
{
    "type": "function",
    "function": {
        "name": "view",
        "description": "Read file content",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer"},
                "end_line": {"type": "integer"}
            },
            "required": ["path"]
        }
    }
}
```

### 5. Skills (IPython Functions)

Skills are Python functions available in the IPython environment:

```python
# In IPython, agents can call:
open_file("/path/to/file.py")      # Open and display file
search_dir("pattern", "/dir")      # Search directory
find_file("*.py", "/dir")          # Find files by pattern
edit_file_by_replace(path, old, new)  # Edit file
```

### 6. Prompts (Jinja2 Templates)

21 Jinja2 templates for flexible prompt management:

```
prompts/
├── system_prompt.j2        # Agent system prompt
├── think.j2                # think() method
├── think_before_file.j2    # Pre-file analysis
├── generate_file.j2        # Code generation
├── reflect_on_file.j2      # Post-file reflection
├── fix_issue.j2            # Issue fixing
├── fix_syntax.j2           # Syntax error fix
├── retry_fix.j2            # Retry failed fix
├── continue_code.j2        # Continue truncated code
├── generate_json.j2        # JSON generation
├── fix_json.j2             # JSON error fix
├── generate_test.j2        # Test generation
├── decide_action.j2        # Next action decision
├── final_assessment.j2     # Final file assessment
├── continue_exploration.j2 # Continue exploring
├── explore_fix.j2          # Explore how to fix
├── complete_truncated.j2   # Complete truncated file
├── plan_phase.j2           # Phase planning
├── reflection.j2           # Generation reflection
├── memory_summary.j2       # Memory summarization
└── fix_issues.j2           # Batch issue fixing
```

## Generation Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    GENERATION PHASES                         │
├─────────────────────────────────────────────────────────────┤
│  1. DESIGN   → env_spec.json (entities, features, APIs)     │
│  2. BACKEND  → FastAPI backend (models, routers, auth)      │
│  3. FRONTEND → React/TypeScript UI (pages, components)      │
│  4. OPENENV  → OpenEnv adapter (environment, server)        │
│  5. DOCKER   → docker-compose.yml, Dockerfiles              │
└─────────────────────────────────────────────────────────────┘

Each phase runs with:
┌─────────────────────────────────────────────────────────────┐
│  THINK → PLAN → GENERATE → REFLECT → FIX                    │
│                                                             │
│  Per-file loop:                                             │
│    1. think_before_file() - What context needed?            │
│    2. gather_context() - Read files, grep patterns          │
│    3. generate_file() - Create code                         │
│    4. reflect_on_file() - Check for issues                  │
│    5. fix_issues() - Auto-repair problems                   │
└─────────────────────────────────────────────────────────────┘
```

## Usage

```bash
# Basic generation
python -m llm_generator.main \
    --name calendar \
    --description "A calendar app with events and authentication"

# With testing enabled
python -m llm_generator.main \
    --name calendar \
    --description "A calendar app" \
    --test \
    --verbose

# Resume from checkpoint
python -m llm_generator.main \
    --name calendar \
    --resume
```

## CLI Arguments

| Argument | Description |
|----------|-------------|
| `--name` | Environment name (e.g., "calendar") |
| `--description` | Natural language description |
| `--domain` | Domain type: "web_gui", "cli", "game", etc. |
| `--output` | Output directory (default: "generated") |
| `--test` | Enable runtime testing |
| `--resume` | Resume from checkpoint |
| `--verbose` | Enable detailed logging |
| `--model` | LLM model (default: "gpt-5.1") |

## Output Structure

```
generated/calendar/
├── env_spec.json              # Environment specification
├── calendar_api/              # FastAPI backend
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── requirements.txt
│   └── routers/
├── calendar_ui/               # React frontend
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
└── openenv_adapter/           # OpenEnv integration
    ├── models.py
    └── server/
```

## Memory System

- **Short-term**: Recent context (FIFO buffer)
- **Long-term**: Fix patterns, important files
- **Working**: Current task context

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |

## Dependencies

- Python 3.9+
- OpenAI API (GPT-4, GPT-4o, or GPT-5.1)
- FastAPI, Uvicorn (backend)
- Node.js, npm (frontend)
