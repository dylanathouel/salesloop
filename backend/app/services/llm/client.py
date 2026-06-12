"""OpenRouter implementation of LLMProvider (httpx, retry with backoff)."""

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.core.exceptions import LLMUnavailableError
from app.services.llm.base import LLMMessage, LLMProvider, LLMResult

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class _RetryableLLMError(Exception):
    """Internal marker for errors worth retrying (network, 5xx, 429)."""


class OpenRouterProvider(LLMProvider):
    """Talks to OpenRouter. Shares one httpx client across requests."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=settings.llm_timeout_seconds)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def chat(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        max_tokens: int = 300,
    ) -> LLMResult:
        payload = {
            "model": settings.openrouter_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
        }
        try:
            data = await self._post_with_retry(payload)
        except (_RetryableLLMError, httpx.HTTPError) as exc:
            logger.error("OpenRouter unavailable after retries: %s", exc)
            raise LLMUnavailableError(
                "Le service IA est momentanément indisponible, réessaie dans un instant."
            ) from exc

        try:
            content: str = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            logger.error("Unexpected OpenRouter response shape: %s", data)
            raise LLMUnavailableError(
                "Le service IA a renvoyé une réponse inattendue, réessaie dans un instant."
            ) from exc

        usage = data.get("usage") or {}
        return LLMResult(
            content=content,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )

    @retry(
        retry=retry_if_exception_type((_RetryableLLMError, httpx.TransportError)),
        stop=stop_after_attempt(1 + settings.llm_max_retries),
        wait=wait_exponential(multiplier=1, max=10),
        reraise=True,
    )
    async def _post_with_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if response.status_code == 429 or response.status_code >= 500:
            raise _RetryableLLMError(f"OpenRouter HTTP {response.status_code}")
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result
