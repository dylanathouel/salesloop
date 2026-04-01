from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
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


@router.post("/{conversation_id}/messages", response_model=list[MessageResponse], status_code=status.HTTP_201_CREATED)
async def add_message(
    conversation_id: str,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Vérifier que la conversation existe et appartient au bon tenant
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    if conversation.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    # 1. Sauvegarder le message du user
    user_message = Message(
        conversation_id=conversation.id,
        sender="user",
        content=data.content,
    )
    db.add(user_message)
    await db.flush()

    # 2. Charger l'historique des messages pour le contexte
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    all_messages = result.scalars().all()

    # 3. Construire l'historique au format OpenRouter
    history = [
        {"role": "user" if m.sender == "user" else "assistant", "content": m.content}
        for m in all_messages
    ]

    # 4. Construire le system prompt avec le contexte du commercial
    from app.services.prompts import COLLECTOR_SYSTEM_PROMPT

    context = f"""
{COLLECTOR_SYSTEM_PROMPT}

CONTEXTE DE CETTE SESSION :
- Commercial : {current_user.full_name}
- Type : conversation avec l'agent collecteur
"""

    # 5. Appeler l'agent
    from app.services.agent import get_agent_response

    agent_reply = await get_agent_response(
        system_prompt=context,
        messages=history,
    )

    # 6. Sauvegarder la réponse de l'agent
    agent_message = Message(
        conversation_id=conversation.id,
        sender="agent",
        content=agent_reply,
    )
    db.add(agent_message)
    await db.commit()
    await db.refresh(user_message)
    await db.refresh(agent_message)

    # 7. Retourner les deux messages
    return [
        MessageResponse(
            id=str(user_message.id),
            sender=user_message.sender,
            content=user_message.content,
            token_count=user_message.token_count,
            created_at=str(user_message.created_at),
        ),
        MessageResponse(
            id=str(agent_message.id),
            sender=agent_message.sender,
            content=agent_message.content,
            token_count=agent_message.token_count,
            created_at=str(agent_message.created_at),
        ),
    ]


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

@router.post("/{conversation_id}/close", response_model=ConversationResponse)
async def close_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Vérifier que la conversation existe
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    if conversation.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Accès refusé")

    if conversation.status == "completed":
        raise HTTPException(status_code=400, detail="Conversation déjà clôturée")

    # Charger les messages
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    all_messages = result.scalars().all()

    history = [
        {"role": "user" if m.sender == "user" else "assistant", "content": m.content}
        for m in all_messages
    ]

    # Extraire les données structurées
    from app.services.agent import extract_conversation_data

    extracted = await extract_conversation_data(history)

    # Mettre à jour la conversation
    conversation.status = "completed"
    conversation.extracted_data = extracted
    conversation.ended_at = func.now()
    await db.commit()
    await db.refresh(conversation)

    return ConversationResponse(
        id=str(conversation.id),
        agent_type=conversation.agent_type,
        status=conversation.status,
        total_tokens=conversation.total_tokens,
        started_at=str(conversation.started_at),
        ended_at=str(conversation.ended_at) if conversation.ended_at else None,
    )