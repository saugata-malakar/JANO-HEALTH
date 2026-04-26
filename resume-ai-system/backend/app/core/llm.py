"""
Unified LLM client.

Supports Anthropic (preferred) and OpenAI. Exposes a single async `chat_json`
method that returns a parsed JSON dict — the system prompt is responsible
for instructing the model to emit valid JSON.

We use tenacity for retries with exponential backoff on transient failures.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings
from app.utils.json_repair import extract_json

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when the LLM call fails after retries."""


class LLMClient:
    """Provider-agnostic chat-completion client."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._anthropic = None
        self._openai = None

        if self.settings.llm_provider == "anthropic":
            if not self.settings.anthropic_api_key:
                logger.warning("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY not set")
            else:
                from anthropic import AsyncAnthropic

                self._anthropic = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        else:
            if not self.settings.openai_api_key:
                logger.warning("LLM_PROVIDER=openai but OPENAI_API_KEY not set")
            else:
                from openai import AsyncOpenAI

                self._openai = AsyncOpenAI(api_key=self.settings.openai_api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((LLMError,)),
        reraise=True,
    )
    async def chat_json(
        self,
        system: str,
        user: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Send a chat message and parse the response as JSON.

        The prompt should explicitly instruct the model to emit valid JSON
        with no surrounding prose. We additionally run `extract_json` to
        salvage cases where the model wraps the JSON in markdown fences.
        """
        raw = await self._chat_raw(system, user, max_tokens, temperature)
        try:
            return extract_json(raw)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON output: %s\nRaw: %s", e, raw[:500])
            raise LLMError(f"LLM returned non-JSON output: {e}") from e

    async def chat_text(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.4,
    ) -> str:
        """Plain text completion — used when JSON is not required."""
        return await self._chat_raw(system, user, max_tokens, temperature)

    async def _chat_raw(
        self, system: str, user: str, max_tokens: int, temperature: float
    ) -> str:
        if self._anthropic:
            return await self._anthropic_call(system, user, max_tokens, temperature)
        if self._openai:
            return await self._openai_call(system, user, max_tokens, temperature)
        raise LLMError(
            "No LLM provider configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
        )

    async def _anthropic_call(
        self, system: str, user: str, max_tokens: int, temperature: float
    ) -> str:
        try:
            msg = await self._anthropic.messages.create(
                model=self.settings.llm_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            # Anthropic returns a list of content blocks; concatenate all text blocks
            return "".join(
                block.text for block in msg.content if getattr(block, "type", None) == "text"
            )
        except Exception as e:
            logger.exception("Anthropic API error")
            raise LLMError(str(e)) from e

    async def _openai_call(
        self, system: str, user: str, max_tokens: int, temperature: float
    ) -> str:
        try:
            resp = await self._openai.chat.completions.create(
                model=self.settings.llm_model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.exception("OpenAI API error")
            raise LLMError(str(e)) from e


# Singleton accessor
_client: LLMClient | None = None


def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
