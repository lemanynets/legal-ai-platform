from __future__ import annotations

import math

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import DocumentVersion, GeneratedDocument
from app.services.document_crypto import decrypt_text, encrypt_text
from app.services.generated_documents import get_accessible_user_ids


def get_version_generated_text(version: DocumentVersion) -> str:
    return decrypt_text(version.generated_text)


def create_document_version(
    db: Session,
    *,
    document: GeneratedDocument,
    action: str,
    generated_text: str | None = None,
) -> DocumentVersion:
    last_number = db.execute(
        select(func.max(DocumentVersion.version_number)).where(DocumentVersion.document_id == document.id)
    ).scalar_one()
    next_number = int(last_number or 0) + 1

    source_text = generated_text if generated_text is not None else decrypt_text(document.generated_text)
    row = DocumentVersion(
        document_id=document.id,
        user_id=document.user_id,
        version_number=next_number,
        action=action,
        generated_text=encrypt_text(source_text or ""),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_document_versions(
    db: Session,
    *,
    user_id: str,
    document_id: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[DocumentVersion], int, int, int]:
    normalized_page_size = max(1, min(page_size, 100))
    accessible_user_ids = get_accessible_user_ids(db, user_id)
    filters = [
        DocumentVersion.user_id.in_(accessible_user_ids),
        DocumentVersion.document_id == document_id,
    ]
    total = int(db.execute(select(func.count()).select_from(DocumentVersion).where(*filters)).scalar_one() or 0)
    pages = max(1, math.ceil(total / normalized_page_size)) if total > 0 else 1
    normalized_page = max(1, min(page, pages))

    rows = list(
        db.execute(
            select(DocumentVersion)
            .where(*filters)
            .order_by(desc(DocumentVersion.version_number), desc(DocumentVersion.created_at))
            .offset((normalized_page - 1) * normalized_page_size)
            .limit(normalized_page_size)
        )
        .scalars()
        .all()
    )
    return rows, total, normalized_page, pages


def get_document_version(
    db: Session,
    *,
    user_id: str,
    document_id: str,
    version_id: str,
) -> DocumentVersion | None:
    row = db.get(DocumentVersion, version_id)
    if row is None:
        return None
    if row.document_id != document_id:
        return None
    if row.user_id not in set(get_accessible_user_ids(db, user_id)):
        return None
    return row