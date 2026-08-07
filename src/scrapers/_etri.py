from __future__ import annotations

import re
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from src.contracts.notice import Notice
from src.contracts.scrape_options import ScrapeOptions
from src.scrapers.SITES_INFO import ScrapeTarget


BASE_URL = "https://ebid.etri.re.kr"
LIST_URL = "https://ebid.etri.re.kr/ebid/ebid/ebidCustProgressList.do"
DATE_PATTERN = re.compile(r"\d{4}[.-]\d{2}[.-]\d{2}")
DEBUG_DUMP_DIR = Path("runtime") / "debug" / "etri"
INITIAL_URLS = (
    "https://ebid.etri.re.kr/ebid/index.do",
    "https://ebid.etri.re.kr/ebid/main.do",
    "https://ebid.etri.re.kr/ebid/ebid/ebidCustProgressList.do",
)


@dataclass(frozen=True)
class EtriBidNotice:
    source: str
    bid_no: str
    title: str
    contract_method: str | None
    bid_start_at: str | None
    bid_end_at: str | None
    manager: str | None
    status: str | None
    page_no: int
    detail_action: str | None
    raw_columns: list[str]


class EtriEbidProgressScraper:
    target = ScrapeTarget.ETRI_EBID_PROGRESS

    def __init__(
        self,
        max_pages: int = 20,
        page_interval_seconds: float = 0.5,
        method: Literal["GET", "POST"] = "GET",
        session: requests.Session | None = None,
    ) -> None:
        self.max_pages = max_pages
        self.page_interval_seconds = page_interval_seconds
        self.method = method
        self.session = session or make_session()

    def scrape(self, options: ScrapeOptions) -> list[Notice]:
        from_date, to_date = _resolve_etri_query_range(options)
        scraped_at = datetime.now().astimezone().isoformat(timespec="seconds")
        notices: list[Notice] = []
        initialize_public_session(self.session)
        cs_signature = fetch_initial_cs_signature(self.session)

        for page_no in range(1, self.max_pages + 1):
            html, page_items, next_signature = fetch_and_parse_progress(
                self.session,
                page_no=page_no,
                cs_signature=cs_signature,
                from_date=from_date,
                to_date=to_date,
                preferred_method=self.method,
            )
            if next_signature:
                cs_signature = next_signature

            _print_debug(
                {
                    "page_no": page_no,
                    "from_date": from_date,
                    "to_date": to_date,
                    "html_len": len(html),
                    "has_table01": "#table01" in html or 'id="table01"' in html or "id='table01'" in html,
                    "page_items": len(page_items),
                }
            )

            if not page_items:
                break

            notices.extend(_to_notices(page_items, scraped_at))
            time.sleep(self.page_interval_seconds)

        return _dedupe_notices(notices)


def clean_text(value: str | None) -> str:
    if not value:
        return ""

    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def _resolve_etri_query_range(options: ScrapeOptions) -> tuple[str, str]:
    """ETRI 검색일은 등록일이 아니라 입찰시작일 범위다."""
    start = options.start_date
    end = options.end_date
    min_future_end = date.today() + timedelta(days=90)

    if end < min_future_end:
        end = min_future_end

    return _format_query_date(start.isoformat()), _format_query_date(end.isoformat())


def _print_debug(payload: dict[str, object]) -> None:
    if not _is_debug_enabled():
        return
    print("[ETRI DEBUG]", payload, flush=True)


def _is_debug_enabled() -> bool:
    return str(os.getenv("ETRI_DEBUG") or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Referer": "https://ebid.etri.re.kr/ebid/main.do",
        }
    )
    return session


def extract_cs_signature(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one('input[name="csSignature"]')
    return str(node.get("value")) if node and node.get("value") else None


def initialize_public_session(session: requests.Session) -> None:
    for url in INITIAL_URLS:
        try:
            response = session.get(url, timeout=20)
            response.raise_for_status()
        except requests.RequestException:
            continue
        response.encoding = response.apparent_encoding
        if not is_session_end_page(response.text):
            _print_debug({"session_init_url": url, "html_len": len(response.text)})


def is_session_end_page(html: str) -> bool:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return "다시로그인" in text and "초기화면 이동" in text


def fetch_initial_cs_signature(session: requests.Session) -> str | None:
    for params in ({}, {"first": "Y"}, {"search": "Y"}):
        try:
            response = session.get(LIST_URL, params=params, timeout=20)
            response.raise_for_status()
        except requests.RequestException:
            continue

        response.encoding = response.apparent_encoding
        if is_session_end_page(response.text):
            continue

        signature = extract_cs_signature(response.text)
        if signature:
            return signature

    return None


def build_query_params(
    *,
    page_no: int = 1,
    cs_signature: str | None = None,
    from_date: str,
    to_date: str,
    bid_no: str = "",
    bid_name: str = "",
    contract_method: str = "",
    bid_state: str = "",
) -> list[tuple[str, str]]:
    params: list[tuple[str, str]] = []

    if cs_signature:
        params.append(("csSignature", cs_signature))

    params.extend(
        [
            ("first", "Y" if page_no == 1 else ""),
            ("pageNo", str(page_no)),
            ("biNo", ""),
            ("tabId", ""),
            ("biType", ""),
            ("pageGb", ""),
            ("sch_biBizList", ""),
            ("search", "Y"),
            ("order", ""),
            ("sch_biNo", bid_no),
            ("sch_biName", bid_name),
            ("sch_succDeciMeth", contract_method),
            ("sch_biState", bid_state),
            ("sch_fromDate", from_date),
            ("sch_toDate", to_date),
            ("sch_spotFromDate", ""),
            ("sch_spotToDate", ""),
            ("sch_enterFromDate", ""),
            ("sch_enterToDate", ""),
        ]
    )

    return params


def fetch_progress_html(
    session: requests.Session,
    *,
    page_no: int = 1,
    cs_signature: str | None = None,
    from_date: str,
    to_date: str,
    method: Literal["GET", "POST"] = "GET",
) -> str:
    params = build_query_params(
        page_no=page_no,
        cs_signature=cs_signature,
        from_date=from_date,
        to_date=to_date,
    )

    html = _request_progress_html(session, params=params, method=method)
    if not is_session_end_page(html):
        return html

    initialize_public_session(session)
    html = _request_progress_html(session, params=params, method=method)
    return html


def _request_progress_html(
    session: requests.Session,
    *,
    params: list[tuple[str, str]],
    method: Literal["GET", "POST"],
) -> str:
    if method == "POST":
        response = session.post(LIST_URL, data=params, timeout=20)
    else:
        response = session.get(LIST_URL, params=params, timeout=20)

    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return response.text


def fetch_and_parse_progress(
    session: requests.Session,
    *,
    page_no: int,
    cs_signature: str | None,
    from_date: str,
    to_date: str,
    preferred_method: Literal["GET", "POST"],
) -> tuple[str, list[EtriBidNotice], str | None]:
    methods: list[Literal["GET", "POST"]] = [preferred_method]
    fallback_method: Literal["GET", "POST"] = "POST" if preferred_method == "GET" else "GET"
    methods.append(fallback_method)

    last_html = ""
    last_signature: str | None = None

    for method in methods:
        html = fetch_progress_html(
            session,
            page_no=page_no,
            cs_signature=cs_signature,
            from_date=from_date,
            to_date=to_date,
            method=method,
        )
        last_html = html
        last_signature = extract_cs_signature(html)
        page_items = parse_progress_html(html, page_no=page_no)
        dump_path = _dump_debug_html(html, page_no=page_no, method=method)
        _print_debug(
            {
                "method": method,
                "page_no": page_no,
                "from_date": from_date,
                "to_date": to_date,
                "html_len": len(html),
                "has_table01": "#table01" in html or 'id="table01"' in html or "id='table01'" in html,
                "table_count": html.lower().count("<table"),
                "page_items": len(page_items),
                "dump_path": str(dump_path) if dump_path else None,
                "text_sample": _html_text_sample(html),
            }
        )
        if page_items:
            return html, page_items, last_signature

    return last_html, [], last_signature


def _dump_debug_html(html: str, *, page_no: int, method: str) -> Path | None:
    if not _is_debug_enabled():
        return None

    DEBUG_DUMP_DIR.mkdir(parents=True, exist_ok=True)
    path = DEBUG_DUMP_DIR / f"progress_page_{page_no}_{method.lower()}.html"
    path.write_text(html, encoding="utf-8")
    return path


def _html_text_sample(html: str, max_length: int = 500) -> str:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return text[:max_length]


def parse_progress_html(html: str, page_no: int = 1) -> list[EtriBidNotice]:
    soup = BeautifulSoup(html, "html.parser")
    tables = _find_progress_tables(soup)
    if not tables:
        return []

    notices: list[EtriBidNotice] = []

    for table in tables:
        for tr in table.select("tr"):
            parsed = _parse_progress_row(tr, page_no)
            if parsed is not None:
                notices.append(parsed)

    return notices


def _find_progress_tables(soup: BeautifulSoup):
    table = soup.select_one("#table01")
    if table is not None:
        return [table]

    tables = []
    for candidate in soup.select("table"):
        text = candidate.get_text(" ", strip=True)
        if "입찰공고번호" in text or "입찰공고명" in text or "입찰시작일시" in text:
            tables.append(candidate)
    return tables


def _parse_progress_row(tr, page_no: int) -> EtriBidNotice | None:
    columns = [clean_text(td.get_text(" ", strip=True)) for td in tr.select("td")]
    if len(columns) < 7:
        return None
    if "입찰공고번호" in columns:
        return None

    offset = _find_bid_column_offset(columns)
    if offset is None or len(columns) < offset + 7:
        return None

    bid_no = columns[offset]
    title = columns[offset + 1]
    detail_action = None
    onclick_bid_no = None

    for node in tr.select("[onclick]"):
        onclick = str(node.get("onclick", ""))
        match = re.search(r"fnDetailCustView\([\"']([^\"']+)[\"']\)", onclick)
        if match:
            onclick_bid_no = match.group(1)
            detail_action = onclick
            break

    if onclick_bid_no:
        bid_no = onclick_bid_no
    if not bid_no or not title:
        return None

    return EtriBidNotice(
        source=ScrapeTarget.ETRI_EBID_PROGRESS.source_name,
        bid_no=bid_no,
        title=title,
        contract_method=columns[offset + 2] or None,
        bid_start_at=columns[offset + 3] or None,
        bid_end_at=columns[offset + 4] or None,
        manager=columns[offset + 5] or None,
        status=columns[offset + 6] or None,
        page_no=page_no,
        detail_action=detail_action,
        raw_columns=columns,
    )


def _find_bid_column_offset(columns: list[str]) -> int | None:
    for index, column in enumerate(columns[:3]):
        if _looks_like_bid_no(column):
            return index
    return None


def _looks_like_bid_no(value: str) -> bool:
    return bool(re.search(r"\b[A-Z]{1,4}\d{6,}(?:\(\d+\))?\b", value, re.I))


def parse_max_page(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    page_numbers = []

    for a in soup.select("a[href]"):
        href = str(a.get("href", ""))
        match = re.search(r"gotoPage\((\d+)", href)
        if match:
            page_numbers.append(int(match.group(1)))

    return max(page_numbers) if page_numbers else 1


def _to_notices(items: list[EtriBidNotice], scraped_at: str) -> list[Notice]:
    notices: list[Notice] = []
    for item in items:
        posted_at = _extract_date(item.bid_start_at)
        if posted_at is None:
            continue

        deadline = _extract_date(item.bid_end_at)
        notices.append(
            {
                "source": item.source,
                "title": item.title,
                "url": _build_bid_url(item.bid_no),
                "posted_at": posted_at,
                "deadline": deadline,
                "scraped_at": scraped_at,
                "keywords": [],
                "detail_points": _build_detail_points(item),
                "application_period": _build_application_period(item.bid_start_at, item.bid_end_at),
                "application_start_at": posted_at,
                "application_end_at": deadline,
                "department": item.manager,
                "pblanc_id": item.bid_no,
                "analysis": False,
            }
        )
    return notices


def _build_detail_points(item: EtriBidNotice) -> list[str]:
    points = [f"입찰공고번호: {item.bid_no}"]
    if item.contract_method:
        points.append(f"계약방법: {item.contract_method}")
    if item.bid_start_at:
        points.append(f"입찰시작: {item.bid_start_at}")
    if item.bid_end_at:
        points.append(f"입찰종료: {item.bid_end_at}")
    if item.manager:
        points.append(f"담당자: {item.manager}")
    if item.status:
        points.append(f"진행상태: {item.status}")
    return points


def _build_application_period(start_at: str | None, end_at: str | None) -> str | None:
    if start_at and end_at:
        return f"{start_at} ~ {end_at}"
    return start_at or end_at


def _extract_date(value: str | None) -> str | None:
    if not value:
        return None
    match = DATE_PATTERN.search(value)
    if match is None:
        return None
    return match.group(0).replace(".", "-")


def _format_query_date(value: str) -> str:
    return value.replace("-", "")[:8]


def _build_bid_url(bid_no: str) -> str:
    return f"/api/etri/original?{urlencode({'bid_no': bid_no})}"


def _dedupe_notices(notices: list[Notice]) -> list[Notice]:
    deduped: list[Notice] = []
    seen: set[tuple[str, str, str]] = set()
    for notice in notices:
        key = (str(notice.get("source")), str(notice.get("pblanc_id") or notice.get("url")), str(notice.get("title")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(notice)
    return deduped
