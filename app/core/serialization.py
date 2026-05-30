from __future__ import annotations

from datetime import date, datetime
from typing import Any


def serialize_datetime(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()

    return value
