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


BASE_URL = "https://www.aica-gj.kr"
LIST_URL = "https://www.aica-gj.kr/sub.php"
PID = "0201"
DATE_PATTERN = re.compile(r"\d{4}[.-]\d{2}[.-]\d{2}")
DETAIL_HINT_PATTERN = re.compile(r"idx|seq|no|view|read|bbs|board|wr_id", re.I)
BLOCKED_PATTERNS = (
    "Please prove that you are human",
    "자동등록방지를 위해 보안절차를 거치고 있습니다",
)


class AicaScraper:
    target = ScrapeTarget.AICA

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

            oldest_posted_at = min(datetime.fromisoformat(notice["posted_at"]).date() for notice in page_notices)
            if oldest_posted_at < options.start_date:
                break

            time.sleep(self.page_interval_seconds)

        return _dedupe_notices(notices)

    def _scrape_list_page(self, page: int) -> list[Notice]:
        soup = _fetch_soup(self.session, page)
        if _is_blocked_page(soup):
            return []

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
    params = {"PID": PID}
    if page > 1:
        params["page"] = str(page)

    response = session.get(LIST_URL, params=params, timeout=15)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, "html.parser")


def _is_blocked_page(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True)
    return any(pattern in text for pattern in BLOCKED_PATTERNS)


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

        key = (title, posted_at)
        if key in seen:
            continue
        seen.add(key)

        notices.append(
            _build_notice(
                source_name=source_name,
                title=title,
                url=_build_detail_url(title_link, page, title, posted_at),
                posted_at=posted_at,
                scraped_at=scraped_at,
            )
        )

    return notices


def _parse_text_based_notices(
    soup: BeautifulSoup,
    page: int,
    source_name: str,
    scraped_at: str,
) -> list[Notice]:
    lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]
    notices: list[Notice] = []
    seen: set[tuple[str, str]] = set()

    for index, line in enumerate(lines):
        posted_at = _extract_posted_at(line)
        if posted_at is None:
            continue

        title = _find_title_around_date(lines, index)
        if title is None:
            continue

        title_link = _find_link_by_title(soup, title)
        key = (title, posted_at)
        if key in seen:
            continue
        seen.add(key)

        notices.append(
            _build_notice(
                source_name=source_name,
                title=title,
                url=_build_detail_url(title_link, page, title, posted_at),
                posted_at=posted_at,
                scraped_at=scraped_at,
            )
        )

    return notices


def _build_notice(
    source_name: str,
    title: str,
    url: str,
    posted_at: str,
    scraped_at: str,
) -> Notice:
    return {
        "source": source_name,
        "title": title,
        "url": url,
        "posted_at": posted_at,
        "deadline": None,
        "scraped_at": scraped_at,
        "keywords": [],
        "detail_points": [],
        "analysis": False,
    }


def _find_title_link(root: Tag) -> Tag | None:
    candidates: list[Tag] = []
    for link in root.find_all("a", href=True):
        if not isinstance(link, Tag):
            continue

        title = link.get_text(" ", strip=True)
        href = str(link.get("href", ""))
        onclick = str(link.get("onclick", ""))
        if not _is_title(title):
            continue
        if DETAIL_HINT_PATTERN.search(href) or DETAIL_HINT_PATTERN.search(onclick) or len(title) >= 8:
            candidates.append(link)

    if not candidates:
        return None

    return max(candidates, key=lambda link: len(link.get_text(" ", strip=True)))


def _find_link_by_title(root: BeautifulSoup, title: str) -> Tag | None:
    for link in root.find_all("a", href=True):
        if not isinstance(link, Tag):
            continue
        link_title = link.get_text(" ", strip=True)
        if link_title == title or title in link_title:
            return link
    return None


def _extract_title(row: Tag, title_link: Tag | None) -> str | None:
    if title_link is not None:
        title = title_link.get_text(" ", strip=True)
        if _is_title(title):
            return title

    for line in row.get_text("\n", strip=True).splitlines():
        line = line.strip()
        if _is_title(line):
            return line
    return None


def _find_title_around_date(lines: list[str], date_index: int) -> str | None:
    for line in reversed(lines[max(0, date_index - 5) : date_index]):
        if _is_title(line):
            return line
    for line in lines[date_index + 1 : min(len(lines), date_index + 4)]:
        if _is_title(line):
            return line
    return None


def _extract_posted_at(text: str) -> str | None:
    dates = DATE_PATTERN.findall(text)
    if not dates:
        return None
    return _normalize_date(dates[-1])


def _normalize_date(value: str) -> str:
    return value.replace(".", "-")[:10]


def _build_detail_url(title_link: Tag | None, page: int, title: str, posted_at: str) -> str:
    if title_link is None:
        return _build_fallback_url(page, title, posted_at)

    href = str(title_link.get("href", "")).strip()
    if href and not href.startswith("#") and not href.lower().startswith("javascript:"):
        return urljoin(BASE_URL, href)

    onclick = str(title_link.get("onclick", "")).strip()
    return _build_url_from_script(onclick) or _build_fallback_url(page, title, posted_at)


def _build_url_from_script(script: str) -> str | None:
    numbers = re.findall(r"\d+", script)
    if not numbers:
        return None
    return f"{LIST_URL}?{urlencode({'PID': PID, 'action': 'Read', 'idx': numbers[-1]})}"


def _build_fallback_url(page: int, title: str, posted_at: str) -> str:
    digest = hashlib.sha1(f"{page}:{posted_at}:{title}".encode("utf-8")).hexdigest()[:12]
    query = {"PID": PID}
    if page > 1:
        query["page"] = str(page)
    return f"{LIST_URL}?{urlencode(query)}#notice-{digest}"


def _is_title(value: str) -> bool:
    title = value.strip()
    if len(title) < 6:
        return False
    if title.isdigit():
        return False
    if DATE_PATTERN.search(title):
        return False
    if title in {"번호", "제목", "작성자", "작성일", "등록일", "조회수", "첨부파일", "검색", "목록"}:
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
