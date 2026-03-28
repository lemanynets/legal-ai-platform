"""
Stub intake analyzer — runs the AI document analysis pipeline.

In production this calls the Anthropic/OpenAI API. For Docker local testing
without API keys it returns a placeholder result so the app stays functional.
"""
from __future__ import annotations

import os
from typing import Any


async def run_intake_analysis(
    file_content: bytes,
    file_name: str,
    contract_type: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run AI analysis on the uploaded document."""

    # Check for available AI provider
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if anthropic_key:
        return await _analyze_anthropic(file_content, file_name, contract_type, anthropic_key)
    if openai_key:
        return await _analyze_openai(file_content, file_name, contract_type, openai_key)

    # No API keys — return demo result
    return _demo_result(file_name, contract_type)


async def _analyze_anthropic(
    file_content: bytes,
    file_name: str,
    contract_type: str | None,
    api_key: str,
) -> dict[str, Any]:
    import anthropic  # noqa: PLC0415

    client = anthropic.AsyncAnthropic(api_key=api_key)
    text_content = file_content.decode("utf-8", errors="replace")[:8000]

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Проаналізуй такий юридичний документ ({contract_type or 'контракт'}):\n\n"
                    f"{text_content}\n\n"
                    "Поверни JSON з полями: risk_level (low/medium/high/critical), "
                    "critical_risks (list), medium_risks (list), ok_points (list), recommendations (list)."
                ),
            }
        ],
    )
    import json  # noqa: PLC0415

    try:
        return json.loads(message.content[0].text)
    except Exception:
        return {"risk_level": "medium", "critical_risks": [], "medium_risks": [], "ok_points": [], "recommendations": []}


async def _analyze_openai(
    file_content: bytes,
    file_name: str,
    contract_type: str | None,
    api_key: str,
) -> dict[str, Any]:
    import openai  # noqa: PLC0415
    import json  # noqa: PLC0415

    client = openai.AsyncOpenAI(api_key=api_key)
    text_content = file_content.decode("utf-8", errors="replace")[:8000]

    response = await client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Проаналізуй такий юридичний документ ({contract_type or 'контракт'}):\n\n"
                    f"{text_content}\n\n"
                    "Поверни JSON з полями: risk_level (low/medium/high/critical), "
                    "critical_risks (list), medium_risks (list), ok_points (list), recommendations (list)."
                ),
            }
        ],
    )
    try:
        return json.loads(response.choices[0].message.content or "{}")
    except Exception:
        return {"risk_level": "medium", "critical_risks": [], "medium_risks": [], "ok_points": [], "recommendations": []}


def _demo_result(file_name: str, contract_type: str | None) -> dict[str, Any]:
    """Placeholder result when no AI API keys are configured."""
    return {
        "risk_level": "medium",
        "critical_risks": ["[Demo режим] API ключ не налаштовано"],
        "medium_risks": ["Додайте ANTHROPIC_API_KEY або OPENAI_API_KEY для реального аналізу"],
        "ok_points": [f"Файл '{file_name}' отримано успішно"],
        "recommendations": ["Налаштуйте змінні середовища у файлі .env.docker"],
        "ai_model": "demo",
        "tokens_used": 0,
    }
