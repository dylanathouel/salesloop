"""Conversation business logic: tenant-scoped access, message flow, closing.

All conversation lookups go through `get_scoped_conversation` so tenant
isolation never depends on individual endpoints remembering to filter.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, InvalidStateError, NotFoundError
from app.models.conversation import Conversation
from app.models.enums import AgentType, ConversationStatus, MessageSender, UserRole
from app.models.message import Message
from app.models.user import User
from app.services import extraction
from app.services.agents import collector
from app.services.llm.base import LLMMessage, LLMProvider


async def get_scoped_conversation(
    db: AsyncSession,
    current_user: User,
    conversation_id: uuid.UUID,
) -> Conversation:
    """Load a conversation, enforcing tenant isolation."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()

    if conversation is None:
        raise NotFoundError("Conversation introuvable")
    if conversation.tenant_id != current_user.tenant_id:
        raise ForbiddenError("Accès refusé")

    return conversation


async def create_conversation(
    db: AsyncSession,
    current_user: User,
    agent_type: AgentType,
) -> Conversation:
    """Start a new conversation for the current user."""
    conversation = Conversation(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        agent_type=agent_type,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def list_conversations(db: AsyncSession, current_user: User) -> list[Conversation]:
    """A commercial sees their own conversations, manager/direction the whole tenant."""
    if current_user.role == UserRole.COMMERCIAL:
        query = select(Conversation).where(Conversation.user_id == current_user.id)
    else:
        query = select(Conversation).where(Conversation.tenant_id == current_user.tenant_id)

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
    current_user: User,
    conversation_id: uuid.UUID,
    content: str,
) -> tuple[Message, Message]:
    """Save the user message, get the agent reply, save and return both."""
    conversation = await get_scoped_conversation(db, current_user, conversation_id)

    user_message = Message(
        conversation_id=conversation.id,
        sender=MessageSender.USER,
        content=content,
    )
    db.add(user_message)
    await db.flush()

    history = await _load_history(db, conversation.id)
    reply = await collector.generate_reply(llm, current_user, history)

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

    if conversation.status == ConversationStatus.COMPLETED:
        raise InvalidStateError("Conversation déjà clôturée")

    history = await _load_history(db, conversation.id)
    extracted, tokens_used = await extraction.extract_conversation_data(llm, history)

    conversation.status = ConversationStatus.COMPLETED
    conversation.extracted_data = extracted
    conversation.total_tokens += tokens_used
    conversation.ended_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(conversation)
    return conversation
