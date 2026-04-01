import json
import httpx

from app.config import settings


async def get_agent_response(
    system_prompt: str,
    messages: list[dict],
) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "max_tokens": 300,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *messages,
                ],
            },
            timeout=60.0,
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def extract_conversation_data(messages: list[dict]) -> dict:
    from app.services.prompts import EXTRACTION_PROMPT

    # On envoie toute la conversation + le prompt d'extraction
    conversation_text = "\n".join(
        f"{'Commercial' if m['role'] == 'user' else 'Agent'}: {m['content']}"
        for m in messages
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "max_tokens": 500,
                "messages": [
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": conversation_text},
                ],
            },
            timeout=60.0,
        )
        data = response.json()
        raw = data["choices"][0]["message"]["content"]

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "extraction_failed", "raw": raw}