from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ===== User Schemas =====


class UserBase(BaseModel):
    """Shared user properties exposed via API."""

    email: EmailStr
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    timezone: str = Field(default="UTC", max_length=64)
    is_active: bool = True
    is_verified: bool = False


class UserCreate(BaseModel):
    """Properties required to create a new user."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(default="UTC", max_length=64)


class UserUpdate(BaseModel):
    """Properties allowed to be updated for an existing user."""

    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, max_length=64)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserResponse(UserBase):
    """User representation returned to clients."""

    id: str
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated list of users."""

    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int