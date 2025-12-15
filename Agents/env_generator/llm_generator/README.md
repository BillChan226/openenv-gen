# LLM Generator - Intelligent Environment Code Generator

An AI-powered code generation system that automatically creates complete, runnable OpenEnv-compatible environments using Large Language Models.

## Overview

The LLM Generator is a multi-agent system that generates full-stack applications (backend API + frontend UI + OpenEnv adapter) from natural language descriptions. Unlike simple template-based generators, it uses an iterative approach similar to how a human developer works:

1. **Think** - Understand the requirements
2. **Plan** - Decide what files to generate
3. **Generate** - Create code file by file
4. **Reflect** - Check for errors and issues
5. **Fix** - Automatically repair problems
6. **Test** - Run the code to verify it works

## Architecture

```
llm_generator/
├── main.py                 # CLI entry point
├── __init__.py
├── context.py              # Generation context management
├── events.py               # Real-time event streaming
├── checkpoint.py           # Progress persistence for resume
├── snippets/               # Code templates library
│   ├── __init__.py
│   ├── backend_snippets.py
│   ├── frontend_snippets.py
│   └── openenv_snippets.py
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py     # Main orchestrator (coordinates phases)
│   └── code_agent.py       # Code generation agent
└── tools/
    ├── __init__.py
    ├── file_tools.py       # File system operations
    ├── code_tools.py       # Code manipulation (grep, search_replace, lint)
    └── runtime_tools.py    # Server management, API testing
```

## Key Components

### 1. GeneratorOrchestrator (`orchestrator.py`)

The main coordinator that manages the generation process across multiple phases:

- **Design Phase**: Generate `env_spec.json` with environment specification
- **Backend Phase**: Generate FastAPI backend with authentication
- **Frontend Phase**: Generate React/TypeScript frontend
- **OpenEnv Phase**: Generate OpenEnv adapter for RL integration

Each phase runs through **3 iterations**:
1. **GENERATE**: Create all planned files
2. **VERIFY & FIX**: Run tests, identify issues, apply fixes
3. **FINAL CHECK**: Ensure everything works

### 2. CodeGeneratorAgent (`code_agent.py`)

The intelligent agent that generates individual files with:

- **Dynamic Planning**: LLM decides which files to generate (not hardcoded)
- **Context Gathering**: Uses `grep` and `read_file` to understand existing code
- **Per-File Intelligence**: Thinks before generating each file
- **Reflection**: Checks generated code for issues
- **Self-Fixing**: Automatically repairs detected problems

### 3. Tools

The agent has access to various tools:

#### File Tools
- `read_file(path, start_line?, end_line?)` - Read files with optional line range
- `write_file(path, content)` - Create/overwrite files
- `list_dir(path)` - List directory contents
- `file_exists(path)` - Check if file exists
- `list_generated(phase?)` - List all generated files with summaries

#### Code Tools
- `grep(pattern, path)` - Search for patterns across files
- `search_replace(path, old, new)` - Replace text in files
- `edit_lines(path, start, end, content)` - Replace specific line range
- `insert_lines(path, after_line, content)` - Insert lines at position
- `edit_function(path, name, new_code)` - Replace entire function/class
- `lint(path)` - Check code for errors
- `syntax_check(code, language)` - Verify syntax before writing

#### Runtime Tools
- `install_dependencies(project_type, cwd)` - Install pip/npm packages
- `start_server(name, command, cwd, port)` - Start backend/frontend server
- `stop_server(name)` - Stop a running server
- `test_api(method, url, json_data?)` - Test API endpoints
- `get_server_logs(name)` - Get server output for debugging
- `quick_test(backend_dir)` - Automated backend test cycle

## Generation Flow

### Phase Execution (3 Iterations)

```
┌─────────────────────────────────────────────────────────────┐
│                     PHASE: backend                          │
├─────────────────────────────────────────────────────────────┤
│ ITERATION 1: GENERATE                                       │
│   ├── Think: Analyze phase requirements                     │
│   ├── Plan: LLM decides files to generate                   │
│   └── Generate: Create each file with per-file intelligence │
│       ├── think_before_file() - What context needed?        │
│       ├── gather_context_dynamically() - Read/grep files    │
│       ├── generate_file() - Create the code                 │
│       └── reflect_on_file() - Check for issues              │
├─────────────────────────────────────────────────────────────┤
│ ITERATION 2: VERIFY & FIX                                   │
│   ├── Check for missing planned files                       │
│   ├── Run runtime tests (start server, test API)            │
│   ├── Collect all issues                                    │
│   ├── Call fix_issues() to repair                           │
│   └── Re-test after fixes                                   │
├─────────────────────────────────────────────────────────────┤
│ ITERATION 3: FINAL CHECK                                    │
│   ├── Handle any remaining issues from iteration 2          │
│   ├── Run final tests                                       │
│   └── Mark phase complete (success/failure)                 │
└─────────────────────────────────────────────────────────────┘
```

### Per-File Generation Flow

```
┌──────────────────────────────────────────────────────────┐
│              Generating: calendar_api/main.py            │
├──────────────────────────────────────────────────────────┤
│ 1. think_before_file()                                   │
│    └── LLM decides: "I need to read database.py and     │
│        schemas.py, grep for 'APIRouter' patterns"        │
├──────────────────────────────────────────────────────────┤
│ 2. gather_context_dynamically()                          │
│    ├── read_file("calendar_api/database.py")            │
│    ├── read_file("calendar_api/schemas.py")             │
│    └── grep("APIRouter", ".")                           │
├──────────────────────────────────────────────────────────┤
│ 3. generate_file()                                       │
│    ├── Build prompt with context                         │
│    ├── Call LLM to generate code                         │
│    ├── Strip line numbers if present                     │
│    ├── Fix JSON formatting if needed                     │
│    └── Write file                                        │
├──────────────────────────────────────────────────────────┤
│ 4. reflect_on_file()                                     │
│    ├── Run syntax_check()                               │
│    ├── Run lint()                                       │
│    ├── LLM analyzes code quality                        │
│    └── Return issues list                               │
├──────────────────────────────────────────────────────────┤
│ 5. fix_issues() (if issues found)                        │
│    ├── Parse issue type (IMPORT, SYNTAX, MISSING, etc.) │
│    ├── Apply appropriate fix strategy                    │
│    └── Re-validate after fix                            │
└──────────────────────────────────────────────────────────┘
```

## Issue Detection & Auto-Fixing

The system can detect and fix various issues:

### Issue Types & Fix Strategies

| Issue Type | Detection | Fix Strategy |
|------------|-----------|--------------|
| `IMPORT ERROR: ModuleNotFoundError` | Server fails to start | Convert absolute imports to relative imports |
| `MISSING FILE` | Import references non-existent file | Generate the missing file |
| `SYNTAX ERROR` | syntax_check fails | Regenerate file or apply targeted fix |
| `TRUNCATED` | Code appears incomplete | Continue generation with LLM |
| `JSON FORMATTING` | Single-line JSON | Reformat with proper indentation |
| `INCOMPLETE` | Contains TODO/FIXME markers | Regenerate with complete implementation |

### Example: Import Error Fix

```python
# Detected issue:
"IMPORT ERROR: ModuleNotFoundError: No module named 'calendar_api'. 
This usually means the imports need to be changed to relative imports."

# Fix applied:
# Before: from calendar_api.database import init_db
# After:  from .database import init_db
```

## Runtime Testing

The system includes automated testing capabilities:

1. **Dependency Installation**: `pip install -r requirements.txt`
2. **Server Startup**: `uvicorn main:app --host 0.0.0.0 --port 8008`
3. **API Testing**: 
   - Health check: `GET /health`
   - Registration: `POST /auth/register`
   - Login: `POST /auth/token`
4. **Error Analysis**: Parse server logs for specific error types
5. **Automatic Cleanup**: Stop servers after testing

## Usage

### Basic Usage

```bash
cd Agents/env_generator
python -m llm_generator.main \
    --name calendar \
    --description "A calendar app with events and authentication" \
    --verbose
```

### With Runtime Testing

```bash
python -m llm_generator.main \
    --name calendar \
    --description "A calendar app" \
    --test \
    --verbose
```

### Resume from Checkpoint

```bash
python -m llm_generator.main \
    --name calendar \
    --description "A calendar app" \
    --resume \
    --verbose
```

### CLI Arguments

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

Generated environment structure:

```
generated/calendar/
├── env_spec.json              # Environment specification
├── calendar_api/              # FastAPI backend
│   ├── __init__.py
│   ├── main.py                # FastAPI app entry point
│   ├── database.py            # Database configuration
│   ├── models.py              # SQLAlchemy models
│   ├── schemas.py             # Pydantic schemas
│   ├── requirements.txt       # Python dependencies
│   └── routers/
│       ├── __init__.py
│       └── auth.py            # Authentication endpoints
├── calendar_ui/               # React frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── contexts/
│       ├── pages/
│       └── services/
└── openenv_adapter/           # OpenEnv integration
    ├── models.py
    ├── requirements.txt
    └── server/
        ├── environment.py
        └── main.py
```

## Real-time Logging

The system provides two log files:

1. **`{name}_realtime.log`**: Human-readable event stream
   ```
   [21:22:09] 🤔 THINK: ITERATION 1/3
   [21:22:09] 📋 PLAN: 8 files for phase
   [21:22:30] START: calendar_api/main.py
   [21:22:45] 🔧 TOOL: grep pattern='APIRouter'
   [21:22:46] DONE: calendar_api/main.py (45 lines, good)
   ```

2. **`{name}_generation.log`**: JSON event log for programmatic analysis

## Memory System

The generator uses a shared memory system across phases:

- **Short-term**: Recent context (FIFO buffer)
- **Long-term**: Important patterns and fixes
- **Working**: Current task context

This enables:
- Learning from fixes applied in earlier phases
- Maintaining consistency across generated files
- Recalling relevant patterns for similar files

## Checkpointing

Progress is automatically saved to `.checkpoint.json`:

```json
{
  "name": "calendar",
  "current_phase": "backend",
  "phases": {
    "design": {"status": "complete", "files": ["env_spec.json"]},
    "backend": {"status": "in_progress", "files": ["main.py", "database.py"]}
  },
  "files": {
    "calendar_api/main.py": {
      "status": "complete",
      "content_hash": "abc123...",
      "phase": "backend"
    }
  }
}
```

## Known Limitations

1. **Line Numbers in Output**: LLMs sometimes output code with embedded line numbers. The system now strips these automatically.

2. **Import Resolution**: When running from subdirectories, absolute imports may fail. The system detects this and converts to relative imports.

3. **Server Port Conflicts**: Orphan processes from previous runs can cause port conflicts. The system now checks and cleans up before testing.

4. **tsconfig.node.json**: Special handling added for TypeScript configuration files to ensure valid output.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for GPT models |

## Dependencies

- Python 3.9+
- OpenAI API (GPT-4, GPT-4o, or GPT-5.1)
- FastAPI, Uvicorn (for backend)
- Node.js, npm (for frontend)

## Contributing

The system is designed to be extensible:

1. **Add new tools**: Create in `tools/` and register in `code_agent.py`
2. **Add code snippets**: Add to `snippets/` for common patterns
3. **Customize phases**: Modify `_get_phase_spec()` in `orchestrator.py`

## License

[Your License Here]
