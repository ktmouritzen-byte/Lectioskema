from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True)
class LectioEvent:
    uid: str
    title: str
    start: Optional[datetime]
    end: Optional[datetime]
    all_day_date: Optional[date]
    location: str
    description: str
    status: str = "CONFIRMED"

    @property
    def is_all_day(self) -> bool:
        return self.all_day_date is not None
