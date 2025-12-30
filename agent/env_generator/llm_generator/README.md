# LLM Generator - Multi-Agent Environment Code Generator

An AI-powered **multi-agent system** that automatically creates complete, runnable OpenEnv-compatible web environments through parallel collaborative development.

## 🏗️ Architecture Overview

```
llm_generator/
├── main.py                     # CLI entry point
├── multi_agent/                # ⭐ Multi-agent system
│   ├── orchestrator.py         # Central coordinator
│   ├── workspace_manager.py    # Per-agent file access control
│   ├── agents/
│   │   ├── base.py             # EnvGenAgent base class
│   │   ├── user_agent.py       # Requirements, testing, QA
│   │   ├── design_agent.py     # Architecture & specs
│   │   ├── database_agent.py   # Schema & data loading
│   │   ├── backend_agent.py    # API development
│   │   └── frontend_agent.py   # UI development
│   ├── prompts/                # Jinja2 templates per agent
│   │   ├── user_agent.j2
│   │   ├── design_agent.j2
│   │   └── code_agents.j2
│   └── tools.py                # Tool assignment per agent
│
├── tools/                      # Agent tools (~60 tools)
│   ├── file_tools.py           # read, write, edit, glob
│   ├── browser/                # Playwright browser automation
│   ├── docker_tools.py         # Docker operations
│   ├── debug_tools.py          # Cross-layer debugging
│   └── reasoning_debugger.py   # LLM-based debugging
│
├── checkpoint.py               # Progress persistence
├── context.py                  # Generation context (ports, etc.)
├── progress.py                 # Real-time event streaming
└── verification/               # Spec validation
    └── spec_validator.py
```

## 🤖 Multi-Agent System

### Agent Roles

| Agent | Role | Workspace | Key Tools |
|-------|------|-----------|-----------|
| **UserAgent** | PM/QA: Requirements, testing, issues | Full read | Browser, Docker, Vision |
| **DesignAgent** | Architect: Specs, contracts, structure | `design/` | File, Analysis |
| **DatabaseAgent** | DBA: Schema, migrations, data loading | `app/database/` | File, DataEngine |
| **BackendAgent** | Backend Dev: APIs, routes, services | `app/backend/` | File, Runtime |
| **FrontendAgent** | Frontend Dev: UI, components, styles | `app/frontend/` | File, Runtime |

### Communication Flow

```
                              ┌─────────────────┐
                              │   Orchestrator  │
                              │  (Event-driven) │
                              └────────┬────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
    ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
    │ UserAgent   │◄──────────►│ DesignAgent │◄──────────►│   CodeAgents│
    │             │   ask/tell │             │   ask/tell │   (DB/BE/FE)│
    │ • Refine    │            │ • README    │            │             │
    │ • Test      │            │ • API Spec  │            │ • Generate  │
    │ • Issues    │            │ • DB Spec   │            │ • Fix       │
    └─────────────┘            │ • UI Spec   │            └─────────────┘
                               └─────────────┘
```

### Agent Communication

Agents communicate via **MessageBus** with 3 methods:

```python
# Ask and wait for answer
schema = await self.ask("design", "What's the database schema?")

# Send notification (one-way)
await self.tell("frontend", "API ready for integration")

# Broadcast to all agents
await self.broadcast("Database migration complete")
```

Each agent knows its peers:
```python
# Get available agents
agents = self.get_available_agents()
# [{"id": "design", "name": "DesignAgent", "role": "..."}, ...]

# Check before communicating
if self.can_talk_to("backend"):
    await self.ask("backend", "What's the response format?")
```

## 🔄 Generation Workflow

### Phase 1: Design (Sequential)
```
User Requirements
      │
      ▼
┌─────────────┐     ┌─────────────┐
│  UserAgent  │────►│ DesignAgent │
│  (Refine)   │     │  (Specs)    │
└─────────────┘     └─────────────┘
                           │
                    ┌──────┼──────┐
                    ▼      ▼      ▼
              spec.api  spec.db  spec.ui
```

### Phase 2: Development (Parallel)
```
              Design Specs
                   │
      ┌────────────┼────────────┐
      ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Database │ │ Backend  │ │ Frontend │
│  Agent   │ │  Agent   │ │  Agent   │
│          │ │          │ │          │
│ • Schema │ │ • Routes │ │ • Pages  │
│ • Seeds  │ │ • Models │ │ • API    │
│ • Data*  │ │ • Auth   │ │ • State  │
└──────────┘ └──────────┘ └──────────┘
      │            │            │
      └────────────┼────────────┘
                   ▼
            Integration Ready
```

*DatabaseAgent can load real data from HuggingFace via DataEngine

### Phase 3: Verification & Fix Loop
```
┌─────────────────────────────────────────┐
│                                         │
│   ┌─────────────┐                       │
│   │  UserAgent  │                       │
│   │  (Testing)  │                       │
│   └──────┬──────┘                       │
│          │                              │
│          ▼                              │
│   ┌─────────────┐    Pass?              │
│   │   Issues    │───────────────► Done  │
│   └──────┬──────┘                       │
│          │ No                           │
│          ▼                              │
│   ┌──────────────────────────┐          │
│   │   Parallel Fix           │          │
│   │                          │          │
│   │  DB Issues → DatabaseAgent          │
│   │  BE Issues → BackendAgent │          │
│   │  FE Issues → FrontendAgent│          │
│   └──────────────────────────┘          │
│          │                              │
│          └──────────────────────────────┘
│                    (max N iterations)
└─────────────────────────────────────────┘
```

## 📦 DataEngine Integration

DatabaseAgent integrates with **DataEngine** to load real data from HuggingFace:

```python
# Automatic: Based on project description
# DatabaseAgent infers domain and finds matching datasets

# Manual: Load specific dataset
await db_agent.load_dataset(
    dataset_id="milistu/AMAZON-Products-2023",
    output_path="app/data/products.db",
    domain="e-commerce",
    max_records=5000
)
```

Supported domains:
- **e-commerce**: Products, categories, reviews
- **social-media**: Posts, users, comments
- **news**: Articles, authors
- **restaurant**: Menus, reviews
- **real-estate**: Listings, properties

## 🛠️ Tool Categories

| Category | Tools | Agents |
|----------|-------|--------|
| **File** | read_file, write_file, edit_file, glob | All |
| **Browser** | navigate, click, fill, screenshot | UserAgent |
| **Docker** | build, up, down, logs, exec | UserAgent |
| **Vision** | analyze_screenshot, compare_ui | UserAgent |
| **Runtime** | find_port, run_background, test_api | BE/FE |
| **Analysis** | analyze_spec, suggest_structure | Design |
| **Reasoning** | think, plan, finish | All |

## 🚀 Usage

### Basic Generation

```bash
python -m env_generator.llm_generator.main \
    --name jira \
    --description "Jira-like project management with kanban boards" \
    --model gpt-4.1
```

### With Different Providers

```bash
# Google Gemini
python -m env_generator.llm_generator.main \
    --name calendar \
    --description "Calendar app with events" \
    --provider google \
    --model gemini-2.0-flash-exp

# Anthropic Claude
python -m env_generator.llm_generator.main \
    --name shop \
    --description "E-commerce shop" \
    --provider anthropic \
    --model claude-sonnet-4-20250514
```

### Resume from Checkpoint

```bash
python -m env_generator.llm_generator.main \
    --name jira \
    --resume
```

## 📁 Output Structure

```
generated/jira/
├── design/
│   ├── README.md              # Project overview
│   ├── spec.api.json          # API contracts with response_key
│   ├── spec.database.json     # Database schema
│   └── spec.ui.json           # UI components
├── app/
│   ├── frontend/              # React + Vite
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── pages/
│   │   │   └── services/api.js
│   │   └── package.json
│   ├── backend/               # Express.js
│   │   ├── src/
│   │   │   ├── routes/
│   │   │   ├── models/
│   │   │   └── middleware/
│   │   └── package.json
│   ├── database/              # PostgreSQL
│   │   ├── init.sql
│   │   ├── seed.sql
│   │   └── Dockerfile
│   └── data/                  # Real data (if loaded)
│       └── products.db
├── docker/
│   └── docker-compose.yml
├── env/                       # OpenEnv adapter
└── .checkpoint.json           # Resume state
```

## ⚙️ CLI Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--name` | Project name | required |
| `--description` | Natural language description | required |
| `--provider` | LLM: openai, google, anthropic, azure | openai |
| `--model` | Model name | gpt-4.1 |
| `--output` | Output directory | generated/{name} |
| `--resume` | Resume from checkpoint | false |
| `--verbose` | Enable debug logging | false |

## 🔧 Key Features

### 1. Workspace Isolation
Each agent has restricted file access:
```python
# DatabaseAgent can only write to:
write_paths = ["app/database/"]

# But can read from:
read_paths = ["design/", "app/backend/", "app/frontend/"]
```

### 2. Dynamic Port Allocation
No hardcoded ports - agents find available ports:
```python
context.api_port = 8000    # Or next available
context.ui_port = 3000     # Or next available
```

### 3. Checkpointing
Generation progress is saved automatically:
```json
{
  "phases": {
    "design": {"status": "complete"},
    "database": {"status": "complete"},
    "backend": {"status": "in_progress"}
  },
  "files": {...}
}
```

### 4. Real-time Events
Progress streaming via EventEmitter:
```python
emitter.emit(EventType.PHASE_START, "Starting backend generation")
emitter.emit(EventType.FILE_CREATED, "Created routes/users.js")
emitter.emit(EventType.AGENT_MESSAGE, "BackendAgent: API ready")
```

### 5. Spec Validation
Design specs are validated before development:
```python
result = validate_specs("./design")
if result.has_errors:
    for issue in result.issues:
        print(f"{issue.severity}: {issue.message}")
```

## 🔍 Debug Tools

### Cross-Layer Debugger
```python
from tools.debug_tools import CrossLayerDebugger
debugger = CrossLayerDebugger()
trace = debugger.trace_error("invalid input syntax for uuid")
# Returns: origin=database, root_cause="route ordering issue"
```

### API Alignment Verifier
```python
from tools.debug_tools import APIAlignmentVerifier
verifier = APIAlignmentVerifier()
issues = verifier.verify_alignment(frontend_dir, backend_dir)
```

### Reasoning Debugger
```python
from tools.reasoning_debugger import ReasoningDebugger
debugger = ReasoningDebugger(llm_client=llm)
diagnosis = await debugger.debug_error(error, context)
```

## 🌐 Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `GOOGLE_API_KEY` | Google AI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |

## 📦 Dependencies

- Python 3.9+
- Node.js 18+ (frontend)
- Docker (containerization)
- Playwright (browser testing)
- PostgreSQL (database)
- huggingface_hub (DataEngine)
