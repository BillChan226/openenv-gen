# Environment Generator

A multi-agent system for generating OpenEnv-compatible environments, built on the AgentForge framework.

## Quick Start

```bash
# Set API key
export OPENAI_API_KEY=sk-...

# Generate a calendar app
cd /path/to/Agents/env_generator
python -m llm_generator.main --name calendar --domain calendar --description "A calendar app"
```

## Architecture

```
GeneratorOrchestrator (Coordinator)
    │
    ├── Phase: design    → env_spec.json
    ├── Phase: backend   → FastAPI (models, schemas, routers)
    ├── Phase: frontend  → React (pages, components, services)
    ├── Phase: openenv   → OpenEnv adapter
    └── Phase: docker    → Docker configuration
    
Each phase uses CodeGeneratorAgent with:
    THINK → PLAN → GENERATE → REFLECT → FIX (iterative)
```

## Key Features

### 1. Iterative Generation (Not One-Shot)

Unlike simple generators, each phase runs iteratively:

```
THINK    → Analyze what needs to be done
PLAN     → Break into steps, identify dependencies  
GENERATE → Create files one by one
REFLECT  → Check for errors, import issues
FIX      → If issues found, analyze and fix
(repeat until satisfied)
```

### 2. Tool-Augmented Generation

Agents have access to developer tools (like how I work):

| Tool | Description |
|------|-------------|
| `read_file` | Read existing files for context |
| `write_file` | Create new files |
| `grep` | Search for patterns in code |
| `search_replace` | Make targeted modifications |
| `lint` | Check code for errors |
| `syntax_check` | Verify syntax before writing |

### 3. Cross-Phase Consistency

The orchestrator verifies:
- Backend endpoints match frontend API calls
- Imports reference existing files
- Database models match schemas

## Directory Structure

```
env_generator/
├── __init__.py
├── README.md
├── generated/              # Output directory
└── llm_generator/          # Main generator module
    ├── __init__.py
    ├── main.py             # CLI entry point
    ├── context.py          # Shared generation context
    ├── agents/
    │   ├── code_agent.py   # CodeGeneratorAgent (THINK/PLAN/GENERATE/REFLECT/FIX)
    │   └── orchestrator.py # GeneratorOrchestrator (coordinates phases)
    └── tools/
        ├── file_tools.py   # read_file, write_file, list_dir
        └── code_tools.py   # grep, search_replace, lint, syntax_check
```

## Usage

### CLI

```bash
# Basic usage
python -m llm_generator.main --name myapp --domain custom

# With description
python -m llm_generator.main --name shop --domain ecommerce \
    --description "An e-commerce platform with products and orders"

# Verbose output
python -m llm_generator.main --name calendar --domain calendar --verbose

# Custom model
python -m llm_generator.main --name api --model gpt-4-turbo
```

### Python API

```python
import asyncio
from env_generator.llm_generator import GeneratorOrchestrator
from utils.config import AgentConfig, LLMConfig, LLMProvider

async def main():
    config = AgentConfig(
        agent_name="Generator",
        llm=LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
            api_key="sk-...",
        ),
    )
    
    orchestrator = GeneratorOrchestrator(config, output_dir=Path("./generated"))
    await orchestrator.initialize()
    
    result = await orchestrator.generate_environment(
        name="myapp",
        description="My application",
        domain_type="custom",
    )
    
    print(f"Generated {result['total_files']} files")

asyncio.run(main())
```

## Generated Output

```
generated/
└── calendar/
    ├── env_spec.json           # Environment specification
    ├── calendar_api/           # FastAPI backend
    │   ├── main.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── database.py
    │   ├── routers/
    │   │   └── auth.py
    │   ├── requirements.txt
    │   └── Dockerfile
    ├── calendar_ui/            # React frontend
    │   ├── package.json
    │   ├── src/
    │   │   ├── App.tsx
    │   │   ├── main.tsx
    │   │   ├── contexts/
    │   │   ├── pages/
    │   │   └── services/
    │   └── Dockerfile
    ├── openenv_adapter/        # OpenEnv integration
    │   ├── models.py
    │   └── server/
    │       └── environment.py
    ├── docker-compose.yml
    └── generation_result.json  # Generation report
```

## How It Works

### CodeGeneratorAgent

The core agent that generates code with thinking capabilities:

```python
class CodeGeneratorAgent(PlanningAgent):
    """
    Agent that generates code with:
    - think(): Analyze task before acting
    - plan_generation(): Create step-by-step plan
    - generate_file(): Generate with syntax verification
    - reflect_on_generation(): Check for issues
    - fix_issues(): Analyze and fix problems
    """
```

### GeneratorOrchestrator

Coordinates multiple phases:

```python
class GeneratorOrchestrator(PlanningAgent):
    PHASES = ["design", "backend", "frontend", "openenv", "docker"]
    
    async def generate_environment(self, name, description, domain_type):
        for phase in self.PHASES:
            result = await self._run_phase(phase)
            # Each phase: THINK → PLAN → GENERATE → REFLECT → FIX
```

## Based On

Built on the AgentForge framework (`utils/`):
- `BaseAgent` - Agent lifecycle management
- `PlanningAgent` - Planning and reasoning capabilities  
- `ReActEngine` - THINK-ACTION-OBSERVATION loop
- `ToolRegistry` - Tool management
- `LLM` - LLM client wrapper
