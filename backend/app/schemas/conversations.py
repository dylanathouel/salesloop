import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import AgentType, ConversationStatus, MessageSender


class ConversationCreate(BaseModel):
    agent_type: AgentType


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender: MessageSender
    content: str
    token_count: int
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_type: AgentType
    status: ConversationStatus
    extracted_data: dict[str, Any] | None = None
    total_tokens: int
    started_at: datetime
    ended_at: datetime | None = None
