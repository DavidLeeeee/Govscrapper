from __future__ import annotations

import re
import time
from collections.abc import Callable
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.contracts.notice import Notice
from src.contracts.scrape_options import ScrapeOptions


BASE_URL = "https://www.bizinfo.go.kr"
LIST_URL = "https://www.bizinfo.go.kr/sii/siia/selectSIIA200View.do"
SOURCE_NAME = "bizinfo_region"
DISPLAY_NAME = "기업마당 지역공고"
DATE_PATTERN = re.compile(r"\d{4}[-.]\d{2}[-.]\d{2}")
REGION_PATTERN = re.compile(r"^\[([^\]]+)\]")


class BizInfoRegionScraper:
    source_name = SOURCE_NAME
    display_name = DISPLAY_NAME

    def __init__(
        self,
        max_pages: int = 5,
        with_detail: bool = False,
        page_interval_seconds: float = 0.8,
        detail_interval_seconds: float = 0.4,
        session: requests.Session | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        self.max_pages = max_pages
        self.with_detail = with_detail
        self.page_interval_seconds = page_interval_seconds
        self.detail_interval_seconds = detail_interval_seconds
        self.session = session or _make_session()
        self.on_progress = on_progress

    def scrape(self, options: ScrapeOptions) -> list[Notice]:
        notices: list[Notice] = []

        for page in range(1, self.max_pages + 1):
            self._progress(f"[regional] 목록 수집: page={page}/{self.max_pages}")
            page_notices = self._scrape_list_page(page)
            if not page_notices:
                self._progress(f"[regional] page={page} 공고 없음, 종료")
                break

            in_range_notices = [
                notice
                for notice in page_notices
                if _is_in_range(notice.get("posted_at"), options)
            ]
            self._progress(f"[regional] page={page} 목록 {len(page_notices)}건, 기간 내 {len(in_range_notices)}건")

            if self.with_detail:
                detailed_notices: list[Notice] = []
                total = len(in_range_notices)
                for index, notice in enumerate(in_range_notices, start=1):
                    self._progress(f"[regional] 상세 수집 {index}/{total}: {notice['title']}")
                    detailed_notices.append(self._append_detail_fields(notice))
                in_range_notices = detailed_notices

            notices.extend(in_range_notices)

            oldest_posted_at = min(
                datetime.fromisoformat(str(notice["posted_at"])).date()
                for notice in page_notices
                if notice.get("posted_at")
            )
            if oldest_posted_at < options.start_date:
                break

            time.sleep(self.page_interval_seconds)

        return notices

    def _progress(self, message: str) -> None:
        if self.on_progress is not None:
            self.on_progress(message)

    def _scrape_list_page(self, page: int) -> list[Notice]:
        soup = _fetch_soup(self.session, LIST_URL, params=_build_list_params(page))
        scraped_at = datetime.now().astimezone().isoformat(timespec="seconds")
        notices: list[Notice] = []
        seen: set[str] = set()

        for link in soup.select('a[href*="selectSIIA200Detail.do"][href*="pblancId="]'):
            row = link.find_parent("tr")
            if row is None:
                continue

            cells = [td.get_text(" ", strip=True) for td in row.select("td")]
            if len(cells) < 8:
                continue

            title = link.get_text(" ", strip=True)
            detail_url = urljoin(BASE_URL, str(link.get("href", "")))
            pblanc_id = _extract_pblanc_id(detail_url)
            if not title or not pblanc_id or pblanc_id in seen:
                continue
            seen.add(pblanc_id)

            application_period = cells[3]
            start_at, end_at = _parse_date_range(application_period)
            posted_at = _normalize_date(cells[6])
            if posted_at is None:
                continue

            notices.append(
                {
                    "source": SOURCE_NAME,
                    "title": title,
                    "url": detail_url,
                    "posted_at": posted_at,
                    "deadline": end_at,
                    "scraped_at": scraped_at,
                    "keywords": [],
                    "region": _extract_region(title),
                    "category": cells[1] or None,
                    "application_period": application_period or None,
                    "application_start_at": start_at,
                    "application_end_at": end_at,
                    "department": cells[4] or None,
                    "agency": cells[5] or None,
                    "pblanc_id": pblanc_id,
                    "views": _parse_int(cells[7]),
                }
            )

        return notices

    def _append_detail_fields(self, notice: Notice) -> Notice:
        soup = _fetch_soup(self.session, str(notice["url"]))
        content_area = soup.select_one("#content") or soup.select_one(".content") or soup.select_one("main") or soup.body
        full_text = content_area.get_text("\n", strip=True) if content_area else ""

        updated = dict(notice)
        summary = _extract_section_text(full_text, "사업개요", ["사업신청 방법", "문의처", "첨부파일", "본문출력파일"])
        apply_method = _extract_section_text(full_text, "사업신청 방법", ["문의처", "첨부파일", "본문출력파일"])
        contact = _extract_section_text(full_text, "문의처", ["첨부파일", "본문출력파일", "정보에 만족하셨나요"])
        if summary:
            updated["summary"] = summary
        if apply_method:
            updated["apply_method"] = apply_method
        if contact:
            updated["contact"] = contact
        attachments = _extract_attachments(soup)
        if attachments:
            updated["attachments"] = attachments
        updated["detail_fetched_at"] = datetime.now().astimezone().isoformat(timespec="seconds")

        time.sleep(self.detail_interval_seconds)
        return updated  # type: ignore[return-value]


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
            "Referer": "https://www.bizinfo.go.kr/",
        }
    )
    return session


def _fetch_soup(session: requests.Session, url: str, params: dict[str, str] | None = None) -> BeautifulSoup:
    response = session.get(url, params=params, timeout=15)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, "html.parser")


def _build_list_params(page: int, rows: int = 15) -> dict[str, str]:
    return {
        "pblancId": "",
        "hashCode": "02",
        "rowsSel": "6",
        "rows": str(rows),
        "cpage": str(page),
        "cat": "",
        "schJrsdCodeTy": "",
        "schWntyAt": "",
        "schAreaDetailCodes": "",
        "schEndAt": "N",
        "orderGb": "",
        "sort": "",
        "schPblancDiv": "01",
        "condition": "searchPblancNm",
        "condition1": "AND",
        "preKeywords": "",
        "keyword": "",
    }


def _is_in_range(posted_at: object, options: ScrapeOptions) -> bool:
    if not posted_at:
        return False

    try:
        posted_date = datetime.fromisoformat(str(posted_at)).date()
    except ValueError:
        return False

    return options.start_date <= posted_date <= options.end_date


def _extract_pblanc_id(url: str) -> str | None:
    values = parse_qs(urlparse(url).query).get("pblancId")
    return values[0] if values else None


def _extract_region(title: str) -> str | None:
    match = REGION_PATTERN.match(title.strip())
    return match.group(1).strip() if match else None


def _parse_date_range(text: str) -> tuple[str | None, str | None]:
    dates = DATE_PATTERN.findall(text)
    if len(dates) >= 2:
        return _normalize_date(dates[0]), _normalize_date(dates[1])
    return None, None


def _normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace(".", "-")


def _parse_int(value: str) -> int | None:
    cleaned = re.sub(r"[^\d]", "", value)
    return int(cleaned) if cleaned else None


def _extract_section_text(full_text: str, start_label: str, end_labels: list[str]) -> str | None:
    start_index = full_text.find(start_label)
    if start_index == -1:
        return None

    start_index += len(start_label)
    end_candidates = [full_text.find(label, start_index) for label in end_labels]
    end_candidates = [index for index in end_candidates if index != -1]
    end_index = min(end_candidates) if end_candidates else len(full_text)
    value = full_text[start_index:end_index].strip()
    return value or None


def _extract_attachments(soup: BeautifulSoup) -> list[dict[str, str]]:
    attachments: list[dict[str, str]] = []
    for link in soup.select("a[href]"):
        text = link.get_text(" ", strip=True)
        href = str(link.get("href", ""))
        if (
            "다운로드" in text
            or "download" in href.lower()
            or "file" in href.lower()
            or re.search(r"\.(pdf|hwp|hwpx|zip|xlsx?|docx?|pptx?)", text, re.I)
        ):
            attachments.append({"name": text, "url": urljoin(BASE_URL, href)})
    return attachments
