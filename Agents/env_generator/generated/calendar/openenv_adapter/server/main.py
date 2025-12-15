from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from .environment import CalendarEnvironment

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ActionRequest(BaseModel):
    """Request model for the /step endpoint.

    The exact structure of the action depends on the CalendarEnvironment
    implementation. For flexibility, we accept an arbitrary JSON object.
    """