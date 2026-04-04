from __future__ import annotations

import csv
from datetime import date
import difflib
import json
from io import BytesIO, StringIO
import re
from typing import Any
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.catalog import DOCUMENT_TYPES, get_document_type, get_form_schema
from app.database import get_db
from app.schemas import (
    DocumentBulkProcessualRepairRequest,
    DocumentBulkProcessualRepairResponse,
    DocumentBulkDeleteRequest,
    DocumentBulkDeleteResponse,
    DocumentCloneResponse,
    DocumentDetailResponse,
    DocumentProcessualCheckResponse,
    DocumentProcessualRepairResponse,
    DocumentDeleteResponse,
    DocumentVersionDetailResponse,
    DocumentVersionDiffResponse,
    DocumentRestoreResponse,
    DocumentsHistoryResponse,
    DocumentUpdateRequest,
    DocumentUpdateResponse,
    DocumentVersionsResponse,
    GenerateResponse,
    GenerateRequest,
    GenerateBundleResponse,
    CaseLawRefItem,
)
from app.services.audit import log_action, log_analytics_event
from app.services.ai_generator import generate_legal_document_for_role
from app.services.agentic_generation import (
    is_rate_limited_error,
    run_case_law_rerank_agent,
    run_intake_agent,
)
from app.services.case_law_enricher import (
    attach_case_law_refs_to_document,
    build_case_law_prompt_context,
    build_motivation_reference_block,
    clone_case_law_refs,
    enrich_document_with_case_law,
    inject_motivation_references,
)
from app.services.case_law_cache import get_case_law_digest
from app.services.case_law_digests import get_case_law_digest_by_id
from app.services.calculators import calculate_court_fee, calculate_penalty
from app.services.document_export import render_docx_bytes, render_pdf_bytes, sanitize_filename
from app.services.document_storage import (
    build_export_rel_path,
    delete_export_file,
    read_export_bytes,
    write_export_bytes,
)
from app.services.generated_documents import (
    create_generated_document,
    delete_generated_document,
    get_document_form_data,
    get_document_generated_text,
    get_document_preview_text,
    get_generated_document,
    get_generated_documents_by_ids,
    list_generated_documents,
    set_document_export_path,
    update_generated_document_text,
)
from app.services.document_versions import (
    create_document_version,
    get_document_version,
    get_version_generated_text,
    list_document_versions,
)
from app.services.court_submissions import evaluate_document_filing_readiness
from app.services.auto_processor import auto_repair_form_data_for_generation
from app.services.ai_generator import SYSTEM_PROMPT
from app.services.realtime import publish_user_event
from app.services.prompt_builder import (
    build_generation_validation_checks,
    build_pre_generation_gate_checks,
    build_preview_text,
    build_processual_validation_checks,
    build_user_prompt,
    sanitize_prompt_context,
    has_blocking_pre_generation_issues,
    normalize_prayer_section,
    ensure_processual_quality,
)
from app.services.subscriptions import (
    ensure_document_quota,
    get_or_create_subscription,
    mark_document_generated,
    to_payload,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _form_data_to_source_text(form_data: dict[str, Any]) -> str:
    rows: list[str] = []
    for key, value in (form_data or {}).items():
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            if cleaned:
                rows.append(f"{key}: {'; '.join(cleaned[:8])}")
            continue
        text = str(value or "").strip()
        if text:
            rows.append(f"{key}: {text}")
    return "\n".join(rows)


def _build_digest_prompt_context(rows: list[Any]) -> str:
    if not rows:
        return ""
    lines = ["Use these digest decisions as additional legal context and cite relevant ones directly:"]
    for index, row in enumerate(rows, start=1):
        case_ref = row.case_number or row.decision_id
        court = row.court_name or row.court_type or "Court not specified"
        date_text = row.decision_date.isoformat() if row.decision_date else "n/a"
        summary = (row.summary or "").strip()
        line = f"{index}. [{row.source}] case {case_ref}, {court}, date {date_text}"
        if summary:
            line += f". Summary: {summary[:260]}"
        lines.append(line)
    return "\n".join(lines)


def _build_saved_digest_prompt_context(digest: Any) -> str:
    prompt_text = (getattr(digest, "prompt_text", None) or "").strip()
    if prompt_text:
        return f"Use this saved case-law digest as additional legal context:\n{prompt_text}"

    items = getattr(digest, "items", None) or []
    if not items:
        return ""

    lines = ["Use this saved case-law digest as additional legal context:"]
    for index, item in enumerate(items, start=1):
        snippet = (getattr(item, "prompt_snippet", None) or "").strip()
        if not snippet:
            continue
        lines.append(f"{index}. {snippet}")
    return "\n".join(lines)


def _seed_welcome_document(db: Session, user_id: str):
    from app.services.generated_documents import create_generated_document
    create_generated_document(
        db,
        user_id=user_id,
        document_type="Вітальний документ",
        document_category="Довідка",
        form_data={"purpose": "Onboarding"},
        generated_text="Вітаємо у Legal AI Platform!\n\nЦе ваш персональний архів юридичних документів. Тут зберігатимуться всі ваші позови, клопотання та напрацювання. \n\nВи можете:\n1. Редагувати тексти за допомогою нашого інтелектуального редактора.\n2. Експортувати їх у DOCX або PDF для подання до суду.\n3. Створювати копії (клонувати) для нових справ.\n4. Подавати документи безпосередньо до Е-Суду (якщо доступно).\n\nПочніть зі створення вашого першого документа в розділі 'Генератор'.",
        preview_text="Вітаємо у Legal AI Platform! Це ваш персональний архів юридичних документів...",
        calculations={},
        ai_model="Internal Onboarding",
        used_ai=True,
        ai_error=None
    )


def _serialize_history_item(row: Any) -> dict[str, Any]:
    from app.catalog import get_document_type

    readiness = evaluate_document_filing_readiness(row)
    doc_meta = get_document_type(row.document_type)
    return {
        "id": row.id,
        "title": doc_meta.title if doc_meta else row.document_type,
        "document_type": row.document_type,
        "document_category": row.document_category,
        "case_id": row.case_id,
        "generated_text": get_document_generated_text(row),
        "preview_text": get_document_preview_text(row),
        "ai_model": row.ai_model,
        "used_ai": row.used_ai,
        "has_docx_export": bool(row.docx_storage_path),
        "has_pdf_export": bool(row.pdf_storage_path),
        "last_exported_at": row.last_exported_at.isoformat() if row.last_exported_at else None,
        "e_court_ready": bool(readiness.get("ready_for_filing")),
        "filing_blockers": list(readiness.get("filing_blockers") or []),
        "created_at": row.created_at.isoformat(),
    }


def _load_history_rows_for_export(
    db: Session,
    *,
    user_id: str,
    query: str | None,
    doc_type: str | None,
    has_docx_export: bool | None,
    has_pdf_export: bool | None,
    sort_by: str,
    sort_dir: str,
    max_rows: int = 2000,
) -> list[Any]:
    rows: list[Any] = []
    page = 1
    page_size = 100
    while len(rows) < max_rows:
        batch, _, current_page, pages = list_generated_documents(
            db,
            user_id,
            page=page,
            page_size=page_size,
            query=query,
            doc_type=doc_type,
            has_docx_export=has_docx_export,
            has_pdf_export=has_pdf_export,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        if not batch:
            break
        rows.extend(batch)
        if current_page >= pages:
            break
        page = current_page + 1
    return rows[:max_rows]


def _build_history_csv(rows: list[Any]) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "document_type",
            "document_category",
            "created_at",
            "used_ai",
            "ai_model",
            "has_docx_export",
            "has_pdf_export",
            "last_exported_at",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.document_type,
                row.document_category,
                row.created_at.isoformat(),
                "yes" if row.used_ai else "no",
                row.ai_model or "",
                "yes" if row.docx_storage_path else "no",
                "yes" if row.pdf_storage_path else "no",
                row.last_exported_at.isoformat() if row.last_exported_at else "",
            ]
        )
    return output.getvalue()


def _build_history_zip(rows: list[Any]) -> bytes:
    csv_text = _build_history_csv(rows)
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("history.csv", csv_text)
        for row in rows:
            safe_name = sanitize_filename(f"{row.document_type}-{row.id}.txt")
            archive.writestr(
                f"documents/{safe_name}",
                get_document_generated_text(row) or get_document_preview_text(row) or "",
            )
    return output.getvalue()


def _build_processual_report_text(row: Any, *, checks: list[dict[str, str]], gate_checks: list[dict[str, str]]) -> str:
    generated_text = get_document_generated_text(row)
    preview_text = get_document_preview_text(row)
    lines: list[str] = [
        "PROCESSUAL VALIDATION REPORT",
        "",
        f"Document ID: {row.id}",
        f"Document type: {row.document_type}",
        f"Category: {row.document_category}",
        f"Created at: {row.created_at.isoformat()}",
        f"AI used: {'yes' if row.used_ai else 'no'}",
        f"AI model: {row.ai_model or 'n/a'}",
        f"Quality guard fallback: {'yes' if generated_text.strip() == preview_text.strip() else 'no'}",
        "",
        "PRE-GENERATION GATE",
    ]
    if gate_checks:
        for item in gate_checks:
            lines.append(f"- [{item.get('status')}] {item.get('code')}: {item.get('message')}")
    else:
        lines.append("- No gate checks configured for this document type.")
    lines.extend(["", "DOCUMENT STRUCTURE VALIDATION"])
    if checks:
        for item in checks:
            lines.append(f"- [{item.get('status')}] {item.get('code')}: {item.get('message')}")
        failed = sum(1 for item in checks if item.get("status") != "pass")
        lines.append("")
        lines.append(f"Summary: {len(checks) - failed}/{len(checks)} checks passed.")
    else:
        lines.append("- No processual structure checks configured for this document type.")

    return "\n".join(lines).strip()


async def _evaluate_processual_state(
    *,
    document_type: str,
    form_data: dict[str, Any],
    generated_text: str,
) -> dict[str, Any]:
    pre_generation_gate_checks = build_pre_generation_gate_checks(document_type, form_data)
    processual_validation_checks = await build_generation_validation_checks(
        document_type, generated_text, form_data=form_data
    )

    blockers: list[str] = []
    for item in pre_generation_gate_checks:
        if item.get("status") == "fail":
            blockers.append(f"Gate failure: {item.get('code')}")
    for item in processual_validation_checks:
        if item.get("status") != "pass":
            blockers.append(f"Validation failure: {item.get('code')}")

    deduped: list[str] = []
    seen: set[str] = set()
    for item in blockers:
        key = str(item).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(key)

    return {
        "is_valid": len(deduped) == 0,
        "blockers": deduped,
        "pre_generation_gate_checks": pre_generation_gate_checks,
        "processual_validation_checks": processual_validation_checks,
    }


@router.get("/types")
def list_document_types() -> dict[str, Any]:
    return {"items": [item.__dict__ for item in DOCUMENT_TYPES]}


# Безпечний патерн для doc_type (тільки a-z, _, максимум 50 символів)
SAFE_DOC_TYPE_RE = re.compile(r"^[a-z_]{1,50}$")


@router.get("/form/{doc_type}")
def document_form_schema(doc_type: str) -> dict[str, Any]:
    if not SAFE_DOC_TYPE_RE.match(doc_type):
        raise HTTPException(status_code=400, detail="Invalid document type format")
    document = get_document_type(doc_type)
    if document is None:
        raise HTTPException(status_code=404, detail="Document type not found")
    return {"doc_type": doc_type, "schema": list(get_form_schema(doc_type))}



async def _generate_one(
    db: Session,
    user: CurrentUser,
    payload: GenerateRequest,
    doc_type: str,
) -> GenerateResponse:
    from app.services.prompt_builder import build_user_prompt
    from app.catalog import get_document_type
    from app.models.knowledge_base import KnowledgeBaseEntry

    document = get_document_type(doc_type)
    if not document:
        raise HTTPException(status_code=404, detail=f"Document type {doc_type} not found")

    form_data = payload.form_data
    calculations: dict[str, Any] = {}

    # Simplified gate checks for bundle items or single doc
    pre_generation_gate_checks = build_pre_generation_gate_checks(doc_type, form_data)
    
    source_text_for_intake = _form_data_to_source_text(form_data)
    intake_payload, intake_ai = await run_intake_agent(
        doc_type=doc_type,
        title=document.title,
        source_text=source_text_for_intake,
        form_data=form_data,
    )

    case_law_refs = enrich_document_with_case_law(db, document_type=doc_type, form_data=form_data, limit=5)
    if case_law_refs and not is_rate_limited_error(getattr(intake_ai, "error", "")):
        rerank_candidates = [
            {
                "id": str(item.id),
                "decision_id": item.decision_id,
                "case_number": item.case_number,
                "court_name": item.court_name,
                "court_type": item.court_type,
                "decision_date": (
                    item.decision_date.isoformat()
                    if item.decision_date and hasattr(item.decision_date, "isoformat")
                    else (str(item.decision_date) if item.decision_date else None)
                ),
                "summary": item.summary,
                "subject_categories": item.subject_categories or [],
            }
            for item in case_law_refs
        ]
        selected_ids, _ = await run_case_law_rerank_agent(
            intake=intake_payload,
            candidates=rerank_candidates,
            limit=min(5, len(rerank_candidates)),
        )
        if selected_ids:
            by_id = {str(item.id): item for item in case_law_refs}
            selected_set = {str(item_id) for item_id in selected_ids}
            prioritized = [by_id[item_id] for item_id in selected_ids if item_id in by_id]
            tail = [item for item in case_law_refs if str(item.id) not in selected_set]
            case_law_refs = prioritized + tail
    
    precedents: list[KnowledgeBaseEntry] = []
    if payload.precedent_ids:
        precedents = db.query(KnowledgeBaseEntry).filter(
            KnowledgeBaseEntry.id.in_(payload.precedent_ids),
            KnowledgeBaseEntry.user_id == user.user_id
        ).all()

    prompt_user = build_user_prompt(
        document.title,
        form_data,
        doc_type=doc_type,
        deep=(payload.mode == "deep"),
        style=payload.style,
        precedents=precedents
    )

    case_law_context = sanitize_prompt_context(build_case_law_prompt_context(case_law_refs))
    motivation_refs_context = sanitize_prompt_context(build_motivation_reference_block(doc_type, case_law_refs))

    context_blocks = [c for c in [case_law_context, motivation_refs_context] if c]
    if context_blocks:
        prompt_user = f"{prompt_user}\n\n" + "\n\n".join(context_blocks)

    ai_result = await generate_legal_document_for_role(
        "draft",
        prompt_user,
        deep=(payload.mode == "deep")
    )

    preview_text = build_preview_text(document.title, form_data, doc_type=doc_type)
    draft_text = ai_result.text or preview_text
    generated_text = ensure_processual_quality(doc_type, draft_text, preview_text)
    generated_text = normalize_prayer_section(doc_type, generated_text)
    quality_guard_applied = bool(draft_text.strip()) and generated_text.strip() == preview_text.strip() and draft_text.strip() != preview_text.strip()

    saved_doc = create_generated_document(
        db,
        user_id=user.user_id,
        document_type=document.doc_type,
        document_category=document.category,
        form_data=form_data,
        generated_text=generated_text,
        preview_text=preview_text,
        calculations=calculations,
        ai_model=ai_result.model,
        used_ai=ai_result.used_ai,
        ai_error=ai_result.error,
        case_id=payload.case_id,
    )
    attach_case_law_refs_to_document(db, document_id=saved_doc.id, case_law_refs=case_law_refs)
    create_document_version(db, document=saved_doc, action="generate")

    validation_checks = await build_generation_validation_checks(
        doc_type, generated_text, form_data=form_data, preview_text=preview_text
    )

    return GenerateResponse(
        document_id=saved_doc.id,
        created_at=saved_doc.created_at.isoformat(),
        doc_type=saved_doc.document_type,
        title=document.title,
        prompt_system="role:draft",
        prompt_user=prompt_user,
        case_id=saved_doc.case_id,
        generated_text=saved_doc.generated_text,
        preview_text=saved_doc.preview_text,
        calculations=saved_doc.calculations or {},
        ai_model=str(saved_doc.ai_model or ""),
        used_ai=bool(saved_doc.used_ai),
        ai_error=str(saved_doc.ai_error or ""),
        quality_guard_applied=quality_guard_applied,
        pre_generation_gate_checks=pre_generation_gate_checks,
        processual_validation_checks=validation_checks,
        case_law_refs=[
            CaseLawRefItem(
                id=str(item.id),
                source=item.source,
                decision_id=item.decision_id,
                case_number=item.case_number,
                court_type=item.court_type,
                decision_date=(
                    item.decision_date.isoformat()
                    if item.decision_date and hasattr(item.decision_date, "isoformat")
                    else (str(item.decision_date) if item.decision_date else None)
                ),
                summary=item.summary,
                court_name=item.court_name,
                relevance_score=item.relevance_score
            ) for item in case_law_refs
        ],
        usage=to_payload(get_or_create_subscription(db, user))
    )

@router.post("/generate", response_model=GenerateResponse | GenerateBundleResponse)
async def generate_document(
    payload: GenerateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> GenerateResponse | GenerateBundleResponse:
    from app.services.subscriptions import get_or_create_subscription, ensure_document_quota, mark_document_generated

    subscription = get_or_create_subscription(db, user)
    quota_ok, quota_message = ensure_document_quota(subscription)
    if not quota_ok:
        raise HTTPException(status_code=402, detail=quota_message)

    if payload.bundle_doc_types:
        # Preflight check for package generation
        from app.routers.auto_process import _compute_full_lawyer_preflight_state
        preflight_state = await _compute_full_lawyer_preflight_state(payload.prompt, payload.prompt, "package")
        unresolved_questions = preflight_state.get("unresolved_questions") or []
        unresolved_review_items = preflight_state.get("unresolved_review_items") or []
        if unresolved_questions or unresolved_review_items:
            raise HTTPException(
                status_code=400,
                detail="Preflight check failed: unresolved questions or review items. Please resolve before generating package."
            )

        from uuid import uuid4
        bundle_id = str(uuid4())
        items = []
        for dtype in payload.bundle_doc_types:
            items.append(await _generate_one(db, user, payload, dtype))
        
        mark_document_generated(db, subscription)
        publish_user_event(
            user.user_id,
            "generation.bundle_completed",
            {
                "bundle_id": bundle_id,
                "count": len(items),
                "doc_types": [item.doc_type for item in items],
            },
        )
        
        return GenerateBundleResponse(
            bundle_id=bundle_id,
            items=items,
            total_count=len(items),
            created_at=str(date.today())
        )

    # Single doc logic
    res = await _generate_one(db, user, payload, payload.doc_type)
    mark_document_generated(db, subscription)
    publish_user_event(
        user.user_id,
        "generation.document_completed",
        {
            "document_id": res.document_id,
            "doc_type": res.doc_type,
        },
    )
    log_analytics_event(
        db,
        user_id=user.user_id,
        event_type="completion",
        metadata={"doc_type": res.doc_type, "document_id": res.document_id},
    )
    return res


@router.get("/history", response_model=DocumentsHistoryResponse)
def documents_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    query: str | None = Query(default=None),
    doc_type: str | None = Query(default=None),
    case_id: str | None = Query(default=None),
    has_docx_export: bool | None = Query(default=None),
    has_pdf_export: bool | None = Query(default=None),
    sort_by: str = Query(default="created_at", pattern="^(created_at|document_type|document_category)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentsHistoryResponse:
    subscription = get_or_create_subscription(db, user)
    rows, total, normalized_page, pages = list_generated_documents(
        db,
        user.user_id,
        page=page,
        page_size=page_size,
        query=query,
        doc_type=doc_type,
        case_id=case_id,
        has_docx_export=has_docx_export,
        has_pdf_export=has_pdf_export,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    
    # If entirely empty archive, seed a "Welcome" document for better onboarding
    if not rows and page == 1 and not query and not doc_type and not case_id:
         _seed_welcome_document(db, user.user_id)
         # Re-list
         rows, total, normalized_page, pages = list_generated_documents(
            db, user.user_id, page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir
         )

    items = [_serialize_history_item(row) for row in rows]
    return DocumentsHistoryResponse(
        user_id=user.user_id,
        total=total,
        page=normalized_page,
        page_size=page_size,
        pages=pages,
        sort_by=sort_by,
        sort_dir=sort_dir,
        query=(query or "").strip() or None,
        doc_type=(doc_type or "").strip() or None,
        has_docx_export=has_docx_export,
        has_pdf_export=has_pdf_export,
        items=items,
        usage=to_payload(subscription),
    )


@router.get("/history/export")
def export_documents_history(
    format: str = Query(default="csv", pattern="^(csv|zip)$"),
    query: str | None = Query(default=None),
    doc_type: str | None = Query(default=None),
    has_docx_export: bool | None = Query(default=None),
    has_pdf_export: bool | None = Query(default=None),
    sort_by: str = Query(default="created_at", pattern="^(created_at|document_type|document_category)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    rows = _load_history_rows_for_export(
        db,
        user_id=user.user_id,
        query=query,
        doc_type=doc_type,
        has_docx_export=has_docx_export,
        has_pdf_export=has_pdf_export,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    if format == "zip":
        content = _build_history_zip(rows)
        media_type = "application/zip"
        extension = "zip"
    else:
        content = _build_history_csv(rows).encode("utf-8-sig")
        media_type = "text/csv; charset=utf-8"
        extension = "csv"

    filename = sanitize_filename(f"documents-history-{user.user_id}.{extension}")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type=media_type, headers=headers)


@router.post("/bulk-delete", response_model=DocumentBulkDeleteResponse)
def bulk_delete_documents(
    payload: DocumentBulkDeleteRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentBulkDeleteResponse:
    requested_ids: list[str] = []
    seen: set[str] = set()
    for raw in payload.ids:
        item = str(raw).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        requested_ids.append(item)
    if not requested_ids:
        raise HTTPException(status_code=422, detail="ids must contain at least one non-empty id")

    rows = get_generated_documents_by_ids(db, user_id=user.user_id, ids=requested_ids)
    row_by_id = {row.id: row for row in rows}

    deleted_ids: list[str] = []
    missing_ids: list[str] = []
    file_paths: list[str | None] = []
    for document_id in requested_ids:
        row = row_by_id.get(document_id)
        if row is None:
            missing_ids.append(document_id)
            continue
        file_paths.extend([row.docx_storage_path, row.pdf_storage_path])
        db.delete(row)
        deleted_ids.append(document_id)

    if deleted_ids:
        db.commit()
        for path in file_paths:
            try:
                delete_export_file(path)
            except Exception:
                pass
        log_action(
            db,
            user_id=user.user_id,
            action="document_bulk_delete",
            entity_type="generated_document",
            entity_id=None,
            metadata={
                "requested": len(requested_ids),
                "deleted": len(deleted_ids),
                "missing": len(missing_ids),
                "deleted_ids": deleted_ids[:100],
            },
        )

    return DocumentBulkDeleteResponse(
        status="completed",
        requested=len(requested_ids),
        deleted=len(deleted_ids),
        deleted_ids=deleted_ids,
        missing_ids=missing_ids,
    )


@router.post("/bulk-processual-repair", response_model=DocumentBulkProcessualRepairResponse)
async def bulk_processual_repair_documents(
    payload: DocumentBulkProcessualRepairRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentBulkProcessualRepairResponse:
    ids = list(dict.fromkeys([item.strip() for item in payload.ids if item.strip()]))
    rows = get_generated_documents_by_ids(db, user_id=user.user_id, ids=ids)
    by_id = {row.id: row for row in rows}
    missing_ids = [item for item in ids if item not in by_id]

    items: list[dict[str, Any]] = []
    repaired_count = 0

    for document_id in ids:
        row = by_id.get(document_id)
        if row is None:
            continue

        doc_meta = get_document_type(row.document_type)
        doc_title = doc_meta.title if doc_meta is not None else row.document_type
        row_form_data = get_document_form_data(row)
        row_generated_text = get_document_generated_text(row)
        preview_text = build_preview_text(doc_title, row_form_data, doc_type=row.document_type)
        repaired_text = normalize_prayer_section(row.document_type, row_generated_text or "")
        repaired_text = ensure_processual_quality(row.document_type, repaired_text, preview_text)
        changed = repaired_text.strip() != row_generated_text.strip()

        target_row = row
        if changed:
            try:
                delete_export_file(row.docx_storage_path)
                delete_export_file(row.pdf_storage_path)
            except Exception:
                pass
            target_row = update_generated_document_text(db, document=row, generated_text=repaired_text)
            create_document_version(db, document=target_row, action="repair_processual_bulk")
            repaired_count += 1

        state = await _evaluate_processual_state(
            document_type=target_row.document_type,
            form_data=get_document_form_data(target_row),
            generated_text=get_document_generated_text(target_row),
        )
        items.append(
            {
                "id": target_row.id,
                "status": "repaired" if changed else "checked",
                "repaired": changed,
                "is_valid": bool(state["is_valid"]),
                "blockers": list(state["blockers"]),
            }
        )

    log_action(
        db,
        user_id=user.user_id,
        action="document_bulk_processual_repair",
        entity_type="generated_document",
        entity_id=None,
        metadata={
            "requested": len(ids),
            "processed": len(items),
            "repaired": repaired_count,
            "missing_ids": missing_ids,
        },
    )
    return DocumentBulkProcessualRepairResponse(
        status="completed",
        requested=len(ids),
        processed=len(items),
        repaired=repaired_count,
        missing_ids=missing_ids,
        items=items,
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document_detail(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDetailResponse:
    row = get_generated_document(db, user.user_id, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    readiness = evaluate_document_filing_readiness(row)

    return DocumentDetailResponse(
        id=row.id,
        document_type=row.document_type,
        document_category=row.document_category,
        form_data=get_document_form_data(row),
        generated_text=get_document_generated_text(row),
        preview_text=get_document_preview_text(row),
        calculations=row.calculations or {},
        ai_model=row.ai_model,
        used_ai=bool(row.used_ai),
        ai_error=row.ai_error,
        has_docx_export=bool(row.docx_storage_path),
        has_pdf_export=bool(row.pdf_storage_path),
        last_exported_at=row.last_exported_at.isoformat() if row.last_exported_at else None,
        e_court_ready=bool(readiness.get("ready_for_filing")),
        filing_blockers=list(readiness.get("filing_blockers") or []),
        created_at=row.created_at.isoformat(),
    )


@router.get("/{document_id}/processual-check", response_model=DocumentProcessualCheckResponse)
async def check_document_processual_state(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentProcessualCheckResponse:
    row = get_generated_document(db, user.user_id, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    state = await _evaluate_processual_state(
        document_type=row.document_type,
        form_data=get_document_form_data(row),
        generated_text=get_document_generated_text(row),
    )
    return DocumentProcessualCheckResponse(
        status="ok",
        id=row.id,
        is_valid=bool(state["is_valid"]),
        blockers=list(state["blockers"]),
        pre_generation_gate_checks=state["pre_generation_gate_checks"],
        processual_validation_checks=state["processual_validation_checks"],
    )


@router.get("/{document_id}/versions", response_model=DocumentVersionsResponse)
def get_document_versions(
    document_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentVersionsResponse:
    row = get_generated_document(db, user.user_id, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    versions, total, normalized_page, pages = list_document_versions(
        db,
        user_id=user.user_id,
        document_id=document_id,
        page=page,
        page_size=page_size,
    )
    return DocumentVersionsResponse(
        document_id=document_id,
        total=total,
        page=normalized_page,
        page_size=page_size,
        pages=pages,
        items=[
            {
                "id": item.id,
                "document_id": item.document_id,
                "version_number": item.version_number,
                "action": item.action,
                "created_at": item.created_at.isoformat(),
            }
            for item in versions
        ],
    )


@router.get("/{document_id}/versions/{version_id}", response_model=DocumentVersionDetailResponse)
def get_document_version_detail(
    document_id: str,
    version_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentVersionDetailResponse:
    row = get_generated_document(db, user.user_id, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    version = get_document_version(
        db,
        user_id=user.user_id,
        document_id=document_id,
        version_id=version_id,
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    return DocumentVersionDetailResponse(
        id=version.id,
        document_id=version.document_id,
        version_number=version.version_number,
        action=version.action,
        generated_text=get_version_generated_text(version),
        created_at=version.created_at.isoformat(),
    )


@router.get("/{document_id}/versions/{version_id}/diff", response_model=DocumentVersionDiffResponse)
def get_document_version_diff(
    document_id: str,
    version_id: str,
    against: str = Query(default="current"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentVersionDiffResponse:
    row = get_generated_document(db, user.user_id, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    target = get_document_version(
        db,
        user_id=user.user_id,
        document_id=document_id,
        version_id=version_id,
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Version not found")

    against_raw = (against or "current").strip() or "current"
    if against_raw == "current":
        against_text = get_document_generated_text(row)
        against_label = "current"
        against_version_number: int | None = None
    else:
        against_version = get_document_version(
            db,
            user_id=user.user_id,
            document_id=document_id,
            version_id=against_raw,
        )
        if against_version is None:
            raise HTTPException(status_code=404, detail="Against version not found")
        against_text = get_version_generated_text(against_version)
        against_label = against_version.id
        against_version_number = against_version.version_number
    diff_lines = list(
        difflib.unified_diff(
            against_text.splitlines(),
            get_version_generated_text(target).splitlines(),
            fromfile="against",
            tofile=f"version_{target.version_number}",
            lineterm="",
        )
    )
    added_lines = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed_lines = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    diff_text = "\n".join(diff_lines) if diff_lines else "No differences."

    return DocumentVersionDiffResponse(
        document_id=document_id,
        target_version_id=target.id,
        target_version_number=target.version_number,
        against=against_label,
        against_version_number=against_version_number,
        diff_text=diff_text,
        added_lines=added_lines,
        removed_lines=removed_lines,
    )


@router.patch("/{document_id}", response_model=DocumentUpdateResponse)
def update_document(
    document_id: str,
    payload: DocumentUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentUpdateResponse:
    cleaned_text = payload.generated_text.strip()
    if not cleaned_text:
        raise HTTPException(status_code=422, detail="generated_text must not be empty")

    row = get_generated_document(db, user.user_id, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        delete_export_file(row.docx_storage_path)
        delete_export_file(row.pdf_storage_path)
    except Exception:
        pass

    updated = update_generated_document_text(db, document=row, generated_text=cleaned_text)
    if payload.case_id is not None:
        updated.case_id = payload.case_id or None
        db.add(updated)
        db.commit()
        db.refresh(updated)
    create_document_version(db, document=updated, action="update")
    log_action(
        db,
        user_id=user.user_id,
        action="document_update",
        entity_type="generated_document",
        entity_id=updated.id,
        metadata={"document_type": updated.document_type},
    )
    return DocumentUpdateResponse(
        status="updated",
        id=updated.id,
        has_docx_export=bool(updated.docx_storage_path),
        has_pdf_export=bool(updated.pdf_storage_path),
    )


@router.post("/{document_id}/processual-repair", response_model=DocumentProcessualRepairResponse)
async def repair_processual_document(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentProcessualRepairResponse:
    row = get_generated_document(db, user.user_id, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_meta = get_document_type(row.document_type)
    doc_title = doc_meta.title if doc_meta is not None else row.document_type
    row_form_data = get_document_form_data(row)
    row_generated_text = get_document_generated_text(row)
    preview_text = build_preview_text(doc_title, row_form_data, doc_type=row.document_type)
    repaired_text = normalize_prayer_section(row.document_type, row_generated_text or "")
    repaired_text = ensure_processual_quality(row.document_type, repaired_text, preview_text)

    state = await _evaluate_processual_state(
        document_type=row.document_type,
        form_data=row_form_data,
        generated_text=repaired_text,
    )
    pre_generation_gate_checks = state["pre_generation_gate_checks"]
    processual_validation_checks = state["processual_validation_checks"]
    changed = repaired_text.strip() != row_generated_text.strip()

    target_row = row
    if changed:
        try:
            delete_export_file(row.docx_storage_path)
            delete_export_file(row.pdf_storage_path)
        except Exception:
            pass
        target_row = update_generated_document_text(db, document=row, generated_text=repaired_text)
        create_document_version(db, document=target_row, action="repair_processual")

    log_action(
        db,
        user_id=user.user_id,
        action="document_processual_repair",
        entity_type="generated_document",
        entity_id=target_row.id,
        metadata={
            "document_type": target_row.document_type,
            "changed": changed,
            "validation_failures": sum(1 for item in processual_validation_checks if item.get("status") != "pass"),
        },
    )
    return DocumentProcessualRepairResponse(
        status="repaired" if changed else "already_compliant",
        id=target_row.id,
        repaired=changed,
        has_docx_export=bool(target_row.docx_storage_path),
        has_pdf_export=bool(target_row.pdf_storage_path),
        pre_generation_gate_checks=pre_generation_gate_checks,
        processual_validation_checks=processual_validation_checks,
    )


@router.post("/{document_id}/versions/{version_id}/restore", response_model=DocumentRestoreResponse)
def restore_document_version(
    document_id: str,
    version_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentRestoreResponse:
    row = get_generated_document(db, user.user_id, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    version = get_document_version(
        db,
        user_id=user.user_id,
        document_id=document_id,
        version_id=version_id,
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    try:
        delete_export_file(row.docx_storage_path)
        delete_export_file(row.pdf_storage_path)
    except Exception:
        pass

    create_document_version(
        db,
        document=row,
        action="snapshot_before_restore",
        generated_text=get_document_generated_text(row),
    )
    updated = update_generated_document_text(db, document=row, generated_text=get_version_generated_text(version))
    restored_version = create_document_version(db, document=updated, action="restore")
    restored_version_number = restored_version.version_number

    log_action(
        db,
        user_id=user.user_id,
        action="document_restore_version",
        entity_type="generated_document",
        entity_id=updated.id,
        metadata={
            "restored_from_version_id": version.id,
            "restored_from_version_number": version.version_number,
            "restored_to_version_number": restored_version_number,
        },
    )
    return DocumentRestoreResponse(
        status="restored",
        id=updated.id,
        restored_from_version_id=version.id,
        restored_to_version_number=restored_version_number,
        has_docx_export=bool(updated.docx_storage_path),
        has_pdf_export=bool(updated.pdf_storage_path),
    )


@router.post("/{document_id}/clone", response_model=DocumentCloneResponse)
def clone_document(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentCloneResponse:
    source = get_generated_document(db, user.user_id, document_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Document not found")

    subscription = get_or_create_subscription(db, user)
    quota_ok, quota_message = ensure_document_quota(subscription)
    if not quota_ok:
        raise HTTPException(status_code=402, detail=quota_message)

    clone = create_generated_document(
        db,
        user_id=user.user_id,
        document_type=source.document_type,
        document_category=source.document_category,
        form_data=get_document_form_data(source),
        generated_text=get_document_generated_text(source),
        preview_text=get_document_preview_text(source),
        calculations=source.calculations or {},
        ai_model=source.ai_model,
        used_ai=source.used_ai,
        ai_error=source.ai_error,
    )
    create_document_version(db, document=clone, action="clone")
    linked_case_law_count = 0
    try:
        linked_case_law_count = clone_case_law_refs(
            db,
            source_document_id=source.id,
            target_document_id=clone.id,
        )
    except Exception:
        db.rollback()

    updated_subscription = mark_document_generated(db, subscription)
    log_action(
        db,
        user_id=user.user_id,
        action="document_clone",
        entity_type="generated_document",
        entity_id=clone.id,
        metadata={
            "source_id": source.id,
            "document_type": clone.document_type,
            "case_law_refs_linked": linked_case_law_count,
        },
    )
    return DocumentCloneResponse(
        status="created",
        source_id=source.id,
        document_id=clone.id,
        created_at=clone.created_at.isoformat(),
        usage=to_payload(updated_subscription),
    )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
def delete_document(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDeleteResponse:
    row = get_generated_document(db, user.user_id, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    docx_path = row.docx_storage_path
    pdf_path = row.pdf_storage_path
    delete_generated_document(db, document=row)

    try:
        delete_export_file(docx_path)
        delete_export_file(pdf_path)
    except Exception:
        pass

    log_action(
        db,
        user_id=user.user_id,
        action="document_delete",
        entity_type="generated_document",
        entity_id=document_id,
        metadata={},
    )
    return DocumentDeleteResponse(status="deleted", id=document_id)


@router.get("/{document_id}/export")
def export_document(
    document_id: str,
    format: str = Query(default="docx", pattern="^(docx|pdf)$"),
    report: bool = Query(default=False),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    row = get_generated_document(db, user.user_id, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    document_meta = get_document_type(row.document_type)
    title = document_meta.title if document_meta is not None else row.document_type
    text = get_document_generated_text(row) or get_document_preview_text(row) or ""

    from app.models.user import User

    profile = db.get(User, user.user_id)
    logo_url = profile.logo_url if profile else None
    if report:
        validation_checks = build_processual_validation_checks(row.document_type, text)
        gate_checks = build_pre_generation_gate_checks(row.document_type, get_document_form_data(row))
        title = f"{title} - Processual Validation Report"
        text = _build_processual_report_text(row, checks=validation_checks, gate_checks=gate_checks)

    persist_needed = False
    if format == "pdf":
        extension = "pdf"
        media_type = "application/pdf"
        existing_path = row.pdf_storage_path
        content = None if report else read_export_bytes(existing_path)
        if content is None:
            content = render_pdf_bytes(title=title, text=text, logo_url=logo_url)
            persist_needed = not report
    else:
        extension = "docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        existing_path = row.docx_storage_path
        content = None if report else read_export_bytes(existing_path)
        if content is None:
            content = render_docx_bytes(title=title, text=text, logo_url=logo_url)
            persist_needed = not report

    if persist_needed:
        try:
            relative_path = existing_path or build_export_rel_path(
                user_id=user.user_id,
                document_id=row.id,
                extension=extension,
            )
            write_export_bytes(relative_path=relative_path, content=content)
            set_document_export_path(db, document=row, format=format, relative_path=relative_path)
        except Exception:
            db.rollback()
    elif existing_path and not report:
        try:
            set_document_export_path(db, document=row, format=format, relative_path=existing_path)
        except Exception:
            db.rollback()

    suffix = "-processual-report" if report else ""
    filename = sanitize_filename(f"{row.document_type}-{row.id}{suffix}.{extension}")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type=media_type, headers=headers)
