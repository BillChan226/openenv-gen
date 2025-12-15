from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Type, TypeVar, Optional


TAction = TypeVar("TAction", bound="CalendarAction")
TObservation = TypeVar("TObservation", bound="CalendarObservation")
TState = TypeVar("TState", bound="CalendarState")


@dataclass
class Calendar:
    pass