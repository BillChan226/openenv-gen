from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, TypeVar, Generic

import requests

from openenv_adapter.models import (
    TAction,
    TObservation,
    TState,
)


# Basic protocol-style base classes.
# These mirror the conceptual OpenEnv interfaces used in the examples.
class BaseProtocol:
    """Placeholder base protocol-style class."""
    pass