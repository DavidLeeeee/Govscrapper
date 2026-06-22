from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from src.contracts.notice import Notice
from src.contracts.scrape_options import ScrapeOptions
from src.scrapers.SITES_INFO import ScrapeTarget


BASE_URL = "https://www.nipa.kr"
DATE_PATTERN = re.compile(r"\d{4}[.-]\d{2}[.-]\d{2}")
DATE_TIME_PATTERN = re.compile(r"(\d{4}[.-]\d{2}[.-]\d{2})(?:\s+\d{1,2}:\d{2})?")
APPLICATION_PERIOD_PATTERN = re.compile(
    r"신청기간\s*[:：]\s*"
    r"(?P<start>\d{4}[.-]\d{2}[.-]\d{2}(?:\s+\d{1,2}:\d{2})?)"
    r"\s*~\s*"
    r"(?P<end>\d{4}[.-]\d{2}[.-]\d{2}(?:\s+\d{1,2}:\d{2})?)"
)


@dataclass(frozen=True)
class NipaBoard:
    name: str
    path: str
    label: str
    has_application_period: bool


BOARDS = [
    NipaBoard("business", "/home/2-2", "사업공고", True),
    NipaBoard("bid", "/home/2-3", "입찰공고", False),
]


class NipaScraper:
    target = ScrapeTarget.NIPA

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

        for board in BOARDS:
            for page in range(1, self.max_pages + 1):
                page_notices = self._scrape_list_page(board, page)
                if not page_notices:
                    break

                in_range_notices = [
                    notice
                    for notice in page_notices
                    if options.start_date <= datetime.fromisoformat(notice["posted_at"]).date() <= options.end_date
                ]
                notices.extend(in_range_notices)

                oldest_posted_at = min(datetime.fromisoformat(notice["posted_at"]).date() for notice in page_notices)
                if oldest_posted_at < options.start_date:
                    break

                time.sleep(self.page_interval_seconds)

        return _dedupe_notices(notices)

    def _scrape_list_page(self, board: NipaBoard, page: int) -> list[Notice]:
        soup = _fetch_soup(self.session, board, page)
        scraped_at = datetime.now().astimezone().isoformat(timespec="seconds")
        notices: list[Notice] = []
        seen: set[tuple[str, str, str]] = set()

        for link in _find_notice_links(soup, board):
            title = link.get_text(" ", strip=True)
            if not _is_title(title):
                continue

            row_text = _find_notice_context_text(link)
            posted_at = _extract_posted_at(row_text)
            if posted_at is None:
                continue

            application_period = _extract_application_period(row_text) if board.has_application_period else None
            deadline = _extract_application_end_date(application_period)
            detail_url = urljoin(BASE_URL, str(link.get("href") or ""))
            key = (board.name, title, posted_at)
            if key in seen:
                continue
            seen.add(key)

            detail_points = [f"구분: {board.label}"]
            if application_period:
                detail_points.append(f"신청기간: {application_period}")

            notices.append(
                {
                    "source": self.target.source_name,
                    "title": title,
                    "url": detail_url,
                    "posted_at": posted_at,
                    "deadline": deadline,
                    "scraped_at": scraped_at,
                    "keywords": [],
                    "detail_points": detail_points,
                    "analysis": False,
                }
            )

        return notices


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


def _fetch_soup(session: requests.Session, board: NipaBoard, page: int) -> BeautifulSoup:
    response = session.get(
        urljoin(BASE_URL, board.path),
        params={"curPage": page},
        timeout=15,
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, "html.parser")


def _find_notice_links(soup: BeautifulSoup, board: NipaBoard) -> list[Tag]:
    links: list[Tag] = []
    detail_pattern = re.compile(rf"^{re.escape(board.path)}/\d+/?$")
    for link in soup.find_all("a", href=True):
        if not isinstance(link, Tag):
            continue
        href = str(link.get("href") or "").strip()
        href_path = urlparse(urljoin(BASE_URL, href)).path
        if detail_pattern.search(href_path):
            links.append(link)
    return links


def _find_notice_context_text(link: Tag) -> str:
    best_text = link.get_text(" ", strip=True)
    for ancestor in link.parents:
        if not isinstance(ancestor, Tag):
            continue
        text = ancestor.get_text(" ", strip=True)
        if DATE_PATTERN.search(text):
            return text
        if len(text) > len(best_text):
            best_text = text
        if ancestor.name in {"tr", "li", "article"}:
            break
    return best_text


def _extract_posted_at(text: str) -> str | None:
    dates = DATE_PATTERN.findall(text)
    if not dates:
        return None
    return _normalize_date(dates[-1])


def _extract_application_period(text: str) -> str | None:
    match = APPLICATION_PERIOD_PATTERN.search(text)
    if match is None:
        return None
    return f"{match.group('start').strip()} ~ {match.group('end').strip()}"


def _extract_application_end_date(application_period: str | None) -> str | None:
    if not application_period:
        return None
    matches = DATE_TIME_PATTERN.findall(application_period)
    if len(matches) < 2:
        return None
    return _normalize_date(matches[-1])


def _normalize_date(value: str) -> str:
    return value.replace(".", "-")[:10]


def _is_title(title: str) -> bool:
    clean_title = title.strip()
    if len(clean_title) < 6:
        return False
    if clean_title.isdigit():
        return False
    return True


def _dedupe_notices(notices: list[Notice]) -> list[Notice]:
    deduped: list[Notice] = []
    seen: set[tuple[str, str, str]] = set()
    for notice in notices:
        key = (str(notice.get("source")), str(notice.get("title")), str(notice.get("posted_at")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(notice)
    return deduped
