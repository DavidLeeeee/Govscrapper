from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import threading
from typing import Any

from src.contracts.notice import Notice
from src.services.deep_analysis.prompting import (
    SYSTEM_PROMPT,
    build_deep_analysis_prompt,
    normalize_analysis,
    parse_analysis_json,
)


class ClaudeSDKDeepAnalyzer:
    def __init__(
        self,
        model: str | None = None,
        max_file_chars: int = 50000,
        max_prompt_chars: int = 180000,
        max_output_tokens: int = 4000,
    ) -> None:
        self.model = model
        self.max_file_chars = max_file_chars
        self.max_prompt_chars = max_prompt_chars
        self.max_output_tokens = max_output_tokens

    def analyze(self, notice: Notice, material: dict[str, Any]) -> dict[str, Any]:
        prompt = "\n\n".join(
            [
                SYSTEM_PROMPT,
                "반드시 JSON만 출력해라. Markdown 코드블록을 쓰지 마라.",
                build_deep_analysis_prompt(
                    notice,
                    material,
                    max_file_chars=self.max_file_chars,
                    max_prompt_chars=self.max_prompt_chars,
                ),
            ]
        )
        usage: dict[str, Any]
        try:
            text, usage = _query_claude_cli(prompt, model=self.model)
        except Exception as cli_exc:
            try:
                text = _run_async_query(self._query(prompt))
                usage = {
                    "provider": "claude",
                    "transport": "sdk",
                    "model": self.model,
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "total_cost_usd": None,
                }
            except Exception as sdk_exc:
                raise RuntimeError(
                    "Claude CLI와 SDK 호출이 모두 실패했습니다. "
                    f"CLI error: {type(cli_exc).__name__}: {cli_exc}; "
                    f"SDK error: {type(sdk_exc).__name__}: {sdk_exc}"
                ) from sdk_exc
        return {
            **normalize_analysis(parse_analysis_json(text)),
            "analysis_usage": usage,
        }

    async def _query(self, prompt: str) -> str:
        try:
            from claude_code_sdk import ClaudeCodeOptions, query
        except ImportError as exc:
            raise RuntimeError(
                "ANALYSIS_PROVIDER=claude를 사용하려면 서버 환경에 claude-code-sdk가 설치되어 있고 Claude 로그인이 완료되어야 합니다."
            ) from exc

        options_kwargs: dict[str, Any] = {
            "max_turns": 1,
        }
        if self.model:
            options_kwargs["model"] = self.model
        if self.max_output_tokens:
            options_kwargs["max_output_tokens"] = self.max_output_tokens

        try:
            options = ClaudeCodeOptions(**options_kwargs)
        except TypeError:
            options_kwargs.pop("max_output_tokens", None)
            options = ClaudeCodeOptions(**options_kwargs)

        chunks: list[str] = []
        async for message in query(prompt=prompt, options=options):
            chunks.extend(_extract_message_text(message))

        text = "\n".join(chunks).strip()
        if not text:
            raise ValueError("Claude SDK response did not include output text")
        return text


def _extract_message_text(message: Any) -> list[str]:
    texts: list[str] = []

    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")

    if isinstance(content, str):
        texts.append(content)
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    texts.append(text)
            else:
                text = getattr(item, "text", None)
                if isinstance(text, str):
                    texts.append(text)

    if not texts:
        text = getattr(message, "text", None)
        if isinstance(text, str):
            texts.append(text)
        elif isinstance(message, dict) and isinstance(message.get("text"), str):
            texts.append(message["text"])

    return texts


def _run_async_query(coro: Any) -> str:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}

    def runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:
            result["error"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()

    if "error" in result:
        raise result["error"]
    return str(result.get("value") or "")


def _query_claude_cli(prompt: str, model: str | None = None) -> tuple[str, dict[str, Any]]:
    claude_path = shutil.which("claude")
    if not claude_path:
        raise RuntimeError("claude CLI를 PATH에서 찾지 못했습니다.")

    command = [claude_path, "-p", "--output-format", "json"]
    if model:
        command.extend(["--model", model])
    try:
        completed = subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=900,
            check=False,
        )
    except Exception as cli_exc:
        raise RuntimeError(f"claude CLI 호출에 실패했습니다: {type(cli_exc).__name__}: {cli_exc}") from cli_exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()[:1200]
        raise RuntimeError(f"claude CLI 실패: exit={completed.returncode}: {detail}")

    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"claude CLI JSON 응답을 해석하지 못했습니다: {completed.stdout[:1200]}") from exc

    if data.get("is_error"):
        raise RuntimeError(f"claude CLI returned error: {str(data.get('result') or data)[:1200]}")

    result = data.get("result")
    if not isinstance(result, str) or not result.strip():
        raise RuntimeError(f"claude CLI response did not include result text: {str(data)[:1200]}")
    return result, _build_claude_cli_usage(data, model)


def _build_claude_cli_usage(data: dict[str, Any], requested_model: str | None) -> dict[str, Any]:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        usage = {}

    model_usage = data.get("modelUsage")
    if isinstance(model_usage, dict) and model_usage:
        actual_model = next(iter(model_usage.keys()))
    else:
        actual_model = requested_model

    input_tokens = usage.get("input_tokens")
    cache_creation_tokens = usage.get("cache_creation_input_tokens")
    cache_read_tokens = usage.get("cache_read_input_tokens")
    output_tokens = usage.get("output_tokens")

    token_parts = [
        value
        for value in (input_tokens, cache_creation_tokens, cache_read_tokens, output_tokens)
        if isinstance(value, int)
    ]

    return {
        "provider": "claude",
        "transport": "cli",
        "model": actual_model,
        "input_tokens": input_tokens,
        "cache_creation_input_tokens": cache_creation_tokens,
        "cache_read_input_tokens": cache_read_tokens,
        "output_tokens": output_tokens,
        "total_tokens": sum(token_parts) if token_parts else None,
        "total_cost_usd": data.get("total_cost_usd"),
        "duration_ms": data.get("duration_ms"),
        "duration_api_ms": data.get("duration_api_ms"),
    }
