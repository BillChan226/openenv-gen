from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Database URL from environment or default to SQLite database file
DEFAULT_DB_NAME = "calendar"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///./{DEFAULT_DB_NAME}.db")

# Create engine, with special handling for SQLite
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(DATABASE_URL)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)

# Base class for models
# Note: __allow_unmapped__ = True allows legacy type annotations without Mapped[]
class _Base:
    __allow_unmapped__ = True

Base = declarative_base(cls=_Base)


def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session and ensure it is closed afterwards.

    Intended for use as a dependency in web frameworks (e.g., FastAPI),
    but can also be used directly in scripts/tests:

        with next(get_db()) as db:
            ...

    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables.

    This function imports models that inherit from Base (if needed)
    and then creates all tables defined on Base.metadata.
    """
    # Import models here if they are not imported elsewhere to ensure
    # they are registered with SQLAlchemy's metadata before creation.
    # Example:
    # from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)