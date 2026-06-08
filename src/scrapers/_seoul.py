from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from src.contracts.notice import Notice
from src.contracts.scrape_options import ScrapeOptions
from src.scrapers.SITES_INFO import ScrapeTarget


BASE_URL = "https://seoul.rnbd.kr"
LIST_URL = "https://seoul.rnbd.kr/client/c030100/c030100_00.jsp"
DATE_RANGE_PATTERN = re.compile(r"(\d{4}[.-]\d{2}[.-]\d{2})\s*~\s*(\d{4}[.-]\d{2}[.-]\d{2})")
DETAIL_HINT_PATTERN = re.compile(r"c030100|view|detail|seq|idx|no", re.I)
STATUS_VALUES = {"모집중", "모집마감", "접수중", "접수마감", "공고중", "마감"}


class SeoulRndScraper:
    target = ScrapeTarget.SEOUL_RND

    def __init__(
        self,
        max_pages: int = 10,
        page_interval_seconds: float = 1.0,
        session: requests.Session | None = None,
    ) -> None:
        self.max_pages = max_pages
        self.page_interval_seconds = page_interval_seconds
        self.session = session or _make_session()

    def scrape(self, options: ScrapeOptions) -> list[Notice]:
        notices: list[Notice] = []

        for page in range(1, self.max_pages + 1):
            page_notices = self._scrape_list_page(page)
            if not page_notices:
                break

            in_range_notices = [
                notice
                for notice in page_notices
                if options.start_date <= datetime.fromisoformat(notice["posted_at"]).date() <= options.end_date
            ]
            notices.extend(in_range_notices)

            oldest_posted_at = min(
                datetime.fromisoformat(notice["posted_at"]).date()
                for notice in page_notices
            )
            if oldest_posted_at < options.start_date:
                break

            time.sleep(self.page_interval_seconds)

        return notices

    def _scrape_list_page(self, page: int) -> list[Notice]:
        soup = _fetch_soup(self.session, page)
        scraped_at = datetime.now().astimezone().isoformat(timespec="seconds")

        notices = _parse_row_based_notices(soup, page, self.target.source_name, scraped_at)
        if notices:
            return notices

        return _parse_text_based_notices(soup, page, self.target.source_name, scraped_at)


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Referer": BASE_URL,
        }
    )
    return session


def _fetch_soup(session: requests.Session, page: int) -> BeautifulSoup:
    response = session.get(
        LIST_URL,
        params={"pageIndex": page},
        timeout=15,
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, "html.parser")


def _parse_row_based_notices(
    soup: BeautifulSoup,
    page: int,
    source_name: str,
    scraped_at: str,
) -> list[Notice]:
    notices: list[Notice] = []
    seen: set[tuple[str, str]] = set()

    for row in soup.select("tr, li"):
        if not isinstance(row, Tag):
            continue

        row_text = row.get_text(" ", strip=True)
        date_range = _extract_date_range(row_text)
        if date_range is None:
            continue

        posted_at, deadline = date_range
        title_link = _find_title_link(row)
        title = _extract_title(row, title_link)
        if title is None:
            continue

        key = (title, posted_at)
        if key in seen:
            continue
        seen.add(key)

        notices.append(
            {
                "source": source_name,
                "title": title,
                "url": _build_detail_url(title_link, page, title, posted_at),
                "posted_at": posted_at,
                "deadline": deadline,
                "scraped_at": scraped_at,
                "keywords": [],
            }
        )

    return notices


def _parse_text_based_notices(
    soup: BeautifulSoup,
    page: int,
    source_name: str,
    scraped_at: str,
) -> list[Notice]:
    lines = [
        line.strip()
        for line in soup.get_text("\n", strip=True).splitlines()
        if line.strip()
    ]
    notices: list[Notice] = []
    seen: set[tuple[str, str]] = set()

    for index, line in enumerate(lines):
        date_range = _extract_date_range(line)
        if date_range is None:
            continue

        posted_at, deadline = date_range
        title = _find_title_before_date_range(lines, index)
        if title is None:
            continue

        key = (title, posted_at)
        if key in seen:
            continue
        seen.add(key)

        notices.append(
            {
                "source": source_name,
                "title": title,
                "url": _build_fallback_url(page, title, posted_at),
                "posted_at": posted_at,
                "deadline": deadline,
                "scraped_at": scraped_at,
                "keywords": [],
            }
        )

    return notices


def _find_title_link(row: Tag) -> Tag | None:
    candidates: list[Tag] = []

    for link in row.find_all("a", href=True):
        if not isinstance(link, Tag):
            continue

        title = link.get_text(" ", strip=True)
        href = str(link.get("href", ""))
        if not _is_title_candidate(title):
            continue
        if DETAIL_HINT_PATTERN.search(href) or len(title) >= 8:
            candidates.append(link)

    if not candidates:
        return None

    return max(candidates, key=lambda link: len(link.get_text(" ", strip=True)))


def _extract_title(row: Tag, title_link: Tag | None) -> str | None:
    if title_link is not None:
        title = title_link.get_text(" ", strip=True)
        if _is_title_candidate(title):
            return title

    for line in row.get_text("\n", strip=True).splitlines():
        line = line.strip()
        if _is_title_candidate(line):
            return line

    return None


def _find_title_before_date_range(lines: list[str], date_index: int) -> str | None:
    for line in reversed(lines[max(0, date_index - 4) : date_index]):
        if _is_title_candidate(line):
            return line
    return None


def _is_title_candidate(line: str) -> bool:
    if len(line) < 8:
        return False
    if line.isdigit():
        return False
    if DATE_RANGE_PATTERN.search(line):
        return False
    if line in STATUS_VALUES:
        return False
    if line in {"번호", "제목", "모집기간", "상태", "조회", "사업공고"}:
        return False
    return True


def _extract_date_range(text: str) -> tuple[str, str] | None:
    match = DATE_RANGE_PATTERN.search(text)
    if match is None:
        return None
    return _normalize_date(match.group(1)), _normalize_date(match.group(2))


def _normalize_date(value: str) -> str:
    return value.replace(".", "-")


def _build_detail_url(title_link: Tag | None, page: int, title: str, posted_at: str) -> str:
    if title_link is None:
        return _build_fallback_url(page, title, posted_at)

    href = str(title_link.get("href", "")).strip()
    if not href or href.startswith("#"):
        return _build_javascript_url(str(title_link.get("onclick", ""))) or _build_fallback_url(page, title, posted_at)
    if href.lower().startswith("javascript:"):
        return _build_javascript_url(href) or _build_fallback_url(page, title, posted_at)

    return urljoin(BASE_URL, href)


def _build_javascript_url(value: str) -> str | None:
    numbers = re.findall(r"\d+", value)
    if not numbers:
        return None

    return f"{LIST_URL}?{urlencode({'pageIndex': 1})}#notice-{numbers[-1]}"


def _build_fallback_url(page: int, title: str, posted_at: str) -> str:
    digest = hashlib.sha1(f"{page}:{posted_at}:{title}".encode("utf-8")).hexdigest()[:12]
    return f"{LIST_URL}?{urlencode({'pageIndex': page})}#notice-{digest}"
