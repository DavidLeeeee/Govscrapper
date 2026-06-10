from __future__ import annotations

from typing import Literal, TypedDict


class TrendItem(TypedDict):
    keyword: str
    count: int
    reason: str


class EmergingTrendItem(TypedDict):
    keyword: str
    reason: str


class TrendWindowReport(TypedDict):
    months: int
    notice_count: int
    trend_notice_words: list[TrendItem]
    developer_emerging_words: list[EmergingTrendItem]


class TrendReport(TypedDict):
    generated_at: str
    source: Literal["openai"]
    windows: dict[str, TrendWindowReport]
