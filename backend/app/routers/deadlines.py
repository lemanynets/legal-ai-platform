from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models import Deadline, GeneratedDocument
from app.schemas import DeadlineCreateRequest, DeadlineItem, DeadlineListResponse, DeadlineUpdateRequest
from app.services.audit import log_action
from app.services.realtime import publish_user_event

router = APIRouter(prefix="/api/deadlines", tags=["deadlines"])


def _to_item(row: Deadline) -> DeadlineItem:
    return DeadlineItem(
        id=row.id,
        user_id=row.user_id,
        title=row.title,
        document_id=row.document_id,
        deadline_type=row.deadline_type,
        start_date=row.start_date,
        end_date=row.end_date,
        reminder_sent=row.reminder_sent,
        notes=row.notes,
        created_at=row.created_at.isoformat(),
    )


@router.get("", response_model=DeadlineListResponse)
def list_deadlines(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeadlineListResponse:
    rows = list(
        db.execute(
            select(Deadline)
            .where(Deadline.user_id == user.user_id)
            .order_by(desc(Deadline.created_at))
            .limit(200)
        )
        .scalars()
        .all()
    )
    items = [_to_item(row) for row in rows]
    return DeadlineListResponse(total=len(items), items=items)


@router.post("", response_model=DeadlineItem)
def create_deadline(
    payload: DeadlineCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeadlineItem:
    if payload.document_id:
        doc = db.get(GeneratedDocument, payload.document_id)
        if doc is None or doc.user_id != user.user_id:
            raise HTTPException(status_code=404, detail="Related generated document not found.")

    row = Deadline(
        user_id=user.user_id,
        title=payload.title,
        document_id=payload.document_id,
        deadline_type=payload.deadline_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_action(
        db,
        user_id=user.user_id,
        action="deadline_create",
        entity_type="deadline",
        entity_id=row.id,
        metadata={"deadline_type": row.deadline_type},
    )
    publish_user_event(
        user.user_id,
        "deadline.created",
        {
            "id": row.id,
            "title": row.title,
            "end_date": row.end_date.isoformat() if row.end_date else None,
        },
    )
    return _to_item(row)


@router.put("/{deadline_id}", response_model=DeadlineItem)
def update_deadline(
    deadline_id: str,
    payload: DeadlineUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeadlineItem:
    row = db.get(Deadline, deadline_id)
    if row is None or row.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Deadline not found.")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)

    log_action(
        db,
        user_id=user.user_id,
        action="deadline_update",
        entity_type="deadline",
        entity_id=row.id,
        metadata={"updated_fields": sorted(list(updates.keys()))},
    )
    publish_user_event(
        user.user_id,
        "deadline.updated",
        {
            "id": row.id,
            "title": row.title,
            "end_date": row.end_date.isoformat() if row.end_date else None,
            "updated_fields": sorted(list(updates.keys())),
        },
    )
    return _to_item(row)


@router.delete("/{deadline_id}")
def delete_deadline(
    deadline_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    row = db.get(Deadline, deadline_id)
    if row is None or row.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Deadline not found.")
    db.delete(row)
    db.commit()

    log_action(
        db,
        user_id=user.user_id,
        action="deadline_delete",
        entity_type="deadline",
        entity_id=deadline_id,
    )
    publish_user_event(
        user.user_id,
        "deadline.deleted",
        {"id": deadline_id},
    )
    return {"status": "deleted", "id": deadline_id}
