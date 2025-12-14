#!/usr/bin/env python
"""
Environment Generator CLI

Command-line tool for generating OpenEnv-compatible environments.

Usage:
    # Generate from description
    python -m env_generator.generate_env --name calendar --domain calendar \
        --description "A calendar application for managing events"
    
    # Generate from JSON spec file
    python -m env_generator.generate_env --spec-file ./calendar_spec.json
    
    # Generate from reference data
    python -m env_generator.generate_env --name inventory --data-file ./sample_data.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import AgentConfig, LLMConfig, LLMProvider

from .orchestrator import EnvGeneratorOrchestrator
from .context import EnvGenerationContext
from .design import EnvDesignerAgent
from .backend import SchemaDesignerAgent, APIBuilderAgent
from .frontend import UIBuilderAgent
from .integration import OpenEnvAdapterAgent, DockerComposerAgent, ValidatorAgent


async def generate_environment_simple(
    name: str,
    domain_type: str = "custom",
    description: str = None,
    output_dir: Path = None,
) -> Path:
    """
    Simple environment generation without LLM.
    
    Uses template-based generation for common domain types.
    
    Args:
        name: Environment name
        domain_type: Domain type (calendar, ecommerce, social, inventory, custom)
        description: Optional description
        output_dir: Output directory
        
    Returns:
        Path to generated environment
    """
    output_dir = output_dir or Path(f"./generated/{name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating environment: {name}")
    print(f"Domain: {domain_type}")
    print(f"Output: {output_dir}")
    print("-" * 50)
    
    # Step 1: Design environment
    print("\n[1/6] Designing environment specification...")
    
    config = AgentConfig(
        agent_id="designer",
        agent_name="EnvDesigner",
    )
    designer = EnvDesignerAgent(config)
    await designer.initialize()
    
    spec = await designer.design_environment(
        name=name,
        description=description,
        domain_type=domain_type,
    )
    
    # Save spec
    spec_file = output_dir / "env_spec.json"
    spec_file.write_text(json.dumps(spec, indent=2, default=str), encoding="utf-8")
    print(f"  - Saved spec: {spec_file}")
    print(f"  - Entities: {len(spec['entities'])}")
    print(f"  - Features: {len(spec['features'])}")
    
    # Create context from spec
    context = EnvGenerationContext(
        name=name,
        display_name=spec.get("display_name", name.replace("_", " ").title()),
        description=description or spec.get("description", ""),
        domain=domain_type,
    )
    
    # Convert entities from spec
    for entity_dict in spec["entities"]:
        context.entities.append(entity_dict)
    
    # Step 2: Generate database schema
    print("\n[2/6] Generating database schema...")
    
    schema_config = AgentConfig(
        agent_id="schema_designer",
        agent_name="SchemaDesigner",
    )
    schema_agent = SchemaDesignerAgent(schema_config)
    await schema_agent.initialize()
    
    schema_files = await schema_agent.generate_schema(context, output_dir)
    print(f"  - Generated {len(schema_files)} schema files")
    for f in schema_files:
        print(f"    - {f}")
    
    # Step 3: Generate API
    print("\n[3/6] Generating FastAPI backend...")
    
    api_config = AgentConfig(
        agent_id="api_builder",
        agent_name="APIBuilder",
    )
    api_agent = APIBuilderAgent(api_config)
    await api_agent.initialize()
    
    api_files = await api_agent.generate_api(context, output_dir)
    print(f"  - Generated {len(api_files)} API files")
    for f in sorted(api_files.keys()):
        print(f"    - {f}")
    
    # Step 4: Generate Frontend
    print("\n[4/6] Generating React frontend...")
    
    ui_config = AgentConfig(
        agent_id="ui_builder",
        agent_name="UIBuilder",
    )
    ui_agent = UIBuilderAgent(ui_config)
    await ui_agent.initialize()
    
    ui_files = await ui_agent.generate_frontend(context, output_dir)
    print(f"  - Generated {len(ui_files)} frontend files")
    for f in sorted(ui_files.keys())[:10]:  # Show first 10
        print(f"    - {f}")
    if len(ui_files) > 10:
        print(f"    ... and {len(ui_files) - 10} more files")
    
    # Step 5: Generate OpenEnv adapter
    print("\n[5/6] Generating OpenEnv adapter...")
    
    adapter_config = AgentConfig(
        agent_id="openenv_adapter",
        agent_name="OpenEnvAdapter",
    )
    adapter_agent = OpenEnvAdapterAgent(adapter_config)
    await adapter_agent.initialize()
    
    adapter_files = await adapter_agent.generate_adapter(context, output_dir)
    print(f"  - Generated {len(adapter_files)} OpenEnv files")
    for f in sorted(adapter_files.keys()):
        print(f"    - {f}")
    
    # Step 6: Generate Docker configuration
    print("\n[6/6] Generating Docker configuration...")
    
    docker_config = AgentConfig(
        agent_id="docker_composer",
        agent_name="DockerComposer",
    )
    docker_agent = DockerComposerAgent(docker_config)
    await docker_agent.initialize()
    
    docker_files = await docker_agent.generate_docker(context, output_dir)
    print(f"  - Generated {len(docker_files)} Docker files")
    for f in sorted(docker_files.keys()):
        print(f"    - {f}")
    
    # Generate README
    readme = generate_readme(context, spec)
    readme_file = output_dir / "README.md"
    readme_file.write_text(readme, encoding="utf-8")
    print(f"  - Saved: {readme_file}")
    
    # Step 7: Validate generated environment
    print("\n[+] Validating generated environment...")
    
    validator_config = AgentConfig(
        agent_id="validator",
        agent_name="Validator",
    )
    validator_agent = ValidatorAgent(validator_config)
    await validator_agent.initialize()
    
    report = await validator_agent.validate(context, output_dir)
    print(f"  - Total checks: {report.total_checks}")
    print(f"  - Passed: {report.passed_checks}")
    print(f"  - Failed: {report.failed_checks}")
    print(f"  - Success rate: {report.success_rate:.1f}%")
    
    if report.failed_checks > 0:
        print("\n  Failed checks:")
        for result in report.results:
            if not result.passed:
                print(f"    - {result.name}: {result.message}")
    
    print("\n" + "=" * 50)
    print(f"Environment generated {'successfully' if report.passed else 'with errors'}!")
    print(f"Output directory: {output_dir}")
    print(f"Validation report: {output_dir}/validation_report.json")
    print("\nNext steps:")
    print(f"  1. cd {output_dir}")
    print(f"  2. docker-compose up --build")
    print(f"  3. Access UI at http://localhost:{context.ui_port}")
    print(f"  4. Access API at http://localhost:{context.api_port}")
    print(f"  5. OpenEnv endpoint at http://localhost:{context.openenv_port}")
    print(f"  6. Run tests: pytest tests/")
    
    return output_dir


def generate_docker_compose(context: EnvGenerationContext) -> str:
    """Generate docker-compose.yml"""
    return f'''# {context.display_name} Docker Compose Configuration
# Auto-generated by EnvGenerator

version: "3.8"

services:
  # PostgreSQL Database
  db:
    image: postgres:15-alpine
    container_name: {context.name}-db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: {context.name}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Backend API
  api:
    build:
      context: ./{context.name}_api
      dockerfile: Dockerfile
    container_name: {context.name}-api
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/{context.name}
      SECRET_KEY: change-me-in-production
      DEBUG: "false"
    ports:
      - "{context.api_port}:{context.api_port}"
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{context.api_port}/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # OpenEnv Adapter
  openenv:
    build:
      context: .
      dockerfile: openenv_adapter/Dockerfile
    container_name: {context.name}-openenv
    environment:
      API_BASE_URL: http://api:{context.api_port}
    ports:
      - "{context.openenv_port}:{context.openenv_port}"
    depends_on:
      api:
        condition: service_healthy

volumes:
  postgres_data:

networks:
  default:
    name: {context.name}-network
'''


def generate_readme(context: EnvGenerationContext, spec: dict) -> str:
    """Generate README.md"""
    entities_list = "\n".join(
        f"- **{e['name']}**: {e.get('description', '')}"
        for e in spec.get("entities", [])
    )
    
    features_list = "\n".join(
        f"- {f['name']}"
        for f in spec.get("features", [])
    )
    
    return f'''# {context.display_name}

{context.description}

Auto-generated by EnvGenerator Multi-Agent System.

## Quick Start

```bash
# Start all services
docker-compose up --build

# Or run locally
cd {context.name}_api
pip install -r requirements.txt
python main.py
```

## Endpoints

- **API**: http://localhost:{context.api_port}
- **API Docs**: http://localhost:{context.api_port}/docs
- **OpenEnv**: http://localhost:{context.openenv_port}

## Entities

{entities_list}

## Features

{features_list}

## OpenEnv Integration

This environment is OpenEnv-compatible and can be used for RL training:

```python
from openenv_adapter import {context.class_name}Env, {context.class_name}Action

# Connect to environment
client = {context.class_name}Env(base_url="http://localhost:{context.openenv_port}")

# Reset environment
result = client.reset()
print(result.observation)

# Take action
result = client.step({context.class_name}Action(
    action_type="login",
    params={{"email": "user@example.com", "password": "password"}}
))
print(result.observation.success)
```

## Project Structure

```
{context.name}/
├── {context.name}_api/          # FastAPI backend
│   ├── main.py                  # Application entry point
│   ├── models.py                # SQLAlchemy models
│   ├── schemas.py               # Pydantic schemas
│   ├── database.py              # Database configuration
│   ├── auth.py                  # Authentication module
│   ├── routers/                 # API routers
│   └── requirements.txt         # Python dependencies
├── openenv_adapter/             # OpenEnv integration
│   ├── models.py                # Action/Observation/State
│   ├── client.py                # HTTPEnvClient
│   └── server/                  # Environment server
│       ├── environment.py       # Environment implementation
│       └── app.py               # FastAPI app
├── docker-compose.yml           # Docker orchestration
└── README.md                    # This file
```

## API Authentication

1. Register: `POST /api/v1/auth/register`
2. Login: `POST /api/v1/auth/login`
3. Use the returned `access_token` in the `Authorization: Bearer <token>` header

## License

MIT
'''


def main():
    parser = argparse.ArgumentParser(
        description="Generate OpenEnv-compatible environments"
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Environment name (e.g., calendar, inventory)",
    )
    parser.add_argument(
        "--domain",
        default="custom",
        choices=["calendar", "ecommerce", "social", "inventory", "custom"],
        help="Domain type for template-based generation",
    )
    parser.add_argument(
        "--description",
        help="Environment description",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory (default: ./generated/<name>)",
    )
    parser.add_argument(
        "--spec-file",
        type=Path,
        help="JSON specification file",
    )
    
    args = parser.parse_args()
    
    # Run generation
    asyncio.run(generate_environment_simple(
        name=args.name,
        domain_type=args.domain,
        description=args.description,
        output_dir=args.output,
    ))


if __name__ == "__main__":
    main()

