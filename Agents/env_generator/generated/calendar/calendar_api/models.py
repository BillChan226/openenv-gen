from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from calendar_api.database import Base


def _uuid_str() -> str:
    return str(uuid.uuid4())


class User(Base):
    """Represents an authenticated user of the calendar application."""

    __tablename__ = "users"

    id = Column(
        String(36),
        primary_key=True,
        default=_uuid_str,
        unique=True,
        nullable=False,
    )
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    timezone = Column(String(64), nullable=False, default="UTC")

    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    auth_sessions = relationship(
        "AuthSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    calendars = relationship(
        "Calendar",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    attending_events = relationship(
        "EventAttendee",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


class AuthSession(Base):
    """Represents an authenticated session or refresh token for a user."""

    __tablename__ = "auth_sessions"

    id = Column(
        String(36),
        primary_key=True,
        default=_uuid_str,
        unique=True,
        nullable=False,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    refresh_token = Column(String(512), nullable=False, unique=True, index=True)
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(64), nullable=True)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user = relationship("User", back_populates="auth_sessions")

    def __repr__(self) -> str:
        return f"<AuthSession id={self.id} user_id={self.user_id}>"


class Calendar(Base):
    """Logical collection of events, typically owned by a user."""

    __tablename__ = "calendars"

    id = Column(
        String(36),
        primary_key=True,
        default=_uuid_str,
        unique=True,
        nullable=False,
    )
    owner_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(32), nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    is_shared = Column(Boolean, nullable=False, default=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    owner = relationship("User", back_populates="calendars")
    events = relationship(
        "Event",
        back_populates="calendar",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_calendars_owner_name"),
    )

    def __repr__(self) -> str:
        return f"<Calendar id={self.id} name={self.name!r} owner_id={self.owner_id}>"


class Event(Base):
    """Represents an event within a calendar."""

    __tablename__ = "events"

    id = Column(
        String(36),
        primary_key=True,
        default=_uuid_str,
        unique=True,
        nullable=False,
    )
    calendar_id = Column(
        String(36),
        ForeignKey("calendars.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)

    start_at = Column(DateTime(timezone=True), nullable=False, index=True)
    end_at = Column(DateTime(timezone=True), nullable=False, index=True)
    all_day = Column(Boolean, nullable=False, default=False)

    # Optional recurrence rule (e.g., RFC 5545 RRULE string)
    recurrence_rule = Column(String(1024), nullable=True)

    is_cancelled = Column(Boolean, nullable=False, default=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    calendar = relationship("Calendar", back_populates="events")
    attendees = relationship(
        "EventAttendee",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    reminders = relationship(
        "Reminder",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_events_calendar_start_at", "calendar_id", "start_at"),
    )

    def __repr__(self) -> str:
        return f"<Event id={self.id} title={self.title!r} calendar_id={self.calendar_id}>"


class EventAttendee(Base):
    """Association table between events and users, with RSVP status."""

    __tablename__ = "event_attendees"

    id = Column(
        String(36),
        primary_key=True,
        default=_uuid_str,
        unique=True,
        nullable=False,
    )
    event_id = Column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Example RSVP statuses: "pending", "accepted", "declined", "tentative"
    status = Column(String(32), nullable=False, default="pending")
    is_organizer = Column(Boolean, nullable=False, default=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    event = relationship("Event", back_populates="attendees")
    user = relationship("User", back_populates="attending_events")

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "user_id",
            name="uq_event_attendees_event_user",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<EventAttendee id={self.id} event_id={self.event_id} "
            f"user_id={self.user_id} status={self.status!r}>"
        )


class Reminder(Base):
    """Represents a reminder associated with an event."""

    __tablename__ = "reminders"

    id = Column(
        String(36),
        primary_key=True,
        default=_uuid_str,
        unique=True,
        nullable=False,
    )
    event_id = Column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Number of minutes before event.start_at when reminder should trigger
    minutes_before = Column(
        String(16), nullable=False
    )  # could be int; kept string if schemas expect it

    method = Column(
        String(32),
        nullable=False,
        default="email",
    )  # e.g., "email", "popup", "sms"

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    event = relationship("Event", back_populates="reminders")

    def __repr__(self) -> str:
        return (
            f"<Reminder id={self.id} event_id={self.event_id} "
            f"minutes_before={self.minutes_before!r} method={self.method!r}>"
        )