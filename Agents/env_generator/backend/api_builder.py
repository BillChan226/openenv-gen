"""
APIBuilder Agent - Generates FastAPI backend

This agent generates the complete FastAPI backend including:
- Authentication system (JWT)
- CRUD routers for each entity
- Main application entry point
"""

from pathlib import Path
from typing import Any, Dict, List
from jinja2 import Environment, FileSystemLoader

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import (
    PlanningAgent,
    AgentConfig,
    AgentRole,
    AgentCapability,
    TaskMessage,
    ResultMessage,
    create_result_message,
)

from ..context import EnvGenerationContext


class APIBuilderAgent(PlanningAgent):
    """
    Agent for generating FastAPI backend.
    
    Generates:
    - Authentication module (auth.py, JWT handling)
    - Entity routers (CRUD operations)
    - Main application (main.py)
    - Configuration files
    
    Usage:
        agent = APIBuilderAgent(config)
        await agent.initialize()
        
        files = await agent.generate_api(context, output_dir)
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config, role=AgentRole.SPECIALIST, enable_reasoning=True)
        
        self.add_capability(AgentCapability(
            name="api_generation",
            description="Generate FastAPI backend code",
        ))
        
        # Initialize Jinja2 environment
        template_dir = Path(__file__).parent.parent / "templates" / "backend"
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    
    async def on_initialize(self) -> None:
        """Initialize API builder tools"""
        await super().on_initialize()
        self._logger.info("APIBuilderAgent initialized")
    
    async def generate_api(
        self,
        context: EnvGenerationContext,
        output_dir: Path,
        entities: List[Dict] = None,
    ) -> Dict[str, str]:
        """
        Generate FastAPI backend files.
        
        Args:
            context: Environment generation context
            output_dir: Output directory
            entities: Prepared entity data (from SchemaDesignerAgent)
            
        Returns:
            Dict mapping file paths to content
        """
        files = {}
        api_dir = output_dir / f"{context.name}_api"
        routers_dir = api_dir / "routers"
        routers_dir.mkdir(parents=True, exist_ok=True)
        
        # Use entities from context if not provided
        if entities is None:
            entities = self._prepare_entities(context.entities)
        
        # Generate auth module
        auth_content = self._generate_auth(context)
        files[f"{context.name}_api/auth.py"] = auth_content
        
        # Generate auth router
        auth_router_content = self._generate_auth_router(context)
        files[f"{context.name}_api/routers/auth.py"] = auth_router_content
        
        # Generate entity routers
        for entity in entities:
            if entity["name"] != "User":
                router_content = self._generate_entity_router(context, entity)
                files[f"{context.name}_api/routers/{entity['name'].lower()}.py"] = router_content
        
        # Generate routers __init__.py
        routers_init = self._generate_routers_init(entities)
        files[f"{context.name}_api/routers/__init__.py"] = routers_init
        
        # Generate main.py
        main_content = self._generate_main(context, entities)
        files[f"{context.name}_api/main.py"] = main_content
        
        # Generate __init__.py
        files[f"{context.name}_api/__init__.py"] = f'"""{context.display_name} API"""\n'
        
        # Generate .env.example
        env_content = self._generate_env_example(context)
        files[f"{context.name}_api/.env.example"] = env_content
        
        # Write files
        for path, content in files.items():
            file_path = output_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        
        return files
    
    def _prepare_entities(self, entities: List[Any]) -> List[Dict]:
        """Prepare entity data for code generation"""
        prepared = []
        
        for entity in entities:
            if hasattr(entity, "__dict__"):
                entity_dict = {
                    "name": entity.name,
                    "table_name": entity.table_name,
                    "description": entity.description,
                    "fields": [],
                }
                fields = entity.fields
            else:
                entity_dict = dict(entity)
                fields = entity.get("fields", [])
            
            for field in fields:
                if hasattr(field, "__dict__"):
                    entity_dict["fields"].append(field.__dict__.copy())
                else:
                    entity_dict["fields"].append(dict(field))
            
            # Check for user_id field
            entity_dict["has_user_id"] = any(
                f.get("name") == "user_id"
                for f in entity_dict["fields"]
            )
            
            # Get ID field type
            id_field = next(
                (f for f in entity_dict["fields"] if f.get("primary_key")),
                None
            )
            entity_dict["id_type"] = "int"
            if id_field:
                sql_type = id_field.get("type", "Integer")
                if "String" in sql_type:
                    entity_dict["id_type"] = "str"
            
            prepared.append(entity_dict)
        
        return prepared
    
    def _generate_auth(self, context: EnvGenerationContext) -> str:
        """Generate authentication module"""
        return f'''"""
Authentication module for {context.display_name}
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .schemas import TokenData


# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({{"exp": expire}})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={{"WWW-Authenticate": "Bearer"}},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    
    return user
'''
    
    def _generate_auth_router(self, context: EnvGenerationContext) -> str:
        """Generate authentication router"""
        return f'''"""
Authentication router for {context.display_name}
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import Token, LoginRequest, UserCreate, UserResponse
from ..auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    """Register a new user"""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=getattr(user_data, "full_name", None),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/login", response_model=Token)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
):
    """Login and get access token"""
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={{"WWW-Authenticate": "Bearer"}},
        )
    
    access_token = create_access_token(
        data={{"sub": user.email}},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    
    return {{"access_token": access_token, "token_type": "bearer"}}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user
'''
    
    def _generate_entity_router(self, context: EnvGenerationContext, entity: Dict) -> str:
        """Generate CRUD router for entity"""
        name = entity["name"]
        name_lower = name.lower()
        table_name = entity["table_name"]
        id_type = entity.get("id_type", "int")
        has_user_id = entity.get("has_user_id", False)
        
        user_filter = ""
        if has_user_id:
            user_filter = f".filter({name}.user_id == current_user.id)"
        
        return f'''"""
{name} router for {context.display_name}
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import {name}
from ..schemas import {name}Create, {name}Update, {name}Response
from ..auth import get_current_user


router = APIRouter(prefix="/{table_name}", tags=["{name}"])


@router.get("/", response_model=List[{name}Response])
def list_{name_lower}s(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List all {name_lower}s"""
    items = db.query({name}){user_filter}.offset(skip).limit(limit).all()
    return items


@router.post("/", response_model={name}Response, status_code=status.HTTP_201_CREATED)
def create_{name_lower}(
    data: {name}Create,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Create a new {name_lower}"""
    item = {name}(**data.model_dump())
    {"item.user_id = current_user.id" if has_user_id else ""}
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{{{name_lower}_id}}", response_model={name}Response)
def get_{name_lower}(
    {name_lower}_id: {id_type},
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get a {name_lower} by ID"""
    item = db.query({name}).filter({name}.id == {name_lower}_id){user_filter}.first()
    if not item:
        raise HTTPException(status_code=404, detail="{name} not found")
    return item


@router.put("/{{{name_lower}_id}}", response_model={name}Response)
def update_{name_lower}(
    {name_lower}_id: {id_type},
    data: {name}Update,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Update a {name_lower}"""
    item = db.query({name}).filter({name}.id == {name_lower}_id){user_filter}.first()
    if not item:
        raise HTTPException(status_code=404, detail="{name} not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{{{name_lower}_id}}", status_code=status.HTTP_204_NO_CONTENT)
def delete_{name_lower}(
    {name_lower}_id: {id_type},
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Delete a {name_lower}"""
    item = db.query({name}).filter({name}.id == {name_lower}_id){user_filter}.first()
    if not item:
        raise HTTPException(status_code=404, detail="{name} not found")
    
    db.delete(item)
    db.commit()
'''
    
    def _generate_routers_init(self, entities: List[Dict]) -> str:
        """Generate routers __init__.py"""
        imports = ["from .auth import router as auth_router"]
        exports = ["auth_router"]
        
        for entity in entities:
            if entity["name"] != "User":
                name = entity["name"].lower()
                imports.append(f"from .{name} import router as {name}_router")
                exports.append(f"{name}_router")
        
        return f'''"""
API Routers
"""

{chr(10).join(imports)}

__all__ = [
    {", ".join(f'"{e}"' for e in exports)},
]
'''
    
    def _generate_main(self, context: EnvGenerationContext, entities: List[Dict]) -> str:
        """Generate main.py"""
        router_imports = ["auth_router"]
        router_includes = ['app.include_router(auth_router, prefix="/api/v1")']
        
        for entity in entities:
            if entity["name"] != "User":
                name = entity["name"].lower()
                router_imports.append(f"{name}_router")
                router_includes.append(f'app.include_router({name}_router, prefix="/api/v1")')
        
        return f'''"""
{context.display_name} API Server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .routers import {", ".join(router_imports)}


# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="{context.display_name} API",
    description="{context.description}",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
{chr(10).join(router_includes)}


@app.get("/")
def root():
    """Root endpoint"""
    return {{"message": "{context.display_name} API", "version": "1.0.0"}}


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {{"status": "healthy"}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port={context.api_port})
'''
    
    def _generate_env_example(self, context: EnvGenerationContext) -> str:
        """Generate .env.example"""
        return f'''# {context.display_name} Environment Variables

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/{context.name}

# Security
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server
HOST=0.0.0.0
PORT={context.api_port}
DEBUG=true
'''
    
    async def process_task(self, task: TaskMessage) -> ResultMessage:
        """Process API generation task"""
        params = task.task_params
        context = params.get("context")
        output_dir = Path(params.get("output_dir", "./generated"))
        entities = params.get("entities")
        
        if not context:
            return create_result_message(
                source_id=self.agent_id,
                target_id=task.header.source_agent_id,
                task_id=task.task_id,
                success=False,
                error_message="Context required",
            )
        
        files = await self.generate_api(context, output_dir, entities)
        
        return create_result_message(
            source_id=self.agent_id,
            target_id=task.header.source_agent_id,
            task_id=task.task_id,
            success=True,
            result_data={"files": list(files.keys())},
        )

