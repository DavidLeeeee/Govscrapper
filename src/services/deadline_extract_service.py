"""본문 텍스트에서 신청/공개/의견제출 마감일 후보를 규칙 기반으로 추출한다."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


DEADLINE_KEYWORDS = (
    "공개기간",
    "공개 기간",
    "접수기간",
    "접수 기간",
    "신청기간",
    "신청 기간",
    "공모기간",
    "공모 기간",
    "입찰기간",
    "입찰 기간",
    "입찰마감",
    "입찰 마감",
    "제출기간",
    "제출 기간",
    "제안서 제출",
    "의견제출",
    "의견 제출",
    "공고기간",
    "공고 기간",
    "등록기간",
    "등록 기간",
    "마감일",
    "마감 일",
    "마감일시",
    "마감 일시",
    "마감기한",
    "마감 기한",
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
ISO_DATE_PATTERN = re.compile(r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})")


@dataclass(frozen=True)
class DeadlineCandidate:
    deadline: str
    source_text: str
    confidence: str = "high"


def extract_deadline_candidate(text: str) -> DeadlineCandidate | None:
    lines = [_normalize_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    for index, line in enumerate(lines):
        if not line:
            continue

        window_lines = lines[index : index + 7]
        window_text = " ".join(window_lines)
        if not _is_deadline_context(window_text):
            continue

        dates = _extract_dates(window_text)
        if not dates:
            continue

        return DeadlineCandidate(
            deadline=max(dates).isoformat(),
            source_text=_trim_source_text(window_text),
            confidence="high",
        )

    return None


def _is_deadline_context(text: str) -> bool:
    compact_text = _compact(text)
    return any(_compact(keyword) in compact_text for keyword in DEADLINE_KEYWORDS)


def _extract_dates(line: str) -> list[date]:
    dates: list[date] = []
    context_year: int | None = None

    for pattern in (ISO_DATE_PATTERN, KOREAN_DATE_PATTERN, DOT_DATE_PATTERN):
        for match in pattern.finditer(line):
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


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _trim_source_text(value: str, max_length: int = 220) -> str:
    if len(value) <= max_length:
        return value

    return value[: max_length - 1].rstrip() + "…"
