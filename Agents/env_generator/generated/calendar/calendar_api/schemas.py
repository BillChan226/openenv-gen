from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ===== User Schemas =====


class UserBase(BaseModel):
    """Shared user properties exposed to or accepted from clients."""

    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    """Properties required to register a new user."""

    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """Credentials used for logging in."""

    email: EmailStr
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """User fields that can be updated (all optional)."""

    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)


class UserResponse(UserBase):
    """User data returned to clients."""

    id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Auth / Token Schemas =====


class Token(BaseModel):
    """Access token returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Data encoded inside access tokens (e.g., JWT)."""

    sub: Optional[str] = None  # user id
    exp: Optional[int] = None  # expiration timestamp (Unix epoch)