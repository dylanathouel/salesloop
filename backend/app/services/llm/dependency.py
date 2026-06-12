"""FastAPI dependency exposing the app-wide LLM provider (set in lifespan)."""

from fastapi import Request

from app.core.exceptions import LLMUnavailableError
from app.services.llm.base import LLMProvider


def get_llm_provider(request: Request) -> LLMProvider:
    provider = getattr(request.app.state, "llm_provider", None)
    if not isinstance(provider, LLMProvider):
        raise LLMUnavailableError("Le service IA n'est pas configuré.")
    return provider
