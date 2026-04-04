from __future__ import annotations

import json
import re
import time
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import AnalysisCache, ContractAnalysis, IntakeCache
from app.services.ai_generator import generate_legal_document_for_role


class _AnalysisPayloadModel(BaseModel):
    contract_type: str = "Невизначений тип"
    overall_risk: Literal["low", "medium", "high", "critical"] = "medium"
    critical_risks: list[str] = Field(default_factory=list)
    medium_risks: list[str] = Field(default_factory=list)
    ok_points: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


_FALLBACK_PAYLOAD: dict[str, Any] = {
    "contract_type": "Невизначений тип",
    "overall_risk": "medium",
    "critical_risks": [],
    "medium_risks": [
        "AI аналіз недоступний або повернув невалідну структуру. Перевірте налаштування провайдера."
    ],
    "ok_points": [],
    "recommendations": [
        "Перевірте договір вручну та повторіть аналіз після стабілізації AI-відповіді."
    ],
}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        cleaned: list[str] = []
        for item in value:
            text = str(item).strip()
            if not text:
                continue
            cleaned.append(text[:500])
            if len(cleaned) >= 25:
                break
        return cleaned
    return []


def _redact_pii(text: str) -> str:
    """Basic PII redaction using regex."""
    # Email
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL REDACTED]", text
    )
    # Phone (simple)
    text = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE REDACTED]", text)
    # Names (basic, assuming capitalized words)
    text = re.sub(r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b", "[NAME REDACTED]", text)
    return text


def _check_gdpr_violations(payload: dict[str, Any]) -> list[str]:
    """Check for potential GDPR violations in analysis payload."""
    violations = []
    text_fields = [
        "contract_type",
        "critical_risks",
        "medium_risks",
        "ok_points",
        "recommendations",
    ]
    for field in text_fields:
        value = payload.get(field, "")
        if isinstance(value, list):
            value = " ".join(str(v) for v in value)
        if re.search(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", str(value)
        ):
            violations.append(f"Potential email in {field}")
        if re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", str(value)):
            violations.append(f"Potential phone in {field}")
    return violations


def _redact_gdpr_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Redact PII from analysis payload."""
    redacted = payload.copy()
    text_fields = [
        "contract_type",
        "critical_risks",
        "medium_risks",
        "ok_points",
        "recommendations",
    ]
    for field in text_fields:
        value = redacted.get(field, "")
        if isinstance(value, list):
            redacted[field] = [_redact_pii(str(item)) for item in value]
        else:
            redacted[field] = _redact_pii(str(value))
    return redacted


def _normalize_analysis_payload(raw: dict[str, Any]) -> dict[str, Any]:
    safe_raw = dict(raw or {})
    risk = str(safe_raw.get("overall_risk") or "medium").lower()
    safe_raw["overall_risk"] = (
        risk if risk in {"low", "medium", "high", "critical"} else "medium"
    )
    try:
        payload = _AnalysisPayloadModel.model_validate(safe_raw)
    except ValidationError:
        payload = _AnalysisPayloadModel.model_validate(_FALLBACK_PAYLOAD)

    return {
        "contract_type": str(payload.contract_type).strip() or "Невизначений тип",
        "risk_level": payload.overall_risk,
        "critical_risks": _as_list(payload.critical_risks),
        "medium_risks": _as_list(payload.medium_risks),
        "ok_points": _as_list(payload.ok_points),
        "recommendations": _as_list(payload.recommendations),
    }


_JSON_FENCE_RE = re.compile(r"^```(?:json)?|```$", flags=re.IGNORECASE | re.MULTILINE)


def _strip_markdown_fences(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text or "").strip()


def _parse_json_object(raw: str) -> dict[str, Any] | None:
    text = _strip_markdown_fences((raw or "").strip())
    if not text:
        return None

    # Try to find a fenced JSON block first
    match = re.search(r"```(?:json)?\s*({[\s\S]*?})\s*```", text)
    json_text = ""
    if match:
        json_text = match.group(1)
    else:
        # If no fence, find the largest JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_text = text[start : end + 1]

    if not json_text:
        # As a last resort, try to parse the whole text. It might be a raw JSON string.
        if text.startswith("{") and text.endswith("}"):
            json_text = text
        else:
            return None

    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        return None


async def analyze_contract_text(
    contract_text: str, mode: str = "standard"
) -> tuple[dict[str, Any], str | None, int | None, int]:
    started = time.perf_counter()
    fallback = {
        "contract_type": "Невизначений тип",
        "overall_risk": "medium",
        "critical_risks": [],
        "medium_risks": [
            "AI аналіз недоступний, перевірте AI_PROVIDER, API-ключі та ліміт постачальника."
        ],
        "ok_points": [],
        "recommendations": [
            "Налаштуйте AI_PROVIDER та відповідний API-ключ для повного AI-аналізу."
        ],
    }

    user_prompt = f"Текст договору:\n{contract_text}"

    ai_result = await generate_legal_document_for_role(
        "research", user_prompt, deep=(mode == "deep")
    )
    if not ai_result.used_ai or not (ai_result.text or "").strip():
        normalized = _normalize_analysis_payload(_FALLBACK_PAYLOAD)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return normalized, ai_result.model or None, ai_result.tokens_used, elapsed_ms

    parsed = _parse_json_object(ai_result.text)
    if parsed is None:
        normalized = _normalize_analysis_payload(_FALLBACK_PAYLOAD)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return normalized, ai_result.model or None, ai_result.tokens_used, elapsed_ms

    normalized = _normalize_analysis_payload(parsed)
    # GDPR redaction
    normalized = _redact_gdpr_payload(normalized)
    gdpr_violations = _check_gdpr_violations(normalized)
    if gdpr_violations:
        normalized["gdpr_warnings"] = gdpr_violations
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return normalized, ai_result.model or None, ai_result.tokens_used, elapsed_ms


def create_contract_analysis(
    db: Session,
    *,
    user_id: str,
    file_name: str | None,
    file_url: str | None,
    file_size: int | None,
    analysis_payload: dict[str, Any],
    ai_model: str | None,
    tokens_used: int | None,
    processing_time_ms: int | None,
) -> ContractAnalysis:
    row = ContractAnalysis(
        user_id=user_id,
        file_name=file_name,
        file_url=file_url,
        file_size=file_size,
        contract_type=str(analysis_payload.get("contract_type") or "Невизначений тип"),
        risk_level=str(analysis_payload.get("risk_level") or "medium"),
        critical_risks=analysis_payload.get("critical_risks") or [],
        medium_risks=analysis_payload.get("medium_risks") or [],
        ok_points=analysis_payload.get("ok_points") or [],
        recommendations=analysis_payload.get("recommendations") or [],
        ai_model=ai_model,
        tokens_used=tokens_used,
        processing_time_ms=processing_time_ms,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_contract_analyses(
    db: Session, user_id: str, limit: int = 100
) -> list[ContractAnalysis]:
    stmt = (
        select(ContractAnalysis)
        .where(ContractAnalysis.user_id == user_id)
        .order_by(desc(ContractAnalysis.created_at))
        .limit(max(1, min(limit, 200)))
    )
    return list(db.execute(stmt).scalars().all())


def get_contract_analysis(
    db: Session, user_id: str, analysis_id: str
) -> ContractAnalysis | None:
    row = db.get(ContractAnalysis, analysis_id)
    if row is None or row.user_id != user_id:
        return None
    return row


def delete_contract_analysis(db: Session, user_id: str, analysis_id: str) -> bool:
    row = get_contract_analysis(db, user_id, analysis_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def get_analysis_cache(
    db: Session, user_id: str, file_hash: str
) -> AnalysisCache | None:
    stmt = select(AnalysisCache).where(
        AnalysisCache.user_id == user_id, AnalysisCache.file_hash == file_hash
    )
    return db.execute(stmt).scalar_one_or_none()


def create_analysis_cache(
    db: Session,
    user_id: str,
    file_hash: str,
    analysis_payload: dict[str, Any],
    ai_model: str | None,
    tokens_used: int | None,
    processing_time_ms: int | None,
) -> AnalysisCache:
    row = AnalysisCache(
        user_id=user_id,
        file_hash=file_hash,
        analysis_payload=analysis_payload,
        ai_model=ai_model,
        tokens_used=tokens_used,
        processing_time_ms=processing_time_ms,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_intake_cache(db: Session, user_id: str, file_hash: str) -> IntakeCache | None:
    stmt = select(IntakeCache).where(
        IntakeCache.user_id == user_id,
        IntakeCache.file_hash == file_hash
    )
    return db.execute(stmt).scalar_one_or_none()


def create_intake_cache(
    db: Session,
    user_id: str,
    file_hash: str,
    intake_result: dict[str, Any],
    ai_model: str | None,
    tokens_used: int | None,
    processing_time_ms: int,
) -> IntakeCache:
    row = IntakeCache(
        user_id=user_id,
        file_hash=file_hash,
        intake_result=intake_result,
        ai_model=ai_model,
        tokens_used=tokens_used,
        processing_time_ms=processing_time_ms,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
