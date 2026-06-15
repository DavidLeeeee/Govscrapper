from __future__ import annotations

import time
from dataclasses import dataclass
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
SUB_GOVERNMENT_CODES = (
    "AR4999",
    "AR4001",
    "AR4002",
    "AR4003",
    "AR4004",
    "AR4005",
    "AR4006",
    "AR4007",
    "AR4008",
    "AR4009",
    "AR4010",
    "AR4011",
    "AR4012",
    "AR4013",
    "AR4014",
    "AR4015",
    "AR4016",
    "AR4017",
    "AR4018",
    "AR4902",
    "AR4903",
    "AR4904",
    "AR4908",
    "AR4911",
    "AR4915",
    "AR4916",
    "AR4930",
    "AR4932",
    "AR4933",
    "AR4981",
    "AR4986",
    "AR4988",
    "AR4019",
    "AR4021",
)
SUB_ORGANIZATION_IDS = (
    "10000",
    "10001",
    "10002",
    "10003",
    "10004",
    "10005",
    "10006",
    "10007",
    "10008",
    "10009",
    "10010",
    "10011",
    "10012",
    "10013",
    "10014",
    "10015",
    "10016",
    "10017",
    "10018",
    "10019",
    "10020",
    "10021",
    "10022",
    "10023",
    "10024",
    "10025",
    "10026",
    "10027",
    "10028",
    "10029",
    "10030",
    "10031",
    "10032",
    "10035",
    "10036",
    "10043",
    "10045",
    "10046",
    "10047",
    "10050",
    "10051",
    "10052",
)
SUB_TECH_FIELDS = ("EE", "OC")


@dataclass(frozen=True)
class IrisQueryProfile:
    name: str
    government_codes: tuple[str, ...]
    allowed_government_names: tuple[str, ...] | None = None
    organization_ids: tuple[str, ...] = ()
    tech_fields: tuple[str, ...] = ()
    select_all_governments: bool = False
    select_all_organizations: bool = False
    announcement_progress: str | None = None


SUB_QUERY_PROFILE = IrisQueryProfile(
    name="SUB",
    government_codes=SUB_GOVERNMENT_CODES,
    organization_ids=SUB_ORGANIZATION_IDS,
    tech_fields=SUB_TECH_FIELDS,
    select_all_governments=True,
    select_all_organizations=True,
    announcement_progress="ancmIng",
)


class IrisBtinSituScraper:
    target = ScrapeTarget.IRIS_BTIN_SITU

    def __init__(
        self,
        max_pages: int = 20,
        page_interval_seconds: float = 1.0,
        government_codes: tuple[str, ...] = DEFAULT_GOVERNMENT_CODES,
        allowed_government_names: tuple[str, ...] = DEFAULT_GOVERNMENT_NAMES,
        include_sub_query: bool = True,
        session: requests.Session | None = None,
    ) -> None:
        self.max_pages = max_pages
        self.page_interval_seconds = page_interval_seconds
        self.government_codes = government_codes
        self.allowed_government_names = allowed_government_names
        self.include_sub_query = include_sub_query
        self.session = session or _make_session()

    def scrape(self, options: ScrapeOptions) -> list[Notice]:
        profiles = [
            IrisQueryProfile(
                name="MAIN",
                government_codes=self.government_codes,
                allowed_government_names=self.allowed_government_names,
            )
        ]
        if self.include_sub_query:
            profiles.append(SUB_QUERY_PROFILE)

        notices: list[Notice] = []
        seen_keys: set[tuple[str, str, str, str]] = set()

        for profile in profiles:
            profile_notices = self._scrape_profile(options, profile)
            for notice in profile_notices:
                key = _notice_identity(notice)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                notices.append(notice)

        return notices

    def _scrape_profile(self, options: ScrapeOptions, profile: IrisQueryProfile) -> list[Notice]:
        notices: list[Notice] = []

        for page in range(1, self.max_pages + 1):
            rows = self._fetch_list_page(page, profile)
            if not rows:
                break

            page_notices = [
                _row_to_notice(row)
                for row in rows
                if _is_allowed_government_name(row, profile.allowed_government_names)
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

    def _fetch_list_page(self, page: int, profile: IrisQueryProfile) -> list[dict[str, Any]]:
        payload = _build_list_payload(page, profile)
        response = self.session.post(LIST_API_URL, data=payload, timeout=15)
        response.raise_for_status()
        data = response.json()

        rows = data.get("listBsnsAncmBtinSitu", [])
        if not isinstance(rows, list):
            return []

        return [row for row in rows if isinstance(row, dict)]


def _build_list_payload(page: int, profile: IrisQueryProfile) -> list[tuple[str, str | int]]:
    if profile.name == "MAIN":
        payload: list[tuple[str, str | int]] = [
            ("pageIndex", page),
            ("blngGovdSeArr", "|".join(profile.government_codes)),
        ]
        for government_code in profile.government_codes:
            payload.append(("blngGovdSe[]", government_code))
        return payload

    payload = [
        ("pageIndex", page),
        ("ancmId", ""),
        ("ancmNo", ""),
        ("ancmTurn", ""),
        ("seq", ""),
        ("hirkSorgnBsnsCd", ""),
        ("bsnsAncmTap", ""),
        ("shSorgnYyBsnsCd", ""),
        ("ancmSttArr", ""),
        ("pbofrTpArr", ""),
        ("qualCndtArr", ""),
        ("blngGovdSeArr", "|".join(profile.government_codes)),
    ]
    if profile.announcement_progress:
        payload.append(("ancmPrg", profile.announcement_progress))
    if profile.select_all_governments:
        payload.append(("selectAllBlngGovdSe", "all"))
    for government_code in profile.government_codes:
        payload.append(("blngGovdSe[]", government_code))

    if profile.organization_ids:
        payload.append(("sorgnIdArr", "|".join(profile.organization_ids)))
    if profile.select_all_organizations:
        payload.append(("selectAllsorgnId", "on"))
    for organization_id in profile.organization_ids:
        payload.append(("sorgnId[]", organization_id))

    if profile.tech_fields:
        payload.append(("techFildArr", "|".join(profile.tech_fields)))
    for tech_field in profile.tech_fields:
        payload.append(("techFild[]", tech_field))

    return payload


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


def _is_allowed_government_name(row: dict[str, Any], allowed_government_names: tuple[str, ...] | None) -> bool:
    if allowed_government_names is None:
        return True
    government_name = _first_text(row, "blngGovdSeNm", "blngGovdSe")
    return government_name in allowed_government_names


def _build_detail_url(ancm_id: str, sorgn_id: str) -> str:
    query = {"ancmId": ancm_id}
    if sorgn_id:
        query["sorgnId"] = sorgn_id
    return f"{DETAIL_URL}?{urlencode(query)}"


def _notice_identity(notice: Notice) -> tuple[str, str, str, str]:
    return (
        str(notice.get("source") or ""),
        str(notice.get("url") or ""),
        str(notice.get("title") or ""),
        str(notice.get("posted_at") or ""),
    )
