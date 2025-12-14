from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

    class Config:
        orm_mode = True
        anystr_strip_whitespace = True
        from_attributes = True

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserResponse(UserBase):
    id: int
    is_active: bool

# Event Schemas
class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime

    class Config:
        orm_mode = True
        from_attributes = True

class EventCreate(EventBase):
    pass

class EventUpdate(EventBase):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class EventResponse(EventBase):
    id: int
    creator_id: int

# Invitation Schemas
class InvitationBase(BaseModel):
    event_id: int
    invitee_email: EmailStr

    class Config:
        orm_mode = True
        from_attributes = True

class InvitationCreate(InvitationBase):
    pass

class InvitationResponse(InvitationBase):
    id: int
    status: str

# Reminder Schemas
class ReminderBase(BaseModel):
    event_id: int
    remind_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True

class ReminderCreate(ReminderBase):
    pass

class ReminderResponse(ReminderBase):
    id: int

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str