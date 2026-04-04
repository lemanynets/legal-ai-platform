from __future__ import annotations

from decimal import Decimal
import html
import hashlib
import json
import re
from datetime import datetime
from typing import Any, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.catalog import get_document_type
from app.database import get_db
from app.models.legal_strategy import (
    DocumentAnalysisIntake,
    LegalStrategyBlueprint,
)
from app.schemas import (
    DocumentIntakeIssueItem,
    DocumentIntakeResponse,
    GenerateWithStrategyRequest,
    GenerateWithStrategyResponse,
    GenerateBundleWithStrategyResponse,
    PrecedentGroupItem,
    PrecedentMapRefItem,
    PrecedentMapResponse,
    ProcessualValidationCheck,
    StrategyAuditResponse,
    StrategyBlueprintRequest,
    StrategyBlueprintResponse,
    JudgeSimulationResponse,
)
from app.services.ai_generator import generate_legal_document_for_role
from app.services.agentic_generation import (
    is_rate_limited_error,
    run_case_law_rerank_agent,
    run_intake_agent,
)
from app.services.audit import log_action
from app.services.auto_processor import (
    build_form_data_for_doc_type,
    extract_parties_and_facts,
)
from app.services.case_law_enricher import (
    attach_case_law_refs_to_document,
    build_case_law_prompt_context,
    build_motivation_reference_block,
    enrich_document_with_case_law,
    inject_motivation_references,
)
from app.services.document_versions import create_document_version
from app.services.file_text_extractor import (
    _repair_mojibake_text,
    extract_text_from_file,
)
from app.models.generated_document import GeneratedDocument
from app.services.generated_documents import create_generated_document
from app.services.legal_strategy import (
    bind_strategy_to_document,
    build_precedent_groups_for_intake,
    build_strategy_blueprint,
    classify_document_intake,
    create_document_analysis_intake,
    create_document_generation_audit,
    get_document_analysis_intake,
    get_document_generation_audit,
    get_strategy_blueprint,
    list_precedent_groups,
)
from app.services.contract_analyses import (
    create_analysis_cache,
    create_intake_cache,
    get_analysis_cache,
    get_intake_cache,
)
from app.services.judge_simulator import simulate_judge_perspective
from app.services.document_export import render_docx_bytes
from app.services.ai_generator import SYSTEM_PROMPT
from app.services.prompt_builder import (
    build_generation_validation_checks,
    build_pre_generation_gate_checks,
    build_preview_text,
    build_user_prompt,
    sanitize_prompt_context,
    ensure_processual_quality,
    normalize_prayer_section,
)
from app.services.realtime import publish_user_event
from app.services.subscriptions import (
    ensure_analysis_quota,
    ensure_document_quota,
    get_or_create_subscription,
    mark_analysis_processed,
    mark_document_generated,
    to_payload,
)


router = APIRouter(prefix="/api", tags=["strategy"])
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_META_TAG_RE = re.compile(
    r"<meta\s+name=\"(?P<name>[^\"]+)\"\s+content=\"(?P<content>[^\"]*)\"[^>]*>",
    flags=re.IGNORECASE,
)
_CASE_NUMBER_RE = re.compile(
    r"(?:справа\s*№\s*|case\s*no\.?\s*|causenum\s*[=:]?\s*)([0-9A-Za-zА-Яа-яІіЇїЄє/\-]+)",
    flags=re.IGNORECASE,
)
_PROCEEDING_NUMBER_RE = re.compile(
    r"(?:провадження\s*№\s*|procnum\s*[=:]?\s*)([0-9A-Za-zА-Яа-яІіЇїЄє/\-]+)",
    flags=re.IGNORECASE,
)
_APPELLANT_RE = re.compile(
    r"(?:апелянт|скаржник)\s*:\s*([^\n\r]+)", flags=re.IGNORECASE
)
_OTHER_PARTY_RE = re.compile(
    r"(?:інший\s+учасник|інша\s+сторона|відповідач|боржник)\s*:\s*([^\n\r]+)",
    flags=re.IGNORECASE,
)
_REPRESENTATIVE_RE = re.compile(
    r"(?:представник)\s*:\s*([^\n\r]+)", flags=re.IGNORECASE
)
_DOC_KIND_MARKERS: tuple[tuple[str, str], ...] = (
    ("апеляційна скарга", "Апеляційна скарга"),
    ("касаційна скарга", "Касаційна скарга"),
    ("ухвала", "Ухвала"),
    ("постанова", "Постанова"),
    ("рішення", "Рішення"),
)
_STRATEGY_TEXT_KEYWORDS: tuple[str, ...] = (
    "суд",
    "апеляц",
    "касац",
    "скарга",
    "рішення",
    "ухвала",
    "постанова",
    "справа",
    "провадження",
    "позивач",
    "відповідач",
    "апелянт",
    "представник",
)


def _extract_meta_fields(source_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in _META_TAG_RE.finditer(source_text or ""):
        name = str(match.group("name") or "").strip().upper()
        content = html.unescape(str(match.group("content") or "").strip())
        if name and content:
            fields[name] = content
    return fields


def _score_strategy_text_candidate(source_text: str) -> int:
    text = str(source_text or "")
    lowered = text.lower()
    keyword_score = sum(lowered.count(token) for token in _STRATEGY_TEXT_KEYWORDS) * 40
    cyrillic_score = len(re.findall(r"[А-Яа-яІіЇїЄєҐґ]", text))
    noise_penalty = (
        sum(
            lowered.count(token)
            for token in ("meta name", "<!doctype", "<html", "content=")
        )
        * 25
    )
    mojibake_penalty = (
        len(re.findall(r"(?:Р[А-яЁёІіЇїЄєҐґ]|С[А-яЁёІіЇїЄєҐґ]|Ѓ|є|ї|џ)", text)) * 3
    )
    return keyword_score + cyrillic_score - noise_penalty - mojibake_penalty


def _repair_strategy_text(source_text: str) -> str:
    original = str(source_text or "")
    candidates = [original, _repair_mojibake_text(original)]
    for source_encoding in ("cp1251", "windows-1251", "cp1250", "cp1252", "latin1"):
        try:
            repaired = original.encode(source_encoding, errors="ignore").decode(
                "utf-8", errors="ignore"
            )
        except Exception:
            continue
        repaired = repaired.strip()
        if repaired:
            candidates.append(repaired)
    unique_candidates = [item for item in dict.fromkeys(candidates) if item]
    if not unique_candidates:
        return ""
    return max(unique_candidates, key=_score_strategy_text_candidate)


def _clean_strategy_source_text(source_text: str) -> str:
    text = _repair_strategy_text(html.unescape(str(source_text or "")))
    text = re.sub(r"&nbsp;?", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"&#\d+;", " ", text)
    text = _HTML_TAG_RE.sub(" ", text)
    text = re.sub(
        r"\b(?:doctype|html|head|body|meta)\b", " ", text, flags=re.IGNORECASE
    )
    text = re.sub(
        r"\b(?:name|content)\s*=\s*\"[^\"]*\"", " ", text, flags=re.IGNORECASE
    )
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _extract_case_number(source_text: str, meta_fields: dict[str, str]) -> str:
    for key in ("CAUSENUM",):
        value = str(meta_fields.get(key) or "").strip()
        if value:
            return value
    match = _CASE_NUMBER_RE.search(source_text or "")
    return str(match.group(1) or "").strip() if match else ""


def _extract_proceeding_number(source_text: str, meta_fields: dict[str, str]) -> str:
    for key in ("PROCNUM",):
        value = str(meta_fields.get(key) or "").strip()
        if value:
            return value
    match = _PROCEEDING_NUMBER_RE.search(source_text or "")
    return str(match.group(1) or "").strip() if match else ""


def _extract_named_field(pattern: re.Pattern[str], source_text: str) -> str:
    match = pattern.search(source_text or "")
    if not match:
        return ""
    value = re.sub(r"\s+", " ", str(match.group(1) or "")).strip(" ,.;:")
    blocked = {"відсутній", "не зазначено", "дані уточнюються за матеріалами справи"}
    if value.lower() in blocked:
        return ""
    return value


def _detect_doc_kind(source_text: str) -> str:
    lowered = str(source_text or "").lower()
    for marker, label in _DOC_KIND_MARKERS:
        if marker in lowered:
            return label
    return "Процесуальний документ"


def _extract_key_lines(cleaned_text: str, *, limit: int = 5) -> list[str]:
    lines: list[str] = []
    for raw_line in re.split(r"[\n\r]+", cleaned_text or ""):
        line = re.sub(r"\s+", " ", raw_line).strip(" -–—")
        if len(line) < 25:
            continue
        lowered = line.lower()
        if any(
            token in lowered for token in ("meta name", "doctype", "html4", "content=")
        ):
            continue
        if line not in lines:
            lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def _build_strategy_source_brief(source_text: str) -> str:
    source_text = _repair_strategy_text(str(source_text or ""))
    meta_fields = _extract_meta_fields(source_text)
    if (
        not meta_fields
        and "meta name=" not in str(source_text or "").lower()
        and "<!doctype" not in str(source_text or "").lower()
    ):
        return str(source_text or "").strip()

    cleaned_text = _clean_strategy_source_text(source_text)
    facts = extract_parties_and_facts(cleaned_text)
    case_number = (
        _extract_case_number(source_text, meta_fields)
        or str(facts.get("case_number") or "").strip()
    )
    proceeding_number = _extract_proceeding_number(source_text, meta_fields)
    court_name = str(
        meta_fields.get("COURTNAME") or facts.get("court_name") or ""
    ).strip()
    previous_court_name = str(meta_fields.get("PREVCOURTNAME") or "").strip()
    document_date = str(meta_fields.get("DOCDATE") or "").strip()
    cause_date = str(meta_fields.get("CAUSEDATE") or "").strip()
    appellant = _extract_named_field(_APPELLANT_RE, cleaned_text)
    other_party = _extract_named_field(_OTHER_PARTY_RE, cleaned_text)
    representative = _extract_named_field(_REPRESENTATIVE_RE, cleaned_text)
    fact_summary = str(facts.get("fact_summary") or "").strip()
    request_summary = str(facts.get("request_summary") or "").strip()
    legal_basis_summary = str(facts.get("legal_basis_summary") or "").strip()

    lines = [
        f"Тип документа: {_detect_doc_kind(cleaned_text)}",
        f"Суд: {court_name or 'уточнюється за матеріалами справи'}",
    ]
    if previous_court_name:
        lines.append(f"Суд першої інстанції: {previous_court_name}")
    if case_number:
        lines.append(f"Номер справи: {case_number}")
    if proceeding_number:
        lines.append(f"Номер провадження: {proceeding_number}")
    if document_date:
        lines.append(f"Дата документа: {document_date}")
    if cause_date:
        lines.append(f"Дата оскаржуваного акта/події: {cause_date}")
    if appellant:
        lines.append(f"Позивач: {appellant}")
    if other_party:
        lines.append(f"Відповідач: {other_party}")
    if representative:
        lines.append(f"Представник: {representative}")
    if fact_summary:
        lines.append(f"Фактичні обставини: {fact_summary[:900]}")
    key_lines = _extract_key_lines(cleaned_text, limit=4)
    if key_lines:
        lines.append(f"Ключові фрагменти рішення: {' '.join(key_lines)[:900]}")
    if request_summary:
        lines.append(f"Прохальна частина/ціль генерації: {request_summary[:500]}")
    if legal_basis_summary:
        lines.append(f"Ключові правові орієнтири: {legal_basis_summary[:400]}")
    return "\n".join(line for line in lines if line.strip())


def _extract_strategy_source_text(
    file_name: str, content_type: str | None, content: bytes
) -> str:
    try:
        source_text = extract_text_from_file(
            file_name=file_name, content_type=content_type, data=content
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    source_text = _build_strategy_source_brief((source_text or "").strip())
    if len(source_text) >= 20:
        return source_text

    lower_name = (file_name or "").lower()
    lower_content_type = (content_type or "").lower()
    if lower_name.endswith(".pdf") or "pdf" in lower_content_type:
        raise HTTPException(
            status_code=422,
            detail=(
                "Не вдалося витягнути достатньо тексту з PDF. "
                "Система використала вбудовані екстрактори та OCR fallback, але тексту недостатньо. "
                "Ймовірно, PDF сканований/зображенням або має низьку якість. "
                "Завантажте пошуковий PDF/TXT/DOCX або виконайте OCR з кращою якістю джерела."
            ),
        )
    raise HTTPException(
        status_code=422,
        detail="Не вдалося витягнути достатньо тексту із завантаженого файлу.",
    )


def _safe_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _serialize_intake(
    row, usage: dict[str, Any] | None = None
) -> DocumentIntakeResponse:
    issues = [
        DocumentIntakeIssueItem(
            issue_type=str(item.get("issue_type") or ""),
            severity=str(item.get("severity") or ""),
            description=str(item.get("description") or ""),
            impact=str(item.get("impact") or ""),
            snippet=item.get("snippet"),
            start_index=item.get("start_index"),
            end_index=item.get("end_index"),
        )
        for item in (row.detected_issues or [])
    ]
    return DocumentIntakeResponse(
        id=row.id,
        user_id=row.user_id,
        source_file_name=row.source_file_name,
        classified_type=row.classified_type,
        document_language=row.document_language,
        jurisdiction=row.jurisdiction,
        primary_party_role=row.primary_party_role,
        identified_parties=row.identified_parties or [],
        subject_matter=row.subject_matter,
        financial_exposure_amount=_safe_float(row.financial_exposure_amount),
        financial_exposure_currency=row.financial_exposure_currency,
        financial_exposure_type=row.financial_exposure_type,
        document_date=(row.document_date if isinstance(row.document_date, str) else row.document_date.isoformat()) if row.document_date else None,
        deadline_from_document=(row.deadline_from_document if isinstance(row.deadline_from_document, str) else row.deadline_from_document.isoformat()) if row.deadline_from_document else None,
        urgency_level=row.urgency_level,
        risk_level_legal=row.risk_level_legal,
        risk_level_procedural=row.risk_level_procedural,
        risk_level_financial=row.risk_level_financial,
        detected_issues=issues,
        classifier_confidence=float(row.classifier_confidence or 0.0),
        classifier_model=row.classifier_model,
        raw_text_preview=row.raw_text_preview,
        created_at=row.created_at.isoformat(),
        usage=usage or {},
    )


def _serialize_group(row) -> PrecedentGroupItem:
    return PrecedentGroupItem(
        id=row.id,
        pattern_type=row.pattern_type,
        pattern_description=row.pattern_description,
        precedent_ids=list(row.precedent_ids or []),
        precedent_count=int(row.precedent_count or 0),
        pattern_strength=float(row.pattern_strength or 0.0),
        counter_arguments=[str(item) for item in (row.counter_arguments or [])],
        mitigation_strategy=row.mitigation_strategy,
        strategic_advantage=row.strategic_advantage,
        vulnerability_to_appeal=row.vulnerability_to_appeal,
        created_at=row.created_at.isoformat(),
    )


def _serialize_strategy(row) -> StrategyBlueprintResponse:
    return StrategyBlueprintResponse(
        id=row.id,
        intake_id=row.intake_id,
        precedent_group_id=row.precedent_group_id,
        immediate_actions=list(row.immediate_actions or []),
        procedural_roadmap=list(row.procedural_roadmap or []),
        evidence_strategy=list(row.evidence_strategy or []),
        negotiation_playbook=list(row.negotiation_playbook or []),
        risk_heat_map=list(row.risk_heat_map or []),
        critical_deadlines=list(row.critical_deadlines or []),
        swot_analysis=row.swot_analysis,
        win_probability=row.win_probability,
        financial_strategy=row.financial_strategy,
        timeline_projection=row.timeline_projection,
        penalty_forecast=row.penalty_forecast,
        confidence_score=float(row.confidence_score or 0.0),
        confidence_rationale=row.confidence_rationale,
        recommended_next_steps=row.recommended_next_steps,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


@router.post("/analyze/intake", response_model=DocumentIntakeResponse)
async def analyze_intake(
    file: UploadFile = File(...),
    mode: str = "standard",
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentIntakeResponse:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Завантажений файл порожній.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail="Завантажений файл занадто великий."
        )

    source_text = _extract_strategy_source_text(
        file_name=file.filename or "upload.bin",
        content_type=file.content_type,
        content=content,
    )

    import hashlib
    file_hash = hashlib.md5(content).hexdigest()
    cached = get_intake_cache(db, user.user_id, file_hash)
    if cached:
        payload = cached.intake_result
    else:
        payload = await classify_document_intake(source_text, mode=mode)
        # Cache the result (assume tokens and time are tracked)
        create_intake_cache(
            db,
            user_id=user.user_id,
            file_hash=file_hash,
            intake_result=payload,
            ai_model=None,  # TODO: get from classify
            tokens_used=None,
            processing_time_ms=0,
        )

    subscription = get_or_create_subscription(db, user)
    quota_ok, quota_message = ensure_analysis_quota(subscription)
    if not quota_ok:
        raise HTTPException(status_code=402, detail=quota_message)

    cache_key = hashlib.md5(
        f"strategy-intake::{mode}::{source_text}".encode("utf-8")
    ).hexdigest()
    cached = get_analysis_cache(db, user.user_id, cache_key)
    if cached and isinstance(cached.analysis_payload, dict):
        cached_payload = cached.analysis_payload.get("intake_payload")
        payload = cached_payload if isinstance(cached_payload, dict) else None
    else:
        payload = None

    if payload is None:
        payload = await classify_document_intake(source_text, mode=mode)
        safe_payload = json.loads(json.dumps(payload, ensure_ascii=False, default=str))
        create_analysis_cache(
            db,
            user_id=user.user_id,
            file_hash=cache_key,
            analysis_payload={"flow": "strategy_intake", "intake_payload": safe_payload},
            ai_model=str(payload.get("classifier_model") or ""),
            tokens_used=None,
            processing_time_ms=0,
        )

    row = create_document_analysis_intake(
        db,
        user_id=user.user_id,
        source_file_name=file.filename,
        source_text=source_text,
        intake_payload=payload,
    )
    subscription = mark_analysis_processed(db, subscription)

    log_action(
        db,
        user_id=user.user_id,
        action="analysis_intake_create",
        entity_type="document_analysis_intake",
        entity_id=row.id,
        metadata={
            "classified_type": row.classified_type,
            "subject_matter": row.subject_matter,
            "classifier_model": row.classifier_model,
        },
    )
    publish_user_event(
        user.user_id,
        "analysis.intake_completed",
        {
            "intake_id": row.id,
            "classified_type": row.classified_type,
            "subject_matter": row.subject_matter,
        },
    )
    return _serialize_intake(row, usage=to_payload(subscription))


@router.post("/analyze/intake-stream")
async def analyze_intake_stream(
    file: UploadFile = File(...),
    mode: str = "standard",
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Завантажений файл порожній.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail="Завантажений файл занадто великий."
        )

    async def event_generator():
        try:
            # Step 1: Text extraction
            yield f"data: {json.dumps({'step': 'extract', 'status': 'done', 'message': 'Вилучення тексту завершено'})}\n\n"
            await asyncio.sleep(0.5)

            source_text = _extract_strategy_source_text(
                file_name=file.filename or "upload.bin",
                content_type=file.content_type,
                content=content,
            )

            subscription = get_or_create_subscription(db, user)
            quota_ok, quota_message = ensure_analysis_quota(subscription)
            if not quota_ok:
                yield f"data: {json.dumps({'step': 'error', 'status': 'error', 'message': quota_message})}\n\n"
                return

            # Step 2: Intake analysis
            yield f"data: {json.dumps({'step': 'intake', 'status': 'active', 'message': 'Аналіз intake'})}\n\n"
            payload = await classify_document_intake(source_text, mode=mode)

            row = create_document_analysis_intake(
                db,
                user_id=user.user_id,
                source_file_name=file.filename,
                source_text=source_text,
                intake_payload=payload,
            )

            # Serialize before yield to avoid SQLAlchemy expiry after commit
            serialized = _serialize_intake(row, usage=to_payload(subscription))
            result_dict = serialized.model_dump(mode="json")

            yield f"data: {json.dumps({'step': 'intake', 'status': 'done', 'message': 'Аналіз intake завершено', 'intake_id': row.id})}\n\n"

            # Step 3: Emit final result so the frontend stream reader can capture it
            yield f"data: {json.dumps({'step': 'generation', 'status': 'done', 'result': result_dict})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'step': 'error', 'status': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/analyze/{intake_id}/precedent-map", response_model=PrecedentMapResponse)
def analyze_precedent_map(
    intake_id: str,
    limit: int = 15,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PrecedentMapResponse:
    intake = get_document_analysis_intake(db, user_id=user.user_id, intake_id=intake_id)
    if intake is None:
        raise HTTPException(status_code=404, detail="Intake not found.")

    groups, refs, query_used = build_precedent_groups_for_intake(
        db,
        user_id=user.user_id,
        intake=intake,
        limit=limit,
    )
    return PrecedentMapResponse(
        intake_id=intake.id,
        query_used=query_used or "supreme court case law",
        groups=[_serialize_group(item) for item in groups],
        refs=[PrecedentMapRefItem(**item) for item in refs],
    )


@router.post("/strategy/blueprint", response_model=StrategyBlueprintResponse)
async def strategy_blueprint(
    payload: StrategyBlueprintRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StrategyBlueprintResponse:
    intake = get_document_analysis_intake(
        db, user_id=user.user_id, intake_id=payload.intake_id
    )
    if intake is None:
        raise HTTPException(status_code=404, detail="Intake not found.")

    if payload.refresh_precedent_map:
        groups, _, _ = build_precedent_groups_for_intake(
            db,
            user_id=user.user_id,
            intake=intake,
            limit=payload.precedent_limit,
        )
    else:
        groups = list_precedent_groups(db, user_id=user.user_id, intake_id=intake.id)
    if not groups:
        groups, _, _ = build_precedent_groups_for_intake(
            db,
            user_id=user.user_id,
            intake=intake,
            limit=payload.precedent_limit,
        )

    strategy = await build_strategy_blueprint(
        db,
        user_id=user.user_id,
        intake=intake,
        precedent_groups=groups,
        regenerate=payload.regenerate,
    )
    log_action(
        db,
        user_id=user.user_id,
        action="strategy_blueprint_create",
        entity_type="legal_strategy_blueprint",
        entity_id=strategy.id,
        metadata={
            "intake_id": intake.id,
            "confidence_score": float(strategy.confidence_score or 0.0),
        },
    )
    publish_user_event(
        user.user_id,
        "strategy.blueprint_created",
        {
            "strategy_id": strategy.id,
            "intake_id": intake.id,
            "confidence_score": float(strategy.confidence_score or 0.0),
        },
    )
    return _serialize_strategy(strategy)


async def _generate_single_with_strategy(
    db: Session,
    user: CurrentUser,
    strategy: LegalStrategyBlueprint,
    intake: DocumentAnalysisIntake,
    doc_type: str,
    form_data_input: dict[str, Any] | None = None,
    extra_prompt_context: str | None = None,
) -> GenerateWithStrategyResponse:
    document = get_document_type(doc_type)
    if document is None:
        raise HTTPException(
            status_code=404, detail=f"Document type {doc_type} not found."
        )

    subscription = get_or_create_subscription(db, user)
    quota_ok, quota_message = ensure_document_quota(subscription)
    if not quota_ok:
        raise HTTPException(status_code=402, detail=quota_message)

    form_data = dict(form_data_input or {})
    if not form_data:
        form_data = build_form_data_for_doc_type(
            doc_type, intake.source_text or intake.raw_text_preview or ""
        )

    pre_generation_gate_checks_raw = build_pre_generation_gate_checks(
        document.doc_type, form_data
    )
    pre_generation_gate_checks = [
        ProcessualValidationCheck(**item) for item in pre_generation_gate_checks_raw
    ]

    intake_source_text = intake.source_text or intake.raw_text_preview or ""
    intake_payload, intake_ai = await run_intake_agent(
        doc_type=document.doc_type,
        title=document.title,
        source_text=intake_source_text,
        form_data=form_data,
    )

    case_law_refs = enrich_document_with_case_law(
        db, document_type=document.doc_type, form_data=form_data, limit=10
    )
    rerank_ids: list[str] = []
    if case_law_refs and not is_rate_limited_error(intake_ai.error):
        rerank_ids, _rerank_ai = await run_case_law_rerank_agent(
            intake=intake_payload,
            candidates=[item.__dict__ for item in case_law_refs],
            limit=5,
        )
    if rerank_ids:
        by_id = {item.id: item for item in case_law_refs}
        reranked = []
        seen: set[str] = set()
        for case_id in rerank_ids:
            row = by_id.get(case_id)
            if row is None or row.id in seen:
                continue
            seen.add(row.id)
            reranked.append(row)
        for row in case_law_refs:
            if row.id in seen:
                continue
            seen.add(row.id)
            reranked.append(row)
        case_law_refs = reranked[:5]
    else:
        case_law_refs = case_law_refs[:5]

    prompt_user = build_user_prompt(
        document.title, form_data, doc_type=document.doc_type
    )
    intake_context = ""
    if intake_payload:
        intake_context = (
            "Document intake (machine summary, do not cite directly):\n"
            + json.dumps(intake_payload, ensure_ascii=False)
        )

    prompt_blocks = [
        sanitize_prompt_context(build_case_law_prompt_context(case_law_refs)),
        sanitize_prompt_context(
            build_motivation_reference_block(document.doc_type, case_law_refs)
        ),
        sanitize_prompt_context(
            (
                "Strategy blueprint context:\n"
                f"- Immediate actions: {json.dumps(strategy.immediate_actions or [], ensure_ascii=False)}\n"
                f"- Procedural roadmap: {json.dumps(strategy.procedural_roadmap or [], ensure_ascii=False)}\n"
                f"- Evidence strategy: {json.dumps(strategy.evidence_strategy or [], ensure_ascii=False)}\n"
                f"- Counter-argument preemption: {json.dumps((strategy.negotiation_playbook or [])[:3], ensure_ascii=False)}"
            )
        ),
        sanitize_prompt_context(str(extra_prompt_context or "").strip()),
        sanitize_prompt_context(intake_context),
    ]
    prompt_blocks = [item for item in prompt_blocks if item]
    if prompt_blocks:
        prompt_user = f"{prompt_user}\n\n" + "\n\n".join(prompt_blocks)

    preview_text = build_preview_text(
        document.title, form_data, doc_type=document.doc_type
    )
    ai_result = await generate_legal_document_for_role(
        "draft",
        prompt_user,
    )
    draft_text = ai_result.text or preview_text
    generated_text = ensure_processual_quality(
        document.doc_type, draft_text, preview_text
    )
    generated_text = normalize_prayer_section(document.doc_type, generated_text)
    quality_guard_applied = (
        bool(draft_text.strip())
        and generated_text.strip() == preview_text.strip()
        and draft_text.strip() != preview_text.strip()
    )
    generated_text = inject_motivation_references(
        document_type=document.doc_type,
        generated_text=generated_text,
        case_law_refs=case_law_refs,
    )
    validation_checks_raw = await build_generation_validation_checks(
        document.doc_type,
        generated_text,
        form_data=form_data,
        preview_text=preview_text,
    )
    validation_checks = [
        ProcessualValidationCheck(**item) for item in validation_checks_raw
    ]

    saved_doc = create_generated_document(
        db,
        user_id=user.user_id,
        document_type=document.doc_type,
        document_category=document.category,
        form_data=form_data,
        generated_text=generated_text,
        preview_text=preview_text,
        calculations={},
        ai_model=ai_result.model,
        used_ai=ai_result.used_ai,
        ai_error=ai_result.error,
    )
    create_document_version(db, document=saved_doc, action="generate_with_strategy")
    attach_case_law_refs_to_document(
        db, document_id=saved_doc.id, case_law_refs=case_law_refs
    )
    bind_strategy_to_document(db, strategy=strategy, document_id=saved_doc.id)

    strategy_audit = create_document_generation_audit(
        db,
        document_id=saved_doc.id,
        strategy_blueprint_id=strategy.id,
        precedent_citations=[
            item.case_number or item.decision_id for item in case_law_refs
        ],
        counter_argument_addresses=[
            str(item.get("counterparty_offer") or "")
            for item in (strategy.negotiation_playbook or [])
            if str(item.get("counterparty_offer") or "").strip()
        ],
        evidence_positioning_notes="Strong facts first, then damages/economic section, then counter-argument preemption.",
        procedure_optimization_notes="Document generated with strategy-grounded procedural roadmap and gate checks.",
        appeal_proofing_notes="Core assertions are backed by citations and preemptive rebuttals for likely appeal points.",
    )
    mark_document_generated(db, subscription)

    log_action(
        db,
        user_id=user.user_id,
        action="strategy_document_generate",
        entity_type="generated_document",
        entity_id=saved_doc.id,
        metadata={
            "strategy_blueprint_id": strategy.id,
            "doc_type": saved_doc.document_type,
            "used_ai": bool(saved_doc.used_ai),
        },
    )
    publish_user_event(
        user.user_id,
        "generation.document_completed",
        {
            "document_id": saved_doc.id,
            "strategy_blueprint_id": strategy.id,
            "doc_type": saved_doc.document_type,
        },
    )

    return GenerateWithStrategyResponse(
        document_id=saved_doc.id,
        strategy_blueprint_id=strategy.id,
        doc_type=saved_doc.document_type,
        title=document.title,
        preview_text=saved_doc.preview_text,
        generated_text=saved_doc.generated_text,
        used_ai=bool(saved_doc.used_ai),
        ai_model=saved_doc.ai_model or "",
        ai_error=saved_doc.ai_error or "",
        quality_guard_applied=quality_guard_applied,
        pre_generation_gate_checks=pre_generation_gate_checks,
        processual_validation_checks=validation_checks,
        case_law_refs=[
            {
                "id": item.id,
                "source": item.source,
                "decision_id": item.decision_id,
                "case_number": item.case_number,
                "court_name": item.court_name,
                "court_type": item.court_type,
                "decision_date": item.decision_date,
                "summary": item.summary,
                "relevance_score": item.relevance_score,
            }
            for item in case_law_refs
        ],
        strategy_audit_id=strategy_audit.id,
        created_at=saved_doc.created_at.isoformat(),
        usage=to_payload(subscription),
    )


@router.post(
    "/generate-with-strategy",
    response_model=GenerateWithStrategyResponse | GenerateBundleWithStrategyResponse,
)
async def generate_with_strategy(
    payload: GenerateWithStrategyRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GenerateWithStrategyResponse | GenerateBundleWithStrategyResponse:
    strategy = get_strategy_blueprint(
        db, user_id=user.user_id, strategy_id=payload.strategy_blueprint_id
    )
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy blueprint not found.")

    intake = get_document_analysis_intake(
        db, user_id=user.user_id, intake_id=strategy.intake_id
    )
    if intake is None:
        raise HTTPException(status_code=404, detail="Linked intake not found.")

    if payload.bundle_doc_types:
        items = []
        for dt in payload.bundle_doc_types:
            # We don't fail the whole bundle if one document fails, unless it's a quota issue
            try:
                item = await _generate_single_with_strategy(
                    db,
                    user,
                    strategy,
                    intake,
                    dt,
                    payload.form_data,
                    payload.extra_prompt_context,
                )
                items.append(item)
            except HTTPException as e:
                # If it's quota, we re-raise
                if e.status_code == 402:
                    raise e
                # Else continue? For now we fail fast.
                raise e

        return GenerateBundleWithStrategyResponse(
            strategy_blueprint_id=strategy.id,
            items=items,
            created_at=datetime.utcnow().isoformat(),
            usage=items[-1].usage if items else {},
        )

    # Single document
    if not payload.doc_type:
        raise HTTPException(
            status_code=400, detail="Missing doc_type for single document generation."
        )

    return await _generate_single_with_strategy(
        db,
        user,
        strategy,
        intake,
        payload.doc_type,
        payload.form_data,
        payload.extra_prompt_context,
    )


@router.get(
    "/documents/{document_id}/strategy-audit", response_model=StrategyAuditResponse
)
def document_strategy_audit(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StrategyAuditResponse:
    row = get_document_generation_audit(
        db, user_id=user.user_id, document_id=document_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy audit not found.")
    return StrategyAuditResponse(
        id=row.id,
        document_id=row.document_id,
        strategy_blueprint_id=row.strategy_blueprint_id,
        precedent_citations=[str(item) for item in (row.precedent_citations or [])],
        counter_argument_addresses=[
            str(item) for item in (row.counter_argument_addresses or [])
        ],
        evidence_positioning_notes=row.evidence_positioning_notes,
        procedure_optimization_notes=row.procedure_optimization_notes,
        appeal_proofing_notes=row.appeal_proofing_notes,
        generated_at=row.generated_at.isoformat(),
    )


@router.post(
    "/strategy/simulate-judge",
    response_model=JudgeSimulationResponse,
    tags=["Strategy"],
)
async def run_judge_simulation(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    strategy_id = payload.get("strategy_id")
    document_id = payload.get("document_id")

    if not strategy_id:
        raise HTTPException(status_code=400, detail="strategy_id is required")

    strategy = get_strategy_blueprint(db, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    document_text = ""
    if document_id:
        doc = (
            db.query(GeneratedDocument)
            .filter(
                GeneratedDocument.id == document_id,
                GeneratedDocument.user_id == user.user_id,
            )
            .first()
        )
        if doc:
            document_text = doc.generated_text

    if not document_text:
        # Fallback to strategy summary if no document or not found
        document_text = f"Процесуальна дорожня карта: {json.dumps(strategy.procedural_roadmap, ensure_ascii=False)}"

    simulation = await simulate_judge_perspective(strategy_id, document_text)
    publish_user_event(
        user.user_id,
        "strategy.judge_simulation_completed",
        {
            "strategy_id": strategy_id,
            "document_id": document_id,
            "simulation_id": simulation.id,
        },
    )
    return simulation


@router.get("/documents/{document_id}/export/docx", tags=["Documents"])
def export_document_docx(
    document_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    doc = (
        db.query(GeneratedDocument)
        .filter(
            GeneratedDocument.id == document_id,
            GeneratedDocument.user_id == user.user_id,
        )
        .first()
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    docx_bytes = render_docx_bytes(title=doc.title, text=doc.generated_text)

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename=document_{document_id}.docx"
        },
    )
