from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
import requests


# --- Base abstractions -----------------------------------------------------


class Environment:
    """
    Minimal base Environment pattern.

    Concrete environments should implement:
    - reset() -> Observation
    - step(action) -> Tuple[Observation, float, bool, Dict[str, Any]]
    """