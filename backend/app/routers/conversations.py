import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_db
from app.schemas.conversations import (
    ConversationCreate,
    ConversationResponse,
    ConversationStartResponse,
    MessageCreate,
    MessageResponse,
)
from app.services import conversations as conversations_service
from app.services.llm.base import LLMProvider
from app.services.llm.dependency import get_llm_provider
from app.services.rag.embeddings import EmbeddingProvider, get_embedding_provider

router = APIRouter(prefix="/conversations", tags=["conversations"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
Llm = Annotated[LLMProvider, Depends(get_llm_provider)]
Embedder = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]


@router.post("/", response_model=ConversationStartResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user: CurrentUser,
    db: DbSession,
    llm: Llm,
    embedder: Embedder,
) -> ConversationStartResponse:
    conversation, first_message = await conversations_service.create_conversation(
        db, llm, embedder, current_user, data.agent_type
    )
    response = ConversationStartResponse.model_validate(conversation)
    response.first_message = MessageResponse.model_validate(first_message)
    return response


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: CurrentUser,
    db: DbSession,
) -> list[ConversationResponse]:
    conversations = await conversations_service.list_conversations(db, current_user)
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> list[MessageResponse]:
    messages = await conversations_service.list_messages(db, current_user, conversation_id)
    return [MessageResponse.model_validate(m) for m in messages]


@router.post(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    current_user: CurrentUser,
    db: DbSession,
    llm: Llm,
    embedder: Embedder,
) -> list[MessageResponse]:
    user_message, agent_message = await conversations_service.send_message(
        db, llm, embedder, current_user, conversation_id, data.content
    )
    return [
        MessageResponse.model_validate(user_message),
        MessageResponse.model_validate(agent_message),
    ]


@router.post("/{conversation_id}/close", response_model=ConversationResponse)
async def close_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    llm: Llm,
) -> ConversationResponse:
    conversation = await conversations_service.close_conversation(
        db, llm, current_user, conversation_id
    )
    return ConversationResponse.model_validate(conversation)
