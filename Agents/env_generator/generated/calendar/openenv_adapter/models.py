from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Type, TypeVar


T = TypeVar("T", bound="BaseModel")


class BaseModel:
    """Base model with common (de)serialization helpers."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the dataclass to a plain dict.

        Datetime fields are converted to ISO 8601 strings.
        """
        def serialize_value(value: Any) -> Any:
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, list):
                return [serialize_value(v) for v in value]
            if isinstance(value, dict):
                return {k: serialize_value(v) for k, v in value.items()}
            return value

        raw = asdict(self)
        return {k: serialize_value(v) for k, v in raw.items()}

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Deserialize a dict into an instance of the dataclass.

        Datetime fields are parsed from ISO 8601 strings if the target
        field type is `datetime`. For other fields, values are used as-is.
        """
        # We avoid heavy introspection and assume that callers pass
        # correctly-typed data, except for datetime which we normalize.
        field_types = {f.name: f.type for f in getattr(cls, "__dataclass_fields__", {}).values()}  # type: ignore[attr-defined]

        def deserialize_value(name: str, value: Any) -> Any:
            expected_type = field_types.get(name)
            if expected_type is datetime and isinstance(value, str):
                return datetime.fromisoformat(value)
            return value

        kwargs = {k: deserialize_value(k, v) for k, v in data.items()}
        return cls(**kwargs)  # type: ignore[arg-type]


@dataclass
class CalendarAction(BaseModel):
    """Action that the agent can take in the calendar environment.

    Attributes:
        action_type: High-level action identifier
            (e.g., 'login', 'create_event', 'navigate', 'click').
        parameters: Action-specific parameters such as form fields,
            element identifiers, navigation targets, etc.
    """
    action_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CalendarObservation(BaseModel):
    """Observation returned by the environment after an action.

    Attributes:
        page_content: Textual summary of the current page or view.
        elements: List of interactable UI elements, each represented
            as a dictionary (e.g., with id, type, label, metadata).
        message: Feedback or status message produced by the last action.
        success: Whether the last action was considered successful.
    """
    page_content: str
    elements: List[Dict[str, Any]] = field(default_factory=list)
    message: str = ""
    success: bool = True


@dataclass
class CalendarState(BaseModel):
    """Full internal state snapshot of the calendar environment.

    Attributes:
        user_logged_in: Whether the current user is authenticated.
        current_page: Logical name or identifier of the current page/view.
        session_data: Arbitrary session-related data such as user info,
            CSRF tokens, UI state, etc.
        timestamp: Timestamp for when this state snapshot was created.
    """
    user_logged_in: bool = False
    current_page: str = ""
    session_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)