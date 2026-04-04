from __future__ import annotations

import json
from typing import Any

from app.services.ai_generator import AIGenerationOptions, AIResult, generate_legal_document_for_role


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    text = str(raw_text or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


def _short(value: str, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def is_rate_limited_error(error: str | None) -> bool:
    text = str(error or "").lower()
    if not text:
        return False
    return "429" in text or "too many requests" in text or "insufficient_quota" in text


async def run_intake_agent(
    *,
    doc_type: str,
    title: str,
    source_text: str,
    form_data: dict[str, Any],
) -> tuple[dict[str, Any], AIResult]:
    # system_prompt is now handled by generate_legal_document_for_role
    
    payload = {
        "doc_type": doc_type,
        "title": title,
        "source_text_preview": _short(source_text, 9000),
        "form_data": form_data,
    }
    user_prompt = (
        "Create a short intake analysis from the input.\n"
        "Input data:\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )
    result = await generate_legal_document_for_role(
        "intake",
        user_prompt,
        options=AIGenerationOptions(temperature=0.1, max_tokens=900),
    )
    parsed = _parse_json_object(result.text)

    if not isinstance(parsed.get("jurisdiction"), str):
        parsed["jurisdiction"] = "UA"
    if not isinstance(parsed.get("court_type"), str):
        parsed["court_type"] = "unknown"
    if not isinstance(parsed.get("parties"), list):
        parsed["parties"] = []
    if not isinstance(parsed.get("key_facts"), list):
        parsed["key_facts"] = []
    if not isinstance(parsed.get("key_dates"), list):
        parsed["key_dates"] = []
    if not isinstance(parsed.get("amounts"), list):
        parsed["amounts"] = []
    if not isinstance(parsed.get("keywords"), list):
        parsed["keywords"] = []

    return parsed, result


async def run_case_law_rerank_agent(
    *,
    intake: dict[str, Any],
    candidates: list[dict[str, Any]],
    limit: int,
) -> tuple[list[str], AIResult]:
    safe_limit = max(1, min(int(limit or 5), 20))
    if not candidates:
        empty = AIResult(text="", used_ai=False, model="", error="No candidates provided.")
        return [], empty

    system_prompt = (
        "You are a legal researcher. Select the most relevant court decisions for this case.\n"
        "Return JSON only, with no prose outside JSON:\n"
        '{ "selected": [{"id":"string","score":0.0,"why":"string"}] }\n'
        f"Select no more than {safe_limit} items. Use only the provided ids."
    )
    user_prompt = json.dumps(
        {
            "intake": intake,
            "limit": safe_limit,
            "candidates": [
                {
                    "id": str(item.get("id") or ""),
                    "decision_id": item.get("decision_id"),
                    "case_number": item.get("case_number"),
                    "court_name": item.get("court_name"),
                    "court_type": item.get("court_type"),
                    "decision_date": item.get("decision_date"),
                    "summary": _short(str(item.get("summary") or ""), 600),
                    "subject_categories": item.get("subject_categories") or [],
                }
                for item in candidates
                if str(item.get("id") or "").strip()
            ],
        },
        ensure_ascii=False,
    )

    result = await generate_legal_document_for_role(
        "research",
        user_prompt,
        options=AIGenerationOptions(temperature=0.1, max_tokens=700),
    )
    parsed = _parse_json_object(result.text)
    selected = parsed.get("selected")
    if not isinstance(selected, list):
        return [], result

    ids: list[str] = []
    seen: set[str] = set()
    for item in selected:
        if not isinstance(item, dict):
            continue
        raw_id = str(item.get("id") or "").strip()
        if not raw_id or raw_id in seen:
            continue
        seen.add(raw_id)
        ids.append(raw_id)
        if len(ids) >= safe_limit:
            break

    return ids, result


async def run_swot_agent(
    *,
    intake: dict[str, Any],
    precedent_groups: list[dict[str, Any]],
) -> tuple[dict[str, Any], AIResult]:
    system_prompt = (
        "You are a premium strategic litigation consultant and legal economist for Ukrainian law. "
        "Perform a multi-dimensional analysis of this case: SWOT, win probability, financial outlook, and a temporal roadmap.\n"
        "Return valid JSON only, with no prose outside JSON.\n"
        "JSON schema (required keys):\n"
        "{\n"
        '  "strengths": ["string"],\n'
        '  "weaknesses": ["string"],\n'
        '  "opportunities": ["string"],\n'
        '  "threats": ["string"],\n'
        '  "win_probability": 0.0 to 1.0,\n'
        '  "financial_strategy": {\n'
        '     "expected_recovery_min": 0.0,\n'
        '     "expected_recovery_max": 0.0,\n'
        '     "estimated_court_fees": 0.0,\n'
        '     "estimated_attorney_costs": 0.0,\n'
        '     "economic_viability_score": 0.0 to 1.0,\n'
        '     "roi_rationale": "string"\n'
        '  },\n'
        '  "timeline_projection": [\n'
        '     {"stage": "string", "duration_days": 0, "status": "predicted" | "current"}\n'
        '  ],\n'
        '  "penalty_forecast": {\n'
        '     "three_percent_annual": 0.0,\n'
        '     "inflation_losses": 0.0,\n'
        '     "penalties_contractual": 0.0,\n'
        '     "total_extra": 0.0,\n'
        '     "basis_days": 0\n'
        '  }\n'
        "}\n"
    )

    payload = {
        "intake": {
            "financial_exposure": intake.get("financial_exposure_amount"),
            "urgency": intake.get("urgency_level"),
            "document_date": str(intake.get("document_date")),
            "deadline": str(intake.get("deadline_from_document")),
            "classified_type": intake.get("classified_type"),
        },
        "precedents_summary": [
            {
                "type": pg.get("pattern_type"),
                "description": pg.get("pattern_description"),
                "strength": pg.get("pattern_strength"),
            }
            for pg in precedent_groups
        ],
    }
    user_prompt = (
        "Construct a detailed SWOT analysis, estimate win probability, and provide a financial strategy plus timeline.\n"
        "Crucial: If a debt or principal sum is involved, estimate the 3% annual interest, inflation losses, and potential penalties (penalty_forecast).\n"
        "Input context:\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )

    result = await generate_legal_document_for_role(
        "strategy",
        user_prompt,
        options=AIGenerationOptions(temperature=0.2, max_tokens=2000),
    )
    parsed = _parse_json_object(result.text)
    
    # Ensure structure
    for key in ["strengths", "weaknesses", "opportunities", "threats"]:
        if not isinstance(parsed.get(key), list):
            parsed[key] = []
    
    if "win_probability" not in parsed:
        parsed["win_probability"] = 0.5
    if "financial_strategy" not in parsed:
        parsed["financial_strategy"] = {
            "expected_recovery_min": 0, "expected_recovery_max": 0,
            "estimated_court_fees": 0, "estimated_attorney_costs": 0,
            "economic_viability_score": 0.5, "roi_rationale": "Insufficient data"
        }
    if "timeline_projection" not in parsed or not isinstance(parsed["timeline_projection"], list):
        parsed["timeline_projection"] = [
            {"stage": "Підготовка до суду", "duration_days": 14, "status": "predicted"},
            {"stage": "Розгляд справи в суді", "duration_days": 60, "status": "predicted"}
        ]
    if "penalty_forecast" not in parsed:
         parsed["penalty_forecast"] = {
            "three_percent_annual": 0.0, "inflation_losses": 0.0,
            "penalties_contractual": 0.0, "total_extra": 0.0, "basis_days": 0
         }
        
    return parsed, result
