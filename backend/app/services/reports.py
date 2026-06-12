"""Periodic report generation: aggregate closed conversations of the actor's
scope, compute deterministic metrics, and ask the LLM for a managerial
synthesis (validated, one corrective retry, degraded fallback).
"""

import json
import logging
import uuid
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError, NotFoundError
from app.models.conversation import Conversation
from app.models.enums import ConversationStatus, ReportPeriodType, UserRole
from app.models.report import Report
from app.models.user import User
from app.services.extraction import strip_code_fences
from app.services.llm.base import LLMProvider
from app.services.llm.prompts import REPORT_PROMPT

logger = logging.getLogger(__name__)


class ReportInsights(BaseModel):
    model_config = ConfigDict(extra="ignore")

    trends: list[str] = []
    recurring_objections: list[str] = []
    competitor_alerts: list[str] = []
    training_needs: list[str] = []


class ReportLLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary: str
    insights: ReportInsights = ReportInsights()


async def _scoped_closed_conversations(
    db: AsyncSession,
    actor: User,
    period_start: date,
    period_end: date,
) -> list[Conversation]:
    """Completed conversations of the actor's scope closed within the period."""
    start = datetime.combine(period_start, time.min, tzinfo=UTC)
    end = datetime.combine(period_end + timedelta(days=1), time.min, tzinfo=UTC)

    query = select(Conversation).where(
        Conversation.tenant_id == actor.tenant_id,
        Conversation.status == ConversationStatus.COMPLETED,
        Conversation.ended_at >= start,
        Conversation.ended_at < end,
    )
    if actor.role == UserRole.MANAGER:
        team_ids = select(User.id).where(User.manager_id == actor.id)
        query = query.where(
            or_(Conversation.user_id == actor.id, Conversation.user_id.in_(team_ids))
        )

    result = await db.execute(query.order_by(Conversation.ended_at))
    return list(result.scalars().all())


def _compute_metrics(conversations: list[Conversation]) -> dict[str, Any]:
    """Deterministic metrics computed in Python (no LLM involved)."""
    sentiments: Counter[str] = Counter()
    objections: Counter[str] = Counter()
    competitors: Counter[str] = Counter()
    knowledge_gaps = 0

    for conversation in conversations:
        data = conversation.extracted_data or {}
        if data.get("sentiment"):
            sentiments[str(data["sentiment"])] += 1
        for objection in data.get("objections") or []:
            objections[str(objection)] += 1
        for competitor in data.get("competitors") or []:
            if isinstance(competitor, dict) and competitor.get("name"):
                competitors[str(competitor["name"])] += 1
        if data.get("product_knowledge_gap"):
            knowledge_gaps += 1

    return {
        "conversation_count": len(conversations),
        "sentiments": dict(sentiments),
        "top_objections": [o for o, _ in objections.most_common(10)],
        "competitors_mentioned": dict(competitors),
        "knowledge_gap_count": knowledge_gaps,
    }


def _build_corpus(conversations: list[Conversation]) -> str:
    lines = []
    for conversation in conversations:
        data = conversation.extracted_data or {}
        if "error" in data:
            continue  # skip failed extractions, they carry no signal
        closed = conversation.ended_at.date().isoformat() if conversation.ended_at else "?"
        lines.append(f"- [{closed}] {json.dumps(data, ensure_ascii=False)}")
    return "\n".join(lines)


async def _generate_synthesis(
    llm: LLMProvider, corpus: str, metrics: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    """LLM synthesis with one corrective retry; degraded fallback on failure."""
    user_content = (
        f"MÉTRIQUES DE LA PÉRIODE :\n{json.dumps(metrics, ensure_ascii=False)}\n\n"
        f"DONNÉES DES DEBRIEFINGS :\n{corpus}"
    )
    result = await llm.chat(
        system_prompt=REPORT_PROMPT,
        messages=[{"role": "user", "content": user_content}],
        max_tokens=1200,
    )

    try:
        output = ReportLLMOutput.model_validate(json.loads(strip_code_fences(result.content)))
        return output.summary, output.insights.model_dump()
    except (json.JSONDecodeError, ValidationError) as first_error:
        logger.warning("Report parsing failed, retrying once: %s", first_error)

    retry_result = await llm.chat(
        system_prompt=REPORT_PROMPT,
        messages=[
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": result.content},
            {
                "role": "user",
                "content": (
                    "Ta réponse précédente n'est pas un JSON valide conforme au format demandé. "
                    "Renvoie UNIQUEMENT le JSON corrigé, sans aucun texte autour."
                ),
            },
        ],
        max_tokens=1200,
    )
    try:
        output = ReportLLMOutput.model_validate(json.loads(strip_code_fences(retry_result.content)))
        return output.summary, output.insights.model_dump()
    except (json.JSONDecodeError, ValidationError) as second_error:
        logger.error("Report synthesis failed after retry: %s", second_error)
        # Degraded report: keep the raw text as summary rather than crashing
        return retry_result.content, {"error": "parsing_failed"}


async def generate_report(
    db: AsyncSession,
    llm: LLMProvider,
    actor: User,
    period_type: ReportPeriodType,
    period_start: date,
    period_end: date,
) -> Report:
    """Aggregate the scope's closed conversations into an LLM-written report."""
    conversations = await _scoped_closed_conversations(db, actor, period_start, period_end)
    if not conversations:
        raise InvalidStateError("Aucune conversation clôturée sur cette période")

    metrics = _compute_metrics(conversations)
    summary, insights = await _generate_synthesis(llm, _build_corpus(conversations), metrics)

    report = Report(
        tenant_id=actor.tenant_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        summary=summary,
        insights=insights,
        metrics=metrics,
    )
    report.conversations = conversations
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def list_reports(db: AsyncSession, actor: User) -> list[Report]:
    result = await db.execute(
        select(Report)
        .where(Report.tenant_id == actor.tenant_id)
        .order_by(Report.generated_at.desc())
    )
    return list(result.scalars().all())


async def get_report(db: AsyncSession, actor: User, report_id: uuid.UUID) -> Report:
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if report is None or report.tenant_id != actor.tenant_id:
        raise NotFoundError("Rapport introuvable")
    return report
