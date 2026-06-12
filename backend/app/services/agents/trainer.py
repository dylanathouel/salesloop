"""Trainer agent: sales coaching backed by the tenant's training content (RAG)
and the knowledge gaps detected by the collector agent.

If the embedding provider is unavailable, the trainer still coaches —
just without documentary context.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmbeddingUnavailableError
from app.models.conversation import Conversation
from app.models.enums import AgentType, ConversationStatus
from app.models.user import User
from app.services.llm.base import LLMMessage, LLMProvider, LLMResult
from app.services.llm.prompts import TRAINER_SYSTEM_PROMPT
from app.services.rag import retrieval
from app.services.rag.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)

MAX_GAPS = 5


async def _recent_knowledge_gaps(db: AsyncSession, user: User) -> list[str]:
    """Knowledge gaps detected by the collector in the user's recent debriefs."""
    result = await db.execute(
        select(Conversation.extracted_data)
        .where(
            Conversation.user_id == user.id,
            Conversation.agent_type == AgentType.COLLECTOR,
            Conversation.status == ConversationStatus.COMPLETED,
        )
        .order_by(Conversation.ended_at.desc())
        .limit(20)
    )
    gaps: list[str] = []
    for (data,) in result.all():
        detail = (data or {}).get("knowledge_gap_detail")
        if (data or {}).get("product_knowledge_gap") and detail and detail not in gaps:
            gaps.append(str(detail))
        if len(gaps) >= MAX_GAPS:
            break
    return gaps


async def _retrieve_context(
    db: AsyncSession,
    embedder: EmbeddingProvider,
    user: User,
    query: str,
) -> list[retrieval.RetrievedChunk]:
    try:
        return await retrieval.retrieve(db, embedder, user.tenant_id, query)
    except EmbeddingUnavailableError as exc:
        logger.warning("Retrieval unavailable, trainer continues without context: %s", exc.message)
        return []


def build_system_prompt(
    user: User,
    gaps: list[str],
    chunks: list[retrieval.RetrievedChunk],
) -> str:
    prompt = f"""
{TRAINER_SYSTEM_PROMPT}

CONTEXTE DE CETTE SESSION :
- Commercial : {user.full_name}
"""
    if gaps:
        listing = "\n".join(f"- {gap}" for gap in gaps)
        prompt += f"""
LACUNES DÉTECTÉES (issues de ses derniers debriefings) :
{listing}
"""
    if chunks:
        documents = "\n\n".join(f"[{c.title}]\n{c.text}" for c in chunks)
        prompt += f"""
CONTEXTE DOCUMENTAIRE :
{documents}
"""
    return prompt


async def generate_opening(
    llm: LLMProvider,
    embedder: EmbeddingProvider,
    db: AsyncSession,
    user: User,
) -> LLMResult:
    """First trainer message: proposes a session based on the detected gaps."""
    gaps = await _recent_knowledge_gaps(db, user)
    chunks = await _retrieve_context(db, embedder, user, " ".join(gaps)) if gaps else []
    instruction: list[LLMMessage] = [
        {
            "role": "user",
            "content": (
                "(Le commercial vient d'ouvrir une session d'entraînement. "
                "Accueille-le et propose-lui un premier exercice, en priorité "
                "sur ses lacunes détectées s'il y en a.)"
            ),
        }
    ]
    return await llm.chat(
        system_prompt=build_system_prompt(user, gaps, chunks), messages=instruction
    )


async def generate_reply(
    llm: LLMProvider,
    embedder: EmbeddingProvider,
    db: AsyncSession,
    user: User,
    history: list[LLMMessage],
    query: str,
) -> LLMResult:
    """Trainer reply: retrieval on the user's last message + detected gaps."""
    gaps = await _recent_knowledge_gaps(db, user)
    chunks = await _retrieve_context(db, embedder, user, query)
    return await llm.chat(system_prompt=build_system_prompt(user, gaps, chunks), messages=history)
