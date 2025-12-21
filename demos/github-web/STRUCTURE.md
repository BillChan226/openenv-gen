# Web Environment Template Structure

This template provides a comprehensive foundation for generating web-based training environments compatible with BrowserGym and OpenEnv.

**Optimized for Agent Training**: This template prioritizes diverse UI interactions and clear state indicators over production complexity. See `OPTIMIZATION_FOR_AGENTS.md` for design philosophy.

## Directory Structure

```
web/
├── STRUCTURE.md                         # This file
├── README.md                            # Template usage documentation
├── config.yaml                          # Environment configuration schema
├── OPTIMIZATION_FOR_AGENTS.md           # Design philosophy for agent training
├── CHANGES_FOR_AGENT_TRAINING.md        # Summary of optimizations
│
├── app/                                 # The generated web application
│   ├── frontend/                        # React-based frontend
│   │   ├── public/
│   │   │   └── index.html
│   │   ├── src/
│   │   │   ├── index.jsx                # Entry point
│   │   │   ├── App.jsx                  # Main app component
│   │   │   ├── api/                     # Structured API layer
│   │   │   │   ├── client.js           # Base axios client
│   │   │   │   ├── auth.js             # Auth endpoints
│   │   │   │   ├── types.js            # JSDoc type definitions
│   │   │   │   ├── mocks.js            # Mock data utilities
│   │   │   │   └── {{resource}}.js     # Generated resource APIs
│   │   │   ├── components/              # Reusable UI components
│   │   │   │   ├── common/             # Common components
│   │   │   │   │   ├── Button.jsx      # Button with loading states
│   │   │   │   │   ├── Input.jsx       # Form input with validation
│   │   │   │   │   ├── Select.jsx      # Dropdown component
│   │   │   │   │   ├── Modal.jsx       # Dialog pattern
│   │   │   │   │   ├── Card.jsx        # Content container
│   │   │   │   │   ├── Table.jsx       # Data display
│   │   │   │   │   ├── Tabs.jsx        # Multi-view navigation
│   │   │   │   │   └── ProtectedRoute.jsx
│   │   │   │   ├── layout/             # Layout components
│   │   │   │   │   ├── Layout.jsx
│   │   │   │   │   ├── Header.jsx
│   │   │   │   │   └── Footer.jsx
│   │   │   │   └── forms/              # Form components
│   │   │   ├── pages/                   # Page components (routes)
│   │   │   │   ├── Home.jsx
│   │   │   │   ├── Login.jsx
│   │   │   │   ├── Register.jsx
│   │   │   │   ├── Dashboard.jsx
│   │   │   │   └── {{page}}.jsx        # Generated pages
│   │   │   ├── hooks/                   # Custom React hooks
│   │   │   ├── context/                 # React context providers
│   │   │   │   └── AuthContext.jsx
│   │   │   ├── services/                # Legacy API services
│   │   │   │   └── api.js              # Exports from api/ folder
│   │   │   ├── utils/                   # Utility functions
│   │   │   └── styles/                  # CSS styles
│   │   │       └── global.css
│   │   ├── package.json
│   │   ├── vite.config.js
│   │   └── Dockerfile
│   │
│   ├── backend/                         # Node.js/Express backend
│   │   ├── src/
│   │   │   ├── index.js                 # Entry point
│   │   │   ├── app.js                   # Express app setup
│   │   │   ├── config/                  # Configuration
│   │   │   │   ├── database.js         # Sequelize config
│   │   │   │   └── auth.js             # Simplified auth (no JWT/bcrypt)
│   │   │   ├── routes/                  # API routes
│   │   │   │   ├── auth.js             # Auth endpoints
│   │   │   │   ├── users.js            # User CRUD
│   │   │   │   └── {{resource}}.js     # Generated routes
│   │   │   ├── controllers/             # Route handlers
│   │   │   ├── models/                  # Database models (Sequelize)
│   │   │   │   ├── User.js             # User model
│   │   │   │   ├── index.js            # Model registry
│   │   │   │   └── {{Model}}.js        # Generated models
│   │   │   ├── middleware/              # Express middleware
│   │   │   │   ├── auth.js             # Simple auth check
│   │   │   │   └── error.js            # Error handling
│   │   │   ├── services/                # Business logic
│   │   │   └── utils/                   # Utility functions
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

## Key Design for Agent Training

### 1. Simplified Authentication
- **No JWT complexity**: Simple session tokens instead
- **No password hashing**: Plain text comparison for speed
- **Predefined test users**: `admin@example.com / admin123`, `user@example.com / user123`
- **Focus**: Form interaction patterns, not security

### 2. Structured API Layer (`src/api/`)
- **Organized endpoints**: One file per resource
- **Type definitions**: JSDoc types without TypeScript
- **Mock data support**: Frontend works without backend
- **Easy generation**: Clear template for new resources

### 3. Rich Component Library
All components include `data-testid` for agent targeting:

| Component | Purpose | Agent Learning |
|-----------|---------|----------------|
| `Button` | Actions with loading states | Visual feedback, disabled states |
| `Input` | Form fields with validation | Error states, required fields |
| `Select` | Dropdown selections | Option selection patterns |
| `Modal` | Dialog interactions | Overlay clicks, close patterns |
| `Card` | Content grouping | Clickable areas, visual hierarchy |
| `Table` | Data display | Row actions, sorting, empty states |
| `Tabs` | Multi-view navigation | State management, active indicators |

### 4. Mock Data System
Enable with `VITE_USE_MOCKS=true`:
- Predefined mock data in `src/api/mocks.js`
- Intercepts API calls automatically
- Allows frontend-only development
- Easy to extend for new resources

### 5. Data-testid Coverage
Every interactive element has a unique identifier:
```jsx
<Button testId="login-btn">Login</Button>
<Input testId="email-input" />
<Table testId="users-table" />
```

## Template Variables

Use `{{VARIABLE_NAME}}` syntax for generation-time substitution:

### Basic Configuration
- `{{ENV_NAME}}` - Environment identifier (e.g., "ecommerce-basic")
- `{{ENV_TITLE}}` - Human-readable title (e.g., "E-Commerce App")
- `{{ENV_DESCRIPTION}}` - Environment description
- `{{APP_TYPE}}` - Application type (e-commerce, social, cms, etc.)
- `{{COMPLEXITY}}` - Complexity level (simple, medium, complex)

### Frontend Generation
- `{{GENERATED_ROUTES}}` - React route definitions
- `{{GENERATED_NAV_LINKS}}` - Navigation links in Header
- `{{GENERATED_API_ENDPOINTS}}` - New API modules in `src/api/`
- `{{GENERATED_COMPONENTS}}` - Custom UI components
- `{{GENERATED_PAGES}}` - Page components
- `{{GENERATED_MOCK_DATA}}` - Mock data definitions

### Backend Generation
- `{{GENERATED_ROUTES}}` - Express route files
- `{{GENERATED_MODELS}}` - Sequelize models
- `{{GENERATED_CONTROLLERS}}` - Route handlers

### Database Generation
- `{{GENERATED_SCHEMA}}` - SQL table definitions
- `{{GENERATED_SEED_DATA}}` - Test data
- `{{GENERATED_FUNCTIONS}}` - PostgreSQL functions

### Task Generation
- `{{GENERATED_TASKS}}` - Task class definitions
- `{{GENERATED_TASK_IMPORTS}}` - Task import statements
