from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from src.contracts.notice import Notice
from src.contracts.scrape_options import ScrapeOptions
from src.scrapers.SITES_INFO import ScrapeTarget


BASE_URL = "https://www.nia.or.kr"
LIST_URL = "https://www.nia.or.kr/site/nia_kor/ex/bbs/List.do"
BOARD_ID = "78336"
DATE_PATTERN = re.compile(r"\d{4}[.-]\d{2}[.-]\d{2}")
DETAIL_HINT_PATTERN = re.compile(r"View\.do|view\.do|bbs|bcIdx|ntt|seq", re.I)


class NiaBidScraper:
    target = ScrapeTarget.NIA

    def __init__(
        self,
        max_pages: int = 20,
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
        params={
            "cbIdx": BOARD_ID,
            "pageIndex": page,
        },
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
        posted_at = _extract_posted_at(row_text)
        if posted_at is None:
            continue

        title_link = _find_title_link(row)
        title = _extract_title(row, title_link)
        if title is None:
            continue

        url = _build_detail_url(title_link, page, title, posted_at)
        key = (title, posted_at)
        if key in seen:
            continue
        seen.add(key)

        notices.append(
            {
                "source": source_name,
                "title": title,
                "url": url,
                "posted_at": posted_at,
                "deadline": None,
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

    for index, line in enumerate(lines):
        posted_at = _extract_posted_at(line)
        if posted_at is None:
            continue

        title = _find_title_before_date(lines, index)
        if title is None:
            continue

        notices.append(
            {
                "source": source_name,
                "title": title,
                "url": _build_fallback_url(page, title, posted_at),
                "posted_at": posted_at,
                "deadline": None,
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
        if not title:
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


def _find_title_before_date(lines: list[str], date_index: int) -> str | None:
    for line in reversed(lines[max(0, date_index - 4) : date_index]):
        if _is_title_candidate(line):
            return line
    return None


def _is_title_candidate(line: str) -> bool:
    if len(line) < 8:
        return False
    if DATE_PATTERN.search(line):
        return False
    if line.isdigit():
        return False
    if line in {"전체", "검색", "목록", "등록일", "조회수", "첨부파일"}:
        return False
    return True


def _extract_posted_at(text: str) -> str | None:
    match = DATE_PATTERN.search(text)
    if match is None:
        return None
    return _normalize_date(match.group(0))


def _normalize_date(value: str) -> str:
    return value.replace(".", "-")


def _build_detail_url(title_link: Tag | None, page: int, title: str, posted_at: str) -> str:
    if title_link is None:
        return _build_fallback_url(page, title, posted_at)

    href = str(title_link.get("href", "")).strip()
    if not href or href.startswith("#") or href.lower().startswith("javascript:"):
        onclick = str(title_link.get("onclick", ""))
        return _build_url_from_numbers(onclick) or _build_fallback_url(page, title, posted_at)

    absolute_url = urljoin(BASE_URL, href)
    return _normalize_detail_url(absolute_url) or absolute_url


def _build_url_from_numbers(value: str) -> str | None:
    bc_idx = _extract_named_number(value, "bcIdx") or _extract_named_number(value, "parentSeq")
    if bc_idx is not None:
        return _build_view_url(bc_idx)

    numbers = re.findall(r"\d+", value)
    if not numbers:
        return None

    if len(numbers) >= 2 and numbers[0] == BOARD_ID:
        return _build_view_url(numbers[1])

    return _build_view_url(numbers[0])


def _normalize_detail_url(url: str) -> str | None:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    bc_idx = _first_query_value(query, "bcIdx") or _first_query_value(query, "parentSeq")
    if bc_idx is None:
        return _build_url_from_numbers(url)

    return _build_view_url(bc_idx)


def _first_query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    return values[0]


def _extract_named_number(value: str, key: str) -> str | None:
    match = re.search(rf"{key}\s*[=:]\s*['\"]?(\d+)", value)
    if match is None:
        return None
    return match.group(1)


def _build_view_url(bc_idx: str) -> str:
    query = {
        "cbIdx": BOARD_ID,
        "bcIdx": bc_idx,
        "parentSeq": bc_idx,
    }
    return f"{BASE_URL}/site/nia_kor/ex/bbs/View.do?{urlencode(query)}"


def _build_fallback_url(page: int, title: str, posted_at: str) -> str:
    digest = hashlib.sha1(f"{page}:{posted_at}:{title}".encode("utf-8")).hexdigest()[:12]
    return f"{LIST_URL}?{urlencode({'cbIdx': BOARD_ID, 'pageIndex': page})}#notice-{digest}"
