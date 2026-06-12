"""Post-conversation structured extraction.

The LLM output is validated against a Pydantic schema; on parsing failure we
retry once with a corrective message, and finally store an error payload
instead of crashing.
"""

import json
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from app.services.llm.base import LLMMessage, LLMProvider
from app.services.llm.prompts import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class CompetitorMention(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    price_mentioned: bool | None = None
    price_detail: str | None = None


class ExtractedData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sentiment: str | None = None
    client_name: str | None = None
    order_result: str | None = None
    order_trend: str | None = None
    objections: list[str] = []
    competitors: list[CompetitorMention] = []
    product_knowledge_gap: bool | None = None
    knowledge_gap_detail: str | None = None
    follow_up_needed: bool | None = None
    follow_up_date: str | None = None
    follow_up_note: str | None = None


def strip_code_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def _parse(raw: str) -> dict[str, Any]:
    return ExtractedData.model_validate(json.loads(strip_code_fences(raw))).model_dump()


def _transcript(messages: list[LLMMessage]) -> str:
    return "\n".join(
        f"{'Commercial' if m['role'] == 'user' else 'Agent'}: {m['content']}" for m in messages
    )


async def extract_conversation_data(
    llm: LLMProvider,
    messages: list[LLMMessage],
) -> tuple[dict[str, Any], int]:
    """Turn a closed conversation into structured data.

    Returns (extracted payload, total LLM tokens used). Never raises on bad
    LLM output: falls back to an error payload after one corrective retry.
    """
    transcript = _transcript(messages)
    result = await llm.chat(
        system_prompt=EXTRACTION_PROMPT,
        messages=[{"role": "user", "content": transcript}],
        max_tokens=500,
    )
    tokens_used = result.total_tokens

    try:
        return _parse(result.content), tokens_used
    except (json.JSONDecodeError, ValidationError) as first_error:
        logger.warning("Extraction parsing failed, retrying once: %s", first_error)

    # One corrective retry: show the model its invalid output and ask again
    retry_result = await llm.chat(
        system_prompt=EXTRACTION_PROMPT,
        messages=[
            {"role": "user", "content": transcript},
            {"role": "assistant", "content": result.content},
            {
                "role": "user",
                "content": (
                    "Ta réponse précédente n'est pas un JSON valide conforme au format demandé. "
                    "Renvoie UNIQUEMENT le JSON corrigé, sans aucun texte autour."
                ),
            },
        ],
        max_tokens=500,
    )
    tokens_used += retry_result.total_tokens

    try:
        return _parse(retry_result.content), tokens_used
    except (json.JSONDecodeError, ValidationError) as second_error:
        logger.error("Extraction failed after retry: %s", second_error)
        return {"error": "extraction_failed", "raw": retry_result.content}, tokens_used
