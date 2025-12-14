# OpenEnv Generator Multi-Agent System

A multi-agent system for automatically generating OpenEnv-compatible execution environments with web GUI support.

## Overview

This system uses multiple specialized AI agents to generate complete, production-ready environments that conform to the OpenEnv specification. The most complex use case is generating web GUI environments (like Google Calendar), which includes:

- Backend API (FastAPI + SQLAlchemy)
- Frontend UI (React)
- Database (SQLite/PostgreSQL)
- Docker orchestration
- OpenEnv adapter for RL training

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EnvGenerator Orchestrator                             │
│                    (Coordinator Agent - Main Controller)                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
           ▼                        ▼                        ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   Phase 1: Design   │  │  Phase 2: Backend   │  │  Phase 3: Frontend  │
│                     │  │                     │  │                     │
│ • EnvDesignerAgent  │  │ • SchemaDesigner    │  │ • UIDesignerAgent   │
│ • RequirementDoc    │  │ • DatabaseBuilder   │  │ • ComponentBuilder  │
│   Agent             │  │ • APIBuilderAgent   │  │ • StyleBuilderAgent │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │     Phase 4: Integration        │
                    │                                 │
                    │ • DockerComposerAgent           │
                    │ • OpenEnvAdapterAgent           │
                    │ • ValidatorAgent                │
                    └─────────────────────────────────┘
```

## Input Sources

The system supports three input modes for environment generation:

1. **User Description**: Natural language description of the desired environment
2. **Agent Design**: Agent autonomously designs based on domain type
3. **Data-Driven**: Agent infers environment structure from sample data

## Generated Repository Structure

Each generated environment follows this standardized structure:

```
{env_name}/
├── README.md                      # Environment documentation
├── openenv.yaml                   # OpenEnv manifest
├── docker-compose.yml             # Full stack orchestration
├── .env.example                   # Environment variables template
├── .gitignore
│
├── spec/                          # Phase 1 outputs (Design Artifacts)
│   ├── environment_spec.yaml      # Environment specification
│   ├── data_schema.yaml           # Data model definitions
│   ├── api_spec.yaml              # OpenAPI spec
│   └── ui_wireframe.md            # UI component structure
│
├── {env_name}_api/                # Phase 2 outputs (Backend)
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry
│   ├── models.py                  # SQLAlchemy models
│   ├── schemas.py                 # Pydantic schemas
│   ├── database.py                # DB connection
│   ├── auth.py                    # Authentication
│   ├── routers/                   # API route modules
│   │   ├── __init__.py
│   │   └── {resource}.py          # Per-resource routers
│   ├── services/                  # Business logic
│   │   ├── __init__.py
│   │   └── {service}.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
│
├── {env_name}_ui/                 # Phase 3 outputs (Frontend)
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.ico
│   ├── src/
│   │   ├── index.js
│   │   ├── App.js
│   │   ├── App.css
│   │   ├── api.js                 # API client
│   │   ├── components/            # React components
│   │   │   ├── {Component}.js
│   │   │   └── {Component}.css
│   │   └── pages/                 # Page components
│   │       └── {Page}.js
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
│
├── openenv_adapter/               # Phase 4 outputs (OpenEnv Integration)
│   ├── __init__.py
│   ├── models.py                  # Action, Observation, State
│   ├── client.py                  # HTTPEnvClient implementation
│   ├── server/
│   │   ├── __init__.py
│   │   ├── app.py                 # OpenEnv HTTP server
│   │   ├── environment.py         # Environment implementation
│   │   └── Dockerfile
│   ├── openenv.yaml
│   └── pyproject.toml
│
├── data/                          # Persistent data
│   └── .gitkeep
│
├── init_examples/                 # Example initialization data
│   └── basic_scenario.json
│
└── tests/                         # Test suite
    ├── test_api.py
    ├── test_ui.py
    └── test_openenv.py
```

## Workflow Phases

### Phase 1: Environment Design

**Agents:**
- `EnvDesignerAgent`: Analyzes requirements and designs environment structure
- `RequirementDocAgent`: Generates detailed specifications

**Inputs:**
| Input | Type | Description |
|-------|------|-------------|
| `user_description` | `string \| null` | User-provided description |
| `reference_data` | `json \| null` | Sample data for inference |
| `reference_ui` | `image \| null` | UI screenshot reference |
| `domain_type` | `enum` | calendar, ecommerce, social, custom |

**Outputs:**
| File | Description |
|------|-------------|
| `spec/environment_spec.yaml` | Environment specification with entities, roles, features |
| `spec/data_schema.yaml` | Database schema definition |
| `spec/api_spec.yaml` | OpenAPI 3.0 specification |
| `spec/ui_wireframe.md` | UI component structure |

**environment_spec.yaml Schema:**
```yaml
name: string
description: string
domain: string
entities:
  - name: string
    description: string
    attributes: list
    relationships: list
user_roles:
  - name: string
    permissions: list
core_features:
  - name: string
    description: string
    user_stories: list
```

**data_schema.yaml Schema:**
```yaml
entities:
  - name: string
    table_name: string
    fields:
      - name: string
        type: string
        nullable: bool
        default: any
        constraints: list
    relationships:
      - type: one-to-many | many-to-many
        target: string
        foreign_key: string
```

### Phase 2: Backend Generation

**Agents:**
- `SchemaDesignerAgent`: Generates SQLAlchemy models and Pydantic schemas
- `DatabaseBuilderAgent`: Creates database connection and migrations
- `APIBuilderAgent`: Generates FastAPI routers and business logic

**Inputs:**
- `spec/data_schema.yaml`
- `spec/api_spec.yaml`
- `spec/environment_spec.yaml`

**Outputs:**
| File | Description |
|------|-------------|
| `{env}_api/models.py` | SQLAlchemy ORM models |
| `{env}_api/schemas.py` | Pydantic request/response schemas |
| `{env}_api/database.py` | Database connection setup |
| `{env}_api/auth.py` | Authentication logic |
| `{env}_api/main.py` | FastAPI application entry |
| `{env}_api/routers/*.py` | API route handlers |
| `{env}_api/services/*.py` | Business logic services |
| `{env}_api/Dockerfile` | Container definition |

**Workflow:**
1. `SchemaDesignerAgent` generates models.py and schemas.py from data_schema.yaml
2. `DatabaseBuilderAgent` generates database.py and auth.py
3. `APIBuilderAgent` generates main.py, routers, and services from api_spec.yaml

### Phase 3: Frontend Generation

**Agents:**
- `UIDesignerAgent`: Designs component hierarchy and styling
- `ComponentBuilderAgent`: Generates React components with API integration
- `StyleBuilderAgent`: Creates CSS styles

**Inputs:**
- `spec/ui_wireframe.md`
- `spec/api_spec.yaml`
- `spec/environment_spec.yaml`
- `reference_ui` (optional image)

**Outputs:**
| File | Description |
|------|-------------|
| `{env}_ui/src/App.js` | Main application component |
| `{env}_ui/src/api.js` | API client functions |
| `{env}_ui/src/components/*.js` | Reusable React components |
| `{env}_ui/src/components/*.css` | Component styles |
| `{env}_ui/src/pages/*.js` | Page-level components |
| `{env}_ui/package.json` | NPM dependencies |
| `{env}_ui/Dockerfile` | Container definition |
| `{env}_ui/nginx.conf` | Production server config |

**Workflow:**
1. `UIDesignerAgent` analyzes wireframe and creates component_tree.json, style_guide.yaml
2. `ComponentBuilderAgent` generates React components with hooks and API integration
3. `StyleBuilderAgent` creates CSS styles matching the design guide

### Phase 4: Integration

**Agents:**
- `DockerComposerAgent`: Creates Docker orchestration files
- `OpenEnvAdapterAgent`: Generates OpenEnv-compatible wrapper
- `ValidatorAgent`: Validates and tests the generated environment

**Inputs:**
- All Phase 2 & 3 outputs
- `spec/environment_spec.yaml`

**Outputs:**
| File | Description |
|------|-------------|
| `docker-compose.yml` | Multi-container orchestration |
| `.env.example` | Environment variables template |
| `openenv_adapter/models.py` | Action, Observation, State dataclasses |
| `openenv_adapter/client.py` | HTTPEnvClient implementation |
| `openenv_adapter/server/environment.py` | Environment implementation |
| `openenv_adapter/server/app.py` | OpenEnv HTTP server |
| `README.md` | Generated documentation |
| `tests/*` | Test suite |

**OpenEnv Adapter Structure:**

```python
# models.py - OpenEnv type definitions
@dataclass(kw_only=True)
class {EnvName}Action(Action):
    action_type: str  # "create", "update", "delete", "query"
    resource: str     # "event", "user", "item"
    params: Dict[str, Any] = None

@dataclass(kw_only=True)
class {EnvName}Observation(Observation):
    success: bool = True
    data: Any = None
    error_message: Optional[str] = None
    available_actions: List[str] = None

@dataclass
class {EnvName}State(State):
    current_user: Optional[str] = None
    current_page: str = "home"
    session_data: Dict[str, Any] = None
```

**Validation Checklist:**
- [ ] Docker build succeeds
- [ ] API health check passes
- [ ] UI loads correctly
- [ ] OpenEnv reset/step/state endpoints work
- [ ] All tests pass

## Agent Definitions

### Base Agent Classes

All agents extend from the AgentForge framework:

```python
from utils import PlanningAgent, AgentConfig, LLMConfig
```

### Orchestrator Agent

```python
class EnvGeneratorOrchestrator(PlanningAgent):
    """
    Main coordinator for environment generation.
    Manages the 4-phase workflow and agent communication.
    """
    
    async def generate_environment(
        self,
        name: str,
        description: str = None,
        reference_data: dict = None,
        reference_ui: str = None,
        domain_type: str = "custom",
        output_dir: str = "./generated_envs",
    ) -> dict:
        """Main entry point for environment generation."""
        pass
```

### Design Phase Agents

```python
class EnvDesignerAgent(PlanningAgent):
    """Analyzes requirements and designs environment structure."""
    pass

class RequirementDocAgent(PlanningAgent):
    """Generates detailed specifications from environment design."""
    pass
```

### Backend Phase Agents

```python
class SchemaDesignerAgent(PlanningAgent):
    """Generates SQLAlchemy models and Pydantic schemas."""
    pass

class DatabaseBuilderAgent(PlanningAgent):
    """Creates database connection and auth modules."""
    pass

class APIBuilderAgent(PlanningAgent):
    """Generates FastAPI routers and business logic."""
    pass
```

### Frontend Phase Agents

```python
class UIDesignerAgent(PlanningAgent):
    """Designs component hierarchy and styling."""
    pass

class ComponentBuilderAgent(PlanningAgent):
    """Generates React components with API integration."""
    pass

class StyleBuilderAgent(PlanningAgent):
    """Creates CSS styles matching the design."""
    pass
```

### Integration Phase Agents

```python
class DockerComposerAgent(PlanningAgent):
    """Creates Docker orchestration files."""
    pass

class OpenEnvAdapterAgent(PlanningAgent):
    """Generates OpenEnv-compatible wrapper."""
    pass

class ValidatorAgent(PlanningAgent):
    """Validates and tests the generated environment."""
    pass
```

## Quick Start

### CLI Usage (No LLM Required)

The simplest way to generate an environment:

```bash
# Generate a calendar environment
cd Agents/env_generator
python generate_env.py --name calendar --domain calendar \
    --description "A calendar application for managing events"

# Generate an e-commerce environment
python generate_env.py --name shop --domain ecommerce \
    --description "An online shopping platform"

# Generate a social media environment
python generate_env.py --name social --domain social

# Check output
ls generated/calendar/
```

### Python API Usage

```python
import asyncio
from env_generator.generate_env import generate_environment_simple

# Generate environment
asyncio.run(generate_environment_simple(
    name="calendar",
    domain_type="calendar",
    description="A Google Calendar-like application",
))
```

## Full Usage Example (with LLM)

```python
from agents.env_generator import EnvGeneratorOrchestrator
from utils import AgentConfig, LLMConfig, LLMProvider

# Configure with LLM
config = AgentConfig(
    agent_id="env_generator",
    agent_name="EnvGenerator",
    llm=LLMConfig(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4",
        api_key="your-api-key",
    ),
)

# Create orchestrator
orchestrator = EnvGeneratorOrchestrator(config)
await orchestrator.initialize()

# Generate from description
result = await orchestrator.generate_environment(
    name="calendar",
    description="""
    A Google Calendar-like application with:
    - User authentication (register, login)
    - Calendar management (create, list, update, delete)
    - Event management with attendees
    - Recurring events support
    - Free/busy query
    """,
    domain_type="calendar",
    output_dir="./generated_envs",
)

# Or generate from reference data
result = await orchestrator.generate_environment(
    name="inventory",
    reference_data={
        "products": [
            {"id": 1, "name": "Widget", "price": 9.99, "stock": 100},
            {"id": 2, "name": "Gadget", "price": 19.99, "stock": 50},
        ],
        "orders": [
            {"id": 1, "product_id": 1, "quantity": 5, "status": "pending"},
        ],
    },
    domain_type="ecommerce",
)

print(f"Environment generated at: {result['output_dir']}")
```

## Templates

The system uses Jinja2 templates for code generation. Templates are stored in `templates/`:

```
templates/
├── backend/
│   ├── models.py.j2
│   ├── schemas.py.j2
│   ├── database.py.j2
│   ├── auth.py.j2
│   ├── main.py.j2
│   ├── router.py.j2
│   └── Dockerfile.j2
├── frontend/
│   ├── App.js.j2
│   ├── api.js.j2
│   ├── component.js.j2
│   ├── page.js.j2
│   ├── package.json.j2
│   └── Dockerfile.j2
├── openenv/
│   ├── models.py.j2
│   ├── client.py.j2
│   ├── environment.py.j2
│   └── app.py.j2
└── docker/
    ├── docker-compose.yml.j2
    └── .env.example.j2
```

## Implementation Roadmap

| Phase | Task | Priority | Status |
|-------|------|----------|--------|
| 1 | Implement `EnvGeneratorOrchestrator` base framework | P0 | ✅ Done |
| 2 | Implement Phase 1 Design Agents (`EnvDesignerAgent`) | P0 | ✅ Done |
| 3 | Implement Phase 2 Backend Agents (`SchemaDesignerAgent`, `APIBuilderAgent`) | P0 | ✅ Done |
| 4 | Implement Phase 3 Frontend Agents (`UIBuilderAgent`) | P1 | ✅ Done |
| 5 | Implement Phase 4 Integration Agents (`OpenEnvAdapterAgent`, `DockerComposerAgent`) | P0 | ✅ Done |
| 6 | Add template system (Jinja2) | P1 | ✅ Done |
| 7 | Add CLI tool (`generate_env.py`) | P1 | ✅ Done |
| 8 | Implement `ValidatorAgent` (testing framework) | P1 | ✅ Done |
| 9 | Add UI reference image parsing (Vision) | P2 | Pending |

## Dependencies

```txt
# Core
pyyaml>=6.0
jinja2>=3.0.0

# LLM
openai>=1.0.0
anthropic>=0.18.0

# Validation
docker>=6.0.0
requests>=2.25.0
pytest>=7.0.0
```

## References

- [OpenEnv Main Repository](https://github.com/meta-pytorch/OpenEnv)
- [AgentForge Framework](./utils/README.md)
- [Calendar Environment Example](../../openenv-gen-cursor-generated-env/calendar/)

## License

MIT

