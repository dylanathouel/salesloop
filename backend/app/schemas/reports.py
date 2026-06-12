import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import ReportPeriodType


class ReportGenerateRequest(BaseModel):
    period_type: ReportPeriodType
    period_start: date
    period_end: date

    @model_validator(mode="after")
    def check_period(self) -> "ReportGenerateRequest":
        if self.period_end < self.period_start:
            raise ValueError("period_end doit être postérieure à period_start")
        return self


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    period_type: ReportPeriodType
    period_start: date
    period_end: date
    summary: str | None
    insights: dict[str, Any]
    metrics: dict[str, Any]
    generated_at: datetime
