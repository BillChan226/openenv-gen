from dataclasses import dataclass, field
from typing import Any, List

@dataclass(kw_only=True)
class CalendarAction:
    action_type: str
    resource: str
    resource_id: str
    params: dict = field(default_factory=dict)

@dataclass(kw_only=True)
class CalendarObservation:
    success: bool
    data: Any
    error_message: str
    available_actions: List[str]

@dataclass(kw_only=True)
class CalendarState:
    episode_id: str
    step_count: int
    current_user: str
    current_page: str