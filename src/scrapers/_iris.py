from __future__ import annotations

import time
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import requests

from src.contracts.notice import Notice
from src.contracts.scrape_options import ScrapeOptions
from src.scrapers.SITES_INFO import ScrapeTarget


BASE_URL = "https://www.iris.go.kr"
LIST_API_URL = "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituList.do"
DETAIL_URL = "https://www.iris.go.kr/contents/retrieveBsnsAncmView.do"
DEFAULT_GOVERNMENT_CODES = ("AR4001", "AR4981")
DEFAULT_GOVERNMENT_NAMES = ("과학기술정보통신부", "개인정보보호위원회")


class IrisBtinSituScraper:
    target = ScrapeTarget.IRIS_BTIN_SITU

    def __init__(
        self,
        max_pages: int = 20,
        page_interval_seconds: float = 1.0,
        government_codes: tuple[str, ...] = DEFAULT_GOVERNMENT_CODES,
        allowed_government_names: tuple[str, ...] = DEFAULT_GOVERNMENT_NAMES,
        session: requests.Session | None = None,
    ) -> None:
        self.max_pages = max_pages
        self.page_interval_seconds = page_interval_seconds
        self.government_codes = government_codes
        self.allowed_government_names = allowed_government_names
        self.session = session or _make_session()

    def scrape(self, options: ScrapeOptions) -> list[Notice]:
        notices: list[Notice] = []

        for page in range(1, self.max_pages + 1):
            rows = self._fetch_list_page(page)
            if not rows:
                break

            page_notices = [
                _row_to_notice(row)
                for row in rows
                if _is_allowed_government_name(row, self.allowed_government_names)
            ]
            if not page_notices:
                continue

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

    def _fetch_list_page(self, page: int) -> list[dict[str, Any]]:
        payload: list[tuple[str, str | int]] = [
            ("pageIndex", page),
            ("blngGovdSeArr", "|".join(self.government_codes)),
        ]
        for government_code in self.government_codes:
            payload.append(("blngGovdSe[]", government_code))

        response = self.session.post(LIST_API_URL, data=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        rows = data.get("listBsnsAncmBtinSitu", [])
        if not isinstance(rows, list):
            return []

        return [row for row in rows if isinstance(row, dict)]


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": BASE_URL,
            "Referer": "https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituListView.do",
            "X-Requested-With": "XMLHttpRequest",
        }
    )
    return session


def _row_to_notice(row: dict[str, Any]) -> Notice:
    posted_at = _normalize_date(_first_text(row, "ancmDe", "rcveStrDe"))
    deadline = _normalize_optional_date(_first_text(row, "rcveEndDe"))
    ancm_id = _first_text(row, "ancmId")
    sorgn_id = _first_text(row, "sorgnId")

    return {
        "source": ScrapeTarget.IRIS_BTIN_SITU.source_name,
        "title": _first_text(row, "ancmTl"),
        "url": _build_detail_url(ancm_id, sorgn_id),
        "posted_at": posted_at,
        "deadline": deadline,
        "scraped_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "keywords": [],
    }


def _first_text(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _normalize_date(value: str) -> str:
    return value.replace(".", "-")


def _normalize_optional_date(value: str) -> str | None:
    if not value:
        return None
    return _normalize_date(value)


def _is_allowed_government_name(row: dict[str, Any], allowed_government_names: tuple[str, ...]) -> bool:
    government_name = _first_text(row, "blngGovdSeNm", "blngGovdSe")
    return government_name in allowed_government_names


def _build_detail_url(ancm_id: str, sorgn_id: str) -> str:
    query = {"ancmId": ancm_id}
    if sorgn_id:
        query["sorgnId"] = sorgn_id
    return f"{DETAIL_URL}?{urlencode(query)}"
