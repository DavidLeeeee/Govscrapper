from __future__ import annotations

import asyncio
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
        text = asyncio.run(self._query(prompt))
        return normalize_analysis(parse_analysis_json(text))

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
