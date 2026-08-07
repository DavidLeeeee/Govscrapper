from __future__ import annotations

import re
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

from src.scrapers._etri import (
    BASE_URL,
    LIST_URL,
    extract_cs_signature,
    initialize_public_session,
    is_session_end_page,
    make_session,
)
from src.services.detail_fetch_service import extract_readable_text


DETAIL_URL_CANDIDATES = (
    "https://ebid.etri.re.kr/ebid/ebid/ebidCustInfoMainView.do",
    "https://ebid.etri.re.kr/ebid/ebid/ebidCustProgressList.do",
    "https://ebid.etri.re.kr/ebid/ebid/ebidCustProgressDetail.do",
    "https://ebid.etri.re.kr/ebid/ebid/ebidCustProgressView.do",
    "https://ebid.etri.re.kr/ebid/ebid/ebidCustDetail.do",
)


def build_etri_original_url(bid_no: str) -> str:
    return f"/api/etri/original?{urlencode({'bid_no': bid_no})}"


def fetch_etri_detail_html(bid_no: str, timeout: int = 20) -> str:
    session = make_session()
    initialize_public_session(session)
    cs_signature = _fetch_cs_signature(session, timeout=timeout)

    last_html = ""
    for detail_url in DETAIL_URL_CANDIDATES:
        for payload in _detail_payload_candidates(bid_no, cs_signature):
            for method in ("POST", "GET"):
                html = _request_detail(
                    session,
                    detail_url=detail_url,
                    payload=payload,
                    method=method,
                    timeout=timeout,
                )
                last_html = html
                if _looks_like_detail_html(html, bid_no):
                    return _rewrite_relative_links(html, detail_url)

    return _rewrite_relative_links(last_html, LIST_URL)


def debug_etri_detail_candidates(bid_no: str, timeout: int = 20) -> list[dict[str, object]]:
    session = make_session()
    initialize_public_session(session)
    cs_signature = _fetch_cs_signature(session, timeout=timeout)

    results: list[dict[str, object]] = []
    for detail_url in DETAIL_URL_CANDIDATES:
        for payload in _detail_payload_candidates(bid_no, cs_signature):
            for method in ("POST", "GET"):
                html = _request_detail(
                    session,
                    detail_url=detail_url,
                    payload=payload,
                    method=method,
                    timeout=timeout,
                )
                results.append(
                    {
                        "url": detail_url,
                        "method": method,
                        "pageGb": _payload_value(payload, "pageGb"),
                        "biNo": _payload_value(payload, "biNo"),
                        "html_len": len(html),
                        "looks_like_detail": _looks_like_detail_html(html, bid_no),
                        "title": _html_title(html),
                        "text_sample": BeautifulSoup(html, "html.parser").get_text(" ", strip=True)[:300],
                    }
                )
    return results


def fetch_etri_notice_materials(bid_no: str, timeout: int = 20) -> dict[str, object]:
    html = fetch_etri_detail_html(bid_no, timeout=timeout)
    return {
        "detail_text": extract_readable_text(html),
        "attachments": _extract_etri_attachments(html, LIST_URL),
    }


def extract_etri_posted_at(html: str) -> str | None:
    return _extract_labeled_date(html, "공고일시")


def extract_etri_budget_text(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for label in soup.find_all(["td", "th"]):
        label_text = _normalize_text(label.get_text(" ", strip=True))
        if "추정금액" not in label_text:
            continue

        value_cell = label.find_next_sibling(["td", "th"])
        if value_cell is None:
            continue

        value = _normalize_text(value_cell.get_text(" ", strip=True))
        if value and value != "원":
            return value

    return None


def get_etri_session() -> requests.Session:
    session = make_session()
    initialize_public_session(session)
    return session


def _fetch_cs_signature(session: requests.Session, timeout: int) -> str | None:
    try:
        response = session.get(LIST_URL, params={"first": "Y"}, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException:
        return None

    response.encoding = response.apparent_encoding
    return extract_cs_signature(response.text)


def _request_detail(
    session: requests.Session,
    *,
    detail_url: str,
    payload: list[tuple[str, str]],
    method: str,
    timeout: int,
) -> str:
    if method == "POST":
        response = session.post(detail_url, data=payload, timeout=timeout)
    else:
        response = session.get(detail_url, params=payload, timeout=timeout)

    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return response.text


def _detail_payload_candidates(bid_no: str, cs_signature: str | None) -> list[list[tuple[str, str]]]:
    # DevTools 기준 상세 화면은 ebidCustInfoMainView.do POST + pageGb 빈 값으로 렌더링된다.
    page_gb_candidates = ("", "D", "V", "R", "S")
    return [_detail_payload(bid_no, cs_signature, page_gb) for page_gb in page_gb_candidates]


def _detail_payload(bid_no: str, cs_signature: str | None, page_gb: str) -> list[tuple[str, str]]:
    payload: list[tuple[str, str]] = []
    if cs_signature:
        payload.append(("csSignature", cs_signature))
    payload.extend(
        [
            ("pageNo", "1"),
            ("biNo", bid_no),
            ("tabId", ""),
            ("biType", ""),
            ("pageGb", page_gb),
            ("sch_biBizList", ""),
            ("search", "Y"),
            ("order", ""),
            ("sch_biNo", ""),
            ("sch_biName", ""),
            ("sch_succDeciMeth", ""),
            ("sch_biState", ""),
            ("sch_fromDate", "20260730"),
            ("sch_toDate", "20261006"),
            ("sch_spotFromDate", ""),
            ("sch_spotToDate", ""),
            ("sch_enterFromDate", ""),
            ("sch_enterToDate", ""),
            ("interestBiNo", bid_no),
        ]
    )
    return payload


def _looks_like_detail_html(html: str, bid_no: str) -> bool:
    if not html or is_session_end_page(html):
        return False

    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    title = _html_title(html)
    if "입찰내용" in title and bid_no in html:
        return True
    if "입찰공고번호" in text and bid_no in text:
        return True
    if "입찰공고명" in text and bid_no in html:
        return True
    if "첨부" in text and bid_no in html:
        return True
    return False


def _payload_value(payload: list[tuple[str, str]], key: str) -> str:
    for name, value in payload:
        if name == key:
            return value
    return ""


def _html_title(html: str) -> str:
    title = BeautifulSoup(html, "html.parser").select_one("title")
    return title.get_text(" ", strip=True) if title else ""


def _extract_labeled_date(html: str, label_name: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for label in soup.find_all(["td", "th"]):
        if _normalize_text(label.get_text(" ", strip=True)) != label_name:
            continue

        value_cell = label.find_next_sibling(["td", "th"])
        if value_cell is None:
            continue

        parsed = _parse_korean_or_iso_date(value_cell.get_text(" ", strip=True))
        if parsed:
            return parsed

    return None


def _parse_korean_or_iso_date(value: str) -> str | None:
    text = _normalize_text(value)
    korean_match = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if korean_match:
        year, month, day = korean_match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    iso_match = re.search(r"(\d{4})[.-](\d{1,2})[.-](\d{1,2})", text)
    if iso_match:
        year, month, day = iso_match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    return None


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def _rewrite_relative_links(html: str, base_url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag_name, attribute in (("a", "href"), ("link", "href"), ("script", "src"), ("img", "src")):
        for tag in soup.select(f"{tag_name}[{attribute}]"):
            value = str(tag.get(attribute) or "").strip()
            if value and not value.lower().startswith(("javascript:", "#", "data:")):
                tag[attribute] = urljoin(base_url, value)
    return str(soup)


def _extract_etri_attachments(html: str, base_url: str) -> list[dict[str, str]]:
    from src.services.deep_analysis.attachment_discovery import _extract_attachments

    attachments = _extract_attachments(html, base_url)
    attachments.extend(_extract_file_download_enc_attachments(html))
    return _dedupe_attachments(attachments)


def _extract_file_download_enc_attachments(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    attachments: list[dict[str, str]] = []
    pattern = re.compile(r"fileDownloadEncStr\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)")

    for link in soup.select("[onclick]"):
        onclick = str(link.get("onclick") or "")
        match = pattern.search(onclick)
        if match is None:
            continue

        name = link.get_text(" ", strip=True) or "ETRI 첨부파일"
        enc_str, file_type, work = match.groups()
        attachments.append(
            {
                "name": name,
                "url": "https://ebid.etri.re.kr/ebid/commons/fileDownloadEncStr.do",
                "method": "POST",
                "data": urlencode(
                    {
                        "encStr": enc_str,
                        "fileType": file_type,
                        "work": work,
                    }
                ),
                "referer": "https://ebid.etri.re.kr/ebid/ebid/ebidCustInfoMainView.do",
            }
        )
    return attachments


def _dedupe_attachments(attachments: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for attachment in attachments:
        signature = "|".join(
            [
                str(attachment.get("url") or ""),
                str(attachment.get("method") or "GET"),
                str(attachment.get("data") or ""),
            ]
        )
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(attachment)
    return deduped
