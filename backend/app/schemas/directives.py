import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DirectivePriority, DirectiveStatus


class DirectiveCreate(BaseModel):
    content: str = Field(min_length=3, max_length=2000)
    priority: DirectivePriority = DirectivePriority.MEDIUM


class DirectiveUpdate(BaseModel):
    """Partial update; only provided fields are applied."""

    content: str | None = Field(default=None, min_length=3, max_length=2000)
    priority: DirectivePriority | None = None
    status: DirectiveStatus | None = None


class DirectiveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content: str
    priority: DirectivePriority
    status: DirectiveStatus
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
