"""신규 공고 목록을 외부 알림 메시지로 변환한다.
현재는 Google Chat Incoming Webhook 전송만 담당한다."""

from __future__ import annotations

from urllib import request
import json

from src.contracts.notice import Notice


def build_new_notice_message(notices: list[Notice]) -> str:
    lines = ["[정부지원사업 신규 공고]"]

    for notice in notices:
        title = notice.get("title", "제목 없음")
        url = notice.get("url", "")
        lines.append(f"- {title}")
        if url:
            lines.append(f"  {url}")

    return "\n".join(lines)


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
