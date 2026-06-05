from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class ScrapeMode(Enum):
    DAILY = "daily"
    BACKFILL = "backfill"


@dataclass(frozen=True)
class ScrapeOptions:
    mode: ScrapeMode
    start_date: date
    end_date: date

    @classmethod
    def daily(cls, target_date: date) -> "ScrapeOptions":
        return cls(
            mode=ScrapeMode.DAILY,
            start_date=target_date,
            end_date=target_date,
        )

    @classmethod
    def backfill(cls, start_date: date, end_date: date) -> "ScrapeOptions":
        return cls(
            mode=ScrapeMode.BACKFILL,
            start_date=start_date,
            end_date=end_date,
        )
