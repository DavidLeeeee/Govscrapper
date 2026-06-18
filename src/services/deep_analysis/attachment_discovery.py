from __future__ import annotations

import re
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

from src.contracts.notice import Notice
from src.services.detail_fetch_service import DEFAULT_HEADERS, extract_readable_text


FILE_HINT_PATTERN = re.compile(
    r"download|file|attach|atch|첨부|다운로드|\.(pdf|hwp|hwpx|docx?|xlsx?|pptx?|zip|txt)(\?|$)",
    re.I,
)
JS_CALL_PATTERN = re.compile(r"(?:javascript\s*:\s*)?([A-Za-z_$][\w$]*)\s*\((?P<args>.*)\)\s*;?", re.S)
JS_ARG_PATTERN = re.compile(r"""['"]([^'"]*)['"]|([^,\s][^,]*)""")


def discover_notice_materials(notice: Notice, timeout: int = 15) -> dict[str, object]:
    detail_url = str(notice.get("url") or "").strip()
    html = ""
    detail_text = ""
    attachments = _notice_attachments(notice)

    if detail_url:
        response = requests.get(detail_url, headers=DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()
        response.encoding = response.encoding or response.apparent_encoding
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" in content_type or "text" in content_type:
            html = response.text
            detail_text = extract_readable_text(html)
            attachments = _merge_attachments(attachments, _extract_attachments(html, detail_url))

    return {
        "detail_text": detail_text,
        "attachments": attachments,
    }


def _notice_attachments(notice: Notice) -> list[dict[str, str]]:
    attachments: list[dict[str, str]] = []
    for item in notice.get("attachments", []) or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("title") or item.get("filename") or "").strip()
        url = str(item.get("url") or item.get("href") or "").strip()
        if url:
            attachments.append({"name": name or url, "url": url})
    return attachments


def _extract_attachments(html: str, base_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    attachments: list[dict[str, str]] = []

    for link in soup.select("a[href]"):
        href = str(link.get("href") or "").strip()
        onclick = str(link.get("onclick") or "").strip()
        text = link.get_text(" ", strip=True)
        candidate = f"{text} {href} {onclick}"
        if not href or not FILE_HINT_PATTERN.search(candidate):
            continue
        attachments.extend(_attachment_from_candidate(text or href, href, base_url, html, soup))

    for element in soup.select("[onclick]"):
        onclick = str(element.get("onclick") or "").strip()
        text = element.get_text(" ", strip=True)
        candidate = f"{text} {onclick}"
        if not onclick or not FILE_HINT_PATTERN.search(candidate):
            continue
        attachments.extend(_attachment_from_candidate(text or onclick, onclick, base_url, html, soup))

    return attachments


def _attachment_from_candidate(
    name: str,
    value: str,
    base_url: str,
    html: str,
    soup: BeautifulSoup,
) -> list[dict[str, str]]:
    if value.lower().startswith("javascript:"):
        return _resolve_javascript_attachment(name, value, base_url, html, soup)

    if JS_CALL_PATTERN.match(value):
        resolved = _resolve_javascript_attachment(name, value, base_url, html, soup)
        if resolved:
            return resolved

    return [{"name": name or value, "url": urljoin(base_url, value), "referer": base_url}]


def _resolve_javascript_attachment(
    name: str,
    value: str,
    base_url: str,
    html: str,
    soup: BeautifulSoup,
) -> list[dict[str, str]]:
    direct_url = _extract_direct_url_from_javascript(value)
    if direct_url:
        return [{"name": name or direct_url, "url": urljoin(base_url, direct_url), "referer": base_url}]

    call_match = JS_CALL_PATTERN.search(value.strip())
    if call_match is None:
        return []

    function_name = call_match.group(1)
    args = _parse_js_args(call_match.group("args"))
    if not args:
        return []

    function_info = _extract_function_info(function_name, html, soup)
    if function_info is None:
        return []

    action_url, method, param_names = function_info
    if not action_url:
        return []

    data = _build_js_call_data(param_names, args)
    if not data:
        return []

    return [
        {
            "name": name or function_name,
            "url": urljoin(base_url, action_url),
            "method": method,
            "data": data,
            "referer": base_url,
        }
    ]


def _extract_direct_url_from_javascript(value: str) -> str | None:
    for arg in _parse_js_args(value):
        if re.search(r"/|https?://|\.(pdf|hwp|hwpx|docx?|xlsx?|pptx?|zip|txt)(\?|$)", arg, re.I):
            return arg
    return None


def _parse_js_args(value: str) -> list[str]:
    call_match = JS_CALL_PATTERN.search(value.strip())
    args_text = call_match.group("args") if call_match else value
    args: list[str] = []
    for match in JS_ARG_PATTERN.finditer(args_text):
        arg = (match.group(1) if match.group(1) is not None else match.group(2)).strip()
        if arg:
            args.append(arg)
    return args


def _extract_function_info(
    function_name: str,
    html: str,
    soup: BeautifulSoup,
) -> tuple[str, str, list[str]] | None:
    pattern = re.compile(
        rf"function\s+{re.escape(function_name)}\s*\((?P<params>[^)]*)\)\s*\{{(?P<body>.*?)\n\s*\}}",
        re.S,
    )
    match = pattern.search(html)
    if match is None:
        return None

    params = [param.strip() for param in match.group("params").split(",") if param.strip()]
    body = match.group("body")
    action_url = _extract_action_url(body, soup)
    method = _extract_form_method(body, soup)
    param_names = _extract_param_names(body, params)
    return action_url, method, param_names


def _extract_action_url(function_body: str, soup: BeautifulSoup) -> str:
    action_patterns = [
        r"\.attr\(\s*['\"]action['\"]\s*,\s*['\"]([^'\"]+)['\"]",
        r"\.prop\(\s*['\"]action['\"]\s*,\s*['\"]([^'\"]+)['\"]",
        r"\.action\s*=\s*['\"]([^'\"]+)['\"]",
        r"\baction\s*:\s*['\"]([^'\"]+)['\"]",
    ]
    for pattern in action_patterns:
        match = re.search(pattern, function_body, re.I)
        if match:
            return match.group(1)

    form_id_match = re.search(r"\$\(\s*['\"]#([^'\"]+)['\"]\s*\).*?\.submit\(", function_body, re.S)
    if form_id_match:
        form = soup.find("form", id=form_id_match.group(1))
        if form and form.get("action"):
            return str(form.get("action"))

    form_name_match = re.search(r"document\.([A-Za-z_$][\w$]*)\.submit\(", function_body)
    if form_name_match:
        form = soup.find("form", attrs={"name": form_name_match.group(1)})
        if form and form.get("action"):
            return str(form.get("action"))

    return ""


def _extract_form_method(function_body: str, soup: BeautifulSoup) -> str:
    method_match = re.search(r"\.attr\(\s*['\"]method['\"]\s*,\s*['\"]([^'\"]+)['\"]", function_body, re.I)
    if method_match:
        return method_match.group(1).upper()

    form_id_match = re.search(r"\$\(\s*['\"]#([^'\"]+)['\"]\s*\).*?\.submit\(", function_body, re.S)
    if form_id_match:
        form = soup.find("form", id=form_id_match.group(1))
        if form and form.get("method"):
            return str(form.get("method")).upper()

    return "POST"


def _extract_param_names(function_body: str, params: list[str]) -> list[str]:
    assignments: list[tuple[int, str, str]] = []
    for param in params:
        escaped = re.escape(param)
        patterns = [
            rf"\$\(\s*['\"]#([^'\"]+)['\"]\s*\)\.val\(\s*{escaped}\s*\)",
            rf"\$\(\s*['\"]input\[name=['\"]?([^'\"]+)['\"]?\]['\"]\s*\)\.val\(\s*{escaped}\s*\)",
            rf"document\.[A-Za-z_$][\w$]*\.([A-Za-z_$][\w$]*)\.value\s*=\s*{escaped}",
        ]
        for pattern in patterns:
            match = re.search(pattern, function_body)
            if match:
                assignments.append((function_body.find(match.group(0)), param, match.group(1)))
                break

    if assignments:
        by_param = {param: name for _, param, name in sorted(assignments)}
        return [by_param.get(param, param) for param in params]

    return params


def _build_js_call_data(param_names: list[str], args: list[str]) -> str:
    pairs: list[tuple[str, str]] = []
    for index, arg in enumerate(args):
        name = param_names[index] if index < len(param_names) else f"arg{index + 1}"
        pairs.append((name, arg))
    return urlencode(pairs)


def _merge_attachments(*groups: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            url = str(item.get("url") or "").strip()
            signature = "|".join(
                [
                    url,
                    str(item.get("method") or "GET"),
                    str(item.get("data") or ""),
                ]
            )
            if not url or signature in seen:
                continue
            seen.add(signature)
            merged.append({key: str(value) for key, value in item.items() if value is not None})
    return merged
