from __future__ import annotations

from datetime import date
import json
import re
from typing import Any

from app.config import settings
from app.models import CaseLawCache, DocumentAnalysisIntake
from app.services.ai_generator import AIGenerationOptions, generate_legal_document

_CASE_NUMBER_RE = re.compile(r"^\d+/\d+/\d+$")
_ARTICLE_RE = re.compile(r"(ст\.?\s*\d{1,4}(?:[-–]\d{1,4})?\s*[А-ЯA-ZІЇЄҐA-Za-z.\s]{0,40})", flags=re.IGNORECASE)


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
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _clamp(value: float | None, minimum: float = 0.0, maximum: float = 1.0) -> float | None:
    if value is None:
        return None
    return max(minimum, min(maximum, value))


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _safe_iso_date(value: Any) -> str | None:
    text = _normalize_text(value)
    if not text or text.lower() == "null":
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    return None


def _stage_options(stage: str) -> AIGenerationOptions:
    if stage == "intake":
        return AIGenerationOptions(
            temperature=settings.ai_intake_temperature,
            max_tokens=settings.ai_intake_max_tokens,
            openai_model=settings.ai_intake_openai_model,
            anthropic_model=settings.ai_intake_anthropic_model,
            gemini_model=settings.ai_intake_gemini_model,
        )
    if stage == "precedent":
        return AIGenerationOptions(
            temperature=settings.ai_precedent_temperature,
            max_tokens=settings.ai_precedent_max_tokens,
            openai_model=settings.ai_precedent_openai_model,
            anthropic_model=settings.ai_precedent_anthropic_model,
            gemini_model=settings.ai_precedent_gemini_model,
        )
    return AIGenerationOptions(
        temperature=settings.ai_deep_temperature,
        max_tokens=settings.ai_deep_max_tokens,
        openai_model=settings.ai_deep_openai_model,
        anthropic_model=settings.ai_deep_anthropic_model,
        gemini_model=settings.ai_deep_gemini_model,
    )


def _map_document_type(value: Any) -> str:
    normalized = _normalize_text(value).lower()
    if normalized in {"court_order", "court_decision", "judgment", "order"}:
        return "court_decision"
    if normalized in {"appeal", "statement_of_claim", "response", "petition", "motion", "cassation"}:
        return "procedural_document"
    if normalized in {"claim_notice", "demand_letter", "letter_before_claim"}:
        return "claim_notice"
    if normalized in {"contract"}:
        return "contract"
    if normalized in {"unknown", ""}:
        return "other"
    return normalized


def _primary_role_from_parties(parties: list[dict[str, Any]]) -> str | None:
    for item in parties:
        role = _normalize_text(item.get("role")).lower()
        if role:
            return role
    return None


def _normalize_parties(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    parties: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _normalize_text(item.get("name"))
        role = _normalize_text(item.get("role")).lower()
        contact = _normalize_text(item.get("contact"))
        if not name or not role:
            continue
        payload = {"name": name, "role": role}
        if contact:
            payload["contact"] = contact
        parties.append(payload)
    return parties[:8]


def _risk_issue_from_flag(flag: str) -> dict[str, str]:
    normalized = _normalize_text(flag).lower()
    mapping = {
        "expired_statute_of_limitations": (
            "high",
            "Possible limitation period issue.",
            "Urgent limitation analysis is needed before filing.",
        ),
        "missing_defendant_address": (
            "high",
            "Defendant address is missing or incomplete.",
            "Service can fail and delay the case.",
        ),
        "unclear_jurisdiction": (
            "high",
            "Jurisdiction is unclear from the source.",
            "The document can be filed in the wrong court.",
        ),
        "missing_evidence_reference": (
            "medium",
            "The source refers to facts without evidence anchors.",
            "The factual matrix is vulnerable to challenge.",
        ),
        "ambiguous_claim_amount": (
            "medium",
            "Claim amount is unclear or inconsistent.",
            "Financial request may require clarification.",
        ),
        "missing_procedural_date": (
            "medium",
            "A key procedural date is missing.",
            "Timeline planning remains uncertain.",
        ),
    }
    severity, description, impact = mapping.get(
        normalized,
        ("medium", f"Risk flag detected: {normalized or 'unspecified'}.", "Human review is recommended."),
    )
    return {
        "issue_type": normalized or "unspecified_risk",
        "severity": severity,
        "description": description,
        "impact": impact,
    }


def _risk_levels_from_flags(flags: list[str]) -> tuple[str, str, str]:
    joined = " ".join(flag.lower() for flag in flags)
    legal = "medium"
    procedural = "medium"
    financial = "low"
    if "expired_statute_of_limitations" in joined:
        legal = "high"
    if any(flag in joined for flag in ("unclear_jurisdiction", "missing_defendant_address", "missing_procedural_date")):
        procedural = "high"
    if "ambiguous_claim_amount" in joined:
        financial = "medium"
    return legal, procedural, financial


def _confidence_score(label: Any, extraction_quality: Any) -> float | None:
    score = _safe_float(extraction_quality)
    if score is not None:
        if score > 1.0:
            score = score / 100.0
        score = _clamp(score)
    label_text = _normalize_text(label).lower()
    label_boost = {"high": 0.88, "medium": 0.68, "low": 0.44}.get(label_text)
    if score is None:
        return label_boost
    if label_boost is None:
        return score
    return round((score + label_boost) / 2.0, 2)


def _extract_legal_basis(text: str, *, max_items: int = 8) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for raw in _ARTICLE_RE.findall(text or ""):
        cleaned = _normalize_text(raw)
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        items.append(cleaned)
        if len(items) >= max_items:
            break
    return items


def _build_intake_preview(data: dict[str, Any], parties: list[dict[str, str]]) -> str:
    lines: list[str] = []
    document_type = _normalize_text(data.get("document_type")) or "unknown"
    case_info = data.get("case_info") if isinstance(data.get("case_info"), dict) else {}
    court = case_info.get("court") if isinstance(case_info.get("court"), dict) else {}
    claim = data.get("claim") if isinstance(data.get("claim"), dict) else {}
    key_dates = data.get("key_dates") if isinstance(data.get("key_dates"), dict) else {}

    lines.append(f"Document type: {document_type}")
    case_number = _normalize_text(case_info.get("case_number"))
    if case_number:
        lines.append(f"Case number: {case_number}")
    court_type = _normalize_text(court.get("type"))
    court_jurisdiction = _normalize_text(court.get("jurisdiction"))
    court_instance = _normalize_text(court.get("instance"))
    if court_type or court_jurisdiction or court_instance:
        lines.append("Court: " + ", ".join(item for item in (court_type, court_jurisdiction, court_instance) if item))
    filing_date = _safe_iso_date(case_info.get("filing_date")) or _safe_iso_date(key_dates.get("filing_date"))
    if filing_date:
        lines.append(f"Filing date: {filing_date}")
    deadline = _safe_iso_date(case_info.get("deadline_response")) or _safe_iso_date(key_dates.get("deadline_for_response"))
    if deadline:
        lines.append(f"Deadline: {deadline}")
    for party in parties[:6]:
        line = f"{party.get('role')}: {party.get('name')}"
        contact = _normalize_text(party.get("contact"))
        if contact:
            line += f" ({contact})"
        lines.append(line)
    subject_matter = _normalize_text(claim.get("subject_matter"))
    if subject_matter:
        lines.append(f"Subject matter: {subject_matter}")
    amount = claim.get("amount_claimed_uah")
    currency = _normalize_text(claim.get("currency"))
    if amount not in (None, ""):
        lines.append(f"Claim amount: {amount} {currency or 'UAH'}")
    legal_basis = data.get("legal_basis") if isinstance(data.get("legal_basis"), list) else []
    if legal_basis:
        lines.append("Legal basis: " + ", ".join(_normalize_text(item) for item in legal_basis if _normalize_text(item)))
    return "\n".join(item for item in lines if item).strip()


async def run_ai_intake_classifier(source_text: str) -> dict[str, Any]:
    text = str(source_text or "").strip()
    if len(text) < 40:
        return {}

    system_prompt = (
        "You are a court intake analyst for Ukrainian litigation. "
        "Extract structured data fast, be strict, use null for missing facts, and return JSON only."
    )
    user_prompt = (
        "PROMPT 1: AI INTAKE CLASSIFIER\n"
        "Output JSON with keys: "
        '{"document_type":"","case_info":{"case_number":"","court":{"type":"","jurisdiction":"","instance":""},"filing_date":"","deadline_response":""},'
        '"parties":[{"name":"","role":"","contact":""}],"claim":{"type":"","amount_claimed_uah":null,"currency":"","subject_matter":""},'
        '"key_dates":{"incident_date":"","filing_date":"","hearing_date":"","deadline_for_response":""},"legal_basis":[],"risk_flags":[],'
        '"extraction_quality":0.0,"confidence":"high|medium|low"}\n'
        "Rules:\n"
        "- If a field is absent, use null.\n"
        '- case_number must match format "123/1234/2024"; otherwise null.\n'
        '- document_type must come from the provided list or be "unknown".\n'
        "- Do not hallucinate parties, dates, or legal basis.\n"
        "- Return JSON only.\n\n"
        f"Document text:\n{text[:14000]}"
    )
    ai_result = await generate_legal_document(system_prompt, user_prompt, options=_stage_options("intake"))
    if not ai_result.used_ai:
        return {}

    parsed = _parse_json_object(ai_result.text)
    if not parsed:
        return {}

    case_info = parsed.get("case_info") if isinstance(parsed.get("case_info"), dict) else {}
    claim = parsed.get("claim") if isinstance(parsed.get("claim"), dict) else {}
    key_dates = parsed.get("key_dates") if isinstance(parsed.get("key_dates"), dict) else {}
    parties = _normalize_parties(parsed.get("parties"))
    risk_flags = [_normalize_text(item).lower() for item in (parsed.get("risk_flags") or []) if _normalize_text(item)]
    case_number = _normalize_text(case_info.get("case_number"))
    if case_number and not _CASE_NUMBER_RE.fullmatch(case_number):
        case_number = ""

    legal, procedural, financial = _risk_levels_from_flags(risk_flags)
    preview = _build_intake_preview(parsed, parties)
    amount_value = _safe_float(claim.get("amount_claimed_uah"))
    confidence_value = _confidence_score(parsed.get("confidence"), parsed.get("extraction_quality"))

    return {
        "classified_type": _map_document_type(parsed.get("document_type")),
        "jurisdiction": "UA",
        "primary_party_role": _primary_role_from_parties(parties),
        "identified_parties": parties,
        "subject_matter": _normalize_text(claim.get("subject_matter")) or _normalize_text(claim.get("type")),
        "financial_exposure_amount": amount_value,
        "financial_exposure_currency": _normalize_text(claim.get("currency")) or "UAH",
        "financial_exposure_type": _normalize_text(claim.get("type")) or None,
        "document_date": _safe_iso_date(case_info.get("filing_date")) or _safe_iso_date(key_dates.get("filing_date")),
        "deadline_from_document": _safe_iso_date(case_info.get("deadline_response")) or _safe_iso_date(key_dates.get("deadline_for_response")),
        "risk_level_legal": legal,
        "risk_level_procedural": procedural,
        "risk_level_financial": financial,
        "urgency_level": "high" if _safe_iso_date(case_info.get("deadline_response")) else "medium",
        "detected_issues": [_risk_issue_from_flag(item) for item in risk_flags[:8]],
        "classifier_confidence": confidence_value,
        "classifier_model": ai_result.model or "ai-intake-classifier",
        "raw_text_preview": preview or text[:2000],
        "legal_basis": _extract_legal_basis(text),
        "case_number_hint": case_number or None,
    }


def serialize_intake_for_agents(intake: DocumentAnalysisIntake) -> dict[str, Any]:
    issues = intake.detected_issues or []
    risk_flags = [str(item.get("issue_type") or "").strip() for item in issues if isinstance(item, dict)]
    return {
        "document_type": intake.classified_type,
        "case_info": {
            "case_number": None,
            "court": {"type": None, "jurisdiction": intake.jurisdiction, "instance": None},
            "filing_date": (intake.document_date if isinstance(intake.document_date, str) else intake.document_date.isoformat()) if intake.document_date else None,
            "deadline_response": (intake.deadline_from_document if isinstance(intake.deadline_from_document, str) else intake.deadline_from_document.isoformat()) if intake.deadline_from_document else None,
        },
        "parties": intake.identified_parties or [],
        "claim": {
            "type": intake.financial_exposure_type,
            "amount_claimed_uah": float(intake.financial_exposure_amount) if intake.financial_exposure_amount is not None else None,
            "currency": intake.financial_exposure_currency,
            "subject_matter": intake.subject_matter,
        },
        "key_dates": {
            "incident_date": None,
            "filing_date": (intake.document_date if isinstance(intake.document_date, str) else intake.document_date.isoformat()) if intake.document_date else None,
            "hearing_date": None,
            "deadline_for_response": (intake.deadline_from_document if isinstance(intake.deadline_from_document, str) else intake.deadline_from_document.isoformat()) if intake.deadline_from_document else None,
        },
        "legal_basis": _extract_legal_basis((intake.source_text or "") + "\n" + (intake.raw_text_preview or "")),
        "risk_flags": [item for item in risk_flags if item],
        "extraction_quality": intake.classifier_confidence,
        "confidence": "high" if float(intake.classifier_confidence or 0.0) >= 0.8 else "medium",
    }


def _court_strength(court_name: str | None) -> str:
    lowered = _normalize_text(court_name).lower()
    if "supreme" in lowered or "верхов" in lowered:
        return "supreme"
    if "appeal" in lowered or "апеляц" in lowered:
        return "appellate"
    return "district"


def _quote_is_supported(quote: str, candidate: CaseLawCache) -> bool:
    snippet = _normalize_text(quote)
    if not snippet:
        return False
    haystacks = [_normalize_text(candidate.full_text), _normalize_text(candidate.summary)]
    return any(snippet.lower() in haystack.lower() for haystack in haystacks if haystack)


def _fallback_ranked_refs(candidates: list[CaseLawCache]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for index, row in enumerate(candidates, start=1):
        refs.append(
            {
                "id": row.id,
                "source": row.source,
                "decision_id": row.decision_id,
                "case_number": row.case_number,
                "court_name": row.court_name,
                "decision_date": row.decision_date.isoformat() if row.decision_date else None,
                "summary": row.summary,
                "pattern_type": "neutral_pattern",
                "relevance_score": round(max(0.1, 1.0 - (index - 1) * 0.06), 2),
                "parties_match": 0.0,
                "fact_similarity": 0.0,
                "legal_basis_match": 0.0,
                "court_strength": _court_strength(row.court_name),
                "outcome": None,
                "reason": "",
                "risk_assessment": "neutral",
                "key_quote": "",
            }
        )
    return refs


async def run_ai_precedent_reranker(intake: DocumentAnalysisIntake, candidates: list[CaseLawCache]) -> dict[str, Any]:
    if not candidates:
        return {"ranked_precedents": [], "summary": {"total_found": 0, "top_3_reasons": [], "danger_flags": []}}

    intake_payload = serialize_intake_for_agents(intake)
    candidate_payload = [
        {
            "id": row.id,
            "decision_id": row.decision_id,
            "court": row.court_name,
            "date": row.decision_date.isoformat() if row.decision_date else None,
            "case_number": row.case_number,
            "subject_categories": row.subject_categories or [],
            "summary": row.summary,
            "full_text_excerpt": _normalize_text((row.full_text or row.summary or "")[:1400]),
        }
        for row in candidates
    ]
    system_prompt = (
        "You are a legal researcher that ranks Ukrainian case law by relevance and strength. "
        "Use only provided decisions, return JSON only, and do not invent quotes."
    )
    user_prompt = (
        "PROMPT 2: AI PRECEDENT RERANKER\n"
        "Return JSON with keys: "
        '{"ranked_precedents":[{"decision_id":"","court":"","date":"","parties_match":0.0,"fact_similarity":0.0,'
        '"legal_basis_match":0.0,"court_strength":"supreme|appellate|district","outcome":"plaintiff_won|defendant_won|partial",'
        '"relevance_score":0.0,"reason":"","risk_assessment":"favorable|neutral|unfavorable","key_quote":""}],"summary":{"total_found":0,"top_3_reasons":[],"danger_flags":[]}}\n'
        "Rules:\n"
        "- Sort by relevance_score descending.\n"
        "- key_quote must be a real quote from the provided summary or full_text_excerpt.\n"
        "- Use only the provided decision ids.\n"
        "- Return JSON only.\n\n"
        "Intake JSON:\n"
        + json.dumps(intake_payload, ensure_ascii=False)
        + "\n\nPrecedents found:\n"
        + json.dumps(candidate_payload, ensure_ascii=False)
    )
    ai_result = await generate_legal_document(system_prompt, user_prompt, options=_stage_options("precedent"))
    if not ai_result.used_ai:
        return {
            "ranked_precedents": _fallback_ranked_refs(candidates),
            "summary": {"total_found": len(candidates), "top_3_reasons": [], "danger_flags": []},
            "ai_model": "",
        }

    parsed = _parse_json_object(ai_result.text)
    ranked_payload = parsed.get("ranked_precedents") if isinstance(parsed.get("ranked_precedents"), list) else []
    summary = parsed.get("summary") if isinstance(parsed.get("summary"), dict) else {}
    lookup: dict[str, CaseLawCache] = {}
    for row in candidates:
        lookup[row.decision_id] = row
        lookup[row.id] = row

    ranked_refs: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for item in ranked_payload:
        if not isinstance(item, dict):
            continue
        key = _normalize_text(item.get("decision_id"))
        row = lookup.get(key)
        if row is None or row.id in used_ids:
            continue
        used_ids.add(row.id)
        relevance_score = _clamp(_safe_float(item.get("relevance_score")) or 0.0) or 0.0
        risk_assessment = _normalize_text(item.get("risk_assessment")).lower() or "neutral"
        if risk_assessment == "favorable":
            pattern_type = "winning_pattern"
        elif risk_assessment == "unfavorable":
            pattern_type = "losing_pattern"
        else:
            pattern_type = "neutral_pattern"
        quote = _normalize_text(item.get("key_quote"))
        if quote and not _quote_is_supported(quote, row):
            quote = ""
        ranked_refs.append(
            {
                "id": row.id,
                "source": row.source,
                "decision_id": row.decision_id,
                "case_number": row.case_number,
                "court_name": row.court_name,
                "decision_date": row.decision_date.isoformat() if row.decision_date else None,
                "summary": row.summary,
                "pattern_type": pattern_type,
                "relevance_score": round(relevance_score, 2),
                "parties_match": round(_clamp(_safe_float(item.get("parties_match")) or 0.0) or 0.0, 2),
                "fact_similarity": round(_clamp(_safe_float(item.get("fact_similarity")) or 0.0) or 0.0, 2),
                "legal_basis_match": round(_clamp(_safe_float(item.get("legal_basis_match")) or 0.0) or 0.0, 2),
                "court_strength": _normalize_text(item.get("court_strength")).lower() or _court_strength(row.court_name),
                "outcome": _normalize_text(item.get("outcome")).lower() or None,
                "reason": _normalize_text(item.get("reason")),
                "risk_assessment": risk_assessment,
                "key_quote": quote[:200],
            }
        )

    if not ranked_refs:
        ranked_refs = _fallback_ranked_refs(candidates)

    for row in candidates:
        if row.id in used_ids:
            continue
        ranked_refs.extend(_fallback_ranked_refs([row]))

    danger_flags = [_normalize_text(item) for item in (summary.get("danger_flags") or []) if _normalize_text(item)]
    top_3_reasons = [_normalize_text(item) for item in (summary.get("top_3_reasons") or []) if _normalize_text(item)]
    return {
        "ranked_precedents": ranked_refs,
        "summary": {
            "total_found": int(summary.get("total_found") or len(candidates)),
            "top_3_reasons": top_3_reasons[:3],
            "danger_flags": danger_flags[:6],
        },
        "ai_model": ai_result.model or "",
    }
