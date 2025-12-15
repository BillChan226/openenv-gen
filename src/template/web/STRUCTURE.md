# Web Environment Template Structure

This template provides a comprehensive foundation for generating web-based training environments compatible with BrowserGym and OpenEnv.

## Directory Structure

```
web/
├── STRUCTURE.md                    # This file
├── README.md                       # Template usage documentation
├── config.yaml                     # Environment configuration schema
│
├── app/                            # The generated web application
│   ├── frontend/                   # React-based frontend
│   │   ├── public/
│   │   │   └── index.html
│   │   ├── src/
│   │   │   ├── index.jsx           # Entry point
│   │   │   ├── App.jsx             # Main app component
│   │   │   ├── components/         # Reusable UI components
│   │   │   │   ├── common/         # Buttons, inputs, modals
│   │   │   │   ├── layout/         # Header, footer, sidebar
│   │   │   │   └── forms/          # Form components
│   │   │   ├── pages/              # Page components (routes)
│   │   │   ├── hooks/              # Custom React hooks
│   │   │   ├── context/            # React context providers
│   │   │   ├── services/           # API client services
│   │   │   ├── utils/              # Utility functions
│   │   │   └── styles/             # CSS styles
│   │   ├── package.json
│   │   ├── vite.config.js
│   │   └── Dockerfile
│   │
│   ├── backend/                    # Node.js/Express backend
│   │   ├── src/
│   │   │   ├── index.js            # Entry point
│   │   │   ├── app.js              # Express app setup
│   │   │   ├── config/             # Configuration
│   │   │   ├── routes/             # API routes
│   │   │   ├── controllers/        # Route handlers
│   │   │   ├── models/             # Database models
│   │   │   ├── middleware/         # Express middleware
│   │   │   ├── services/           # Business logic
│   │   │   └── utils/              # Utility functions
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   └── database/                   # PostgreSQL database
│       ├── init/
│       │   ├── 01_schema.sql       # Table definitions
│       │   ├── 02_seed.sql         # Initial seed data
│       │   └── 03_functions.sql    # Stored procedures
│       └── migrations/             # Database migrations
│
├── tasks/                          # BrowserGym task definitions
│   ├── __init__.py
│   ├── base.py                     # Base task class
│   ├── registry.py                 # Task registration
│   ├── reward_functions.py         # Reusable reward functions
│   ├── validators.py               # State validators
│   └── definitions/                # Individual task definitions
│
├── env/                            # OpenEnv interface
│   ├── __init__.py
│   ├── models.py                   # Action, Observation, State
│   ├── client.py                   # HTTP client
│   ├── openenv.yaml
│   ├── pyproject.toml
│   └── server/
│       ├── __init__.py
│       ├── app.py                  # FastAPI application
│       ├── environment.py          # Environment implementation
│       ├── start.sh
│       ├── Dockerfile
│       └── requirements.txt
│
├── docker/                         # Docker orchestration
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── .env.example
│
├── scripts/                        # Utility scripts
│   ├── setup.sh
│   ├── reset_db.sh
│   └── validate_env.py
│
└── tests/                          # Test suite
    ├── test_frontend.py
    ├── test_backend.py
    └── test_tasks.py
```

## Template Variables

Use `{{VARIABLE_NAME}}` syntax for generation-time substitution:

- `{{ENV_NAME}}` - Environment identifier (e.g., "ecommerce-basic")
- `{{ENV_TITLE}}` - Human-readable title
- `{{ENV_DESCRIPTION}}` - Environment description
- `{{GENERATED_ROUTES}}` - Placeholder for generated React routes
- `{{GENERATED_NAV_LINKS}}` - Placeholder for navigation links
- `{{GENERATED_SERVICES}}` - Placeholder for API services
- `{{GENERATED_MODELS}}` - Placeholder for database models
- `{{GENERATED_TASKS}}` - Placeholder for task definitions
