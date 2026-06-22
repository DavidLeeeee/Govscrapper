from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime
from urllib.parse import urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from src.contracts.notice import Notice
from src.contracts.scrape_options import ScrapeOptions
from src.scrapers.SITES_INFO import ScrapeTarget


BASE_URL = "https://www.k-global.kr"
LIST_URL = "https://www.k-global.kr/support/support.do"
DATE_PATTERN = re.compile(r"\d{4}[.-]\d{2}[.-]\d{2}")
STATUS_PATTERN = re.compile(r"공고\s*중|공고마감")
TYPE_PATTERN = re.compile(r"멘토링[· ]컨설팅|멘토링 컨설팅|인프라|디지털자원|스케일업|해외진출|기술개발|청년정책|기타")


class KglobalScraper:
    target = ScrapeTarget.KGLOBAL

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
        scraped_at = datetime.now().astimezone().isoformat(timespec="seconds")

        notices = _parse_table_notices(soup, page, self.target.source_name, scraped_at)
        if notices:
            return notices

        return _parse_text_notices(soup, page, self.target.source_name, scraped_at)


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
        params={"curPage": page},
        timeout=15,
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, "html.parser")


def _parse_table_notices(
    soup: BeautifulSoup,
    page: int,
    source_name: str,
    scraped_at: str,
) -> list[Notice]:
    notices: list[Notice] = []
    seen: set[tuple[str, str]] = set()

    for row in soup.select("tr"):
        if not isinstance(row, Tag):
            continue

        cells = [cell.get_text(" ", strip=True) for cell in row.select("th, td")]
        if len(cells) < 8:
            continue

        parsed = _parse_cells(cells)
        if parsed is None:
            continue

        title_link = _find_title_link(row, parsed["title"])
        url = _build_detail_url(title_link, page, parsed["title"], parsed["posted_at"])
        key = (parsed["title"], parsed["posted_at"])
        if key in seen:
            continue
        seen.add(key)

        notices.append(_build_notice(source_name, scraped_at, url, parsed))

    return notices


def _parse_cells(cells: list[str]) -> dict[str, str | None] | None:
    dates = [date for cell in cells for date in DATE_PATTERN.findall(cell)]
    if len(dates) < 3:
        return None

    status = _first_match(cells, STATUS_PATTERN)
    category = _first_match(cells, TYPE_PATTERN)
    period_start = _normalize_date(dates[0])
    period_end = _normalize_date(dates[1])
    posted_at = _normalize_date(dates[2])

    title = _find_title_from_cells(cells, status, category)
    if title is None:
        return None

    organization = _find_organization_from_cells(cells, posted_at)

    return {
        "title": title,
        "posted_at": posted_at,
        "deadline": period_end,
        "application_period": f"{period_start} ~ {period_end}",
        "status": status,
        "category": category,
        "organization": organization,
    }


def _parse_text_notices(
    soup: BeautifulSoup,
    page: int,
    source_name: str,
    scraped_at: str,
) -> list[Notice]:
    lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]
    split_notices = _parse_split_text_notices(soup, lines, page, source_name, scraped_at)
    if split_notices:
        return split_notices

    notices: list[Notice] = []
    seen: set[tuple[str, str]] = set()

    for line in lines:
        parsed = _parse_notice_line(line)
        if parsed is None:
            continue

        title_link = _find_link_by_title(soup, parsed["title"] or "")
        url = _build_detail_url(title_link, page, parsed["title"] or "", parsed["posted_at"] or "")
        key = (str(parsed["title"]), str(parsed["posted_at"]))
        if key in seen:
            continue
        seen.add(key)

        notices.append(_build_notice(source_name, scraped_at, url, parsed))

    return notices


def _parse_split_text_notices(
    soup: BeautifulSoup,
    lines: list[str],
    page: int,
    source_name: str,
    scraped_at: str,
) -> list[Notice]:
    notices: list[Notice] = []
    seen: set[tuple[str, str]] = set()
    index = 0

    while index < len(lines):
        if not lines[index].isdigit():
            index += 1
            continue

        parsed = _parse_notice_block(lines, index)
        if parsed is None:
            index += 1
            continue

        title = parsed["title"] or ""
        posted_at = parsed["posted_at"] or ""
        title_link = _find_link_by_title(soup, title)
        url = _build_detail_url(title_link, page, title, posted_at)
        key = (title, posted_at)
        if key not in seen:
            seen.add(key)
            notices.append(_build_notice(source_name, scraped_at, url, parsed))

        index = int(parsed["_next_index"] or index + 1)

    return notices


def _parse_notice_block(lines: list[str], start_index: int) -> dict[str, str | None] | None:
    if start_index + 5 >= len(lines):
        return None

    status_match = STATUS_PATTERN.fullmatch(lines[start_index + 1])
    category_match = TYPE_PATTERN.fullmatch(lines[start_index + 2])
    if status_match is None or category_match is None:
        return None

    title_parts: list[str] = []
    index = start_index + 3
    while index < len(lines):
        dates = DATE_PATTERN.findall(lines[index])
        if len(dates) >= 2:
            break
        title_parts.append(lines[index])
        index += 1

    if index >= len(lines):
        return None

    period_dates = DATE_PATTERN.findall(lines[index])
    if len(period_dates) < 2:
        return None

    title = " ".join(title_parts).strip()
    if not _is_title(title):
        return None

    period_start = _normalize_date(period_dates[0])
    period_end = _normalize_date(period_dates[1])
    organization = lines[index + 1].strip() if index + 1 < len(lines) else None
    posted_at = _find_next_date_line(lines, index + 2)
    if posted_at is None:
        return None

    next_index = _find_next_numeric_index(lines, index + 2)

    return {
        "title": title,
        "posted_at": posted_at,
        "deadline": period_end,
        "application_period": f"{period_start} ~ {period_end}",
        "status": _normalize_status(status_match.group(0)),
        "category": _normalize_category(category_match.group(0)),
        "organization": organization,
        "_next_index": str(next_index),
    }


def _parse_notice_line(line: str) -> dict[str, str | None] | None:
    dates = DATE_PATTERN.findall(line)
    if len(dates) < 3:
        return None
    if not re.match(r"^\d+\s+", line):
        return None

    status_match = STATUS_PATTERN.search(line)
    type_match = TYPE_PATTERN.search(line)
    if status_match is None or type_match is None:
        return None

    period_start = _normalize_date(dates[0])
    period_end = _normalize_date(dates[1])
    posted_at = _normalize_date(dates[2])
    title_start = type_match.end()
    title_end = line.find(dates[0], title_start)
    title = line[title_start:title_end].strip()
    if not _is_title(title):
        return None

    period_end_index = line.find(dates[1], title_end)
    rest_start = period_end_index + len(dates[1])
    rest_end = line.find(dates[2], rest_start)
    organization = line[rest_start:rest_end].strip() or None

    return {
        "title": title,
        "posted_at": posted_at,
        "deadline": period_end,
        "application_period": f"{period_start} ~ {period_end}",
        "status": _normalize_status(status_match.group(0)),
        "category": _normalize_category(type_match.group(0)),
        "organization": organization,
    }


def _find_next_date_line(lines: list[str], start_index: int) -> str | None:
    for line in lines[start_index : min(len(lines), start_index + 5)]:
        dates = DATE_PATTERN.findall(line)
        if len(dates) == 1:
            return _normalize_date(dates[0])
    return None


def _find_next_numeric_index(lines: list[str], start_index: int) -> int:
    for index in range(start_index, len(lines)):
        if lines[index].isdigit():
            return index
    return len(lines)



def _build_notice(
    source_name: str,
    scraped_at: str,
    url: str,
    parsed: dict[str, str | None],
) -> Notice:
    detail_points = []
    if parsed.get("status"):
        detail_points.append(f"공고상태: {parsed['status']}")
    if parsed.get("category"):
        detail_points.append(f"사업유형: {parsed['category']}")
    if parsed.get("application_period"):
        detail_points.append(f"접수기간: {parsed['application_period']}")
    if parsed.get("organization"):
        detail_points.append(f"기관명: {parsed['organization']}")

    return {
        "source": source_name,
        "title": str(parsed["title"]),
        "url": url,
        "posted_at": str(parsed["posted_at"]),
        "deadline": parsed.get("deadline"),
        "scraped_at": scraped_at,
        "keywords": [],
        "detail_points": detail_points,
        "analysis": False,
    }


def _find_title_from_cells(cells: list[str], status: str | None, category: str | None) -> str | None:
    excluded = {
        "번호",
        "제목",
        "접수기간",
        "기관명",
        "작성일",
        "조회수",
        status or "",
        category or "",
    }
    for cell in cells:
        if cell in excluded:
            continue
        if DATE_PATTERN.search(cell):
            continue
        if cell.isdigit():
            continue
        if _is_title(cell):
            return cell
    return None


def _find_organization_from_cells(cells: list[str], posted_at: str) -> str | None:
    previous = ""
    for cell in cells:
        if _normalize_date(cell) == posted_at:
            return previous or None
        if cell and not DATE_PATTERN.search(cell):
            previous = cell
    return None


def _find_title_link(row: Tag, title: str) -> Tag | None:
    exact_match = _find_link_by_title(row, title)
    if exact_match is not None:
        return exact_match

    links = [link for link in row.find_all("a", href=True) if isinstance(link, Tag)]
    if not links:
        return None

    return max(links, key=lambda link: len(link.get_text(" ", strip=True)))


def _find_link_by_title(root: Tag | BeautifulSoup, title: str) -> Tag | None:
    if not title:
        return None

    for link in root.find_all("a", href=True):
        if not isinstance(link, Tag):
            continue
        link_title = link.get_text(" ", strip=True)
        if link_title == title or title in link_title:
            return link
    return None


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
    return f"{LIST_URL}?{urlencode({'mode': 'view', 'idx': numbers[-1]})}"


def _build_fallback_url(page: int, title: str, posted_at: str) -> str:
    digest = hashlib.sha1(f"{page}:{posted_at}:{title}".encode("utf-8")).hexdigest()[:12]
    return f"{LIST_URL}?{urlencode({'curPage': page})}#notice-{digest}"


def _first_match(cells: list[str], pattern: re.Pattern[str]) -> str | None:
    for cell in cells:
        match = pattern.search(cell)
        if match is not None:
            value = match.group(0)
            if pattern is STATUS_PATTERN:
                return _normalize_status(value)
            if pattern is TYPE_PATTERN:
                return _normalize_category(value)
            return value.strip()
    return None


def _normalize_date(value: str) -> str:
    match = DATE_PATTERN.search(value)
    if match is None:
        return value.replace(".", "-")[:10]
    return match.group(0).replace(".", "-")


def _normalize_status(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_category(value: str) -> str:
    return value.replace(" ", "·") if value == "멘토링 컨설팅" else value.strip()


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
