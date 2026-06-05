from __future__ import annotations

import re
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from src.contracts.notice import Notice
from src.contracts.scrape_options import ScrapeOptions
from src.scrapers.SITES_INFO import ScrapeTarget


BASE_URL = "https://www.kisa.or.kr"
LIST_URL = "https://www.kisa.or.kr/403?page={page}"
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
DETAIL_LINK_PATTERN = re.compile(r"/403/form\?.*postSeq=\d+")


class KisaBidScraper:
    target = ScrapeTarget.KISA_BID

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
        soup = _fetch_html(self.session, LIST_URL.format(page=page))
        scraped_at = datetime.now().astimezone().isoformat(timespec="seconds")

        notices: list[Notice] = []
        for link in soup.find_all("a", href=DETAIL_LINK_PATTERN):
            title = link.get_text(" ", strip=True)
            href = str(link.get("href", ""))
            row = link.find_parent("tr")
            row_text = row.get_text(" ", strip=True) if row else ""
            posted_at = _extract_posted_at(row_text)
            if posted_at is None:
                continue

            notices.append(
                {
                    "source": self.target.source_name,
                    "title": title,
                    "url": urljoin(BASE_URL, href),
                    "posted_at": posted_at,
                    "deadline": None,
                    "scraped_at": scraped_at,
                    "keywords": [],
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
            "Referer": "https://www.kisa.or.kr/",
        }
    )
    return session


def _fetch_html(session: requests.Session, url: str) -> BeautifulSoup:
    response = session.get(url, timeout=10)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, "html.parser")


def _extract_posted_at(row_text: str) -> str | None:
    match = DATE_PATTERN.search(row_text)
    if match is None:
        return None
    return match.group(0)
