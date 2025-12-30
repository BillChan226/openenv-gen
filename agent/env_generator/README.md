# Environment Generator

A **multi-agent system** for generating complete, runnable web environments through parallel collaborative development.

## Quick Start

```bash
# Set API key
export OPENAI_API_KEY=sk-...

# Generate a Jira-like app
cd /path/to/agent/env_generator
python -m llm_generator.main \
    --name jira \
    --description "Jira-like project management with kanban boards"
```

## Architecture

### Multi-Agent System

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (Event-driven)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
   ┌──────────────────────────┼──────────────────────────┐
   │                          │                          │
   ▼                          ▼                          ▼

╔═══════════════════════════════════════════════════════════════╗
║                    PHASE 1: DESIGN (Sequential)                ║
║  UserAgent ──refine──► DesignAgent ──specs──► spec.*.json     ║
╚═══════════════════════════════════════════════════════════════╝
                              │
╔═══════════════════════════════════════════════════════════════╗
║                 PHASE 2: DEVELOPMENT (Parallel)                ║
║      ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          ║
║      │  Database   │ │   Backend   │ │  Frontend   │          ║
║      │   Agent     │ │   Agent     │ │   Agent     │          ║
║      └─────────────┘ └─────────────┘ └─────────────┘          ║
╚═══════════════════════════════════════════════════════════════╝
                              │
╔═══════════════════════════════════════════════════════════════╗
║                 PHASE 3: VERIFICATION & FIX LOOP               ║
║  UserAgent(test) → Issues → Parallel Fix → Verify → Done      ║
╚═══════════════════════════════════════════════════════════════╝
```

### 5 Specialized Agents

| Agent | Role | Workspace | Key Tools |
|-------|------|-----------|-----------|
| **UserAgent** | PM/QA: Requirements, testing, issues | Full read | Browser, Docker, Vision |
| **DesignAgent** | Architect: Specs, contracts | `design/` | File, Analysis |
| **DatabaseAgent** | DBA: Schema, migrations, data | `app/database/` | File, DataEngine |
| **BackendAgent** | Backend Dev: APIs, routes | `app/backend/` | File, Runtime |
| **FrontendAgent** | Frontend Dev: UI, components | `app/frontend/` | File, Runtime |

### Inter-Agent Communication

Agents communicate in real-time via MessageBus:

```python
# Ask and wait for answer
schema = await self.ask("design", "What's the database schema?")

# Send notification
await self.tell("frontend", "API ready for integration")

# Broadcast to all
await self.broadcast("Database migration complete")
```

## Key Features

### 1. Parallel Development

Database, Backend, and Frontend agents work **simultaneously**, reducing generation time by ~3x.

### 2. Workspace Isolation

Each agent has restricted write access:
- DatabaseAgent → `app/database/`
- BackendAgent → `app/backend/`
- FrontendAgent → `app/frontend/`

### 3. Dynamic Port Allocation

No hardcoded ports - agents find available ports automatically:
```python
context.api_port = 8000    # Or next available
context.ui_port = 3000     # Or next available
```

### 4. Real Data Loading (DataEngine)

DatabaseAgent can load real data from HuggingFace:
```python
# Automatic based on project description
await db_agent._load_real_data(schema)

# Manual
await db_agent.load_dataset("milistu/AMAZON-Products-2023", "products.db")
```

### 5. Checkpoint & Resume

Generation progress is saved automatically:
```bash
# Resume interrupted generation
python -m llm_generator.main --name jira --resume
```

## Directory Structure

```
env_generator/
├── llm_generator/
│   ├── main.py                 # CLI entry point
│   ├── multi_agent/            # ⭐ Multi-agent system
│   │   ├── orchestrator.py     # Event-driven coordinator
│   │   ├── workspace_manager.py # File access control
│   │   ├── tools.py            # Tool assignment
│   │   ├── agents/
│   │   │   ├── base.py         # EnvGenAgent base class
│   │   │   ├── user_agent.py
│   │   │   ├── design_agent.py
│   │   │   ├── database_agent.py
│   │   │   ├── backend_agent.py
│   │   │   └── frontend_agent.py
│   │   └── prompts/            # Jinja2 templates
│   │       ├── user_agent.j2
│   │       ├── design_agent.j2
│   │       └── code_agents.j2
│   ├── tools/                  # ~60 tools
│   │   ├── file_tools.py
│   │   ├── browser/
│   │   ├── docker_tools.py
│   │   └── ...
│   ├── checkpoint.py           # Save/resume
│   ├── context.py              # Shared state
│   └── progress.py             # Event streaming
└── README.md
```

## Usage

### CLI

```bash
# Basic generation
python -m llm_generator.main \
    --name jira \
    --description "Jira-like project management"

# With specific provider
python -m llm_generator.main \
    --name shop \
    --description "E-commerce platform" \
    --provider google \
    --model gemini-2.0-flash-exp

# Resume from checkpoint
python -m llm_generator.main --name jira --resume

# Verbose output
python -m llm_generator.main --name app --verbose
```

### Python API

```python
import asyncio
from pathlib import Path
from llm_generator.multi_agent import Orchestrator
from utils.config import LLMConfig, LLMProvider

async def main():
    llm_config = LLMConfig(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4o",
        api_key="sk-...",
    )
    
    orchestrator = Orchestrator(
        llm_config=llm_config,
        output_dir=Path("./generated/myapp"),
        verbose=True,
    )
    
    result = await orchestrator.run(
        goal="Create a project management tool like Jira",
        requirements=["Kanban boards", "Issue tracking", "User authentication"],
    )
    
    print(f"Success: {result.success}")
    print(f"Files generated: {len(result.phases_completed)}")

asyncio.run(main())
```

## Generated Output

```
generated/jira/
├── design/
│   ├── README.md              # Project overview
│   ├── spec.api.json          # API contracts (with response_key)
│   ├── spec.database.json     # Database schema
│   └── spec.ui.json           # UI components
├── app/
│   ├── frontend/              # React + Vite
│   │   ├── src/
│   │   │   ├── pages/
│   │   │   ├── components/
│   │   │   └── services/api.js
│   │   └── package.json
│   ├── backend/               # Express.js
│   │   ├── routes/
│   │   ├── middleware/
│   │   └── server.js
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

## Built On

Built on the AgentForge framework (`utils/`):
- `BaseAgent` - Agent lifecycle management
- `MessageBus` - Inter-agent communication
- `LLM` - Multi-provider LLM client
- `ToolRegistry` - Tool management
- `PromptManager` - Jinja2 prompt templates
