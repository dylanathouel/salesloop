"""Collector agent: post-meeting / end-of-day debriefing conversation logic."""

from app.models.user import User
from app.services.llm.base import LLMMessage, LLMProvider, LLMResult
from app.services.llm.prompts import COLLECTOR_SYSTEM_PROMPT


def build_system_prompt(user: User) -> str:
    """Assemble the collector system prompt with the session context."""
    return f"""
{COLLECTOR_SYSTEM_PROMPT}

CONTEXTE DE CETTE SESSION :
- Commercial : {user.full_name}
- Type : conversation avec l'agent collecteur
"""


async def generate_reply(
    llm: LLMProvider,
    user: User,
    history: list[LLMMessage],
) -> LLMResult:
    """Generate the agent's next reply given the full conversation history."""
    return await llm.chat(system_prompt=build_system_prompt(user), messages=history)
