# LLM Generator - Architecture Deep Dive

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLI Entry (main.py)                            │
│  - Parse arguments                                                          │
│  - Initialize LLM config                                                    │
│  - Setup logging and events                                                 │
│  - Load/save memory                                                         │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GeneratorOrchestrator                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Phase Management                                                        ││
│  │  - design → backend → frontend → openenv                                ││
│  │  - Each phase: 3 iterations (GENERATE → VERIFY → FINAL)                 ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Shared Resources                                                        ││
│  │  - AgentMemory (short-term, long-term, working)                         ││
│  │  - GenerationContext (env name, description, output dir, files)         ││
│  │  - EventEmitter (real-time progress streaming)                          ││
│  │  - CheckpointManager (progress persistence)                             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CodeGeneratorAgent                                 │
│  ┌───────────────────┐  ┌────────────────┐  ┌─────────────────────────────┐ │
│  │    ReActEngine    │  │  ToolRegistry  │  │      Shared Memory          │ │
│  │  (Reasoning Loop) │  │   (30+ tools)  │  │  (Context across phases)    │ │
│  └───────────────────┘  └────────────────┘  └─────────────────────────────┘ │
│                                                                             │
│  Core Methods:                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ plan_phase_files()  - LLM decides what files to generate                ││
│  │ think_before_file() - Decide what context is needed                     ││
│  │ gather_context()    - Execute grep/read_file tools                      ││
│  │ generate_file()     - Create code with truncation handling              ││
│  │ reflect_on_file()   - Check for issues                                  ││
│  │ fix_issues()        - Apply targeted fixes                              ││
│  │ verify_planned()    - Ensure all files generated                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Tool Categories                                │
│  ┌────────────────────┐  ┌───────────────────┐  ┌────────────────────────┐  │
│  │    File Tools      │  │    Code Tools     │  │    Runtime Tools       │  │
│  │  - read_file       │  │  - grep           │  │  - install_deps        │  │
│  │  - write_file      │  │  - search_replace │  │  - start_server        │  │
│  │  - list_dir        │  │  - edit_lines     │  │  - stop_server         │  │
│  │  - file_exists     │  │  - insert_lines   │  │  - test_api            │  │
│  │  - list_generated  │  │  - edit_function  │  │  - get_server_logs     │  │
│  │  - update_plan     │  │  - lint           │  │  - quick_test          │  │
│  │                    │  │  - syntax_check   │  │  - should_test         │  │
│  └────────────────────┘  └───────────────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Phase Execution Flow

### 3-Iteration Model

Each phase runs through exactly 3 iterations:

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

### Issue Types & Fix Strategies

| Issue Type | Detection | Fix Strategy |
|------------|-----------|--------------|
| `IMPORT ERROR: ModuleNotFoundError` | Server fails to start | Convert absolute imports to relative imports |
| `MISSING FILE` | Import references non-existent file | Generate the missing file |
| `SYNTAX ERROR` | syntax_check fails | Regenerate file or apply targeted fix |
| `TRUNCATED` | Code appears incomplete | Continue generation with LLM |
| `JSON_FORMAT` | Single-line JSON | Reformat with proper indentation |
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

## Tool System

### Available Tools

#### File Tools (`file_tools.py`)
- `read_file(path, start_line?, end_line?)` - Read file content with optional line range
- `write_file(path, content)` - Create or overwrite file
- `list_dir(path)` - List directory contents
- `file_exists(path)` - Check if file exists
- `list_generated(phase?)` - List all generated files with summaries
- `update_plan(planned_files)` - Update current generation plan

#### Code Tools (`code_tools.py`)
- `grep(pattern, path)` - Search for regex pattern across files
- `search_replace(path, old_string, new_string)` - Replace text in file
- `edit_lines(path, start_line, end_line, new_content)` - Replace specific line range
- `insert_lines(path, after_line, content)` - Insert content at line position
- `edit_function(path, function_name, new_code)` - Replace entire function/class
- `lint(path)` - Run linter on file
- `syntax_check(code, language)` - Verify code syntax

#### Runtime Tools (`runtime_tools.py`)
- `run_command(command, cwd)` - Execute shell command
- `install_dependencies(project_type, cwd)` - Install pip/npm packages
- `start_server(server_name, command, cwd, port)` - Start background server
- `stop_server(server_name)` - Stop running server
- `list_servers()` - List all running servers
- `test_api(method, url, json_data?)` - Test HTTP endpoint
- `get_server_logs(server_name)` - Get server output
- `should_test(file_path)` - Ask LLM if testing is appropriate
- `quick_test(backend_dir)` - Automated backend test cycle

## Memory System

### Components

- **ShortTermMemory**: FIFO buffer for recent context (default: 100 items)
- **LongTermMemory**: Persistent storage with importance-based eviction
- **WorkingMemory**: Current task context and reasoning steps
- **SemanticMemory**: (Optional) Vector embeddings for similarity search

### Usage

```python
# Store fix pattern
shared_memory.store(
    MemoryItem(
        content="Fixed import error by using relative imports",
        metadata={"phase": "backend", "type": "fix_pattern"},
        importance=0.8
    )
)

# Recall relevant context
memories = shared_memory.recall(
    query="import errors",
    top_k=3
)
```

## Event System

### Event Types

- `PHASE_START`, `PHASE_END` - Phase lifecycle
- `FILE_START`, `FILE_END` - File generation lifecycle
- `THINK_START`, `THINK_RESULT` - Agent thinking events
- `FILE_PLAN` - File planning complete
- `TOOL_CALL`, `TOOL_RESULT` - Tool invocations
- `VERIFICATION_PASS`, `VERIFICATION_ERROR` - Verification results
- `ISSUE_FOUND`, `FIX_APPLIED` - Issue detection and fixing

### Real-time Log Format

```
[21:22:09] 🤔 THINK: ITERATION 1/3
[21:22:09] 📋 PLAN: 8 files for phase
[21:22:30] START: calendar_api/main.py
[21:22:45] 🔧 TOOL: grep pattern='APIRouter'
[21:22:46] DONE: calendar_api/main.py (45 lines, good)
```

## Checkpoint System

### Checkpoint Structure

```json
{
  "name": "calendar",
  "timestamp": "2024-01-01T12:00:00",
  "current_phase": "backend",
  "phases": {
    "design": {"status": "complete", "files": ["env_spec.json"]},
    "backend": {"status": "in_progress", "planned_files": [...]}
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

### Resume Logic

On resume:
1. Load checkpoint file
2. Validate all "complete" files exist and have valid content
3. Invalidate files that fail validation
4. Continue from current phase and file

## Code Quality Safeguards

### 1. Line Number Stripping

LLMs sometimes output code with embedded line numbers:

```
   1|from fastapi import FastAPI
   2|app = FastAPI()
```

The generator automatically strips these prefixes.

### 2. JSON Format Fixing

Python dict syntax is converted to valid JSON:
- `'key'` → `"key"` (single to double quotes)
- `None` → `null`
- `True` → `true`
- `False` → `false`
- Trailing commas removed

### 3. Truncation Detection & Continuation

If code appears truncated (unbalanced brackets, ends with `...`), the generator prompts the LLM to continue from where it stopped.

### 4. Smart File Truncation for Context

When reading large files for context, the generator keeps:
- First 30 lines (imports, constants)
- Key signatures from middle
- Last 20 lines (main logic)

## CLI Usage

### Basic Generation

```bash
python -m llm_generator.main \
    --name calendar \
    --description "A calendar app" \
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
    --resume \
    --verbose
```

### CLI Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--name` | Environment name | Required |
| `--description` | Natural language description | Required |
| `--domain` | Domain type | "web_gui" |
| `--output` | Output directory | "generated" |
| `--model` | LLM model | "gpt-5.1" |
| `--test` | Enable runtime testing | False |
| `--resume` | Resume from checkpoint | False |
| `--verbose` | Detailed logging | False |

## Generated Output Structure

```
generated/calendar/
├── env_spec.json              # Environment specification
├── calendar_api/              # FastAPI backend
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── requirements.txt
│   └── routers/
│       ├── __init__.py
│       └── auth.py
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

