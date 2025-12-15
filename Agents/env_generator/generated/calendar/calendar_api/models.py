from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    """
    Application user.

    Includes core authentication and profile fields. Password is stored as a hash.
    """

    __tablename__ = "users"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: str = Column(String(255), unique=True, nullable=False, index=True)
    password_hash: str = Column(String(255), nullable=False)
    name: Optional[str] = Column(String(100), nullable=True)
    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    calendars: List["Calendar"] = relationship(
        "Calendar",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    events_created: List["Event"] = relationship(
        "Event",
        back_populates="creator",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="Event.creator_id",
    )
    notifications: List["Notification"] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r}>"


class Calendar(Base):
    """
    A calendar that groups events and is owned by a user.
    """

    __tablename__ = "calendars"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: str = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: str = Column(String(200), nullable=False)
    description: Optional[str] = Column(Text, nullable=True)
    color: Optional[str] = Column(String(20), nullable=True)
    is_public: bool = Column(Boolean, nullable=False, default=False)
    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Optional[datetime] = Column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )

    owner: User = relationship("User", back_populates="calendars")
    events: List["Event"] = relationship(
        "Event",
        back_populates="calendar",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_calendars_owner_id_name", "owner_id", "name"),
    )

    def __repr__(self) -> str:
        return f"<Calendar id={self.id!r} name={self.name!r}>"


class Event(Base):
    """
    A calendar event with time range and optional recurrence.
    """

    __tablename__ = "events"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    calendar_id: str = Column(
        String(36),
        ForeignKey("calendars.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creator_id: str = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: str = Column(String(255), nullable=False)
    description: Optional[str] = Column(Text, nullable=True)
    location: Optional[str] = Column(String(255), nullable=True)

    start_time: datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time: datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    all_day: bool = Column(Boolean, nullable=False, default=False)

    # Basic recurrence support via RRULE-like string or similar
    recurrence_rule: Optional[str] = Column(String(500), nullable=True)

    is_cancelled: bool = Column(Boolean, nullable=False, default=False)

    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Optional[datetime] = Column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )

    calendar: Calendar = relationship("Calendar", back_populates="events")
    creator: Optional[User] = relationship(
        "User", back_populates="events_created", foreign_keys=[creator_id]
    )

    attendees: List["EventAttendee"] = relationship(
        "EventAttendee",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    reminders: List["Reminder"] = relationship(
        "Reminder",
        back_populates="event",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_events_calendar_start_time", "calendar_id", "start_time"),
    )

    def __repr__(self) -> str:
        return f"<Event id={self.id!r} title={self.title!r}>"


class EventAttendee(Base):
    """
    Join table linking users to events with attendance status.
    """

    __tablename__ = "event_attendees"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    event_id: str = Column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: str = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # e.g., "pending", "accepted", "declined", "tentative"
    status: str = Column(String(20), nullable=False, default="pending")
    is_organizer: bool = Column(Boolean, nullable=False, default=False)

    event: Event = relationship("Event", back_populates="attendees")
    user: User = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "user_id",
            name="uq_event_attendees_event_user",
        ),
    )

    def __repr__(self) -> str:
        return f"<EventAttendee event_id={self.event_id!r} user_id={self.user_id!r}>"


class Reminder(Base):
    """
    Reminder associated with an event, to trigger notifications relative to start time.
    """

    __tablename__ = "reminders"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    event_id: str = Column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # minutes before event start
    minutes_before_start: int = Column(Integer, nullable=False, default=15)

    method: str = Column(
        String(20),
        nullable=False,
        default="email",  # e.g., "email", "push"
    )

    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    event: Event = relationship("Event", back_populates="reminders")

    def __repr__(self) -> str:
        return f"<Reminder id={self.id!r} event_id={self.event_id!r}>"


class Notification(Base):
    """
    Notification generated for a user (e.g., from reminders or shared calendar changes).
    """

    __tablename__ = "notifications"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_id: str = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional link back to an event that this notification concerns
    event_id: Optional[str] = Column(
        String(36),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    message: str = Column(Text, nullable=False)
    is_read: bool = Column(Boolean, nullable=False, default=False)
    created_at: datetime = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: User = relationship("User", back_populates="notifications")
    event: Optional[Event] = relationship("Event")

    def __repr__(self) -> str:
        return f"<Notification id={self.id!r} user_id={self.user_id!r}>"