from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Database URL from environment or default to SQLite
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./calendar.db")

# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        future=True,
    )
else:
    engine = create_engine(DATABASE_URL, future=True)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
    expire_on_commit=False,
    future=True,
)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Yield a SQLAlchemy Session, ensuring it is closed afterwards.

    Designed to be used as a dependency in frameworks like FastAPI.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables.

    This will create all tables defined on the metadata of Base if they
    do not already exist.
    """
    from calendar_api import models  # noqa: F401  - ensure models are imported

    Base.metadata.create_all(bind=engine)