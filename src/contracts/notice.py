from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class Notice(TypedDict):
    source: str
    title: str
    url: str
    posted_at: str
    deadline: str | None
    scraped_at: str
    keywords: list[str]
    summary: NotRequired[str | None]
    detail_points: NotRequired[list[str]]
    detail_fetched_at: NotRequired[str | None]
    marked: NotRequired[bool]
    mark: NotRequired[dict[str, Any]]


class MarkRecord(TypedDict):
    key: str
    source: str | None
    title: str | None
    url: str | None
    deadline: str | None
    marked_by: str
    marked_at: str
    memo: str | None
