from __future__ import annotations

from typing import Protocol

from src.contracts.notice import Notice
from src.contracts.scrape_options import ScrapeOptions
from src.scrapers.SITES_INFO import ScrapeTarget


class Scraper(Protocol):
    """사이트별 스크래퍼가 맞춰야 하는 공통 인터페이스."""

    target: ScrapeTarget

    def scrape(self, options: ScrapeOptions) -> list[Notice]:
        """공고 목록을 수집해 공통 Notice 형식으로 반환한다.

        options.start_date ~ options.end_date 범위만 수집한다.

        반환 예시:
            [
                {
                    "source": "bizinfo",
                    "title": "2026년 정부지원사업 공고",
                    "url": "https://example.com/notice/1",
                    "posted_at": "2026-06-05",
                    "deadline": "2026-06-30",
                    "keywords": ["AI", "수출"],
                }
            ]
        """
