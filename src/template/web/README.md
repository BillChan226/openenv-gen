# {{ENV_TITLE}}

{{ENV_DESCRIPTION}}

## Quick Start

### 1. Setup

```bash
# Run setup script
./scripts/setup.sh

# Or manually:
cd docker && cp .env.example .env
```

### 2. Start the Environment

```bash
cd docker
docker-compose up --build
```

This starts:
- **Frontend** (React): http://localhost:3000
- **Backend** (Node.js): http://localhost:5000
- **Database** (PostgreSQL): localhost:5432
- **Environment Server** (OpenEnv): http://localhost:8000

### 3. Validate Setup

```bash
python scripts/validate_env.py
```

## Usage with OpenEnv

```python
from env import WebEnvClient, WebAction

# Connect to running environment
client = WebEnvClient(base_url="http://localhost:8000")

# Or start from Docker image
client = WebEnvClient.from_docker_image("{{ENV_NAME}}:latest")

# Reset environment
result = client.reset()
print(f"Goal: {result.observation.goal}")

# Take actions
result = client.step(WebAction(action_str="click('login-btn')"))
print(f"Reward: {result.reward}, Done: {result.done}")

# Cleanup
client.close()
```

## Available Tasks

| Task ID | Description | Difficulty |
|---------|-------------|------------|
| `login` | Log in with test credentials | Easy |
| `register` | Create a new account | Easy |
| `navigate-dashboard` | Navigate to dashboard | Easy |
| `login-and-navigate` | Multi-step login task | Medium |

## Project Structure

```
{{ENV_NAME}}/
├── app/                    # Web application
│   ├── frontend/          # React frontend
│   ├── backend/           # Node.js backend
│   └── database/          # PostgreSQL
├── tasks/                  # Task definitions
│   ├── base.py            # Base task class
│   ├── registry.py        # Task registry
│   └── definitions/       # Individual tasks
├── env/                    # OpenEnv interface
│   ├── models.py          # Action/Observation types
│   ├── client.py          # HTTP client
│   └── server/            # Environment server
└── docker/                # Docker setup
```

## Development

### Adding New Tasks

1. Create a new file in `tasks/definitions/`
2. Define a task class extending `BaseTask`
3. Use `@register_task()` decorator
4. Implement `validate()` method

Example:
```python
from tasks import BaseTask, TaskConfig, register_task

@register_task()
class MyTask(BaseTask):
    config = TaskConfig(
        task_id="my-task",
        task_name="My Task",
        goal="Complete the task",
        start_url="/",
    )

    def validate(self, page, db_state):
        if "success" in page.url:
            return 1.0, True, "Success!"
        return 0.0, False, ""
```

### Resetting Database

```bash
./scripts/reset_db.sh
```

## Test Credentials

- **Admin**: admin@example.com / admin123
- **User**: user@example.com / user123
