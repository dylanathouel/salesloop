"""Conversation business logic: tenant-scoped access, message flow, closing.

All conversation lookups go through `get_scoped_conversation` so tenant
isolation and role visibility never depend on individual endpoints
remembering to filter. Cross-tenant access is answered with a 404 so the
existence of another tenant's resources is never confirmed.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, InvalidStateError, NotFoundError
from app.models.conversation import Conversation
from app.models.enums import AgentType, ConversationStatus, MessageSender, UserRole
from app.models.message import Message
from app.models.user import User
from app.services import directives as directives_service
from app.services import extraction
from app.services.agents import collector, trainer
from app.services.llm.base import LLMMessage, LLMProvider
from app.services.rag.embeddings import EmbeddingProvider


async def _is_in_team(db: AsyncSession, manager: User, member_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(User.id).where(User.id == member_id, User.manager_id == manager.id)
    )
    return result.scalar_one_or_none() is not None


async def get_scoped_conversation(
    db: AsyncSession,
    current_user: User,
    conversation_id: uuid.UUID,
) -> Conversation:
    """Load a conversation, enforcing tenant isolation and role visibility."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()

    if conversation is None or conversation.tenant_id != current_user.tenant_id:
        raise NotFoundError("Conversation introuvable")

    if conversation.user_id == current_user.id or current_user.role == UserRole.DIRECTION:
        return conversation
    if current_user.role == UserRole.MANAGER and await _is_in_team(
        db, current_user, conversation.user_id
    ):
        return conversation

    raise NotFoundError("Conversation introuvable")


def _require_owner(conversation: Conversation, current_user: User) -> None:
    """Only the conversation owner can write to it (messages, closing)."""
    if conversation.user_id != current_user.id:
        raise ForbiddenError("Seul le propriétaire de la conversation peut y écrire")


async def create_conversation(
    db: AsyncSession,
    llm: LLMProvider,
    embedder: EmbeddingProvider,
    current_user: User,
    agent_type: AgentType,
) -> tuple[Conversation, Message]:
    """Start a new conversation; the agent opens with a generated message.

    The opening is generated before anything is persisted: if the LLM is
    down, no half-created conversation is left behind.
    """
    if agent_type == AgentType.COLLECTOR:
        directives = await directives_service.get_active_contents(db, current_user.tenant_id)
        opening = await collector.generate_opening(llm, current_user, directives)
    else:
        opening = await trainer.generate_opening(llm, embedder, db, current_user)

    conversation = Conversation(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        agent_type=agent_type,
    )
    db.add(conversation)
    await db.flush()

    first_message = Message(
        conversation_id=conversation.id,
        sender=MessageSender.AGENT,
        content=opening.content,
        token_count=opening.completion_tokens,
    )
    db.add(first_message)
    conversation.total_tokens += opening.total_tokens

    await db.commit()
    await db.refresh(conversation)
    await db.refresh(first_message)
    return conversation, first_message


async def list_conversations(db: AsyncSession, current_user: User) -> list[Conversation]:
    """Commercial: own conversations. Manager: their team's (and own). Direction: tenant."""
    query = select(Conversation).where(Conversation.tenant_id == current_user.tenant_id)

    if current_user.role == UserRole.COMMERCIAL:
        query = query.where(Conversation.user_id == current_user.id)
    elif current_user.role == UserRole.MANAGER:
        team_ids = select(User.id).where(User.manager_id == current_user.id)
        query = query.where(
            or_(Conversation.user_id == current_user.id, Conversation.user_id.in_(team_ids))
        )

    result = await db.execute(query.order_by(Conversation.started_at.desc()))
    return list(result.scalars().all())


async def list_messages(
    db: AsyncSession,
    current_user: User,
    conversation_id: uuid.UUID,
) -> list[Message]:
    await get_scoped_conversation(db, current_user, conversation_id)
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def _load_history(db: AsyncSession, conversation_id: uuid.UUID) -> list[LLMMessage]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return [
        {
            "role": "user" if m.sender == MessageSender.USER else "assistant",
            "content": m.content,
        }
        for m in result.scalars().all()
    ]


async def send_message(
    db: AsyncSession,
    llm: LLMProvider,
    embedder: EmbeddingProvider,
    current_user: User,
    conversation_id: uuid.UUID,
    content: str,
) -> tuple[Message, Message]:
    """Save the user message, get the agent reply, save and return both."""
    conversation = await get_scoped_conversation(db, current_user, conversation_id)
    _require_owner(conversation, current_user)

    user_message = Message(
        conversation_id=conversation.id,
        sender=MessageSender.USER,
        content=content,
    )
    db.add(user_message)
    await db.flush()

    history = await _load_history(db, conversation.id)
    if conversation.agent_type == AgentType.COLLECTOR:
        directives = await directives_service.get_active_contents(db, current_user.tenant_id)
        reply = await collector.generate_reply(llm, current_user, history, directives)
    else:
        reply = await trainer.generate_reply(
            llm, embedder, db, current_user, history, query=content
        )

    agent_message = Message(
        conversation_id=conversation.id,
        sender=MessageSender.AGENT,
        content=reply.content,
        token_count=reply.completion_tokens,
    )
    db.add(agent_message)

    # Real token usage from the provider, accumulated on the conversation
    conversation.total_tokens += reply.total_tokens

    await db.commit()
    await db.refresh(user_message)
    await db.refresh(agent_message)
    return user_message, agent_message


async def close_conversation(
    db: AsyncSession,
    llm: LLMProvider,
    current_user: User,
    conversation_id: uuid.UUID,
) -> Conversation:
    """Close a conversation and store the structured extraction."""
    conversation = await get_scoped_conversation(db, current_user, conversation_id)
    _require_owner(conversation, current_user)

    if conversation.status == ConversationStatus.COMPLETED:
        raise InvalidStateError("Conversation déjà clôturée")

    # Structured extraction only makes sense for debriefings (collector)
    if conversation.agent_type == AgentType.COLLECTOR:
        history = await _load_history(db, conversation.id)
        extracted, tokens_used = await extraction.extract_conversation_data(llm, history)
        conversation.extracted_data = extracted
        conversation.total_tokens += tokens_used

    conversation.status = ConversationStatus.COMPLETED
    conversation.ended_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(conversation)
    return conversation
