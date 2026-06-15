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
    budget: NotRequired[str | None]
    budget_text: NotRequired[str | None]
    detail_fetched_at: NotRequired[str | None]
    ai_deadline: NotRequired[str | None]
    ai_deadline_text: NotRequired[str | None]
    ai_deadline_confidence: NotRequired[str | None]
    region: NotRequired[str | None]
    category: NotRequired[str | None]
    application_period: NotRequired[str | None]
    application_start_at: NotRequired[str | None]
    application_end_at: NotRequired[str | None]
    department: NotRequired[str | None]
    agency: NotRequired[str | None]
    pblanc_id: NotRequired[str | None]
    views: NotRequired[int | None]
    apply_method: NotRequired[str | None]
    contact: NotRequired[str | None]
    attachments: NotRequired[list[dict[str, Any]]]
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


class NoticeSummary(TypedDict):
    summary: str
    detail_points: list[str]
    budget: str | None
    budget_text: str | None
    ai_deadline: str | None
    ai_deadline_text: str | None
    ai_deadline_confidence: str
