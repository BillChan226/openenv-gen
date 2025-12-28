# LLM Generator - Intelligent Environment Code Generator

An AI-powered dual-agent system that automatically creates complete, runnable OpenEnv-compatible web environments.

## Architecture Overview

```
llm_generator/
├── main.py                     # CLI entry point
├── __init__.py                 # Package exports
├── _paths.py                   # Centralized path configuration
├── workspace.py                # Workspace path management
│
├── agents/                     # Dual-agent system
│   ├── coordinator.py          # Orchestrates User↔Code agent interaction
│   ├── user_agent.py           # Plans, verifies, creates issues (PM/QA role)
│   └── code_agent.py           # Generates code, fixes issues (Developer role)
│
├── memory/                     # Memory systems
│   ├── generator_memory.py     # Short/Long-term + condenser memory
│   └── memory_bank.py          # Project documentation (Cursor-style)
│
├── runtime/                    # Code execution
│   ├── bash.py                 # Persistent bash shell
│   ├── ipython.py              # Python execution
│   └── manager.py              # Runtime manager
│
├── tools/                      # Agent tools (~60 tools)
│   ├── _base.py                # Common imports and utilities
│   ├── file_tools.py           # view, write_file, str_replace_editor, glob
│   ├── code_tools.py           # grep, lint, think, plan, finish
│   ├── browser_tools.py        # Browser automation (Playwright)
│   ├── vision_tools.py         # Screenshot analysis (multimodal)
│   ├── docker_tools.py         # Docker operations
│   ├── debug_tools.py          # Cross-layer error tracing
│   └── reasoning_debugger.py   # LLM-based debugging
│
├── prompts/                    # Jinja2 templates
│   ├── code/                   # Code Agent prompts
│   │   ├── system.j2
│   │   ├── execute_task.j2
│   │   └── fix_issue.j2
│   ├── user/                   # User Agent prompts
│   │   ├── system.j2
│   │   ├── plan_tasks.j2
│   │   └── verify_result.j2
│   └── vision/                 # Vision prompts
│
├── specs/                      # Project structure specs
│   └── project_structure.py    # Phases, structure, validation
│
├── verification/               # Verification modules
│   ├── api_verifier.py
│   ├── browser_verifier.py
│   └── full_verifier.py
│
├── checkpoint.py               # Progress persistence
├── context.py                  # Generation context
├── progress.py                 # Event streaming
└── docker_tester.py            # Docker-based testing
```

## Dual-Agent System

```
┌─────────────────────────────────────────────────────────────────────┐
│                         COORDINATOR                                  │
│                                                                     │
│  Orchestrates phases: design → database → backend → frontend →      │
│                       integration → env → docker                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   │                   ▼
┌──────────────────┐          │          ┌──────────────────┐
│   USER AGENT     │◄─────────┴─────────►│   CODE AGENT     │
│                  │                      │                  │
│ - Plan tasks     │    Task/Issue       │ - Generate code  │
│ - Verify results │◄───────────────────►│ - Fix issues     │
│ - Create issues  │    Review/Help      │ - Execute tests  │
│ - Select refs    │                      │ - Plan files     │
└──────────────────┘                      └──────────────────┘
```

### User Agent (PM/QA Role)
- Plans tasks based on project goal
- Selects reference images for design guidance
- Verifies generated code meets requirements
- Creates issues for Code Agent to fix
- Reviews Code Agent's plans

### Code Agent (Developer Role)
- Generates code files using tools
- Executes bash commands for testing
- Fixes issues reported by User Agent
- Can ask User Agent for clarification
- Uses memory bank for context

## Tool Categories

| Category | Tools | Purpose |
|----------|-------|---------|
| **File** | view, write_file, str_replace_editor, glob, delete_file | File operations |
| **Code** | grep, lint, think, plan, finish | Code analysis |
| **Runtime** | execute_bash, start_server, test_api | Execution |
| **Docker** | docker_build, docker_up, docker_logs | Containers |
| **Browser** | browser_navigate, browser_click, browser_screenshot | UI testing |
| **Vision** | analyze_image, compare_with_screenshot | Design analysis |
| **Debug** | CrossLayerDebugger, ReasoningDebugger | Error tracing |

## Generation Phases

| Phase | Output | Description |
|-------|--------|-------------|
| **design** | `design/spec.*.json` | API contracts, UI specs, project structure |
| **database** | `app/database/init/*.sql` | Schema and seed data |
| **backend** | `app/backend/src/**` | Express.js API |
| **frontend** | `app/frontend/src/**` | React frontend |
| **integration** | (verification) | End-to-end testing |
| **env** | `env/**` | OpenEnv adapter |
| **docker** | `docker/*.yml` | Docker configuration |

## Memory Systems

### 1. Generator Memory (Short/Long-term)
- **Short-term**: Recent tool calls, errors (FIFO)
- **Long-term**: Fix patterns, important files
- **Condenser**: LLM-based summarization when context grows

### 2. Memory Bank (Project Documentation)
- `memory-bank/project_brief.md` - High-level goal
- `memory-bank/tech_context.md` - Technology decisions
- `memory-bank/system_patterns.md` - Code patterns
- `memory-bank/progress.md` - What's done/pending
- `memory-bank/active_context.md` - Current focus

## Usage

```bash
# Basic generation
python -m env_generator.llm_generator.main \
    --name jira \
    --description "Jira-like project management with kanban boards" \
    --model gpt-4.1

# With Google Gemini
python -m env_generator.llm_generator.main \
    --name calendar \
    --description "Calendar app with events" \
    --provider google \
    --model gemini-2.0-flash-exp

# Resume from checkpoint
python -m env_generator.llm_generator.main \
    --name jira \
    --resume
```

## CLI Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--name` | Project name | required |
| `--description` | Natural language description | required |
| `--provider` | LLM provider: openai, google, anthropic, azure | openai |
| `--model` | Model name | gpt-4.1 |
| `--output` | Output directory | generated/{name} |
| `--resume` | Resume from checkpoint | false |
| `--verbose` | Enable debug logging | false |

## Output Structure

```
generated/jira/
├── design/
│   ├── spec.api.json          # API contracts
│   ├── spec.project.json      # Business logic
│   └── spec.ui.json           # UI components
├── app/
│   ├── frontend/              # React + Vite
│   ├── backend/               # Express.js
│   └── database/              # PostgreSQL
├── env/                       # OpenEnv adapter
├── docker/                    # Docker configs
├── memory-bank/               # Project docs
└── screenshots/               # Reference images
```

## Debug Tools

### Cross-Layer Debugger
Pattern-based error tracing across frontend → backend → database:
```python
from tools.debug_tools import CrossLayerDebugger
debugger = CrossLayerDebugger()
trace = debugger.trace_error("invalid input syntax for type uuid")
# Returns: origin=database, root_cause="route ordering issue"
```

### API Alignment Verifier
Validates frontend API calls match backend routes:
```python
from tools.debug_tools import APIAlignmentVerifier
verifier = APIAlignmentVerifier()
issues = verifier.verify_alignment(frontend_dir, backend_dir)
```

### Reasoning Debugger
LLM-based chain-of-thought debugging for complex issues:
```python
from tools.reasoning_debugger import ReasoningDebugger
debugger = ReasoningDebugger(llm_client=llm)
diagnosis = await debugger.debug_error(error, context)
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `GOOGLE_API_KEY` | Google AI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GOOGLE_CSE_API_KEY` | Google Custom Search API key |
| `GOOGLE_CSE_CX` | Google Custom Search Engine ID |

## Dependencies

- Python 3.9+
- Node.js 18+ (for frontend)
- Docker (for containerization)
- Playwright (for browser testing)
- PostgreSQL (for database)
