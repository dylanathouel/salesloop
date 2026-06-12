"""Provider-agnostic LLM interface, so the concrete provider can be swapped
or mocked in tests without touching business logic."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypedDict


class LLMMessage(TypedDict):
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True)
class LLMResult:
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMProvider(ABC):
    """Interface for chat-completion providers."""

    @abstractmethod
    async def chat(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        max_tokens: int = 300,
    ) -> LLMResult:
        """Send a conversation and return the assistant reply with token usage.

        Raises LLMUnavailableError if the provider is unreachable after retries.
        """
