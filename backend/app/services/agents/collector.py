"""Collector agent: post-meeting / end-of-day debriefing conversation logic."""

from app.models.user import User
from app.services.llm.base import LLMMessage, LLMProvider, LLMResult
from app.services.llm.prompts import COLLECTOR_SYSTEM_PROMPT


def build_system_prompt(user: User, directives: list[str] | None = None) -> str:
    """Assemble the collector system prompt with session context and the
    tenant's active management directives."""
    prompt = f"""
{COLLECTOR_SYSTEM_PROMPT}

CONTEXTE DE CETTE SESSION :
- Commercial : {user.full_name}
- Type : conversation avec l'agent collecteur
"""
    if directives:
        listing = "\n".join(f"- {d}" for d in directives)
        prompt += f"""
DIRECTIVES DU MANAGEMENT :
Le management a transmis les consignes suivantes. Intègre-les naturellement
dans la conversation quand c'est pertinent (sans les réciter mot à mot) :
{listing}
"""
    return prompt


async def generate_reply(
    llm: LLMProvider,
    user: User,
    history: list[LLMMessage],
    directives: list[str] | None = None,
) -> LLMResult:
    """Generate the agent's next reply given the full conversation history."""
    return await llm.chat(system_prompt=build_system_prompt(user, directives), messages=history)


async def generate_opening(
    llm: LLMProvider,
    user: User,
    directives: list[str] | None = None,
) -> LLMResult:
    """Generate the agent's first message when a debriefing session starts.

    The instruction below is synthetic (never persisted): it only prompts the
    model to ask its opening question.
    """
    instruction: list[LLMMessage] = [
        {
            "role": "user",
            "content": (
                "(Le commercial vient d'ouvrir la session de debriefing. "
                "Pose ta première question, conformément à tes consignes.)"
            ),
        }
    ]
    return await llm.chat(system_prompt=build_system_prompt(user, directives), messages=instruction)
