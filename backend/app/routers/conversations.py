from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services.dependencies import get_current_user

router = APIRouter(prefix="/conversations", tags=["conversations"])


# --- Schémas ---

class ConversationCreate(BaseModel):
    agent_type: str  # "collector" ou "trainer"


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: str
    sender: str
    content: str
    token_count: int
    created_at: str

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: str
    agent_type: str
    status: str
    total_tokens: int
    started_at: str
    ended_at: str | None = None

    class Config:
        from_attributes = True


# --- Routes ---

@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conversation = Conversation(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        agent_type=data.agent_type,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return ConversationResponse(
        id=str(conversation.id),
        agent_type=conversation.agent_type,
        status=conversation.status,
        total_tokens=conversation.total_tokens,
        started_at=str(conversation.started_at),
    )


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Un commercial voit ses conversations, un manager/direction voit tout le tenant
    if current_user.role == "commercial":
        query = select(Conversation).where(Conversation.user_id == current_user.id)
    else:
        query = select(Conversation).where(Conversation.tenant_id == current_user.tenant_id)

    result = await db.execute(query.order_by(Conversation.started_at.desc()))
    convs = result.scalars().all()

    return [
        ConversationResponse(
            id=str(c.id),
            agent_type=c.agent_type,
            status=c.status,
            total_tokens=c.total_tokens,
            started_at=str(c.started_at),
            ended_at=str(c.ended_at) if c.ended_at else None,
        )
        for c in convs
    ]


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(
    conversation_id: str,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Vérifier que la conversation appartient au user ou à son tenant
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    if conversation.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    message = Message(
        conversation_id=conversation.id,
        sender="user",
        content=data.content,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    return MessageResponse(
        id=str(message.id),
        sender=message.sender,
        content=message.content,
        token_count=message.token_count,
        created_at=str(message.created_at),
    )


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Vérifier l'accès
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    if conversation.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return [
        MessageResponse(
            id=str(m.id),
            sender=m.sender,
            content=m.content,
            token_count=m.token_count,
            created_at=str(m.created_at),
        )
        for m in messages
    ]