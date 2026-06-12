import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TrainingContentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=20)
    content_type: str = "text"


class TrainingContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content_type: str
    is_embedded: bool
    chunk_metadata: dict[str, Any]
    created_at: datetime
