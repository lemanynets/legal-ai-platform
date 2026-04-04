from __future__ import annotations

from decimal import Decimal, InvalidOperation
import math
from typing import Any

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models import GeneratedDocument, User
from app.models.base import utcnow
from app.services.document_crypto import decrypt_json, decrypt_text, encrypt_json, encrypt_text, is_document_encryption_enabled


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _get_workspace_id(db: Session, user_id: str) -> str | None:
    stmt = select(User.workspace_id).where(User.id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def get_accessible_user_ids(db: Session, actor_user_id: str) -> list[str]:
    workspace_id = _get_workspace_id(db, actor_user_id)
    if not workspace_id:
        return [actor_user_id]
    stmt = select(User.id).where(User.workspace_id == workspace_id)
    user_ids = [str(item) for item in db.execute(stmt).scalars().all() if item]
    return user_ids or [actor_user_id]


def _has_same_workspace(db: Session, actor_user_id: str, owner_user_id: str) -> bool:
    actor_workspace_id = _get_workspace_id(db, actor_user_id)
    owner_workspace_id = _get_workspace_id(db, owner_user_id)
    return bool(actor_workspace_id and owner_workspace_id and actor_workspace_id == owner_workspace_id)


def get_document_form_data(document: GeneratedDocument) -> dict[str, Any]:
    return decrypt_json(document.form_data)


def get_document_generated_text(document: GeneratedDocument) -> str:
    return decrypt_text(document.generated_text)


def get_document_preview_text(document: GeneratedDocument) -> str:
    return str(document.preview_text or "")


def create_generated_document(
    db: Session,
    *,
    user_id: str,
    document_type: str,
    document_category: str,
    form_data: dict[str, Any],
    generated_text: str,
    preview_text: str,
    calculations: dict[str, Any],
    ai_model: str | None,
    used_ai: bool,
    ai_error: str | None,
    case_id: str | None = None,
) -> GeneratedDocument:
    court_fee = _to_decimal(calculations.get("court_fee_uah"))
    record = GeneratedDocument(
        user_id=user_id,
        document_type=document_type,
        document_category=document_category,
        form_data=encrypt_json(form_data),
        generated_text=encrypt_text(generated_text),
        preview_text=preview_text,
        calculations=calculations,
        court_fee_amount=court_fee,
        ai_model=ai_model or None,
        used_ai=used_ai,
        ai_error=ai_error or None,
        case_id=case_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_generated_documents(
    db: Session,
    user_id: str,
    *,
    page: int = 1,
    page_size: int = 20,
    query: str | None = None,
    doc_type: str | None = None,
    case_id: str | None = None,
    has_docx_export: bool | None = None,
    has_pdf_export: bool | None = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
) -> tuple[list[GeneratedDocument], int, int, int]:
    normalized_page_size = max(1, min(page_size, 100))
    accessible_user_ids = get_accessible_user_ids(db, user_id)
    filters = [GeneratedDocument.user_id.in_(accessible_user_ids)]

    normalized_doc_type = (doc_type or "").strip()
    if normalized_doc_type:
        filters.append(GeneratedDocument.document_type == normalized_doc_type)
    if case_id:
        filters.append(GeneratedDocument.case_id == case_id)
    if has_docx_export is True:
        filters.append(GeneratedDocument.docx_storage_path.is_not(None))
    elif has_docx_export is False:
        filters.append(GeneratedDocument.docx_storage_path.is_(None))
    if has_pdf_export is True:
        filters.append(GeneratedDocument.pdf_storage_path.is_not(None))
    elif has_pdf_export is False:
        filters.append(GeneratedDocument.pdf_storage_path.is_(None))

    normalized_query = (query or "").strip()
    if normalized_query:
        like_value = f"%{normalized_query}%"
        search_filters = [
            GeneratedDocument.document_type.ilike(like_value),
            GeneratedDocument.preview_text.ilike(like_value),
        ]
        if not is_document_encryption_enabled():
            search_filters.append(GeneratedDocument.generated_text.ilike(like_value))
        filters.append(or_(*search_filters))

    total_stmt = select(func.count()).select_from(GeneratedDocument).where(*filters)
    total = int(db.execute(total_stmt).scalar_one() or 0)
    pages = max(1, math.ceil(total / normalized_page_size)) if total > 0 else 1
    normalized_page = max(1, min(page, pages))

    sort_columns = {
        "created_at": GeneratedDocument.created_at,
        "document_type": GeneratedDocument.document_type,
        "document_category": GeneratedDocument.document_category,
    }
    selected_sort = sort_columns.get(sort_by, GeneratedDocument.created_at)
    direction = asc if str(sort_dir).lower() == "asc" else desc

    stmt = (
        select(GeneratedDocument)
        .where(*filters)
        .order_by(direction(selected_sort), desc(GeneratedDocument.id))
        .offset((normalized_page - 1) * normalized_page_size)
        .limit(normalized_page_size)
    )
    rows = list(db.execute(stmt).scalars().all())
    return rows, total, normalized_page, pages


def get_generated_document(db: Session, user_id: str, document_id: str) -> GeneratedDocument | None:
    row = db.get(GeneratedDocument, document_id)
    if row is None:
        return None
    if row.user_id not in set(get_accessible_user_ids(db, user_id)):
        return None
    if not _has_same_workspace(db, user_id, row.user_id):
        return None
    return row


def get_generated_documents_by_ids(
    db: Session,
    *,
    user_id: str,
    ids: list[str],
) -> list[GeneratedDocument]:
    if not ids:
        return []
    deduped_ids = list(dict.fromkeys(ids))
    accessible_user_ids = get_accessible_user_ids(db, user_id)
    stmt = select(GeneratedDocument).where(
        GeneratedDocument.user_id.in_(accessible_user_ids),
        GeneratedDocument.id.in_(deduped_ids),
    )
    rows = list(db.execute(stmt).scalars().all())
    return [row for row in rows if _has_same_workspace(db, user_id, row.user_id)]


def set_document_export_path(
    db: Session,
    *,
    document: GeneratedDocument,
    format: str,
    relative_path: str,
) -> GeneratedDocument:
    if format == "pdf":
        document.pdf_storage_path = relative_path
    else:
        document.docx_storage_path = relative_path
    document.last_exported_at = utcnow()
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def update_generated_document_text(
    db: Session,
    *,
    document: GeneratedDocument,
    generated_text: str,
) -> GeneratedDocument:
    document.generated_text = encrypt_text(generated_text)
    document.docx_storage_path = None
    document.pdf_storage_path = None
    document.last_exported_at = None
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def delete_generated_document(db: Session, *, document: GeneratedDocument) -> None:
    db.delete(document)
    db.commit()