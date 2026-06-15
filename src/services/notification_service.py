"""신규 공고 목록을 외부 알림 메시지로 변환한다.
현재는 Google Chat Incoming Webhook 전송만 담당한다."""

from __future__ import annotations

from urllib import request
import json
from collections import Counter

from src.contracts.notice import MarkRecord, Notice


def build_new_notice_message(notices: list[Notice]) -> str:
    lines = ["[정부지원사업 신규 공고]"]

    for notice in notices:
        title = notice.get("title", "제목 없음")
        url = notice.get("url", "")
        lines.append(f"- {title}")
        if url:
            lines.append(f"  {url}")

    return "\n".join(lines)


def build_daily_scraping_message(
    new_notices: list[Notice],
    new_regional_notices: list[Notice],
    new_mark_records: list[MarkRecord],
    total_mark_count: int,
    site_url: str | None = None,
) -> str:
    lines = [
        "*📢 정부지원사업 공고 알림 📢*",
        f"`일반 {len(new_notices)}건`  `지역 {len(new_regional_notices)}건`  `북마크 {len(new_mark_records)}건`",
        "",
    ]

    lines.append("*📍 신규 일반 공고*")
    if new_notices:
        for notice in new_notices:
            title = str(notice.get("title") or "제목 없음").strip()
            url = str(notice.get("url") or "").strip()
            deadline = _display_deadline(notice)
            title_text = _chat_link(url, title)
            lines.append(f"{title_text}  ⏰ 마감 {deadline}")
    else:
        lines.append("- 신규 공고 없음")

    lines.extend(["", "*📍 신규 지역 공고*"])
    if new_regional_notices:
        region_counts = _count_regions(new_regional_notices)
        summary = " / ".join(f"{region} {count}건" for region, count in region_counts.items())
        lines.append(summary)
    else:
        lines.append("신규 지역 공고 없음")

    lines.extend(["", "*⭐ 신규 북마크*"])
    if new_mark_records:
        for record in new_mark_records:
            title = str(record.get("title") or "제목 없음").strip()
            url = str(record.get("url") or "").strip()
            suffix = "가" if title.endswith("공고") else " 공고가"
            lines.append(f"- {_chat_link(url, title)}{suffix} 신규 북마크로 추가되었습니다. 확인 바랍니다.")
    else:
        lines.append("신규 북마크 없음")
    lines.append(f"총 북마크 {total_mark_count}건")

    if site_url:
        lines.extend(["", f"🔎 {_chat_link(site_url, '공고 조회 바로가기')}"])

    return "\n".join(lines)


def _count_regions(notices: list[Notice]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for notice in notices:
        region = str(notice.get("region") or "").strip() or "지역 미분류"
        counter[region] += 1
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def _display_deadline(notice: Notice) -> str:
    deadline = str(notice.get("deadline") or "").strip()
    if deadline:
        return deadline

    ai_deadline = str(notice.get("ai_deadline") or "").strip()
    confidence = str(notice.get("ai_deadline_confidence") or "").strip().lower()
    if ai_deadline and confidence == "high":
        return ai_deadline

    return "확인 필요"


def _chat_link(url: str | None, label: str) -> str:
    clean_url = str(url or "").strip()
    clean_label = str(label or "").strip() or clean_url
    if not clean_url:
        return clean_label
    return f"<{clean_url}|{clean_label}>"


def send_google_chat_message(webhook_url: str, text: str) -> None:
    payload = json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")
    http_request = request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    with request.urlopen(http_request, timeout=10):
        pass
