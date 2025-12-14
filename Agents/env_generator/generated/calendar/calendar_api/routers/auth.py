from datetime import datetime, timedelta
from typing import Optional, Any, Dict

import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field

from calendar_api.database import get_db
from calendar_api.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

# Configuration (use environment variables in production)
SECRET_KEY = os.getenv("CALENDAR_API_SECRET_KEY", "change-this-secret-in-production")
ALGORITHM = os.getenv("CALENDAR_API_JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("CALENDAR_API_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security
security = HTTPBearer()


# ===== Local Schemas for Auth =====


class Token(BaseModel):
    """JWT access token response."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Data stored in the JWT token."""

    sub: str
    exp: int


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr
    password: str = Field(..., min_length=8)


class RegisterRequest(BaseModel):
    """Request body for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field("UTC", max_length=64)


# ===== Utility Functions =====


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user from a JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


# ===== Endpoints =====


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> Token:
    """
    Register a new user and return an access token.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        timezone=payload.timezone or "UTC",
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token({"sub": user.id})
    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
async def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> Token:
    """
    Authenticate a user and return an access token.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    # Update last login timestamp
    user.last_login_at = datetime.utcnow()
    db.add(user)
    db.commit()

    access_token = create_access_token({"sub": user.id})
    return Token(access_token=access_token)


@router.get("/me")
async def read_current_user(user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Return basic information about the current authenticated user.
    This avoids a hard dependency on specific user response schemas.
    """
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "timezone": user.timezone,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login_at": user.last_login_at,
    }