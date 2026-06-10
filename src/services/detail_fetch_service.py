"""공고 상세 페이지에서 요약에 사용할 텍스트를 추출한다."""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from src.contracts.notice import Notice


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GovBusinessScraper/1.0)",
}


def fetch_notice_detail_text(notice: Notice, timeout: int = 10) -> str:
    url = str(notice.get("url") or "").strip()
    if not url:
        return ""

    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if "html" not in content_type and "text" not in content_type:
        return ""

    response.encoding = response.encoding or response.apparent_encoding
    return extract_readable_text(response.text)


def extract_readable_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    raw_lines = soup.get_text("\n").splitlines()
    cleaned_lines = [_normalize_space(line) for line in raw_lines]
    useful_lines = [line for line in cleaned_lines if len(line) >= 2]
    return "\n".join(_dedupe_adjacent_lines(useful_lines))


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _dedupe_adjacent_lines(lines: list[str]) -> list[str]:
    deduped: list[str] = []
    previous = ""
    for line in lines:
        if line == previous:
            continue
        deduped.append(line)
        previous = line
    return deduped
