import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_manager
from app.database import get_db
from app.models.user import User
from app.schemas.reports import ReportGenerateRequest, ReportResponse
from app.services import reports as reports_service
from app.services.llm.base import LLMProvider
from app.services.llm.dependency import get_llm_provider

router = APIRouter(prefix="/reports", tags=["reports"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
Manager = Annotated[User, require_manager]
Llm = Annotated[LLMProvider, Depends(get_llm_provider)]


@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    data: ReportGenerateRequest, db: DbSession, actor: Manager, llm: Llm
) -> ReportResponse:
    """Aggregate the scope's closed conversations over a period into a report."""
    report = await reports_service.generate_report(
        db, llm, actor, data.period_type, data.period_start, data.period_end
    )
    return ReportResponse.model_validate(report)


@router.get("/", response_model=list[ReportResponse])
async def list_reports(db: DbSession, actor: Manager) -> list[ReportResponse]:
    reports = await reports_service.list_reports(db, actor)
    return [ReportResponse.model_validate(r) for r in reports]


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: uuid.UUID, db: DbSession, actor: Manager) -> ReportResponse:
    report = await reports_service.get_report(db, actor, report_id)
    return ReportResponse.model_validate(report)
