from __future__ import annotations

from typing import Literal, TypedDict


class TrendItem(TypedDict):
    keyword: str
    count: int
    reason: str


class EmergingTrendItem(TypedDict):
    keyword: str
    reason: str


class MonthlyTrendReport(TypedDict):
    month: str
    generated_at: str
    notice_count: int
    trend_notice_words: list[TrendItem]
    developer_emerging_words: list[EmergingTrendItem]


class TrendReport(TypedDict):
    generated_at: str
    source: Literal["openai"]
    months: dict[str, MonthlyTrendReport]
    available_months: list[str]
