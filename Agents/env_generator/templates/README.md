# Code Generation Templates

This directory contains Jinja2 templates for generating environment code.

## Directory Structure

```
templates/
├── backend/                 # Backend (FastAPI) templates
│   ├── models.py.j2        # SQLAlchemy ORM models
│   ├── schemas.py.j2       # Pydantic schemas
│   ├── database.py.j2      # Database connection
│   ├── auth.py.j2          # Authentication module
│   ├── main.py.j2          # FastAPI application entry
│   ├── router.py.j2        # API router template
│   ├── service.py.j2       # Business logic service
│   ├── Dockerfile.j2       # Backend Dockerfile
│   └── pyproject.toml.j2   # Python project config
│
├── frontend/               # Frontend (React) templates
│   ├── App.js.j2          # Main App component
│   ├── api.js.j2          # API client
│   ├── component.js.j2    # Generic component template
│   ├── page.js.j2         # Page component template
│   ├── index.js.j2        # Entry point
│   ├── index.css.j2       # Global styles
│   ├── package.json.j2    # NPM dependencies
│   ├── Dockerfile.j2      # Frontend Dockerfile
│   └── nginx.conf.j2      # Nginx configuration
│
├── openenv/               # OpenEnv adapter templates
│   ├── models.py.j2       # Action, Observation, State
│   ├── client.py.j2       # HTTPEnvClient implementation
│   ├── environment.py.j2  # Environment implementation
│   ├── app.py.j2          # OpenEnv HTTP server
│   └── openenv.yaml.j2    # OpenEnv manifest
│
├── docker/                # Docker orchestration templates
│   ├── docker-compose.yml.j2
│   └── .env.example.j2
│
└── spec/                  # Specification templates
    ├── environment_spec.yaml.j2
    ├── data_schema.yaml.j2
    ├── api_spec.yaml.j2
    └── ui_wireframe.md.j2
```

## Template Variables

### Common Variables

| Variable | Type | Description |
|----------|------|-------------|
| `env_name` | string | Environment name (snake_case) |
| `env_display_name` | string | Display name (Title Case) |
| `env_class_name` | string | Class name (PascalCase) |
| `description` | string | Environment description |
| `api_port` | int | Backend API port |
| `ui_port` | int | Frontend UI port |

### Backend Variables

| Variable | Type | Description |
|----------|------|-------------|
| `entities` | list | List of entity definitions |
| `entity.name` | string | Entity name |
| `entity.table_name` | string | Database table name |
| `entity.fields` | list | Field definitions |
| `entity.relationships` | list | Relationship definitions |

### Frontend Variables

| Variable | Type | Description |
|----------|------|-------------|
| `pages` | list | List of page definitions |
| `components` | list | List of component definitions |
| `api_endpoints` | list | API endpoints for client |

### OpenEnv Variables

| Variable | Type | Description |
|----------|------|-------------|
| `actions` | list | Available action types |
| `resources` | list | Manageable resources |
| `reward_functions` | list | Reward computation logic |

## Usage

```python
from jinja2 import Environment, FileSystemLoader

# Load templates
env = Environment(loader=FileSystemLoader('templates'))

# Render a template
template = env.get_template('backend/models.py.j2')
output = template.render(
    env_name='calendar',
    entities=[
        {
            'name': 'Event',
            'table_name': 'events',
            'fields': [
                {'name': 'id', 'type': 'Integer', 'primary_key': True},
                {'name': 'summary', 'type': 'String(255)'},
                {'name': 'start_time', 'type': 'DateTime'},
            ]
        }
    ]
)

# Write output
with open('calendar_api/models.py', 'w') as f:
    f.write(output)
```

## Adding New Templates

1. Create a new `.j2` file in the appropriate directory
2. Use Jinja2 syntax for variable interpolation
3. Document required variables in this README
4. Add tests for the template

## Template Conventions

- Use `{{ variable }}` for simple variable substitution
- Use `{% for item in list %}...{% endfor %}` for loops
- Use `{% if condition %}...{% endif %}` for conditionals
- Use `{# comment #}` for template comments
- Maintain consistent indentation with the target language

