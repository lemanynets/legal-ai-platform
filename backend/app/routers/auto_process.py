from __future__ import annotations

import json
import math
import re

import asyncio
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.catalog import get_document_type
from app.config import settings
from app.database import get_db
from app.models import AuditLog
from app.models.case import Case
from app.schemas import (
    AutoProcessResponse,
    DecisionAnalysisHistoryResponse,
    DecisionAnalysisPackageResponse,
    DecisionAnalysisResponse,
    FullLawyerPreflightHistoryResponse,
    FullLawyerPreflightResponse,
    FullLawyerResponse,
    FullLawyerSummary,
)
from app.services.ai_generator import generate_legal_document
from app.services.audit import log_action
from app.services.auto_processor import (
    PROCESSUAL_DOCUMENT_TYPES,
    auto_repair_form_data_for_generation,
    build_advocate_signoff_packet,
    build_appeal_reserve_card,
    build_analysis_highlights,
    build_citation_quality_gate,
    build_claim_formula_card,
    build_cpc_175_requisites_map,
    build_cpc_177_attachments_map,
    build_contradiction_hotspots,
    build_court_fee_breakdown,
    build_cpc_compliance_check,
    build_case_law_application_matrix,
    build_citation_pack,
    build_counterparty_pressure_map,
    build_client_instruction_packet,
    build_consistency_report,
    build_deadline_alert_board,
    build_deadline_control,
    build_e_court_submission_preview,
    build_evidence_matrix,
    build_evidence_admissibility_map,
    build_enforcement_plan,
    build_filing_attachments_register,
    build_fee_scenarios,
    build_filing_risk_simulation,
    build_form_data_for_doc_type,
    build_clarifying_questions,
    build_document_processual_checks,
    build_document_fact_enrichment_plan,
    build_document_export_readiness,
    build_document_version_control_card,
    build_digital_signature_readiness,
    build_case_law_update_watchlist,
    build_decision_cassation_vulnerabilities,
    build_decision_defense_plan,
    build_decision_dispute_summary,
    build_decision_document_preparation,
    build_decision_evidence_gaps,
    build_decision_final_conclusion,
    build_decision_key_issues,
    build_decision_key_questions,
    build_decision_quality_gate,
    build_decision_practice_coverage,
    build_decision_procedural_context,
    build_decision_quality_blocks,
    build_decision_side_assessment,
    build_decision_stage_packets,
    build_decision_stage_recommendations,
    build_decision_traceability,
    build_court_behavior_forecast_card,
    build_courtroom_timeline_scenarios,
    build_e_court_packet_readiness,
    build_evidence_pack_compression_plan,
    build_evidence_authenticity_checklist,
    build_evidence_collection_plan,
    build_evidence_disclosure_plan,
    build_factual_circumstances_blocks,
    build_fact_chronology_matrix,
    build_fact_norm_evidence_chain,
    build_filing_packet_order,
    build_filing_channel_strategy_card,
    build_filing_cover_letter,
    build_filing_decision_card,
    build_financial_snapshot,
    build_full_lawyer_brief,
    build_generated_docs_quality,
    build_judge_questions_simulation,
    build_jurisdiction_challenge_guard,
    build_law_context_refs_for_doc_types,
    build_legal_argument_map,
    build_legal_qualification_blocks,
    build_next_actions,
    build_party_profile,
    build_post_filing_plan,
    build_post_filing_monitoring_board,
    build_procedural_defect_scan,
    build_procedural_document_blueprint,
    build_procedural_conclusions,
    build_procedural_timeline,
    build_priority_queue,
    build_pre_filing_red_flags,
    build_procedural_violation_hypotheses,
    build_prayer_rewrite_suggestions,
    build_prayer_part_variants,
    build_prayer_part_audit,
    build_readiness_breakdown,
    build_remedy_coverage,
    build_review_checklist,
    build_rule_validation_checks,
    build_motion_recommendations,
    build_opponent_objections,
    build_counterargument_response_matrix,
    build_opponent_weakness_map,
    build_opponent_response_playbook,
    build_package_completeness,
    build_document_narrative_completeness,
    build_processual_language_audit,
    build_procedural_costs_allocator_card,
    build_settlement_strategy,
    build_settlement_offer_card,
    build_settlement_negotiation_script,
    build_service_plan,
    build_text_section_audit,
    build_evidence_gap_actions,
    build_burden_of_proof_map,
    build_drafting_instructions,
    build_execution_step_tracker,
    build_final_submission_gate,
    build_hearing_evidence_order_card,
    build_limitation_period_card,
    build_jurisdiction_recommendation,
    build_workflow_stages,
    build_hearing_preparation_plan,
    build_hearing_script_pack,
    build_hearing_positioning_notes,
    build_filing_submission_checklist_card,
    build_legal_research_backlog,
    build_legal_budget_timeline_card,
    build_judge_question_drill_card,
    build_hearing_readiness_scorecard,
    build_procedural_risk_heatmap,
    build_procedural_consistency_scorecard,
    build_process_stage_action_map,
    build_remedy_priority_matrix,
    estimate_confidence_score,
    estimate_decision_overall_confidence,
    parse_clarification_answers,
    parse_review_confirmations,
    resolve_review_checklist,
    resolve_clarifying_questions,
    suggest_document_types,
)
from app.services.case_law_cache import search_case_law
from app.services.case_law_enricher import (
    attach_case_law_refs_to_document,
    build_case_law_prompt_context,
    build_motivation_reference_block,
    enrich_document_with_case_law,
    inject_motivation_references,
)
from app.services.document_versions import create_document_version
from app.services.document_export import render_docx_bytes, render_pdf_bytes, sanitize_filename
from app.services.file_text_extractor import extract_text_from_file
from app.services.generated_documents import create_generated_document
from app.services.ai_generator import SYSTEM_PROMPT
from app.services.prompt_builder import (
    build_generation_validation_checks,
    build_pre_generation_gate_checks,
    build_preview_text,
    build_user_prompt,
    sanitize_prompt_context,
    normalize_prayer_section,
    ensure_processual_quality,
)
from app.services.subscriptions import (
    ensure_analysis_quota,
    ensure_document_quota,
    get_or_create_subscription,
    mark_analysis_processed,
    mark_document_generated,
    to_payload,
)

router = APIRouter(prefix="/api/auto", tags=["auto-process"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
PROCESSUAL_DOC_TYPES_SET = set(PROCESSUAL_DOCUMENT_TYPES)


def _merge_recent_practice(*lists: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for items in lists:
        for item in items or []:
            if not isinstance(item, dict):
                continue
            key = (
                str(item.get("decision_id") or "").strip(),
                str(item.get("case_number") or "").strip(),
                str(item.get("decision_date") or "").strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _build_case_bound_context_refs(rows) -> list[dict]:
    refs: list[dict] = []
    for row in rows:
        case_ref = row.case_number or row.decision_id
        refs.append(
            {
                "source": row.source,
                "ref_type": "case_law",
                "reference": f"Case {case_ref}",
                "note": row.summary,
                "relevance_score": 1.0,
            }
        )
    return refs


def _load_case_bound_practice_context(
    *,
    db: Session,
    user: CurrentUser,
    case_id: str | None,
    limit: int = 5,
) -> dict[str, object]:
    result: dict[str, object] = {
        "case_title": "",
        "case_number": "",
        "case_description": "",
        "recent_practice": [],
        "context_refs": [],
        "prompt_context": "",
    }
    if not case_id:
        return result

    row = db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user.user_id).limit(1)
    ).scalar_one_or_none()
    if row is None:
        return result

    case_title = str(row.title or "").strip()
    case_number = str(row.case_number or "").strip()
    case_description = str(row.description or "").strip()
    result["case_title"] = case_title
    result["case_number"] = case_number
    result["case_description"] = case_description

    if not case_number:
        return result

    search_result = search_case_law(
        db,
        query=case_number,
        page=1,
        page_size=max(1, min(int(limit or 1), 10)),
        sort_by="decision_date",
        sort_dir="desc",
    )
    rows = list(search_result.items or [])
    recent_practice = _serialize_recent_practice_rows(rows)
    context_refs = _build_case_bound_context_refs(rows)

    lines = [
        "Контекст із прив'язаної справи:",
        f"Назва справи: {case_title or 'без назви'}",
        f"Номер справи: {case_number}",
    ]
    if case_description:
        lines.append(f"Опис справи: {case_description[:1200]}")
    if rows:
        lines.append("Локальні судові рішення з бази, пов'язані з цією справою:")
        for index, item in enumerate(rows[:5], start=1):
            case_ref = str(item.case_number or item.decision_id or "н/д").strip()
            court_name = str(item.court_name or "Невказаний суд").strip()
            decision_date = item.decision_date.isoformat() if item.decision_date else "без дати"
            summary = str(item.summary or "").strip()[:500]
            lines.append(f"{index}. {court_name} | {case_ref} | {decision_date}")
            if summary:
                lines.append(f"   Суть: {summary}")

    result["recent_practice"] = recent_practice
    result["context_refs"] = context_refs
    result["prompt_context"] = "\n".join(lines).strip()
    return result


async def _read_upload(file: UploadFile) -> tuple[bytes, str]:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Завантажений файл порожній.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Завантажений файл занадто великий.")
    file_name = file.filename or "upload.bin"
    return content, file_name


def _extract_source_text(file_name: str, content_type: str | None, content: bytes) -> str:
    try:
        source_text = extract_text_from_file(file_name=file_name, content_type=content_type, data=content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    source_text = (source_text or "").strip()
    if len(source_text) < 20:
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
        raise HTTPException(status_code=422, detail="Не вдалося витягнути достатньо тексту із завантаженого файлу.")
    return source_text


def _merge_recommended_doc_types(primary: list[str], secondary: list[str], *, limit: int) -> list[str]:
    merged: list[str] = []
    for doc_type in [*primary, *secondary]:
        if doc_type not in merged:
            merged.append(doc_type)
        if len(merged) >= limit:
            break
    return merged


async def _generate_documents_bundle(
    *,
    db: Session,
    user: CurrentUser,
    subscription,
    source_text: str,
    recommended_doc_types: list[str],
    extra_generation_context: str | None = None,
    case_id: str | None = None,
) -> tuple[list[dict], list[str], int, object, list[dict[str, str]], list[dict[str, object]]]:
    generated_items: list[dict] = []
    warnings: list[str] = []
    linked_case_law_total = 0
    generated_for_checks: list[dict[str, object]] = []
    shared_generation_context = sanitize_prompt_context(
        str(extra_generation_context or "").strip(),
        max_len=7000,
    )

    for doc_type in recommended_doc_types:
        document = get_document_type(doc_type)
        if document is None:
            warnings.append(f"Непідтримуваний рекомендований тип документа: {doc_type}")
            continue

        doc_quota_ok, doc_quota_message = ensure_document_quota(subscription)
        if not doc_quota_ok:
            warnings.append(doc_quota_message)
            break

        form_data = build_form_data_for_doc_type(doc_type, source_text)
        pre_generation_gate_checks = build_pre_generation_gate_checks(document.doc_type, form_data)
        initial_fail_count = sum(1 for item in pre_generation_gate_checks if item.get("status") == "fail")
        if initial_fail_count > 0:
            repaired_form_data, repair_notes = auto_repair_form_data_for_generation(document.doc_type, source_text, form_data)
            repaired_checks = build_pre_generation_gate_checks(document.doc_type, repaired_form_data)
            repaired_fail_count = sum(1 for item in repaired_checks if item.get("status") == "fail")
            form_data = repaired_form_data
            pre_generation_gate_checks = repaired_checks

            if repaired_fail_count < initial_fail_count:
                warnings.append(
                    f"{document.doc_type}: auto-fix pre-generation зменшив fail-checks {initial_fail_count} -> {repaired_fail_count}."
                )
            if repair_notes:
                warnings.append(f"{document.doc_type}: auto-fix дії: {', '.join(repair_notes[:4])}.")
            if repaired_fail_count > 0:
                warnings.append(
                    f"Pre-generation gate після auto-fix все ще містить блокуючі пункти для {document.doc_type}."
                )
        case_law_refs = enrich_document_with_case_law(
            db,
            document_type=document.doc_type,
            form_data=form_data,
            limit=5,
        )

        prompt_user = build_user_prompt(document.title, form_data, doc_type=document.doc_type)
        case_law_context = sanitize_prompt_context(build_case_law_prompt_context(case_law_refs))
        motivation_refs_context = sanitize_prompt_context(
            build_motivation_reference_block(document.doc_type, case_law_refs)
        )
        extra_context: list[str] = []
        if shared_generation_context:
            extra_context.append(
                "Додатковий стратегічний контекст за результатами аналізу судового рішення:\n"
                f"{shared_generation_context}"
            )
        extra_context.extend([item for item in [case_law_context, motivation_refs_context] if item])
        if extra_context:
            prompt_user = f"{prompt_user}\n\n" + "\n\n".join(extra_context)

        preview_text = build_preview_text(document.title, form_data, doc_type=document.doc_type)
        ai_result = await generate_legal_document(SYSTEM_PROMPT, prompt_user)
        draft_text = ai_result.text or preview_text
        generated_text = ensure_processual_quality(document.doc_type, draft_text, preview_text)
        generated_text = normalize_prayer_section(document.doc_type, generated_text)
        quality_guard_applied = bool(draft_text.strip()) and generated_text.strip() == preview_text.strip() and draft_text.strip() != preview_text.strip()
        if quality_guard_applied:
            warnings.append(
                f"AI-чернетка для {document.doc_type} не пройшла processual quality guard; використано fallback-шаблон."
            )
        generated_text = inject_motivation_references(
            document_type=document.doc_type,
            generated_text=generated_text,
            case_law_refs=case_law_refs,
        )
        processual_validation_checks = await build_generation_validation_checks(
            document.doc_type,
            generated_text,
            form_data=form_data,
            preview_text=preview_text,
        )
        if any(item.get("status") != "pass" for item in processual_validation_checks):
            warnings.append(f"Processual validation має незакриті перевірки для {document.doc_type}.")

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
            case_id=case_id,
        )
        create_document_version(db, document=saved_doc, action="generate_auto")

        try:
            linked_case_law_total += attach_case_law_refs_to_document(
                db,
                document_id=saved_doc.id,
                case_law_refs=case_law_refs,
            )
        except Exception:
            db.rollback()

        subscription = mark_document_generated(db, subscription)
        generated_items.append(
            {
                "id": saved_doc.id,
                "doc_type": saved_doc.document_type,
                "title": document.title,
                "created_at": saved_doc.created_at.isoformat(),
                "preview_text": saved_doc.preview_text,
                "used_ai": bool(saved_doc.used_ai),
                "ai_model": saved_doc.ai_model,
                "ai_error": saved_doc.ai_error,
                "quality_guard_applied": quality_guard_applied,
                "pre_generation_gate_checks": pre_generation_gate_checks,
                "processual_validation_checks": processual_validation_checks,
            }
        )
        generated_for_checks.append({"doc_type": saved_doc.document_type, "_generated_text": generated_text})

    processual_checks = build_document_processual_checks(generated_for_checks)
    quality_report = build_generated_docs_quality(generated_for_checks)
    return generated_items, warnings, linked_case_law_total, subscription, processual_checks, quality_report


def _build_case_law_context_refs_for_response(case_law_refs) -> list[dict]:
    refs: list[dict] = []
    for item in case_law_refs:
        case_ref = item.case_number or item.decision_id
        refs.append(
            {
                "source": item.source,
                "ref_type": "case_law",
                "reference": f"Case {case_ref}",
                "note": item.summary,
                "relevance_score": float(item.relevance_score),
            }
        )
    return refs


def _serialize_recent_practice_rows(rows) -> list[dict]:
    payload: list[dict] = []
    for row in rows:
        payload.append(
            {
                "id": row.id,
                "source": row.source,
                "decision_id": row.decision_id,
                "court_name": row.court_name,
                "court_type": row.court_type,
                "decision_date": row.decision_date.isoformat() if row.decision_date else None,
                "case_number": row.case_number,
                "summary": row.summary,
            }
        )
    return payload


async def _compute_decision_analysis_state(
    *,
    db: Session,
    source_text: str,
    include_recent_case_law: bool,
    case_law_days: int,
    case_law_limit: int,
    case_law_court_type: str | None,
    case_law_source: str | None,
    only_supreme_case_law: bool,
    ai_enhance: bool,
    seeded_recent_practice: list[dict] | None = None,
) -> dict[str, object]:
    safe_days = max(1, min(int(case_law_days or 1), 3650))
    safe_limit = max(1, min(int(case_law_limit or 1), 50))
    source_items = [item.strip().lower() for item in (case_law_source or "").split(",") if item.strip()]

    brief = await build_full_lawyer_brief(source_text, max_documents=3, processual_only=True)
    financial_snapshot = build_financial_snapshot(source_text, brief)
    dispute_summary = build_decision_dispute_summary(
        source_text,
        brief=brief,
        financial_snapshot=financial_snapshot,
    )
    procedural_context = build_decision_procedural_context(source_text, brief=brief)
    key_issues = build_decision_key_issues(source_text, max_items=6)
    key_questions = build_decision_key_questions(key_issues=key_issues, max_items=8)
    recent_practice: list[dict] = list(seeded_recent_practice or [])
    warnings: list[str] = []

    if include_recent_case_law:
        search_query = str(brief.get("dispute_type") or "").strip() or None
        if search_query and re.search(r"[А-Яа-яІіЇїЄєҐґ]", search_query):
            # Якщо тип спору сформований українською, не звужуємо пошук англомовним кешем.
            search_query = None
        result = search_case_law(
            db,
            query=search_query,
            court_type=(case_law_court_type or "").strip().lower() or None,
            only_supreme=bool(only_supreme_case_law),
            sources=source_items,
            fresh_days=safe_days,
            page=1,
            page_size=safe_limit,
            sort_by="decision_date",
            sort_dir="desc",
        )
        recent_practice = _merge_recent_practice(recent_practice, _serialize_recent_practice_rows(result.items))
        if result.total == 0 and not recent_practice:
            warnings.append("За поточними фільтрами в кеші не знайдено релевантної актуальної судової практики.")
    else:
        warnings.append("Пошук актуальної судової практики вимкнено для цього запуску.")

    practice_coverage = build_decision_practice_coverage(
        recent_practice=recent_practice,
        stale_threshold_days=safe_days,
    )
    practice_instances = sum(
        1
        for count in (practice_coverage.get("instance_levels") or {}).values()
        if int(count or 0) > 0
    )
    if include_recent_case_law and bool(practice_coverage.get("stale")):
        warnings.append(
            "Вибірка практики виглядає застарілою для обраного горизонту. "
            "Оновіть джерела перед використанням для подання."
        )
    if include_recent_case_law and not only_supreme_case_law and int(practice_coverage.get("total_items") or 0) > 0 and practice_instances < 2:
        warnings.append(
            "Вибірка практики надто вузька за покриттям інстанцій. "
            "Додайте матеріали апеляції та/або першої інстанції."
        )

    cassation_vulnerabilities = build_decision_cassation_vulnerabilities(
        source_text,
        key_issues=key_issues,
        recent_practice_count=len(recent_practice),
        max_items=6,
    )
    final_conclusion = build_decision_final_conclusion(
        cassation_vulnerabilities=cassation_vulnerabilities,
        recent_practice_count=len(recent_practice),
    )
    stage_recommendations = build_decision_stage_recommendations(
        cassation_vulnerabilities=cassation_vulnerabilities,
    )
    stage_packets = build_decision_stage_packets(
        key_issues=key_issues,
        cassation_vulnerabilities=cassation_vulnerabilities,
    )
    side_assessment = build_decision_side_assessment(
        source_text,
        key_issues=key_issues,
    )
    evidence_gaps = build_decision_evidence_gaps(
        source_text,
        side=str(side_assessment.get("side") or "unknown"),
    )
    defense_plan = build_decision_defense_plan(
        side_assessment=side_assessment,
        key_issues=key_issues,
        cassation_vulnerabilities=cassation_vulnerabilities,
    )
    document_preparation = build_decision_document_preparation(
        source_text=source_text,
        side_assessment=side_assessment,
        evidence_gaps=evidence_gaps,
    )
    missing_evidence_count = sum(1 for item in evidence_gaps if str(item.get("status")) == "missing")
    if str(side_assessment.get("side") or "unknown") == "unknown":
        warnings.append(
            "Низька впевненість у визначенні процесуальної сторони. "
            "Підтвердіть сторону вручну перед побудовою стратегії."
        )
    if missing_evidence_count >= 3:
        warnings.append(
            "Виявлено кілька критичних доказових прогалин. "
            "Закрийте їх до формування фінального процесуального пакета."
        )

    ai_used = False
    ai_model = ""
    ai_error = ""
    if ai_enhance:
        system_prompt = (
            "Ти старший судовий юрист України. Поверни лише JSON-об'єкт з ключами: "
            "dispute_summary, procedural_context, key_questions, cassation_vulnerabilities, final_conclusion. "
            "Без markdown і без додаткових пояснень."
        )
        user_prompt = (
            "Відредагуй структурований аналіз судового рішення у стислу професійну юридичну форму українською мовою.\n"
            f"Поточний аналіз (JSON):\n{json.dumps({'dispute_summary': dispute_summary, 'procedural_context': procedural_context, 'key_questions': key_questions, 'cassation_vulnerabilities': cassation_vulnerabilities, 'final_conclusion': final_conclusion}, ensure_ascii=False)}\n\n"
            f"Фрагмент джерела:\n{source_text[:10000]}"
        )
        ai_result = await generate_legal_document(system_prompt, user_prompt)
        ai_used = bool(ai_result.used_ai)
        ai_model = ai_result.model or ""
        ai_error = ai_result.error or ""
        if ai_result.used_ai and ai_result.text.strip():
            try:
                parsed = json.loads(ai_result.text)
                if isinstance(parsed, dict):
                    dispute_summary = str(parsed.get("dispute_summary") or dispute_summary).strip() or dispute_summary
                    procedural_context = str(parsed.get("procedural_context") or procedural_context).strip() or procedural_context
                    parsed_questions = parsed.get("key_questions")
                    if isinstance(parsed_questions, list):
                        key_questions = [str(item).strip() for item in parsed_questions if str(item).strip()][:8] or key_questions
                    parsed_vulnerabilities = parsed.get("cassation_vulnerabilities")
                    if isinstance(parsed_vulnerabilities, list):
                        cassation_vulnerabilities = [
                            str(item).strip() for item in parsed_vulnerabilities if str(item).strip()
                        ][:6] or cassation_vulnerabilities
                    final_conclusion = str(parsed.get("final_conclusion") or final_conclusion).strip() or final_conclusion
            except Exception:
                warnings.append(
                    "Результат AI-доопрацювання не є валідним JSON. "
                    "Залишено детермінований аналіз."
                )

    quality_blocks = build_decision_quality_blocks(
        source_text,
        key_issues=key_issues,
        key_questions=key_questions,
        cassation_vulnerabilities=cassation_vulnerabilities,
        recent_practice=recent_practice,
        stage_recommendations=stage_recommendations,
        stage_packets=stage_packets,
        practice_coverage=practice_coverage,
    )
    traceability = build_decision_traceability(
        key_issues=key_issues,
        recent_practice=recent_practice,
        max_items=20,
    )
    overall_confidence_score = estimate_decision_overall_confidence(
        quality_blocks=quality_blocks,
        traceability=traceability,
    )
    quality_gate = build_decision_quality_gate(
        quality_blocks=quality_blocks,
        overall_confidence_score=overall_confidence_score,
        traceability_count=len(traceability),
        practice_coverage=practice_coverage,
        require_multi_instance=include_recent_case_law and not only_supreme_case_law,
        enforce_practice_freshness=include_recent_case_law,
    )
    if not bool(quality_gate.get("can_proceed_to_filing")):
        warnings.append(
            "Гейт якості заблокував використання результату для подання. "
            "Усуньте блокери перед прийняттям процесуальних рішень."
        )

    return {
        "safe_days": safe_days,
        "safe_limit": safe_limit,
        "source_items": source_items,
        "dispute_summary": dispute_summary,
        "procedural_context": procedural_context,
        "key_issues": key_issues,
        "key_questions": key_questions,
        "cassation_vulnerabilities": cassation_vulnerabilities,
        "final_conclusion": final_conclusion,
        "side_assessment": side_assessment,
        "defense_plan": defense_plan,
        "evidence_gaps": evidence_gaps,
        "document_preparation": document_preparation,
        "stage_recommendations": stage_recommendations,
        "stage_packets": stage_packets,
        "recent_practice": recent_practice,
        "practice_coverage": practice_coverage,
        "quality_blocks": quality_blocks,
        "traceability": traceability,
        "overall_confidence_score": overall_confidence_score,
        "quality_gate": quality_gate,
        "used_ai": ai_used,
        "ai_model": ai_model,
        "ai_error": ai_error,
        "warnings": warnings,
    }


def _build_decision_analysis_report_text(
    *,
    source_file_name: str,
    extracted_chars: int,
    state: dict[str, object],
) -> str:
    key_issues = [item for item in list(state.get("key_issues") or []) if isinstance(item, dict)]
    key_questions = [str(item).strip() for item in list(state.get("key_questions") or []) if str(item).strip()]
    cassation_vulnerabilities = [
        str(item).strip() for item in list(state.get("cassation_vulnerabilities") or []) if str(item).strip()
    ]
    side_assessment = state.get("side_assessment") if isinstance(state.get("side_assessment"), dict) else {}
    defense_plan = [item for item in list(state.get("defense_plan") or []) if isinstance(item, dict)]
    evidence_gaps = [item for item in list(state.get("evidence_gaps") or []) if isinstance(item, dict)]
    document_preparation = [item for item in list(state.get("document_preparation") or []) if isinstance(item, dict)]
    stage_recommendations = [item for item in list(state.get("stage_recommendations") or []) if isinstance(item, dict)]
    stage_packets = [item for item in list(state.get("stage_packets") or []) if isinstance(item, dict)]
    recent_practice = [item for item in list(state.get("recent_practice") or []) if isinstance(item, dict)]
    practice_coverage = state.get("practice_coverage") if isinstance(state.get("practice_coverage"), dict) else {}
    quality_blocks = [item for item in list(state.get("quality_blocks") or []) if isinstance(item, dict)]
    traceability = [item for item in list(state.get("traceability") or []) if isinstance(item, dict)]
    quality_gate = state.get("quality_gate") if isinstance(state.get("quality_gate"), dict) else {}
    warnings = [str(item).strip() for item in list(state.get("warnings") or []) if str(item).strip()]

    def _fmt(value: object, default: str = "н/д") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    def _yes_no(value: object) -> str:
        return "так" if bool(value) else "ні"

    lines: list[str] = [
        "ЗВІТ АНАЛІЗУ СУДОВОГО РІШЕННЯ",
        "",
        f"Файл-джерело: {_fmt(source_file_name)}",
        f"Виділено символів: {extracted_chars}",
        f"Загальний бал впевненості: {_fmt(state.get('overall_confidence_score'))}",
        "",
        "БЛОК 1. ФАКТИ ТА ПРОЦЕСУАЛЬНИЙ КОНТЕКСТ",
        f"- Суть спору: {_fmt(state.get('dispute_summary'))}",
        f"- Процесуальний контекст: {_fmt(state.get('procedural_context'))}",
        f"- Статус гейту якості: {_fmt(quality_gate.get('status'))}",
        f"- Можливість переходу до подання: {_yes_no(quality_gate.get('can_proceed_to_filing'))}",
    ]
    for blocker in [str(item).strip() for item in list(quality_gate.get("blockers") or []) if str(item).strip()][:10]:
        lines.append(f"- Блокер: {blocker}")

    lines.extend(["", "БЛОК 2. КЛЮЧОВІ ПРАВОВІ ПИТАННЯ ТА ПОЗИЦІЯ СУДУ"])
    if key_questions:
        lines.extend([f"- Ключове питання: {item}" for item in key_questions[:12]])
    else:
        lines.append("- Ключові питання не були чітко ідентифіковані.")
    for item in key_issues[:10]:
        lines.append(f"- Тема: {_fmt(item.get('topic'))}")
        lines.append(f"  Позиція суду: {_fmt(item.get('court_position'))}")
        legal_basis = [str(v).strip() for v in list(item.get("legal_basis") or []) if str(v).strip()]
        if legal_basis:
            lines.append(f"  Норми права: {', '.join(legal_basis[:8])}")
        practical_effect = str(item.get("practical_effect") or "").strip()
        if practical_effect:
            lines.append(f"  Практичний наслідок: {practical_effect}")

    lines.extend(
        [
            "",
            "БЛОК 3. СУДОВА ПРАКТИКА ТА КАСАЦІЙНІ РИЗИКИ",
            f"- Кількість рішень у вибірці: {_fmt(practice_coverage.get('total_items'))}",
            f"- Кількість охоплених судів: {_fmt(practice_coverage.get('distinct_courts'))}",
            f"- Рівні інстанцій: {_fmt(practice_coverage.get('instance_levels'))}",
            f"- Найновіше рішення: {_fmt(practice_coverage.get('latest_decision_date'))}",
            f"- Найстаріше рішення: {_fmt(practice_coverage.get('oldest_decision_date'))}",
            f"- Давність практики (днів): {_fmt(practice_coverage.get('freshness_days'))}",
            f"- Ознака застарілості: {_yes_no(practice_coverage.get('stale'))}",
        ]
    )
    if recent_practice:
        lines.append("- Релевантна практика:")
        for item in recent_practice[:10]:
            court_name = _fmt(item.get("court_name") or item.get("court_type"))
            case_ref = _fmt(item.get("case_number") or item.get("decision_id"))
            decision_date = _fmt(item.get("decision_date"))
            lines.append(f"  • {court_name} | {case_ref} | {decision_date}")
    if cassation_vulnerabilities:
        lines.append("- Потенційні касаційні вразливості:")
        lines.extend([f"  • {item}" for item in cassation_vulnerabilities[:12]])

    lines.extend(
        [
            "",
            "БЛОК 4. ОЦІНКА СТОРІН, ДОКАЗИ ТА ЗОНИ РИЗИКУ",
            f"- Рекомендована процесуальна сторона: {_fmt(side_assessment.get('side'))}",
            f"- Опонент: {_fmt(side_assessment.get('opposing_side'))}",
            f"- Рівень впевненості оцінки: {_fmt(side_assessment.get('confidence'))}",
        ]
    )
    for rationale in [str(item).strip() for item in list(side_assessment.get("rationale") or []) if str(item).strip()][:8]:
        lines.append(f"- Обґрунтування: {rationale}")
    if evidence_gaps:
        lines.append("- Доказові прогалини:")
        for item in evidence_gaps[:12]:
            lines.append(
                f"  • {_fmt(item.get('title'))} | статус: {_fmt(item.get('status'))} | {_fmt(item.get('detail'))}"
            )

    lines.extend(["", "БЛОК 5. ПЛАН ДІЙ ТА ПІДГОТОВКА ДОКУМЕНТІВ"])
    for item in defense_plan[:8]:
        lines.append(f"- Стадія: {_fmt(item.get('stage'))} | Ціль: {_fmt(item.get('goal'))}")
        for action in [str(v).strip() for v in list(item.get("actions") or []) if str(v).strip()][:6]:
            lines.append(f"  • Дія: {action}")
    if document_preparation:
        lines.append("- Матриця підготовки документів:")
        for item in document_preparation[:12]:
            lines.append(
                "  • "
                f"{_fmt(item.get('title'))} ({_fmt(item.get('doc_type'))}) | "
                f"пріоритет: {_fmt(item.get('priority'))} | "
                f"готовність: {_fmt(item.get('readiness'))}"
            )
    if stage_recommendations:
        lines.append("- Рекомендації за стадіями:")
        for item in stage_recommendations[:8]:
            actions = [str(v).strip() for v in list(item.get("actions") or []) if str(v).strip()]
            lines.append(f"  • {_fmt(item.get('stage'))}: {', '.join(actions[:4]) or 'н/д'}")
    if stage_packets:
        lines.append("- Рекомендовані пакети по стадіях:")
        for item in stage_packets[:8]:
            packets = [str(v).strip() for v in list(item.get("documents") or []) if str(v).strip()]
            lines.append(f"  • {_fmt(item.get('stage'))}: {', '.join(packets[:6]) or 'н/д'}")

    lines.extend(["", "ПІДСУМКОВИЙ ВИСНОВОК", _fmt(state.get("final_conclusion"))])

    if warnings:
        lines.extend(["", "ПОПЕРЕДЖЕННЯ:"])
        lines.extend([f"- {item}" for item in warnings[:25]])

    if quality_blocks:
        lines.extend(["", "ДОДАТОК А. БЛОКИ ЯКОСТІ"])
        for item in quality_blocks[:8]:
            lines.append(
                f"- {_fmt(item.get('title'))} | статус={_fmt(item.get('status'))} | бал={_fmt(item.get('score'))}"
            )
    if traceability:
        lines.extend(["", "ДОДАТОК Б. ТРАСОВАНІСТЬ ВИСНОВКІВ"])
        for item in traceability[:25]:
            lines.append(
                f"- {_fmt(item.get('claim'))} | {_fmt(item.get('support_type'))} | "
                f"{_fmt(item.get('reference'))} | впевненість={_fmt(item.get('confidence'))}"
            )

    return "\n".join(lines).strip()


def _build_decision_package_generation_context(_source_text: str, state: dict[str, object]) -> str:
    dispute_summary = str(state.get("dispute_summary") or "").strip()
    procedural_context = str(state.get("procedural_context") or "").strip()
    final_conclusion = str(state.get("final_conclusion") or "").strip()
    key_questions = [str(item).strip() for item in list(state.get("key_questions") or []) if str(item).strip()]
    key_issues = [item for item in list(state.get("key_issues") or []) if isinstance(item, dict)]
    evidence_gaps = [item for item in list(state.get("evidence_gaps") or []) if isinstance(item, dict)]
    side_assessment = state.get("side_assessment") if isinstance(state.get("side_assessment"), dict) else {}
    defense_plan = [item for item in list(state.get("defense_plan") or []) if isinstance(item, dict)]
    document_preparation = [item for item in list(state.get("document_preparation") or []) if isinstance(item, dict)]
    stage_recommendations = [item for item in list(state.get("stage_recommendations") or []) if isinstance(item, dict)]

    lines: list[str] = ["КОНТЕКСТ ДЛЯ ГЕНЕРАЦІЇ ПРОЦЕСУАЛЬНИХ ДОКУМЕНТІВ:"]
    if dispute_summary:
        lines.append(f"- Суть спору: {dispute_summary}")
    if procedural_context:
        lines.append(f"- Процесуальний контекст: {procedural_context}")
    if key_questions:
        lines.append("- Ключові юридичні питання:")
        lines.extend([f"  • {item}" for item in key_questions[:10]])
    if key_issues:
        lines.append("- Встановлені правові позиції:")
        for item in key_issues[:8]:
            topic = str(item.get("topic") or "").strip()
            position = str(item.get("court_position") or "").strip()
            practical_effect = str(item.get("practical_effect") or "").strip()
            if not topic:
                continue
            lines.append(f"  • {topic}: {position or 'позиція не конкретизована'}")
            if practical_effect:
                lines.append(f"    Наслідок для тактики: {practical_effect}")
    if side_assessment:
        lines.append(
            f"- Рекомендована сторона: {side_assessment.get('side')} "
            f"(впевненість: {side_assessment.get('confidence')})"
        )
        rationale = [str(item).strip() for item in list(side_assessment.get("rationale") or []) if str(item).strip()]
        if rationale:
            lines.append("- Обґрунтування вибору сторони:")
            lines.extend([f"  • {item}" for item in rationale[:6]])

    missing_gaps = [item for item in evidence_gaps if str(item.get("status") or "").strip().lower() == "missing"]
    if missing_gaps:
        lines.append("- Критичні доказові прогалини, які треба закрити у тексті документів:")
        for item in missing_gaps[:8]:
            title = str(item.get("title") or "").strip() or "Невизначена прогалина"
            detail = str(item.get("detail") or "").strip()
            lines.append(f"  • {title}: {detail or 'деталь не надана'}")

    if defense_plan:
        lines.append("- Узгоджений план процесуальних дій:")
        for item in defense_plan[:6]:
            stage = str(item.get("stage") or "").strip()
            goal = str(item.get("goal") or "").strip()
            if stage or goal:
                lines.append(f"  • {stage or 'Стадія'}: {goal or 'ціль не вказана'}")
            for action in [str(v).strip() for v in list(item.get("actions") or []) if str(v).strip()][:4]:
                lines.append(f"    - {action}")

    if document_preparation:
        lines.append("- Матриця підготовки документів:")
        for item in document_preparation[:10]:
            title = str(item.get("title") or "").strip()
            doc_type = str(item.get("doc_type") or "").strip()
            readiness = str(item.get("readiness") or "").strip()
            priority = str(item.get("priority") or "").strip()
            if title or doc_type:
                lines.append(
                    f"  • {title or doc_type} ({doc_type or 'тип не вказано'}) | "
                    f"готовність: {readiness or 'н/д'} | пріоритет: {priority or 'н/д'}"
                )

    if stage_recommendations:
        lines.append("- Рекомендації за стадіями:")
        for item in stage_recommendations[:6]:
            stage = str(item.get("stage") or "").strip()
            actions = [str(v).strip() for v in list(item.get("actions") or []) if str(v).strip()]
            lines.append(f"  • {stage or 'Стадія'}: {', '.join(actions[:4]) or 'без конкретних дій'}")

    if final_conclusion:
        lines.append(f"- Підсумковий висновок: {final_conclusion}")

    return "\n".join(lines).strip()


def _build_processual_package_gate(
    *,
    generated_items: list[dict],
    unresolved_questions: list[str],
    unresolved_review_items: list[str],
) -> dict[str, object]:
    def _is_blocking_validation_check(check: dict[str, object]) -> bool:
        status = str(check.get("status") or "").strip().lower()
        code = str(check.get("code") or "").strip().lower()
        if status == "pass":
            return False
        # AI second-pass is advisory and must not hard-block package assembly.
        if code.startswith("ai_second_pass_"):
            return False
        return True

    blockers: list[str] = []
    if unresolved_questions:
        blockers.append(f"Не закрито уточнення: {len(unresolved_questions)}.")
    if unresolved_review_items:
        blockers.append(f"Не закрито підтвердження checklist: {len(unresolved_review_items)}.")
    if not generated_items:
        blockers.append("Немає згенерованих документів для складання пакета.")

    for item in generated_items:
        doc_type = str(item.get("doc_type") or "")
        if item.get("quality_guard_applied"):
            blockers.append(f"{doc_type}: спрацював fallback quality-guard.")
        gate_failures = [check for check in (item.get("pre_generation_gate_checks") or []) if check.get("status") == "fail"]
        for check in gate_failures:
            blockers.append(f"{doc_type}: провал pre-generation gate ({check.get('code')}).")
        validation_failures = [
            check for check in (item.get("processual_validation_checks") or []) if _is_blocking_validation_check(check)
        ]
        for check in validation_failures:
            blockers.append(f"{doc_type}: провал processual validation ({check.get('code')}).")

    deduped: list[str] = []
    seen: set[str] = set()
    for item in blockers:
        key = str(item).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(key)

    can_generate = len(deduped) == 0
    return {
        "status": "pass" if can_generate else "blocked",
        "can_generate_package": can_generate,
        "blockers": deduped,
    }


def _create_filing_package(
    *,
    db: Session,
    user: CurrentUser,
    source_file_name: str,
    recommended_doc_types: list[str],
    generated_items: list[dict],
    evidence_required: list[str],
    financial_snapshot: dict,
    draft_mode: bool = False,
    case_id: str | None = None,
) -> dict:
    checklist = [
        "Підписаний процесуальний документ.",
        "Опис (реєстр) доказів.",
        "Копії ключових доказів по кожній фактичній обставині.",
        "Підтвердження сплати судового збору.",
        "Підтвердження надсилання іншій стороні (якщо вимагається).",
        "Довіреність/документи про повноваження представника (за наявності).",
    ]
    generated_list = ", ".join(item.get("doc_type", "") for item in generated_items) or "немає"
    preferred_types = ", ".join(recommended_doc_types) or "немає"
    evidence_lines = "\n".join(f"- {item}" for item in evidence_required[:20]) or "- Додайте перелік доказів вручну."
    draft_notice = (
        "РЕЖИМ ЧЕРНЕТКИ: пакет не готовий до подання, доки не усунуті блокери фінального контролю.\n\n"
        if draft_mode
        else ""
    )
    cover_text = (
        "СУПРОВІДНИЙ ЛИСТ ДО ПАКЕТА ПОДАННЯ\n\n"
        f"{draft_notice}"
        f"Вихідний файл: {source_file_name}\n"
        f"Рекомендовані типи документів: {preferred_types}\n"
        f"Згенерований набір документів: {generated_list}\n"
        f"Орієнтовний судовий збір: {financial_snapshot.get('estimated_court_fee_uah')}\n"
        f"Орієнтовні штрафні нарахування: {financial_snapshot.get('estimated_penalty_uah')}\n"
        f"Орієнтовна загальна сума із збором: {financial_snapshot.get('estimated_total_with_fee_uah')}\n\n"
        "Контрольний список:\n"
        + "\n".join(f"- {item}" for item in checklist)
    )
    evidence_inventory_text = (
        "ОПИС ДОКАЗІВ\n\n"
        f"{draft_notice}"
        "Основні обов'язкові докази:\n"
        f"{evidence_lines}\n\n"
        "Додайте до кожного доказу унікальне позначення (E1, E2, ...), дату та коротку примітку про релевантність."
    )

    suffix = "_draft" if draft_mode else ""
    package_specs = [
        (f"filing_package_cover{suffix}", "Супровідний лист до пакета подання", cover_text),
        (f"filing_package_evidence_inventory{suffix}", "Опис доказів", evidence_inventory_text),
    ]
    items: list[dict] = []
    for doc_type, title, text in package_specs:
        saved_doc = create_generated_document(
            db,
            user_id=user.user_id,
            document_type=doc_type,
            document_category="package",
            form_data={"source_file_name": source_file_name, "recommended_doc_types": recommended_doc_types},
            generated_text=text,
            preview_text=text[:1500],
            calculations=financial_snapshot,
            ai_model=None,
            used_ai=False,
            ai_error=None,
            case_id=case_id,
        )
        create_document_version(db, document=saved_doc, action="generate_package_draft" if draft_mode else "generate_package")
        items.append(
            {
                "id": saved_doc.id,
                "doc_type": doc_type,
                "title": title,
                "created_at": saved_doc.created_at.isoformat(),
                "is_draft": draft_mode,
            }
        )

    return {
        "generated": True,
        "items": items,
        "checklist": checklist,
        "status": "draft_generated" if draft_mode else "generated",
        "reason": (
            "Фінальний шлюз подання заблокований. Згенеровано чернетковий пакет для перевірки адвокатом."
            if draft_mode
            else None
        ),
        "is_draft": draft_mode,
    }


async def _compute_full_lawyer_preflight_state(
    *,
    source_text: str,
    safe_max_documents: int,
    processual_only: bool,
    clarifications_json: str | None,
    review_confirmations_json: str | None,
) -> dict[str, object]:
    brief = await build_full_lawyer_brief(
        source_text,
        max_documents=safe_max_documents,
        processual_only=processual_only,
    )
    validation_checks = build_rule_validation_checks(source_text, brief)
    clarifying_questions = build_clarifying_questions(
        source_text,
        missing_information=brief.get("missing_information") or [],
        max_items=8,
    )
    recommended_doc_types = _merge_recommended_doc_types(
        brief.get("recommended_documents") or [],
        suggest_document_types(
            source_text,
            max_documents=safe_max_documents,
            processual_only=processual_only,
        ),
        limit=safe_max_documents,
    )
    clarification_answers = parse_clarification_answers(clarifications_json)
    _, unresolved_questions = resolve_clarifying_questions(clarifying_questions, clarification_answers)
    review_checklist = build_review_checklist(
        summary=brief,
        validation_checks=validation_checks,
        recommended_doc_types=recommended_doc_types,
    )
    review_confirmations = parse_review_confirmations(review_confirmations_json)
    unresolved_review_items = [] if unresolved_questions else resolve_review_checklist(review_checklist, review_confirmations)
    deadline_control = build_deadline_control(
        source_text=source_text,
        recommended_doc_types=recommended_doc_types,
        unresolved_questions=unresolved_questions,
        unresolved_review_items=unresolved_review_items,
    )
    processual_package_gate: dict[str, object] = {
        "status": "pending",
        "can_generate_package": False,
        "blockers": [
            "Preflight-режим не генерує документи. Спочатку запустіть Full Lawyer, потім формуйте пакет подання."
        ],
    }
    preflight_decision = "hold" if unresolved_questions or unresolved_review_items else "conditional_go"
    final_submission_gate = build_final_submission_gate(
        filing_decision_card={"decision": preflight_decision},
        e_court_packet_readiness={"status": "not_ready"},
        digital_signature_readiness={"status": "not_ready"},
        procedural_consistency_scorecard={"score": 0},
        deadline_control=deadline_control,
        recommended_doc_types=recommended_doc_types,
    )

    if unresolved_questions:
        status = "needs_clarification"
        hint_reason = "Закрийте уточнювальні питання перед генерацією документів."
    elif unresolved_review_items:
        status = "needs_review"
        hint_reason = "Завершіть обов'язкові підтвердження human-review перед генерацією документів."
    else:
        status = "ok"
        hint_reason = "Спочатку згенеруйте процесуальні документи; фінальний пакет формуйте після проходження гейтів якості."

    recommended_package_mode = "none"
    if not unresolved_questions and not unresolved_review_items:
        recommended_package_mode = "draft"
    package_hint = {
        "status": "blocked",
        "can_generate_final_package": False,
        "can_generate_draft_package": not unresolved_questions and not unresolved_review_items,
        "recommended_package_mode": recommended_package_mode,
        "blockers": list(processual_package_gate.get("blockers") or []),
        "reason": hint_reason,
    }

    next_actions = build_next_actions(
        recommended_doc_types=recommended_doc_types,
        clarifying_questions=unresolved_questions,
        validation_checks=validation_checks,
    )
    if unresolved_review_items:
        next_actions.insert(0, "Завершіть обов'язкові підтвердження checklist людського контролю.")
        next_actions = next_actions[:8]

    warnings: list[str] = []
    if unresolved_questions:
        warnings.append("Перед фінальною генерацією документів потрібно надати уточнення.")
    elif unresolved_review_items:
        warnings.append("Перед фінальною генерацією документів потрібні підтвердження human-review.")

    return {
        "status": status,
        "recommended_doc_types": recommended_doc_types,
        "validation_checks": validation_checks,
        "clarifying_questions": clarifying_questions,
        "unresolved_questions": unresolved_questions,
        "review_checklist": review_checklist,
        "unresolved_review_items": unresolved_review_items,
        "deadline_control": deadline_control,
        "processual_package_gate": processual_package_gate,
        "final_submission_gate": final_submission_gate,
        "package_generation_hint": package_hint,
        "next_actions": next_actions,
        "warnings": warnings,
    }


def _build_full_lawyer_preflight_report_text(
    *,
    source_file_name: str,
    extracted_chars: int,
    processual_only_mode: bool,
    preflight_state: dict[str, object],
) -> str:
    status = str(preflight_state.get("status") or "unknown")
    recommended_doc_types = [str(item) for item in (preflight_state.get("recommended_doc_types") or [])]
    unresolved_questions = [str(item) for item in (preflight_state.get("unresolved_questions") or [])]
    unresolved_review_items = [str(item) for item in (preflight_state.get("unresolved_review_items") or [])]
    deadline_control = preflight_state.get("deadline_control") or []
    processual_package_gate = preflight_state.get("processual_package_gate") or {}
    final_submission_gate = preflight_state.get("final_submission_gate") or {}
    package_hint = preflight_state.get("package_generation_hint") or {}
    next_actions = [str(item) for item in (preflight_state.get("next_actions") or [])]
    warnings = [str(item) for item in (preflight_state.get("warnings") or [])]

    lines: list[str] = [
        "ЗВІТ PREFLIGHT-ПЕРЕВІРКИ (FULL LAWYER)",
        "",
        f"Файл-джерело: {source_file_name}",
        f"Виділено символів: {extracted_chars}",
        f"Режим лише процесуальних документів: {'так' if processual_only_mode else 'ні'}",
        f"Статус preflight: {status}",
        "",
        "Рекомендовані типи документів:",
    ]
    if recommended_doc_types:
        lines.extend([f"- {item}" for item in recommended_doc_types])
    else:
        lines.append("- немає")

    lines.extend(
        [
            "",
            "Гейт процесуального пакета:",
            f"- статус: {processual_package_gate.get('status')}",
            f"- можна сформувати пакет: {processual_package_gate.get('can_generate_package')}",
        ]
    )
    for blocker in list(processual_package_gate.get("blockers") or [])[:10]:
        lines.append(f"- блокер: {blocker}")

    lines.extend(
        [
            "",
            "Фінальний гейт подання:",
            f"- статус: {final_submission_gate.get('status')}",
            f"- hard-stop: {final_submission_gate.get('hard_stop')}",
        ]
    )
    for blocker in list(final_submission_gate.get("blockers") or [])[:10]:
        lines.append(f"- блокер: {blocker}")
    for item in list(final_submission_gate.get("critical_deadlines") or [])[:10]:
        lines.append(f"- критичний строк: {item}")

    lines.extend(
        [
            "",
            "Підказка щодо формування пакета:",
            f"- статус: {package_hint.get('status')}",
            f"- можна сформувати фінальний пакет: {package_hint.get('can_generate_final_package')}",
            f"- можна сформувати чернетковий пакет: {package_hint.get('can_generate_draft_package')}",
            f"- причина: {package_hint.get('reason')}",
        ]
    )
    for blocker in list(package_hint.get("blockers") or [])[:10]:
        lines.append(f"- блокер: {blocker}")

    lines.extend(["", "Незакриті уточнювальні питання:"])
    if unresolved_questions:
        lines.extend([f"- {item}" for item in unresolved_questions[:20]])
    else:
        lines.append("- немає")

    lines.extend(["", "Незакриті підтвердження review-checklist:"])
    if unresolved_review_items:
        lines.extend([f"- {item}" for item in unresolved_review_items[:20]])
    else:
        lines.append("- немає")

    lines.extend(["", "Контроль процесуальних строків:"])
    if isinstance(deadline_control, list) and deadline_control:
        for item in deadline_control[:20]:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- [{item.get('status')}] {item.get('code')} | до: {item.get('due_date')} | примітка: {item.get('note')}"
            )
    else:
        lines.append("- немає")

    lines.extend(["", "Рекомендовані наступні дії:"])
    if next_actions:
        lines.extend([f"- {item}" for item in next_actions[:20]])
    else:
        lines.append("- немає")

    if warnings:
        lines.extend(["", "Попередження:"])
        lines.extend([f"- {item}" for item in warnings[:20]])

    return "\n".join(lines).strip()


@router.post("/process", response_model=AutoProcessResponse)
async def auto_process_document(
    file: UploadFile = File(...),
    max_documents: int = Form(default=3),
    processual_only: bool = Form(default=settings.auto_process_processual_only_default),
    case_id: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AutoProcessResponse:
    subscription = get_or_create_subscription(db, user)
    quota_ok, quota_message = ensure_analysis_quota(subscription)
    if not quota_ok:
        raise HTTPException(status_code=402, detail=quota_message)

    content, file_name = await _read_upload(file)
    source_text = _extract_source_text(file_name, file.content_type, content)
    case_bound_context = _load_case_bound_practice_context(db=db, user=user, case_id=case_id)

    safe_max_documents = max(1, min(int(max_documents or 1), 5))
    conclusions = await build_procedural_conclusions(source_text, max_items=8)
    all_recommended_doc_types = suggest_document_types(
        source_text,
        max_documents=safe_max_documents,
        processual_only=False,
    )
    recommended_doc_types = suggest_document_types(
        source_text,
        max_documents=safe_max_documents,
        processual_only=processual_only,
    )
    pre_warnings: list[str] = []
    if processual_only and any(doc_type not in PROCESSUAL_DOC_TYPES_SET for doc_type in all_recommended_doc_types):
        pre_warnings.append(
            "Увімкнено режим лише процесуальних документів. Непроцесуальні типи виключено з генерації."
        )

    generated_items, warnings, linked_case_law_total, subscription, _, _ = await _generate_documents_bundle(
        db=db,
        user=user,
        subscription=subscription,
        source_text=source_text,
        recommended_doc_types=recommended_doc_types,
        case_id=case_id,
    )
    if pre_warnings:
        warnings = [*pre_warnings, *warnings]
    if len(generated_items) < safe_max_documents:
        warnings.append(
            f"Згенеровано {len(generated_items)} документ(ів) із запитаних {safe_max_documents}. "
            "Причина: обмежений набір рекомендацій, квота або гейти якості."
        )

    subscription = mark_analysis_processed(db, subscription)
    log_action(
        db,
        user_id=user.user_id,
        action="auto_process_upload",
        entity_type="generated_document",
        entity_id=generated_items[0]["id"] if generated_items else None,
        metadata={
            "mode": "process",
            "file_name": file_name,
            "content_type": file.content_type,
            "bytes": len(content),
            "extracted_chars": len(source_text),
            "recommended_doc_types": recommended_doc_types,
            "generated_count": len(generated_items),
            "warnings": warnings,
            "case_law_refs_linked": linked_case_law_total,
        },
    )

    return AutoProcessResponse(
        status="ok",
        source_file_name=file_name,
        extracted_chars=len(source_text),
        procedural_conclusions=conclusions,
        recommended_doc_types=recommended_doc_types,
        generated_documents=generated_items,
        warnings=warnings,
        processual_only_mode=processual_only,
        case_id=case_id,
        usage=to_payload(subscription),
    )

@router.post("/process-stream")
async def auto_process_document_stream(
    file: UploadFile = File(...),
    max_documents: int = Form(default=3),
    processual_only: bool = Form(default=settings.auto_process_processual_only_default),
    case_id: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Server-Sent Events endpoint that streams the progress of the Auto Process AI Conveyor.
    Useful for showing real-time multi-agent activity on the frontend.
    """
    subscription = get_or_create_subscription(db, user)
    quota_ok, quota_message = ensure_analysis_quota(subscription)
    if not quota_ok:
        raise HTTPException(status_code=402, detail=quota_message)

    content, file_name = await _read_upload(file)
    source_text = _extract_source_text(file_name, file.content_type, content)

    async def event_generator():
        try:
            # Step 1: Text extraction finished (fast)
            yield f"data: {json.dumps({'step': 'extract', 'status': 'done', 'message': 'Вилучення тексту завершено', 'chars': len(source_text)})}\n\n"
            await asyncio.sleep(0.5)

            # Step 2: Synthesis and recommendation
            yield f"data: {json.dumps({'step': 'synthesis', 'status': 'active', 'message': 'Синтез правової позиції'})}\n\n"
            safe_max_documents = max(1, min(int(max_documents or 1), 5))
            conclusions = await build_procedural_conclusions(source_text, max_items=8)
            all_recommended_doc_types = suggest_document_types(
                source_text, max_documents=safe_max_documents, processual_only=False
            )
            recommended_doc_types = suggest_document_types(
                source_text, max_documents=safe_max_documents, processual_only=processual_only
            )
            
            pre_warnings: list[str] = []
            if processual_only and any(doc_type not in PROCESSUAL_DOC_TYPES_SET for doc_type in all_recommended_doc_types):
                pre_warnings.append("Увімкнено режим лише процесуальних документів. Непроцесуальні виключено.")
            
            yield f"data: {json.dumps({'step': 'synthesis', 'status': 'done', 'recommended': recommended_doc_types})}\n\n"
            await asyncio.sleep(0.5)

            # Step 3: Generation
            yield f"data: {json.dumps({'step': 'generation', 'status': 'active', 'message': 'Генерація документів'})}\n\n"
            
            generated_items, warnings, linked_case_law_total, sub, _, _ = await _generate_documents_bundle(
                db=db,
                user=user,
                subscription=subscription,
                source_text=source_text,
                recommended_doc_types=recommended_doc_types,
                case_id=case_id,
            )
            if pre_warnings:
                warnings = [*pre_warnings, *warnings]
            if len(generated_items) < safe_max_documents:
                warnings.append(f"Згенеровано {len(generated_items)} документ(ів) із {safe_max_documents}.")

            mark_analysis_processed(db, sub)
            log_action(
                db, user_id=user.user_id, action="auto_process_upload_stream",
                entity_type="generated_document",
                entity_id=generated_items[0]["id"] if generated_items else None,
                metadata={"file_name": file_name, "generated_count": len(generated_items)}
            )
            
            # Final result
            final_result = {
                "status": "ok",
                "source_file_name": file_name,
                "extracted_chars": len(source_text),
                "procedural_conclusions": conclusions,
                "recommended_doc_types": recommended_doc_types,
                "generated_documents": generated_items,
                "warnings": warnings,
                "processual_only_mode": processual_only,
                "case_id": case_id,
                "usage": to_payload(sub),
            }
            yield f"data: {json.dumps({'step': 'generation', 'status': 'done', 'result': final_result})}\n\n"
        
        except Exception as e:
            yield f"data: {json.dumps({'step': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/decision-analysis", response_model=DecisionAnalysisResponse)
async def auto_process_decision_analysis(
    file: UploadFile = File(...),
    include_recent_case_law: bool = Form(default=True),
    case_law_days: int = Form(default=365),
    case_law_limit: int = Form(default=12),
    case_law_court_type: str | None = Form(default=None),
    case_law_source: str | None = Form(default=None),
    only_supreme_case_law: bool = Form(default=False),
    ai_enhance: bool = Form(default=True),
    case_id: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DecisionAnalysisResponse:
    subscription = get_or_create_subscription(db, user)
    quota_ok, quota_message = ensure_analysis_quota(subscription)
    if not quota_ok:
        raise HTTPException(status_code=402, detail=quota_message)

    content, file_name = await _read_upload(file)
    source_text = _extract_source_text(file_name, file.content_type, content)
    case_bound_context = _load_case_bound_practice_context(db=db, user=user, case_id=case_id)
    state = await _compute_decision_analysis_state(
        db=db,
        source_text=source_text,
        include_recent_case_law=include_recent_case_law,
        case_law_days=case_law_days,
        case_law_limit=case_law_limit,
        case_law_court_type=case_law_court_type,
        case_law_source=case_law_source,
        only_supreme_case_law=only_supreme_case_law,
        ai_enhance=ai_enhance,
        seeded_recent_practice=list(case_bound_context.get("recent_practice") or []),
    )
    report_title = f"Звіт аналізу судового рішення - {file_name}"
    report_text = _build_decision_analysis_report_text(
        source_file_name=file_name,
        extracted_chars=len(source_text),
        state=state,
    )

    subscription = mark_analysis_processed(db, subscription)
    log_action(
        db,
        user_id=user.user_id,
        action="auto_decision_analysis_upload",
        entity_type="generated_document",
        entity_id=None,
        metadata={
            "mode": "decision-analysis",
            "file_name": file_name,
            "content_type": file.content_type,
            "bytes": len(content),
            "extracted_chars": len(source_text),
            "include_recent_case_law": bool(include_recent_case_law),
            "case_law_days": state.get("safe_days"),
            "case_law_limit": state.get("safe_limit"),
            "case_law_court_type": (case_law_court_type or "").strip().lower() or None,
            "case_law_source": state.get("source_items") or [],
            "only_supreme_case_law": bool(only_supreme_case_law),
            "recent_practice_count": len(state.get("recent_practice") or []),
            "key_issues_count": len(state.get("key_issues") or []),
            "key_questions_count": len(state.get("key_questions") or []),
            "cassation_vulnerabilities_count": len(state.get("cassation_vulnerabilities") or []),
            "side_assessment_side": (state.get("side_assessment") or {}).get("side"),
            "side_assessment_confidence": (state.get("side_assessment") or {}).get("confidence"),
            "defense_plan_count": len(state.get("defense_plan") or []),
            "evidence_gaps_count": len(state.get("evidence_gaps") or []),
            "evidence_gaps_missing_count": sum(
                1 for item in (state.get("evidence_gaps") or []) if str(item.get("status")) == "missing"
            ),
            "document_preparation_count": len(state.get("document_preparation") or []),
            "document_preparation_blocked_count": sum(
                1 for item in (state.get("document_preparation") or []) if str(item.get("readiness")) == "blocked"
            ),
            "stage_packets_count": len(state.get("stage_packets") or []),
            "quality_blocks_count": len(state.get("quality_blocks") or []),
            "quality_blocks_fail_count": sum(1 for item in (state.get("quality_blocks") or []) if item.get("status") == "fail"),
            "overall_confidence_score": state.get("overall_confidence_score"),
            "quality_gate_status": (state.get("quality_gate") or {}).get("status"),
            "traceability_count": len(state.get("traceability") or []),
            "practice_total": (state.get("practice_coverage") or {}).get("total_items"),
            "practice_distinct_courts": (state.get("practice_coverage") or {}).get("distinct_courts"),
            "practice_instance_levels": (state.get("practice_coverage") or {}).get("instance_levels"),
            "practice_latest_decision_date": (state.get("practice_coverage") or {}).get("latest_decision_date"),
            "practice_oldest_decision_date": (state.get("practice_coverage") or {}).get("oldest_decision_date"),
            "practice_freshness_days": (state.get("practice_coverage") or {}).get("freshness_days"),
            "practice_stale": (state.get("practice_coverage") or {}).get("stale"),
            "warnings": state.get("warnings") or [],
            "case_bound_case_number": case_bound_context.get("case_number") or None,
            "case_bound_practice_count": len(case_bound_context.get("recent_practice") or []),
            "ai_enhance": bool(ai_enhance),
            "used_ai": bool(state.get("used_ai")),
            "ai_model": str(state.get("ai_model") or "") or None,
            "ai_error": str(state.get("ai_error") or "") or None,
            "report_title": report_title,
            "report_text": report_text,
        },
    )

    return DecisionAnalysisResponse(
        status="ok",
        source_file_name=file_name,
        extracted_chars=len(source_text),
        dispute_summary=str(state.get("dispute_summary") or ""),
        procedural_context=str(state.get("procedural_context") or ""),
        key_issues=list(state.get("key_issues") or []),
        key_questions=list(state.get("key_questions") or []),
        side_assessment=state.get("side_assessment") or {},
        defense_plan=list(state.get("defense_plan") or []),
        evidence_gaps=list(state.get("evidence_gaps") or []),
        document_preparation=list(state.get("document_preparation") or []),
        cassation_vulnerabilities=list(state.get("cassation_vulnerabilities") or []),
        final_conclusion=str(state.get("final_conclusion") or ""),
        stage_recommendations=list(state.get("stage_recommendations") or []),
        stage_packets=list(state.get("stage_packets") or []),
        recent_practice=list(state.get("recent_practice") or []),
        practice_coverage=state.get("practice_coverage") or {},
        quality_blocks=list(state.get("quality_blocks") or []),
        traceability=list(state.get("traceability") or []),
        overall_confidence_score=float(state.get("overall_confidence_score") or 0.0),
        quality_gate=state.get("quality_gate") or {},
        used_ai=bool(state.get("used_ai")),
        ai_model=str(state.get("ai_model") or ""),
        ai_error=str(state.get("ai_error") or ""),
        warnings=list(state.get("warnings") or []),
        case_id=case_id,
        usage=to_payload(subscription),
    )


@router.post("/decision-analysis/export")
async def auto_process_decision_analysis_export(
    file: UploadFile = File(...),
    format: str = Form(default="pdf"),
    include_recent_case_law: bool = Form(default=True),
    case_law_days: int = Form(default=365),
    case_law_limit: int = Form(default=12),
    case_law_court_type: str | None = Form(default=None),
    case_law_source: str | None = Form(default=None),
    only_supreme_case_law: bool = Form(default=False),
    ai_enhance: bool = Form(default=True),
    consume_quota: bool = Form(default=False),
    case_id: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    normalized_format = (format or "pdf").strip().lower()
    if normalized_format not in {"pdf", "docx"}:
        raise HTTPException(status_code=422, detail="Параметр format має бути або pdf, або docx.")

    subscription = get_or_create_subscription(db, user)
    if consume_quota:
        quota_ok, quota_message = ensure_analysis_quota(subscription)
        if not quota_ok:
            raise HTTPException(status_code=402, detail=quota_message)

    content, file_name = await _read_upload(file)
    source_text = _extract_source_text(file_name, file.content_type, content)
    case_bound_context = _load_case_bound_practice_context(db=db, user=user, case_id=case_id)
    state = await _compute_decision_analysis_state(
        db=db,
        source_text=source_text,
        include_recent_case_law=include_recent_case_law,
        case_law_days=case_law_days,
        case_law_limit=case_law_limit,
        case_law_court_type=case_law_court_type,
        case_law_source=case_law_source,
        only_supreme_case_law=only_supreme_case_law,
        ai_enhance=ai_enhance,
        seeded_recent_practice=list(case_bound_context.get("recent_practice") or []),
    )
    report_title = f"Звіт аналізу судового рішення - {file_name}"
    report_text = _build_decision_analysis_report_text(
        source_file_name=file_name,
        extracted_chars=len(source_text),
        state=state,
    )

    if normalized_format == "pdf":
        report_content = render_pdf_bytes(title=report_title, text=report_text)
        media_type = "application/pdf"
        extension = "pdf"
    else:
        report_content = render_docx_bytes(title=report_title, text=report_text)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        extension = "docx"

    if consume_quota:
        subscription = mark_analysis_processed(db, subscription)

    log_action(
        db,
        user_id=user.user_id,
        action="auto_decision_analysis_export",
        entity_type="generated_document",
        entity_id=None,
        metadata={
            "mode": "decision-analysis-export",
            "file_name": file_name,
            "content_type": file.content_type,
            "bytes": len(content),
            "extracted_chars": len(source_text),
            "format": normalized_format,
            "include_recent_case_law": bool(include_recent_case_law),
            "case_law_days": state.get("safe_days"),
            "case_law_limit": state.get("safe_limit"),
            "case_law_court_type": (case_law_court_type or "").strip().lower() or None,
            "case_law_source": state.get("source_items") or [],
            "only_supreme_case_law": bool(only_supreme_case_law),
            "quality_gate_status": (state.get("quality_gate") or {}).get("status"),
            "overall_confidence_score": state.get("overall_confidence_score"),
            "side_assessment_side": (state.get("side_assessment") or {}).get("side"),
            "side_assessment_confidence": (state.get("side_assessment") or {}).get("confidence"),
            "defense_plan_count": len(state.get("defense_plan") or []),
            "evidence_gaps_count": len(state.get("evidence_gaps") or []),
            "evidence_gaps_missing_count": sum(
                1 for item in (state.get("evidence_gaps") or []) if str(item.get("status")) == "missing"
            ),
            "document_preparation_count": len(state.get("document_preparation") or []),
            "document_preparation_blocked_count": sum(
                1 for item in (state.get("document_preparation") or []) if str(item.get("readiness")) == "blocked"
            ),
            "stage_packets_count": len(state.get("stage_packets") or []),
            "quality_blocks_count": len(state.get("quality_blocks") or []),
            "traceability_count": len(state.get("traceability") or []),
            "practice_total": (state.get("practice_coverage") or {}).get("total_items"),
            "practice_distinct_courts": (state.get("practice_coverage") or {}).get("distinct_courts"),
            "practice_instance_levels": (state.get("practice_coverage") or {}).get("instance_levels"),
            "practice_latest_decision_date": (state.get("practice_coverage") or {}).get("latest_decision_date"),
            "practice_oldest_decision_date": (state.get("practice_coverage") or {}).get("oldest_decision_date"),
            "practice_freshness_days": (state.get("practice_coverage") or {}).get("freshness_days"),
            "practice_stale": (state.get("practice_coverage") or {}).get("stale"),
            "warnings": state.get("warnings") or [],
            "case_bound_case_number": case_bound_context.get("case_number") or None,
            "case_bound_practice_count": len(case_bound_context.get("recent_practice") or []),
            "ai_enhance": bool(ai_enhance),
            "used_ai": bool(state.get("used_ai")),
            "ai_model": str(state.get("ai_model") or "") or None,
            "ai_error": str(state.get("ai_error") or "") or None,
            "consume_quota": bool(consume_quota),
            "report_title": report_title,
            "report_text": report_text,
        },
    )

    filename = sanitize_filename(f"decision-analysis-{user.user_id}.{extension}")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=report_content, media_type=media_type, headers=headers)


@router.post("/decision-analysis/package", response_model=DecisionAnalysisPackageResponse)
async def auto_process_decision_analysis_package(
    file: UploadFile = File(...),
    max_documents: int = Form(default=4),
    include_warn_readiness: bool = Form(default=True),
    include_recent_case_law: bool = Form(default=True),
    case_law_days: int = Form(default=365),
    case_law_limit: int = Form(default=12),
    case_law_court_type: str | None = Form(default=None),
    case_law_source: str | None = Form(default=None),
    only_supreme_case_law: bool = Form(default=False),
    ai_enhance: bool = Form(default=True),
    consume_analysis_quota: bool = Form(default=False),
    case_id: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DecisionAnalysisPackageResponse:
    subscription = get_or_create_subscription(db, user)
    if consume_analysis_quota:
        quota_ok, quota_message = ensure_analysis_quota(subscription)
        if not quota_ok:
            raise HTTPException(status_code=402, detail=quota_message)

    content, file_name = await _read_upload(file)
    source_text = _extract_source_text(file_name, file.content_type, content)
    case_bound_context = _load_case_bound_practice_context(db=db, user=user, case_id=case_id)
    state = await _compute_decision_analysis_state(
        db=db,
        source_text=source_text,
        include_recent_case_law=include_recent_case_law,
        case_law_days=case_law_days,
        case_law_limit=case_law_limit,
        case_law_court_type=case_law_court_type,
        case_law_source=case_law_source,
        only_supreme_case_law=only_supreme_case_law,
        ai_enhance=ai_enhance,
        seeded_recent_practice=list(case_bound_context.get("recent_practice") or []),
    )

    safe_limit = max(1, min(int(max_documents or 1), 8))
    prep_items = list(state.get("document_preparation") or [])
    selected_doc_types: list[str] = []
    skipped_doc_types: list[str] = []
    allowed_readiness = {"ready", "warn"} if include_warn_readiness else {"ready"}
    for item in prep_items:
        if not isinstance(item, dict):
            continue
        doc_type = str(item.get("doc_type") or "").strip()
        readiness = str(item.get("readiness") or "").strip().lower()
        if not doc_type:
            continue
        if readiness in allowed_readiness and doc_type not in selected_doc_types:
            selected_doc_types.append(doc_type)
        else:
            skipped_doc_types.append(doc_type)
        if len(selected_doc_types) >= safe_limit:
            break

    package_warnings = list(state.get("warnings") or [])
    if not selected_doc_types and prep_items:
        # Fallback to non-blocked priorities if strict readiness filter leaves no candidates.
        for item in prep_items:
            if not isinstance(item, dict):
                continue
            doc_type = str(item.get("doc_type") or "").strip()
            readiness = str(item.get("readiness") or "").strip().lower()
            if not doc_type or readiness == "blocked" or doc_type in selected_doc_types:
                continue
            selected_doc_types.append(doc_type)
            if len(selected_doc_types) >= safe_limit:
                break
        if selected_doc_types:
            package_warnings.append(
                "Документи не відповідали вибраному фільтру готовності. "
                "Застосовано резервний відбір неблокованих позицій."
            )

    generation_context = _build_decision_package_generation_context(source_text, state)
    if str(case_bound_context.get("prompt_context") or "").strip():
        generation_context = (
            f"{case_bound_context.get('prompt_context')}\n\n{generation_context}"
            if generation_context.strip()
            else str(case_bound_context.get("prompt_context") or "")
        )
    generated_items: list[dict] = []
    linked_case_law_total = 0
    if selected_doc_types:
        generated_items, bundle_warnings, linked_case_law_total, subscription, _, _ = await _generate_documents_bundle(
            db=db,
            user=user,
            subscription=subscription,
            source_text=source_text,
            recommended_doc_types=selected_doc_types,
            extra_generation_context=generation_context,
            case_id=case_id,
        )
        if bundle_warnings:
            package_warnings.extend(bundle_warnings)
    else:
        package_warnings.append(
            "Генерацію пакета пропущено: у матриці підготовки не знайдено допустимих типів документів."
        )

    if consume_analysis_quota:
        subscription = mark_analysis_processed(db, subscription)

    evidence_gaps = list(state.get("evidence_gaps") or [])
    missing_evidence_count = sum(1 for item in evidence_gaps if str(item.get("status")) == "missing")
    log_action(
        db,
        user_id=user.user_id,
        action="auto_decision_analysis_package",
        entity_type="generated_document",
        entity_id=generated_items[0]["id"] if generated_items else None,
        metadata={
            "mode": "decision-analysis-package",
            "file_name": file_name,
            "content_type": file.content_type,
            "bytes": len(content),
            "extracted_chars": len(source_text),
            "max_documents": safe_limit,
            "include_warn_readiness": bool(include_warn_readiness),
            "selected_doc_types": selected_doc_types,
            "skipped_doc_types": skipped_doc_types,
            "generated_count": len(generated_items),
            "linked_case_law_total": linked_case_law_total,
            "side_assessment_side": (state.get("side_assessment") or {}).get("side"),
            "side_assessment_confidence": (state.get("side_assessment") or {}).get("confidence"),
            "evidence_gaps_missing_count": missing_evidence_count,
            "consume_analysis_quota": bool(consume_analysis_quota),
            "warnings": package_warnings,
        },
    )

    return DecisionAnalysisPackageResponse(
        status="ok",
        source_file_name=file_name,
        extracted_chars=len(source_text),
        selected_doc_types=selected_doc_types,
        skipped_doc_types=skipped_doc_types,
        generated_documents=generated_items,
        side_assessment=state.get("side_assessment") or {},
        evidence_gaps_missing_count=missing_evidence_count,
        warnings=package_warnings,
        usage=to_payload(subscription),
    )


@router.get("/decision-analysis/history", response_model=DecisionAnalysisHistoryResponse)
def auto_process_decision_analysis_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    event: str = Query(default="all", pattern="^(all|upload|export)$"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DecisionAnalysisHistoryResponse:
    event_to_actions = {
        "upload": ["auto_decision_analysis_upload"],
        "export": ["auto_decision_analysis_export"],
        "all": ["auto_decision_analysis_upload", "auto_decision_analysis_export"],
    }
    selected_actions = event_to_actions.get(event, event_to_actions["all"])
    filters = [AuditLog.user_id == user.user_id, AuditLog.action.in_(selected_actions)]

    total = int(db.execute(select(func.count()).select_from(AuditLog).where(*filters)).scalar_one() or 0)
    pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    normalized_page = max(1, min(page, pages))

    rows = list(
        db.execute(
            select(AuditLog)
            .where(*filters)
            .order_by(desc(AuditLog.created_at), desc(AuditLog.id))
            .offset((normalized_page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    items: list[dict[str, object]] = []
    for row in rows:
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        items.append(
            {
                "id": row.id,
                "event_type": "upload" if row.action == "auto_decision_analysis_upload" else "export",
                "source_file_name": meta.get("file_name"),
                "extracted_chars": meta.get("extracted_chars"),
                "status": "ok",
                "quality_gate_status": meta.get("quality_gate_status"),
                "overall_confidence_score": meta.get("overall_confidence_score"),
                "practice_total": meta.get("practice_total"),
                "practice_latest_decision_date": meta.get("practice_latest_decision_date"),
                "format": meta.get("format"),
                "has_report_snapshot": bool(str(meta.get("report_text") or "").strip()),
                "created_at": row.created_at.isoformat(),
            }
        )

    return DecisionAnalysisHistoryResponse(
        total=total,
        page=normalized_page,
        page_size=page_size,
        pages=pages,
        event=event,
        items=items,
    )


@router.get("/decision-analysis/history/{audit_id}/export")
def auto_process_decision_analysis_history_export(
    audit_id: str,
    format: str = Query(default="pdf", pattern="^(pdf|docx)$"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    row = db.execute(
        select(AuditLog).where(
            AuditLog.id == audit_id,
            AuditLog.user_id == user.user_id,
            AuditLog.action.in_(["auto_decision_analysis_upload", "auto_decision_analysis_export"]),
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Елемент історії аналізу рішення не знайдено.")

    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    report_text = str(meta.get("report_text") or "").strip()
    if not report_text:
        raise HTTPException(status_code=404, detail="Для цього елемента історії недоступний збережений знімок звіту.")
    report_title = str(meta.get("report_title") or f"Звіт аналізу судового рішення - {audit_id}")

    if format == "pdf":
        content = render_pdf_bytes(title=report_title, text=report_text)
        media_type = "application/pdf"
        extension = "pdf"
    else:
        content = render_docx_bytes(title=report_title, text=report_text)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        extension = "docx"

    log_action(
        db,
        user_id=user.user_id,
        action="auto_decision_analysis_history_export",
        entity_type="audit_log",
        entity_id=row.id,
        metadata={
            "source_action": row.action,
            "format": format,
            "report_title": report_title,
        },
    )

    filename = sanitize_filename(f"decision-analysis-history-{audit_id}.{extension}")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type=media_type, headers=headers)


@router.post("/full-lawyer/preflight", response_model=FullLawyerPreflightResponse)
async def auto_process_full_lawyer_preflight(
    file: UploadFile = File(...),
    max_documents: int = Form(default=4),
    processual_only: bool = Form(default=settings.auto_process_processual_only_default),
    clarifications_json: str | None = Form(default=None),
    review_confirmations_json: str | None = Form(default=None),
    consume_quota: bool = Form(default=False),
    case_id: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FullLawyerPreflightResponse:
    subscription = get_or_create_subscription(db, user)
    if consume_quota:
        quota_ok, quota_message = ensure_analysis_quota(subscription)
        if not quota_ok:
            raise HTTPException(status_code=402, detail=quota_message)

    content, file_name = await _read_upload(file)
    source_text = _extract_source_text(file_name, file.content_type, content)
    case_bound_context = _load_case_bound_practice_context(db=db, user=user, case_id=case_id)
    safe_max_documents = max(1, min(int(max_documents or 1), 5))
    preflight_state = await _compute_full_lawyer_preflight_state(
        source_text=source_text,
        safe_max_documents=safe_max_documents,
        processual_only=processual_only,
        clarifications_json=clarifications_json,
        review_confirmations_json=review_confirmations_json,
    )
    status = str(preflight_state.get("status") or "ok")
    recommended_doc_types = list(preflight_state.get("recommended_doc_types") or [])
    clarifying_questions = list(preflight_state.get("clarifying_questions") or [])
    unresolved_questions = list(preflight_state.get("unresolved_questions") or [])
    review_checklist = list(preflight_state.get("review_checklist") or [])
    unresolved_review_items = list(preflight_state.get("unresolved_review_items") or [])
    warnings = list(preflight_state.get("warnings") or [])
    final_submission_gate = preflight_state.get("final_submission_gate") or {}
    report_title = f"Звіт preflight-перевірки (Full Lawyer) - {file_name}"
    report_text = _build_full_lawyer_preflight_report_text(
        source_file_name=file_name,
        extracted_chars=len(source_text),
        processual_only_mode=processual_only,
        preflight_state=preflight_state,
    )

    if consume_quota:
        subscription = mark_analysis_processed(db, subscription)
    log_action(
        db,
        user_id=user.user_id,
        action="auto_full_lawyer_preflight_upload",
        entity_type="generated_document",
        entity_id=None,
        metadata={
            "mode": "full-lawyer-preflight",
            "file_name": file_name,
            "content_type": file.content_type,
            "bytes": len(content),
            "extracted_chars": len(source_text),
            "status": status,
            "recommended_doc_types": recommended_doc_types,
            "clarifying_questions_count": len(clarifying_questions),
            "unresolved_questions_count": len(unresolved_questions),
            "review_checklist_count": len(review_checklist),
            "unresolved_review_items_count": len(unresolved_review_items),
            "final_submission_gate": final_submission_gate.get("status"),
            "consume_quota": bool(consume_quota),
            "report_title": report_title,
            "report_text": report_text,
            "warnings": warnings,
            "case_bound_case_number": case_bound_context.get("case_number") or None,
            "case_bound_practice_count": len(case_bound_context.get("recent_practice") or []),
        },
    )

    return FullLawyerPreflightResponse(
        status=status,
        source_file_name=file_name,
        extracted_chars=len(source_text),
        processual_only_mode=processual_only,
        recommended_doc_types=recommended_doc_types,
        validation_checks=preflight_state.get("validation_checks") or [],
        clarifying_questions=clarifying_questions,
        unresolved_questions=unresolved_questions,
        review_checklist=review_checklist,
        unresolved_review_items=unresolved_review_items,
        deadline_control=preflight_state.get("deadline_control") or [],
        processual_package_gate=preflight_state.get("processual_package_gate") or {},
        final_submission_gate=final_submission_gate,
        package_generation_hint=preflight_state.get("package_generation_hint") or {},
        next_actions=preflight_state.get("next_actions") or [],
        warnings=warnings,
        usage=to_payload(subscription),
    )


@router.post("/full-lawyer/preflight/export")
async def auto_process_full_lawyer_preflight_export(
    file: UploadFile = File(...),
    format: str = Form(default="pdf"),
    max_documents: int = Form(default=4),
    processual_only: bool = Form(default=settings.auto_process_processual_only_default),
    clarifications_json: str | None = Form(default=None),
    review_confirmations_json: str | None = Form(default=None),
    consume_quota: bool = Form(default=False),
    case_id: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    normalized_format = (format or "pdf").strip().lower()
    if normalized_format not in {"pdf", "docx"}:
        raise HTTPException(status_code=422, detail="Параметр format має бути або pdf, або docx.")

    subscription = get_or_create_subscription(db, user)
    if consume_quota:
        quota_ok, quota_message = ensure_analysis_quota(subscription)
        if not quota_ok:
            raise HTTPException(status_code=402, detail=quota_message)

    content, file_name = await _read_upload(file)
    source_text = _extract_source_text(file_name, file.content_type, content)
    safe_max_documents = max(1, min(int(max_documents or 1), 5))
    preflight_state = await _compute_full_lawyer_preflight_state(
        source_text=source_text,
        safe_max_documents=safe_max_documents,
        processual_only=processual_only,
        clarifications_json=clarifications_json,
        review_confirmations_json=review_confirmations_json,
    )

    report_title = f"Звіт preflight-перевірки (Full Lawyer) - {file_name}"
    report_text = _build_full_lawyer_preflight_report_text(
        source_file_name=file_name,
        extracted_chars=len(source_text),
        processual_only_mode=processual_only,
        preflight_state=preflight_state,
    )

    if normalized_format == "pdf":
        report_content = render_pdf_bytes(title=report_title, text=report_text)
        media_type = "application/pdf"
        extension = "pdf"
    else:
        report_content = render_docx_bytes(title=report_title, text=report_text)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        extension = "docx"

    if consume_quota:
        subscription = mark_analysis_processed(db, subscription)
    log_action(
        db,
        user_id=user.user_id,
        action="auto_full_lawyer_preflight_export",
        entity_type="generated_document",
        entity_id=None,
        metadata={
            "mode": "full-lawyer-preflight-export",
            "file_name": file_name,
            "content_type": file.content_type,
            "bytes": len(content),
            "extracted_chars": len(source_text),
            "format": normalized_format,
            "status": preflight_state.get("status"),
            "recommended_doc_types": preflight_state.get("recommended_doc_types") or [],
            "unresolved_questions_count": len(preflight_state.get("unresolved_questions") or []),
            "unresolved_review_items_count": len(preflight_state.get("unresolved_review_items") or []),
            "consume_quota": bool(consume_quota),
            "report_title": report_title,
            "report_text": report_text,
            "warnings": preflight_state.get("warnings") or [],
        },
    )

    filename = sanitize_filename(f"full-lawyer-preflight-{user.user_id}.{extension}")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=report_content, media_type=media_type, headers=headers)


@router.get("/full-lawyer/preflight/history", response_model=FullLawyerPreflightHistoryResponse)
def auto_process_full_lawyer_preflight_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    event: str = Query(default="all", pattern="^(all|upload|export)$"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FullLawyerPreflightHistoryResponse:
    event_to_actions = {
        "upload": ["auto_full_lawyer_preflight_upload"],
        "export": ["auto_full_lawyer_preflight_export"],
        "all": ["auto_full_lawyer_preflight_upload", "auto_full_lawyer_preflight_export"],
    }
    selected_actions = event_to_actions.get(event, event_to_actions["all"])
    filters = [AuditLog.user_id == user.user_id, AuditLog.action.in_(selected_actions)]

    total = int(db.execute(select(func.count()).select_from(AuditLog).where(*filters)).scalar_one() or 0)
    pages = max(1, math.ceil(total / page_size)) if total > 0 else 1
    normalized_page = max(1, min(page, pages))

    rows = list(
        db.execute(
            select(AuditLog)
            .where(*filters)
            .order_by(desc(AuditLog.created_at), desc(AuditLog.id))
            .offset((normalized_page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )

    items: list[dict[str, object]] = []
    for row in rows:
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        items.append(
            {
                "id": row.id,
                "event_type": "upload" if row.action == "auto_full_lawyer_preflight_upload" else "export",
                "source_file_name": meta.get("file_name"),
                "extracted_chars": meta.get("extracted_chars"),
                "status": meta.get("status"),
                "final_submission_gate_status": meta.get("final_submission_gate"),
                "consume_quota": bool(meta.get("consume_quota")),
                "format": meta.get("format"),
                "has_report_snapshot": bool(str(meta.get("report_text") or "").strip()),
                "created_at": row.created_at.isoformat(),
            }
        )

    return FullLawyerPreflightHistoryResponse(
        total=total,
        page=normalized_page,
        page_size=page_size,
        pages=pages,
        event=event,
        items=items,
    )


@router.get("/full-lawyer/preflight/history/{audit_id}/export")
def auto_process_full_lawyer_preflight_history_export(
    audit_id: str,
    format: str = Query(default="pdf", pattern="^(pdf|docx)$"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    row = db.execute(
        select(AuditLog).where(
            AuditLog.id == audit_id,
            AuditLog.user_id == user.user_id,
            AuditLog.action.in_(["auto_full_lawyer_preflight_upload", "auto_full_lawyer_preflight_export"]),
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Елемент історії preflight-звіту не знайдено.")

    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    report_text = str(meta.get("report_text") or "").strip()
    if not report_text:
        raise HTTPException(status_code=404, detail="Для цього елемента історії недоступний збережений знімок звіту.")
    report_title = str(meta.get("report_title") or f"Звіт preflight-перевірки (Full Lawyer) - {audit_id}")

    if format == "pdf":
        content = render_pdf_bytes(title=report_title, text=report_text)
        media_type = "application/pdf"
        extension = "pdf"
    else:
        content = render_docx_bytes(title=report_title, text=report_text)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        extension = "docx"

    log_action(
        db,
        user_id=user.user_id,
        action="auto_full_lawyer_preflight_history_export",
        entity_type="audit_log",
        entity_id=row.id,
        metadata={
            "source_action": row.action,
            "format": format,
            "report_title": report_title,
        },
    )

    filename = sanitize_filename(f"full-lawyer-preflight-history-{audit_id}.{extension}")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type=media_type, headers=headers)


@router.post("/full-lawyer", response_model=FullLawyerResponse)
async def auto_process_full_lawyer(
    file: UploadFile = File(...),
    max_documents: int = Form(default=4),
    processual_only: bool = Form(default=settings.auto_process_processual_only_default),
    clarifications_json: str | None = Form(default=None),
    review_confirmations_json: str | None = Form(default=None),
    generate_package: bool = Form(default=False),
    generate_package_draft_on_hard_stop: bool = Form(default=False),
    case_id: str | None = Form(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FullLawyerResponse:
    subscription = get_or_create_subscription(db, user)
    quota_ok, quota_message = ensure_analysis_quota(subscription)
    if not quota_ok:
        raise HTTPException(status_code=402, detail=quota_message)

    content, file_name = await _read_upload(file)
    source_text = _extract_source_text(file_name, file.content_type, content)
    case_bound_context = _load_case_bound_practice_context(db=db, user=user, case_id=case_id)

    safe_max_documents = max(1, min(int(max_documents or 1), 5))
    brief = await build_full_lawyer_brief(
        source_text,
        max_documents=safe_max_documents,
        processual_only=processual_only,
    )
    conclusions = await build_procedural_conclusions(source_text, max_items=10)
    financial_snapshot = build_financial_snapshot(source_text, brief)
    validation_checks = build_rule_validation_checks(source_text, brief)
    clarifying_questions = build_clarifying_questions(
        source_text,
        missing_information=brief.get("missing_information") or [],
        max_items=8,
    )

    all_recommended_doc_types = _merge_recommended_doc_types(
        brief.get("recommended_documents") or [],
        suggest_document_types(source_text, max_documents=safe_max_documents, processual_only=False),
        limit=safe_max_documents,
    )
    recommended_doc_types = _merge_recommended_doc_types(
        brief.get("recommended_documents") or [],
        suggest_document_types(
            source_text,
            max_documents=safe_max_documents,
            processual_only=processual_only,
        ),
        limit=safe_max_documents,
    )

    primary_doc_type = recommended_doc_types[0] if recommended_doc_types else "lawsuit_debt_loan"
    primary_form_data = build_form_data_for_doc_type(primary_doc_type, source_text)
    context_case_law_refs = enrich_document_with_case_law(
        db,
        document_type=primary_doc_type,
        form_data=primary_form_data,
        limit=5,
    )
    context_refs = _build_case_law_context_refs_for_response(context_case_law_refs)
    context_refs.extend(list(case_bound_context.get("context_refs") or []))
    context_refs.extend(build_law_context_refs_for_doc_types(recommended_doc_types))
    clarification_answers = parse_clarification_answers(clarifications_json)
    _, unresolved_questions = resolve_clarifying_questions(clarifying_questions, clarification_answers)
    review_checklist = build_review_checklist(
        summary=brief,
        validation_checks=validation_checks,
        recommended_doc_types=recommended_doc_types,
    )
    review_confirmations = parse_review_confirmations(review_confirmations_json)
    unresolved_review_items = [] if unresolved_questions else resolve_review_checklist(review_checklist, review_confirmations)
    analysis_highlights = build_analysis_highlights(
        source_text,
        summary={**brief, "claim_amount_uah": financial_snapshot.get("principal_uah")},
        max_items=8,
    )
    party_profile = build_party_profile(source_text)
    jurisdiction_recommendation = build_jurisdiction_recommendation(
        summary=brief,
        recommended_doc_types=recommended_doc_types,
        party_profile=party_profile,
    )

    generated_items: list[dict] = []
    warnings: list[str] = []
    if processual_only and any(doc_type not in PROCESSUAL_DOC_TYPES_SET for doc_type in all_recommended_doc_types):
        warnings.append("Увімкнено режим лише процесуальних документів. Непроцесуальні типи виключено.")
    linked_case_law_total = 0
    filing_package: dict = {
        "generated": False,
        "items": [],
        "checklist": [],
        "status": "not_requested",
        "reason": None,
        "is_draft": False,
    }
    processual_package_gate: dict[str, object] = {
        "status": "blocked",
        "can_generate_package": False,
        "blockers": ["Generation not started yet."],
    }
    generated_processual_checks: list[dict[str, str]] = []
    generated_docs_quality: list[dict[str, object]] = []

    package_requested = bool(generate_package)
    package_gate_passed = False
    draft_on_hard_stop = bool(generate_package_draft_on_hard_stop)

    if unresolved_questions:
        warnings.append("Перед фінальною генерацією документів потрібно надати уточнення.")
    elif unresolved_review_items:
        warnings.append("Перед фінальною генерацією документів потрібні підтвердження human-review.")
    else:
        generated_items, bundle_warnings, linked_case_law_total, subscription, generated_processual_checks, generated_docs_quality = await _generate_documents_bundle(
            db=db,
            user=user,
            subscription=subscription,
            source_text=source_text,
            recommended_doc_types=recommended_doc_types,
            extra_generation_context=str(case_bound_context.get("prompt_context") or "") or None,
            case_id=case_id,
        )
        if bundle_warnings:
            warnings.extend(bundle_warnings)
        validation_checks.extend(generated_processual_checks)
        processual_package_gate = _build_processual_package_gate(
            generated_items=generated_items,
            unresolved_questions=unresolved_questions,
            unresolved_review_items=unresolved_review_items,
        )
        package_gate_passed = bool(processual_package_gate.get("can_generate_package"))
        if package_requested:
            filing_package["status"] = "pending"
        if package_requested and not package_gate_passed:
            warnings.append("Генерацію пакета подання заблоковано строгим процесуальним гейтом.")
            for blocker in (processual_package_gate.get("blockers") or [])[:5]:
                warnings.append(f"Гейт пакета: {blocker}")
            filing_package["status"] = "blocked_processual_gate"
            filing_package["reason"] = "Процесуальний гейт пакета не пройдено. Усуньте блокери і перезапустіть генерацію."

    if unresolved_questions or unresolved_review_items:
        processual_package_gate = _build_processual_package_gate(
            generated_items=generated_items,
            unresolved_questions=unresolved_questions,
            unresolved_review_items=unresolved_review_items,
        )
        if package_requested:
            filing_package["status"] = "blocked_processual_gate"
            filing_package["reason"] = "Генерація пакета недоступна, доки не закрито гейти уточнення/review."

    next_actions = build_next_actions(
        recommended_doc_types=recommended_doc_types,
        clarifying_questions=unresolved_questions,
        validation_checks=validation_checks,
    )
    if unresolved_review_items:
        next_actions.insert(0, "Завершіть обов'язкові підтвердження checklist людського контролю.")
        next_actions = next_actions[:8]
    confidence_score = estimate_confidence_score(
        summary={**brief, "claim_amount_uah": financial_snapshot.get("principal_uah")},
        validation_checks=validation_checks,
        clarifying_questions=clarifying_questions,
        unresolved_questions=unresolved_questions,
        case_law_refs_count=len(context_case_law_refs),
    )
    if unresolved_questions:
        response_status = "needs_clarification"
    elif unresolved_review_items:
        response_status = "needs_review"
    else:
        response_status = "ok"
    workflow_stages, ready_for_filing = build_workflow_stages(
        procedural_conclusions=conclusions,
        context_refs_count=len(context_refs),
        validation_checks=validation_checks,
        unresolved_questions=unresolved_questions,
        unresolved_review_items=unresolved_review_items,
        generated_documents_count=len(generated_items),
        filing_package_generated=bool(filing_package.get("generated")),
    )
    procedural_timeline = build_procedural_timeline(
        source_text,
        summary=brief,
        recommended_doc_types=recommended_doc_types,
    )
    evidence_matrix = build_evidence_matrix(
        source_text,
        evidence_required=brief.get("evidence_required") or [],
    )
    legal_argument_map = build_legal_argument_map(
        legal_basis=brief.get("legal_basis") or [],
        recommended_doc_types=recommended_doc_types,
    )
    readiness_breakdown = build_readiness_breakdown(
        validation_checks=validation_checks,
        unresolved_questions=unresolved_questions,
        unresolved_review_items=unresolved_review_items,
        generated_documents_count=len(generated_items),
        confidence_score=confidence_score,
    )
    post_filing_plan = build_post_filing_plan(
        recommended_doc_types=recommended_doc_types,
        ready_for_filing=ready_for_filing,
    )
    e_court_submission_preview = build_e_court_submission_preview(
        generated_items=generated_items,
        ready_for_filing=ready_for_filing,
        unresolved_questions=unresolved_questions,
        unresolved_review_items=unresolved_review_items,
    )
    priority_queue = build_priority_queue(
        next_actions=next_actions,
        procedural_timeline=procedural_timeline,
        readiness_breakdown=readiness_breakdown,
    )
    consistency_report = build_consistency_report(
        source_text=source_text,
        summary=brief,
        recommended_doc_types=recommended_doc_types,
        financial_snapshot=financial_snapshot,
    )
    remedy_coverage = build_remedy_coverage(recommended_doc_types=recommended_doc_types)
    citation_pack = build_citation_pack(
        legal_basis=brief.get("legal_basis") or [],
        context_refs=context_refs,
    )
    case_law_application_matrix = build_case_law_application_matrix(
        legal_argument_map=legal_argument_map,
        citation_pack=citation_pack,
        context_refs=context_refs,
    )
    fee_scenarios = build_fee_scenarios(financial_snapshot=financial_snapshot)
    filing_risk_simulation = build_filing_risk_simulation(
        validation_checks=validation_checks,
        unresolved_questions=unresolved_questions,
        unresolved_review_items=unresolved_review_items,
        readiness_breakdown=readiness_breakdown,
    )
    procedural_defect_scan = build_procedural_defect_scan(
        validation_checks=validation_checks,
        unresolved_questions=unresolved_questions,
        unresolved_review_items=unresolved_review_items,
        generated_documents_count=len(generated_items),
    )
    evidence_admissibility_map = build_evidence_admissibility_map(evidence_matrix=evidence_matrix)
    motion_recommendations = build_motion_recommendations(
        summary=brief,
        recommended_doc_types=recommended_doc_types,
        evidence_matrix=evidence_matrix,
        procedural_timeline=procedural_timeline,
        validation_checks=validation_checks,
    )
    hearing_preparation_plan = build_hearing_preparation_plan(
        summary=brief,
        citation_pack=citation_pack,
        priority_queue=priority_queue,
    )
    package_completeness = build_package_completeness(
        generated_documents_count=len(generated_items),
        evidence_matrix=evidence_matrix,
        review_checklist=review_checklist,
        unresolved_review_items=unresolved_review_items,
    )
    opponent_objections = build_opponent_objections(
        validation_checks=validation_checks,
        evidence_admissibility_map=evidence_admissibility_map,
        dispute_type=str(brief.get("dispute_type") or ""),
    )
    settlement_strategy = build_settlement_strategy(
        summary=brief,
        fee_scenarios=fee_scenarios,
        readiness_breakdown=readiness_breakdown,
    )
    enforcement_plan = build_enforcement_plan(
        recommended_doc_types=recommended_doc_types,
        ready_for_filing=ready_for_filing,
    )
    cpc_compliance_check = build_cpc_compliance_check(
        source_text=source_text,
        validation_checks=validation_checks,
        party_profile=party_profile,
        evidence_matrix=evidence_matrix,
        generated_documents_count=len(generated_items),
    )
    procedural_document_blueprint = build_procedural_document_blueprint(
        recommended_doc_types=recommended_doc_types,
        cpc_compliance_check=cpc_compliance_check,
        generated_documents_count=len(generated_items),
    )
    deadline_control = build_deadline_control(
        source_text=source_text,
        recommended_doc_types=recommended_doc_types,
        unresolved_questions=unresolved_questions,
        unresolved_review_items=unresolved_review_items,
    )
    court_fee_breakdown = build_court_fee_breakdown(
        financial_snapshot=financial_snapshot,
        fee_scenarios=fee_scenarios,
        validation_checks=validation_checks,
    )
    filing_attachments_register = build_filing_attachments_register(
        generated_documents_count=len(generated_items),
        evidence_matrix=evidence_matrix,
        validation_checks=validation_checks,
        party_profile=party_profile,
    )
    cpc_175_requisites_map = build_cpc_175_requisites_map(
        source_text=source_text,
        summary=brief,
        party_profile=party_profile,
        validation_checks=validation_checks,
    )
    cpc_177_attachments_map = build_cpc_177_attachments_map(
        filing_attachments_register=filing_attachments_register,
        generated_documents_count=len(generated_items),
    )
    prayer_part_audit = build_prayer_part_audit(
        recommended_doc_types=recommended_doc_types,
        remedy_coverage=remedy_coverage,
        fee_scenarios=fee_scenarios,
        generated_documents_count=len(generated_items),
    )
    fact_norm_evidence_chain = build_fact_norm_evidence_chain(
        legal_argument_map=legal_argument_map,
        evidence_matrix=evidence_matrix,
    )
    pre_filing_red_flags = build_pre_filing_red_flags(
        validation_checks=validation_checks,
        procedural_defect_scan=procedural_defect_scan,
        deadline_control=deadline_control,
        cpc_compliance_check=cpc_compliance_check,
    )
    procedural_violation_hypotheses = build_procedural_violation_hypotheses(
        cpc_compliance_check=cpc_compliance_check,
        procedural_defect_scan=procedural_defect_scan,
        pre_filing_red_flags=pre_filing_red_flags,
    )
    text_section_audit = build_text_section_audit(
        procedural_document_blueprint=procedural_document_blueprint,
        generated_documents=generated_items,
    )
    service_plan = build_service_plan(
        party_profile=party_profile,
        filing_attachments_register=filing_attachments_register,
        deadline_control=deadline_control,
    )
    prayer_rewrite_suggestions = build_prayer_rewrite_suggestions(
        prayer_part_audit=prayer_part_audit,
        remedy_coverage=remedy_coverage,
        summary=brief,
    )
    contradiction_hotspots = build_contradiction_hotspots(
        validation_checks=validation_checks,
        consistency_report=consistency_report,
        cpc_175_requisites_map=cpc_175_requisites_map,
    )
    judge_questions_simulation = build_judge_questions_simulation(
        legal_argument_map=legal_argument_map,
        evidence_admissibility_map=evidence_admissibility_map,
        pre_filing_red_flags=pre_filing_red_flags,
    )
    citation_quality_gate = build_citation_quality_gate(
        citation_pack=citation_pack,
        legal_argument_map=legal_argument_map,
        recommended_doc_types=recommended_doc_types,
    )
    filing_decision_card = build_filing_decision_card(
        readiness_breakdown=readiness_breakdown,
        pre_filing_red_flags=pre_filing_red_flags,
        validation_checks=validation_checks,
        unresolved_questions=unresolved_questions,
        unresolved_review_items=unresolved_review_items,
    )
    processual_language_audit = build_processual_language_audit(
        generated_documents=generated_items,
        cpc_175_requisites_map=cpc_175_requisites_map,
    )
    evidence_gap_actions = build_evidence_gap_actions(
        evidence_matrix=evidence_matrix,
        evidence_admissibility_map=evidence_admissibility_map,
    )
    fact_chronology_matrix = build_fact_chronology_matrix(
        source_text=source_text,
        procedural_timeline=procedural_timeline,
        evidence_matrix=evidence_matrix,
    )
    burden_of_proof_map = build_burden_of_proof_map(
        legal_argument_map=legal_argument_map,
        evidence_matrix=evidence_matrix,
        party_profile=party_profile,
    )
    drafting_instructions = build_drafting_instructions(
        recommended_doc_types=recommended_doc_types,
        summary=brief,
        legal_basis=brief.get("legal_basis") or [],
        evidence_matrix=evidence_matrix,
        deadline_control=deadline_control,
    )
    opponent_weakness_map = build_opponent_weakness_map(
        validation_checks=validation_checks,
        contradiction_hotspots=contradiction_hotspots,
        opponent_objections=opponent_objections,
        evidence_admissibility_map=evidence_admissibility_map,
    )
    evidence_collection_plan = build_evidence_collection_plan(
        evidence_matrix=evidence_matrix,
        evidence_gap_actions=evidence_gap_actions,
        deadline_control=deadline_control,
        recommended_doc_types=recommended_doc_types,
    )
    factual_circumstances_blocks = build_factual_circumstances_blocks(
        fact_chronology_matrix=fact_chronology_matrix,
        evidence_matrix=evidence_matrix,
    )
    legal_qualification_blocks = build_legal_qualification_blocks(
        legal_argument_map=legal_argument_map,
        burden_of_proof_map=burden_of_proof_map,
        legal_basis=brief.get("legal_basis") or [],
    )
    counterargument_response_matrix = build_counterargument_response_matrix(
        opponent_objections=opponent_objections,
        opponent_weakness_map=opponent_weakness_map,
        evidence_admissibility_map=evidence_admissibility_map,
    )
    deadline_alert_board = build_deadline_alert_board(deadline_control=deadline_control)
    filing_packet_order = build_filing_packet_order(
        filing_attachments_register=filing_attachments_register,
        generated_documents=generated_items,
    )
    opponent_response_playbook = build_opponent_response_playbook(
        opponent_objections=opponent_objections,
        contradiction_hotspots=contradiction_hotspots,
    )
    limitation_period_card = build_limitation_period_card(
        source_text=source_text,
        procedural_timeline=procedural_timeline,
        validation_checks=validation_checks,
    )
    jurisdiction_challenge_guard = build_jurisdiction_challenge_guard(
        jurisdiction_recommendation=jurisdiction_recommendation,
        party_profile=party_profile,
        cpc_compliance_check=cpc_compliance_check,
    )
    claim_formula_card = build_claim_formula_card(
        fee_scenarios=fee_scenarios,
        court_fee_breakdown=court_fee_breakdown,
        prayer_part_audit=prayer_part_audit,
    )
    prayer_part_variants = build_prayer_part_variants(
        summary=brief,
        claim_formula_card=claim_formula_card,
        remedy_coverage=remedy_coverage,
        recommended_doc_types=recommended_doc_types,
    )
    document_narrative_completeness = build_document_narrative_completeness(
        generated_documents=generated_items,
        text_section_audit=text_section_audit,
        cpc_175_requisites_map=cpc_175_requisites_map,
        drafting_instructions=drafting_instructions,
        factual_circumstances_blocks=factual_circumstances_blocks,
        legal_qualification_blocks=legal_qualification_blocks,
        prayer_part_variants=prayer_part_variants,
    )
    document_fact_enrichment_plan = build_document_fact_enrichment_plan(
        generated_documents=generated_items,
        text_section_audit=text_section_audit,
        document_narrative_completeness=document_narrative_completeness,
        drafting_instructions=drafting_instructions,
    )
    filing_cover_letter = build_filing_cover_letter(
        summary=brief,
        filing_decision_card=filing_decision_card,
        filing_packet_order=filing_packet_order,
    )
    execution_step_tracker = build_execution_step_tracker(
        enforcement_plan=enforcement_plan,
        filing_decision_card=filing_decision_card,
        deadline_alert_board=deadline_alert_board,
    )
    version_control_card = build_document_version_control_card(
        generated_documents=generated_items,
        filing_packet_order=filing_packet_order,
    )
    e_court_packet_readiness = build_e_court_packet_readiness(
        e_court_submission_preview=e_court_submission_preview,
        filing_attachments_register=filing_attachments_register,
        filing_decision_card=filing_decision_card,
    )
    hearing_script_pack = build_hearing_script_pack(
        legal_argument_map=legal_argument_map,
        judge_questions_simulation=judge_questions_simulation,
        citation_pack=citation_pack,
    )
    hearing_positioning_notes = build_hearing_positioning_notes(
        judge_questions_simulation=judge_questions_simulation,
        counterargument_response_matrix=counterargument_response_matrix,
        hearing_script_pack=hearing_script_pack,
    )
    settlement_offer_card = build_settlement_offer_card(
        settlement_strategy=settlement_strategy,
        claim_formula_card=claim_formula_card,
        opponent_response_playbook=opponent_response_playbook,
    )
    appeal_reserve_card = build_appeal_reserve_card(
        recommended_doc_types=recommended_doc_types,
        deadline_control=deadline_control,
        procedural_timeline=procedural_timeline,
    )
    procedural_costs_allocator_card = build_procedural_costs_allocator_card(
        claim_formula_card=claim_formula_card,
        filing_decision_card=filing_decision_card,
        settlement_offer_card=settlement_offer_card,
    )
    document_export_readiness = build_document_export_readiness(
        generated_documents=generated_items,
        text_section_audit=text_section_audit,
        version_control_card=version_control_card,
    )
    filing_submission_checklist_card = build_filing_submission_checklist_card(
        e_court_packet_readiness=e_court_packet_readiness,
        filing_packet_order=filing_packet_order,
        filing_cover_letter=filing_cover_letter,
    )
    post_filing_monitoring_board = build_post_filing_monitoring_board(
        post_filing_plan=post_filing_plan,
        deadline_alert_board=deadline_alert_board,
        execution_step_tracker=execution_step_tracker,
    )
    legal_research_backlog = build_legal_research_backlog(
        citation_quality_gate=citation_quality_gate,
        contradiction_hotspots=contradiction_hotspots,
        judge_questions_simulation=judge_questions_simulation,
    )
    procedural_consistency_scorecard = build_procedural_consistency_scorecard(
        validation_checks=validation_checks,
        text_section_audit=text_section_audit,
        cpc_compliance_check=cpc_compliance_check,
    )
    hearing_evidence_order_card = build_hearing_evidence_order_card(
        evidence_matrix=evidence_matrix,
        fact_norm_evidence_chain=fact_norm_evidence_chain,
    )
    digital_signature_readiness = build_digital_signature_readiness(
        e_court_packet_readiness=e_court_packet_readiness,
        filing_cover_letter=filing_cover_letter,
        document_export_readiness=document_export_readiness,
    )
    case_law_update_watchlist = build_case_law_update_watchlist(
        context_refs=context_refs,
        citation_pack=citation_pack,
    )
    final_submission_gate = build_final_submission_gate(
        filing_decision_card=filing_decision_card,
        e_court_packet_readiness=e_court_packet_readiness,
        digital_signature_readiness=digital_signature_readiness,
        procedural_consistency_scorecard=procedural_consistency_scorecard,
        deadline_control=deadline_control,
        recommended_doc_types=recommended_doc_types,
    )
    process_stage_action_map = build_process_stage_action_map(
        workflow_stages=workflow_stages,
        deadline_control=deadline_control,
        final_submission_gate=final_submission_gate,
    )
    if package_requested and package_gate_passed and generated_items:
        final_hard_stop = bool(final_submission_gate.get("hard_stop"))
        if final_hard_stop:
            if draft_on_hard_stop:
                filing_package = _create_filing_package(
                    db=db,
                    user=user,
                    source_file_name=file_name,
                    recommended_doc_types=recommended_doc_types,
                    generated_items=generated_items,
                    evidence_required=brief.get("evidence_required") or [],
                    financial_snapshot=financial_snapshot,
                    draft_mode=True,
                    case_id=case_id,
                )
                warnings.append("Фінальний гейт подання заблокував бойове подання. Згенеровано чернетковий пакет.")
                for blocker in (final_submission_gate.get("blockers") or [])[:5]:
                    warnings.append(f"Фінальний гейт: {blocker}")
            else:
                warnings.append("Генерацію пакета подання заблоковано фінальним hard-stop гейтом.")
                for blocker in (final_submission_gate.get("blockers") or [])[:5]:
                    warnings.append(f"Фінальний гейт: {blocker}")
                filing_package["status"] = "blocked_final_gate"
                filing_package["reason"] = "Фінальний hard-stop гейт подання заблокував генерацію пакета."
        else:
            filing_package = _create_filing_package(
                db=db,
                user=user,
                source_file_name=file_name,
                recommended_doc_types=recommended_doc_types,
                generated_items=generated_items,
                evidence_required=brief.get("evidence_required") or [],
                financial_snapshot=financial_snapshot,
                case_id=case_id,
            )
    elif package_requested and package_gate_passed and not generated_items:
        filing_package["status"] = "blocked_processual_gate"
        filing_package["reason"] = "Немає згенерованих документів для складання пакета."
    court_behavior_forecast_card = build_court_behavior_forecast_card(
        filing_risk_simulation=filing_risk_simulation,
        judge_questions_simulation=judge_questions_simulation,
        pre_filing_red_flags=pre_filing_red_flags,
    )
    evidence_pack_compression_plan = build_evidence_pack_compression_plan(
        hearing_evidence_order_card=hearing_evidence_order_card,
        evidence_gap_actions=evidence_gap_actions,
    )
    filing_channel_strategy_card = build_filing_channel_strategy_card(
        e_court_packet_readiness=e_court_packet_readiness,
        digital_signature_readiness=digital_signature_readiness,
        filing_submission_checklist_card=filing_submission_checklist_card,
    )
    legal_budget_timeline_card = build_legal_budget_timeline_card(
        claim_formula_card=claim_formula_card,
        settlement_offer_card=settlement_offer_card,
        deadline_control=deadline_control,
    )
    counterparty_pressure_map = build_counterparty_pressure_map(
        opponent_objections=opponent_objections,
        opponent_response_playbook=opponent_response_playbook,
    )
    courtroom_timeline_scenarios = build_courtroom_timeline_scenarios(
        procedural_timeline=procedural_timeline,
        deadline_alert_board=deadline_alert_board,
    )
    evidence_authenticity_checklist = build_evidence_authenticity_checklist(
        evidence_matrix=evidence_matrix,
        evidence_admissibility_map=evidence_admissibility_map,
    )
    remedy_priority_matrix = build_remedy_priority_matrix(
        remedy_coverage=remedy_coverage,
        prayer_part_audit=prayer_part_audit,
    )
    judge_question_drill_card = build_judge_question_drill_card(
        judge_questions_simulation=judge_questions_simulation,
        contradiction_hotspots=contradiction_hotspots,
    )
    client_instruction_packet = build_client_instruction_packet(
        filing_decision_card=filing_decision_card,
        legal_budget_timeline_card=legal_budget_timeline_card,
        next_actions=next_actions,
    )
    procedural_risk_heatmap = build_procedural_risk_heatmap(
        filing_risk_simulation=filing_risk_simulation,
        procedural_defect_scan=procedural_defect_scan,
        pre_filing_red_flags=pre_filing_red_flags,
    )
    evidence_disclosure_plan = build_evidence_disclosure_plan(
        evidence_authenticity_checklist=evidence_authenticity_checklist,
        hearing_evidence_order_card=hearing_evidence_order_card,
    )
    settlement_negotiation_script = build_settlement_negotiation_script(
        settlement_offer_card=settlement_offer_card,
        counterparty_pressure_map=counterparty_pressure_map,
        remedy_priority_matrix=remedy_priority_matrix,
    )
    hearing_readiness_scorecard = build_hearing_readiness_scorecard(
        hearing_script_pack=hearing_script_pack,
        hearing_evidence_order_card=hearing_evidence_order_card,
        judge_question_drill_card=judge_question_drill_card,
    )
    advocate_signoff_packet = build_advocate_signoff_packet(
        final_submission_gate=final_submission_gate,
        filing_decision_card=filing_decision_card,
        procedural_consistency_scorecard=procedural_consistency_scorecard,
        document_export_readiness=document_export_readiness,
    )

    subscription = mark_analysis_processed(db, subscription)
    log_action(
        db,
        user_id=user.user_id,
        action="auto_full_lawyer_upload",
        entity_type="generated_document",
        entity_id=generated_items[0]["id"] if generated_items else None,
        metadata={
            "mode": "full-lawyer",
            "file_name": file_name,
            "content_type": file.content_type,
            "bytes": len(content),
            "extracted_chars": len(source_text),
            "dispute_type": brief.get("dispute_type"),
            "procedure": brief.get("procedure"),
            "urgency": brief.get("urgency"),
            "recommended_doc_types": recommended_doc_types,
            "generated_count": len(generated_items),
            "clarifying_questions_count": len(clarifying_questions),
            "unresolved_questions_count": len(unresolved_questions),
            "review_checklist_count": len(review_checklist),
            "unresolved_review_items_count": len(unresolved_review_items),
            "validation_warn_count": sum(1 for item in validation_checks if item.get("status") == "warn"),
            "generate_package": bool(generate_package),
            "generate_package_draft_on_hard_stop": bool(generate_package_draft_on_hard_stop),
            "filing_package_generated": bool(filing_package.get("generated")),
            "filing_package_status": filing_package.get("status"),
            "filing_package_is_draft": bool(filing_package.get("is_draft")),
            "confidence_score": confidence_score,
            "warnings": warnings,
            "case_law_refs_linked": linked_case_law_total,
            "workflow_stages": [item.get("status") for item in workflow_stages],
            "ready_for_filing": ready_for_filing,
            "readiness_score": readiness_breakdown.get("score"),
            "cpc_warn_count": sum(1 for item in cpc_compliance_check if item.get("status") != "pass"),
            "deadline_control_count": len(deadline_control),
            "attachments_register_count": len(filing_attachments_register),
            "pre_filing_red_flags_count": len(pre_filing_red_flags),
            "text_section_audit_count": len(text_section_audit),
            "judge_questions_count": len(judge_questions_simulation),
            "citation_quality_status": citation_quality_gate.get("status"),
            "filing_decision": filing_decision_card.get("decision"),
            "deadline_alert_count": len(deadline_alert_board),
            "fact_chronology_count": len(fact_chronology_matrix),
            "burden_of_proof_count": len(burden_of_proof_map),
            "drafting_instructions_count": len(drafting_instructions),
            "opponent_weakness_count": len(opponent_weakness_map),
            "evidence_collection_plan_count": len(evidence_collection_plan),
            "factual_circumstances_count": len(factual_circumstances_blocks),
            "legal_qualification_count": len(legal_qualification_blocks),
            "prayer_part_variants_count": len(prayer_part_variants),
            "counterargument_response_count": len(counterargument_response_matrix),
            "document_narrative_completeness_count": len(document_narrative_completeness),
            "case_law_application_matrix_count": len(case_law_application_matrix),
            "procedural_violation_hypotheses_count": len(procedural_violation_hypotheses),
            "document_fact_enrichment_plan_count": len(document_fact_enrichment_plan),
            "hearing_positioning_notes_count": len(hearing_positioning_notes),
            "process_stage_action_map_count": len(process_stage_action_map),
            "packet_order_count": len(filing_packet_order),
            "limitation_status": limitation_period_card.get("status"),
            "jurisdiction_risk_level": jurisdiction_challenge_guard.get("risk_level"),
            "e_court_packet_status": e_court_packet_readiness.get("status"),
            "version_control_status": version_control_card.get("status"),
            "hearing_script_count": len(hearing_script_pack),
            "export_readiness_status": document_export_readiness.get("status"),
            "research_backlog_count": len(legal_research_backlog),
            "consistency_score": procedural_consistency_scorecard.get("score"),
            "signature_readiness_status": digital_signature_readiness.get("status"),
            "final_submission_gate": final_submission_gate.get("status"),
            "filing_channel_status": filing_channel_strategy_card.get("status"),
            "counterparty_pressure_count": len(counterparty_pressure_map),
            "client_instruction_count": len(client_instruction_packet),
            "timeline_scenarios_count": len(courtroom_timeline_scenarios),
            "hearing_readiness_score": hearing_readiness_scorecard.get("score"),
            "advocate_signoff_status": advocate_signoff_packet.get("status"),
            "case_bound_case_number": case_bound_context.get("case_number") or None,
            "case_bound_practice_count": len(case_bound_context.get("recent_practice") or []),
        },
    )

    return FullLawyerResponse(
        status=response_status,
        source_file_name=file_name,
        extracted_chars=len(source_text),
        summary=FullLawyerSummary(
            dispute_type=str(brief.get("dispute_type") or "Загальний цивільний спір"),
            procedure=str(brief.get("procedure") or "civil"),
            urgency=str(brief.get("urgency") or "medium"),
            claim_amount_uah=financial_snapshot.get("principal_uah"),
            estimated_court_fee_uah=financial_snapshot.get("estimated_court_fee_uah"),
            estimated_penalty_uah=financial_snapshot.get("estimated_penalty_uah"),
            estimated_total_with_fee_uah=financial_snapshot.get("estimated_total_with_fee_uah"),
        ),
        legal_basis=brief.get("legal_basis") or [],
        strategy_steps=brief.get("strategy_steps") or [],
        evidence_required=brief.get("evidence_required") or [],
        risks=brief.get("risks") or [],
        missing_information=brief.get("missing_information") or [],
        clarifying_questions=clarifying_questions,
        clarification_required=bool(unresolved_questions),
        unresolved_questions=unresolved_questions,
        next_actions=next_actions,
        validation_checks=validation_checks,
        context_refs=context_refs,
        confidence_score=confidence_score,
        analysis_highlights=analysis_highlights,
        procedural_conclusions=conclusions,
        recommended_doc_types=recommended_doc_types,
        generated_documents=generated_items,
        filing_package=filing_package,
        processual_package_gate=processual_package_gate,
        review_checklist=review_checklist,
        review_required=bool(unresolved_review_items),
        unresolved_review_items=unresolved_review_items,
        workflow_stages=workflow_stages,
        ready_for_filing=ready_for_filing,
        procedural_timeline=procedural_timeline,
        evidence_matrix=evidence_matrix,
        fact_chronology_matrix=fact_chronology_matrix,
        burden_of_proof_map=burden_of_proof_map,
        drafting_instructions=drafting_instructions,
        opponent_weakness_map=opponent_weakness_map,
        evidence_collection_plan=evidence_collection_plan,
        factual_circumstances_blocks=factual_circumstances_blocks,
        legal_qualification_blocks=legal_qualification_blocks,
        prayer_part_variants=prayer_part_variants,
        counterargument_response_matrix=counterargument_response_matrix,
        document_narrative_completeness=document_narrative_completeness,
        case_law_application_matrix=case_law_application_matrix,
        procedural_violation_hypotheses=procedural_violation_hypotheses,
        document_fact_enrichment_plan=document_fact_enrichment_plan,
        hearing_positioning_notes=hearing_positioning_notes,
        process_stage_action_map=process_stage_action_map,
        legal_argument_map=legal_argument_map,
        readiness_breakdown=readiness_breakdown,
        post_filing_plan=post_filing_plan,
        party_profile=party_profile,
        jurisdiction_recommendation=jurisdiction_recommendation,
        generated_docs_quality=generated_docs_quality,
        e_court_submission_preview=e_court_submission_preview,
        priority_queue=priority_queue,
        consistency_report=consistency_report,
        remedy_coverage=remedy_coverage,
        citation_pack=citation_pack,
        fee_scenarios=fee_scenarios,
        filing_risk_simulation=filing_risk_simulation,
        procedural_defect_scan=procedural_defect_scan,
        evidence_admissibility_map=evidence_admissibility_map,
        motion_recommendations=motion_recommendations,
        hearing_preparation_plan=hearing_preparation_plan,
        package_completeness=package_completeness,
        opponent_objections=opponent_objections,
        settlement_strategy=settlement_strategy,
        enforcement_plan=enforcement_plan,
        cpc_compliance_check=cpc_compliance_check,
        procedural_document_blueprint=procedural_document_blueprint,
        deadline_control=deadline_control,
        court_fee_breakdown=court_fee_breakdown,
        filing_attachments_register=filing_attachments_register,
        cpc_175_requisites_map=cpc_175_requisites_map,
        cpc_177_attachments_map=cpc_177_attachments_map,
        prayer_part_audit=prayer_part_audit,
        fact_norm_evidence_chain=fact_norm_evidence_chain,
        pre_filing_red_flags=pre_filing_red_flags,
        text_section_audit=text_section_audit,
        service_plan=service_plan,
        prayer_rewrite_suggestions=prayer_rewrite_suggestions,
        contradiction_hotspots=contradiction_hotspots,
        judge_questions_simulation=judge_questions_simulation,
        citation_quality_gate=citation_quality_gate,
        filing_decision_card=filing_decision_card,
        processual_language_audit=processual_language_audit,
        evidence_gap_actions=evidence_gap_actions,
        deadline_alert_board=deadline_alert_board,
        filing_packet_order=filing_packet_order,
        opponent_response_playbook=opponent_response_playbook,
        limitation_period_card=limitation_period_card,
        jurisdiction_challenge_guard=jurisdiction_challenge_guard,
        claim_formula_card=claim_formula_card,
        filing_cover_letter=filing_cover_letter,
        execution_step_tracker=execution_step_tracker,
        version_control_card=version_control_card,
        e_court_packet_readiness=e_court_packet_readiness,
        hearing_script_pack=hearing_script_pack,
        settlement_offer_card=settlement_offer_card,
        appeal_reserve_card=appeal_reserve_card,
        procedural_costs_allocator_card=procedural_costs_allocator_card,
        document_export_readiness=document_export_readiness,
        filing_submission_checklist_card=filing_submission_checklist_card,
        post_filing_monitoring_board=post_filing_monitoring_board,
        legal_research_backlog=legal_research_backlog,
        procedural_consistency_scorecard=procedural_consistency_scorecard,
        hearing_evidence_order_card=hearing_evidence_order_card,
        digital_signature_readiness=digital_signature_readiness,
        case_law_update_watchlist=case_law_update_watchlist,
        final_submission_gate=final_submission_gate,
        court_behavior_forecast_card=court_behavior_forecast_card,
        evidence_pack_compression_plan=evidence_pack_compression_plan,
        filing_channel_strategy_card=filing_channel_strategy_card,
        legal_budget_timeline_card=legal_budget_timeline_card,
        counterparty_pressure_map=counterparty_pressure_map,
        courtroom_timeline_scenarios=courtroom_timeline_scenarios,
        evidence_authenticity_checklist=evidence_authenticity_checklist,
        remedy_priority_matrix=remedy_priority_matrix,
        judge_question_drill_card=judge_question_drill_card,
        client_instruction_packet=client_instruction_packet,
        procedural_risk_heatmap=procedural_risk_heatmap,
        evidence_disclosure_plan=evidence_disclosure_plan,
        settlement_negotiation_script=settlement_negotiation_script,
        hearing_readiness_scorecard=hearing_readiness_scorecard,
        advocate_signoff_packet=advocate_signoff_packet,
        processual_only_mode=processual_only,
        warnings=warnings,
        usage=to_payload(subscription),
    )

