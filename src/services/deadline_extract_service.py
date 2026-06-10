"""본문 텍스트에서 신청/공개/의견제출 마감일 후보를 규칙 기반으로 추출한다."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


DEADLINE_KEYWORDS = (
    "공개기간",
    "접수기간",
    "신청기간",
    "공모기간",
    "입찰기간",
    "제출기간",
    "의견제출",
    "의견 제출",
    "마감일",
    "마감",
)

EXCLUDED_KEYWORDS = (
    "사업기간",
    "수행기간",
    "평가일",
    "설명회",
    "교육기간",
)

KOREAN_DATE_PATTERN = re.compile(
    r"(?:(?P<year>\d{4})\s*년\s*)?(?P<month>\d{1,2})\s*월\s*(?P<day>\d{1,2})\s*일?"
)
DOT_DATE_PATTERN = re.compile(
    r"(?:(?P<year>\d{4})[.\-/]\s*)?(?P<month>\d{1,2})[.\-/]\s*(?P<day>\d{1,2})(?:\s*[.])?"
)


@dataclass(frozen=True)
class DeadlineCandidate:
    deadline: str
    source_text: str
    confidence: str = "high"


def extract_deadline_candidate(text: str) -> DeadlineCandidate | None:
    for raw_line in text.splitlines():
        line = _normalize_line(raw_line)
        if not line:
            continue
        if not _is_deadline_line(line):
            continue

        dates = _extract_dates(line)
        if not dates:
            continue

        return DeadlineCandidate(
            deadline=max(dates).isoformat(),
            source_text=line,
            confidence="high",
        )

    return None


def _is_deadline_line(line: str) -> bool:
    if any(keyword in line for keyword in EXCLUDED_KEYWORDS):
        return False

    return any(keyword in line for keyword in DEADLINE_KEYWORDS)


def _extract_dates(line: str) -> list[date]:
    dates: list[date] = []
    context_year: int | None = None

    for match in KOREAN_DATE_PATTERN.finditer(line):
        parsed = _parse_match_date(match, context_year)
        if parsed is None:
            continue
        context_year = parsed.year
        dates.append(parsed)

    if dates:
        return dates

    for match in DOT_DATE_PATTERN.finditer(line):
        parsed = _parse_match_date(match, context_year)
        if parsed is None:
            continue
        context_year = parsed.year
        dates.append(parsed)

    return dates


def _parse_match_date(match: re.Match[str], context_year: int | None) -> date | None:
    year_text = match.group("year")
    year = int(year_text) if year_text else context_year
    if year is None:
        return None

    try:
        return date(
            year=year,
            month=int(match.group("month")),
            day=int(match.group("day")),
        )
    except ValueError:
        return None


def _normalize_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
