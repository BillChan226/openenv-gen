from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .environment import Environment  # CalendarEnvironment should subclass this

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# Try to import CalendarEnvironment if it exists in environment.py
try:
    from .environment import CalendarEnvironment  # type: ignore
except ImportError:  # pragma: no cover - fallback if not present
    CalendarEnvironment = None  # type: ignore[assignment]


class StepRequest(BaseModel):
    """Request body for /step endpoint."""