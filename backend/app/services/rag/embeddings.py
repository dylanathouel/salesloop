"""Provider-agnostic embedding interface + OpenAI-compatible implementation.

Any endpoint speaking the OpenAI `/embeddings` protocol works (OpenAI,
Mistral, Voyage, Ollama/LM Studio locally...). An empty API key means
embeddings are disabled: callers degrade gracefully (content stored
unembedded, trainer works without retrieval).
"""

import logging
from abc import ABC, abstractmethod

import httpx
from fastapi import Request
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.exceptions import EmbeddingUnavailableError

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Interface for text-embedding providers."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, preserving order.

        Raises EmbeddingUnavailableError when the provider is unreachable
        or not configured.
        """


class _RetryableEmbeddingError(Exception):
    """Internal marker for errors worth retrying (network, 5xx, 429)."""


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=settings.llm_timeout_seconds)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not settings.embedding_api_key:
            raise EmbeddingUnavailableError("Le service d'embeddings n'est pas configuré.")
        try:
            data = await self._post_with_retry(texts)
        except (_RetryableEmbeddingError, httpx.HTTPError) as exc:
            logger.error("Embedding provider unavailable after retries: %s", exc)
            raise EmbeddingUnavailableError(
                "Le service d'embeddings est momentanément indisponible."
            ) from exc

        try:
            items = sorted(data["data"], key=lambda item: item["index"])
            return [item["embedding"] for item in items]
        except (KeyError, TypeError) as exc:
            logger.error("Unexpected embedding response shape: %s", data)
            raise EmbeddingUnavailableError(
                "Le service d'embeddings a renvoyé une réponse inattendue."
            ) from exc

    @retry(
        retry=retry_if_exception_type((_RetryableEmbeddingError, httpx.TransportError)),
        stop=stop_after_attempt(1 + settings.llm_max_retries),
        wait=wait_exponential(multiplier=1, max=10),
        reraise=True,
    )
    async def _post_with_retry(self, texts: list[str]) -> dict:
        response = await self._client.post(
            f"{settings.embedding_base_url.rstrip('/')}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.embedding_api_key}",
                "Content-Type": "application/json",
            },
            json={"model": settings.embedding_model, "input": texts},
        )
        if response.status_code == 429 or response.status_code >= 500:
            raise _RetryableEmbeddingError(f"Embeddings HTTP {response.status_code}")
        response.raise_for_status()
        result: dict = response.json()
        return result


def get_embedding_provider(request: Request) -> EmbeddingProvider:
    """FastAPI dependency exposing the app-wide embedding provider."""
    provider = getattr(request.app.state, "embedding_provider", None)
    if not isinstance(provider, EmbeddingProvider):
        raise EmbeddingUnavailableError("Le service d'embeddings n'est pas configuré.")
    return provider
