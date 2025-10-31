from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict
from enum import Enum


class EventType(str, Enum):
    MARKET = "MARKET"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    FILL = "FILL"
    RISK = "RISK"
    HEARTBEAT = "HEARTBEAT"


@dataclass(slots=True)
class Event:
    type: EventType
    data: Dict[str, Any]
