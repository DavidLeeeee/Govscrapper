"""대한민국 영업일 여부를 판정한다."""

from __future__ import annotations

from datetime import date
from functools import lru_cache

import holidays


@lru_cache(maxsize=None)
def _korean_holidays(year: int) -> holidays.HolidayBase:
    return holidays.country_holidays("KR", years=[year])


def korean_non_business_day_reason(target_date: date) -> str | None:
    if target_date.weekday() >= 5:
        return "weekend"

    holiday_name = _korean_holidays(target_date.year).get(target_date)
    if holiday_name:
        return f"public_holiday:{holiday_name}"

    return None
