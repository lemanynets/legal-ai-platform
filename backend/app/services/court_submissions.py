from __future__ import annotations

import math
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import CourtSubmission, GeneratedDocument
from app.services.prompt_builder import build_pre_generation_gate_checks, build_processual_validation_checks


def _now() -> datetime:
    return datetime.now(timezone.utc)


def build_external_submission_id() -> str:
    stamp = _now().strftime("%Y%m%d")
    suffix = str(uuid4()).split("-")[0]
    return f"EC-{stamp}-{suffix}"


def get_owned_document(db: Session, *, user_id: str, document_id: str) -> GeneratedDocument | None:
    return db.execute(
        select(GeneratedDocument).where(GeneratedDocument.id == document_id, GeneratedDocument.user_id == user_id).limit(1)
    ).scalar_one_or_none()


def _try_real_submission(
    *,
    document_type: str,
    court_name: str,
    signer_method: str | None,
    note: str | None,
) -> dict | None:
    """Attempt a real court.gov.ua submission.

    Returns a dict with (external_submission_id, tracking_url, status, response_payload)
    if credentials are configured and the call succeeds. Returns None otherwise so the
    caller can fall back to the stub.
    """
    try:
        from app.services.court_gov_ua_client import (
            CourtApiNotConfiguredError,
            submit_claim,
        )
        return submit_claim(
            document_type=document_type,
            court_name=court_name,
            signer_method=signer_method,
            note=note,
        )
    except Exception:  # CourtApiNotConfiguredError or any real API error → stub fallback
        return None


def create_court_submission(
    db: Session,
    *,
    user_id: str,
    document_id: str,
    court_name: str,
    signer_method: str | None,
    request_payload: dict,
) -> CourtSubmission:
    document_type = request_payload.get("document_type", "")
    note = request_payload.get("note") or None

    real = _try_real_submission(
        document_type=document_type,
        court_name=court_name,
        signer_method=signer_method,
        note=note,
    )

    if real:
        external_id = real["external_submission_id"]
        tracking_url = real.get("tracking_url") or f"https://court.gov.ua/tracking/{external_id}"
        status = real.get("status", "submitted")
        response_payload = real.get("response_payload") or {
            "status": status,
            "external_submission_id": external_id,
        }
        provider = "court_gov_ua"
    else:
        # Stub path: generate a local reference ID and a plausible tracking URL
        external_id = build_external_submission_id()
        tracking_url = f"https://court.gov.ua/tracking/{external_id}"
        status = "submitted"
        response_payload = {
            "status": "accepted",
            "message": "Submission accepted for processing.",
            "external_submission_id": external_id,
            "note": "stub mode — configure COURT_GOV_UA_CLIENT_ID to enable real API",
        }
        provider = "court_gov_ua_stub"

    row = CourtSubmission(
        user_id=user_id,
        document_id=document_id,
        provider=provider,
        external_submission_id=external_id,
        status=status,
        court_name=court_name,
        signer_method=signer_method,
        request_payload=request_payload,
        response_payload=response_payload,
        tracking_url=tracking_url,
        submitted_at=_now(),
        updated_at=_now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def sync_submission_status(db: Session, submission: CourtSubmission) -> CourtSubmission:
    """Poll the real court.gov.ua API and update the submission status in DB.

    If credentials are absent or the API call fails, the submission is returned
    unchanged (status not modified).
    """
    try:
        from app.services.court_gov_ua_client import (
            CourtApiNotConfiguredError,
            get_claim_status,
        )
        result = get_claim_status(submission.external_submission_id)
        new_status: str = result.get("status", submission.status)
        new_tracking: str | None = result.get("tracking_url") or submission.tracking_url
        submission.status = new_status
        submission.tracking_url = new_tracking
        submission.updated_at = _now()
        db.commit()
        db.refresh(submission)
    except Exception:
        # No credentials or network error — return unchanged
        pass
    return submission


def list_court_submissions(
    db: Session,
    *,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
) -> tuple[list[CourtSubmission], int, int, int]:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 100))
    stmt = select(CourtSubmission).where(CourtSubmission.user_id == user_id)
    normalized_status = (status or "").strip().lower() or None
    if normalized_status:
        stmt = stmt.where(CourtSubmission.status == normalized_status)

    total = int(db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one() or 0)
    pages = max(1, math.ceil(total / safe_page_size)) if total > 0 else 1
    if safe_page > pages:
        safe_page = pages

    rows = list(
        db.execute(
            stmt.order_by(desc(CourtSubmission.submitted_at), desc(CourtSubmission.id))
            .offset((safe_page - 1) * safe_page_size)
            .limit(safe_page_size)
        )
        .scalars()
        .all()
    )
    return rows, total, safe_page, pages


def get_court_submission(db: Session, *, user_id: str, submission_id: str) -> CourtSubmission | None:
    return db.execute(
        select(CourtSubmission)
        .where(CourtSubmission.id == submission_id, CourtSubmission.user_id == user_id)
        .limit(1)
    ).scalar_one_or_none()


def evaluate_document_filing_readiness(document: GeneratedDocument) -> dict[str, object]:
    form_data = document.form_data or {}
    generated_text = document.generated_text or document.preview_text or ""
    gate_checks = build_pre_generation_gate_checks(document.document_type, form_data)
    validation_checks = build_processual_validation_checks(document.document_type, generated_text)

    blockers: list[str] = []
    for item in gate_checks:
        if item.get("status") == "fail":
            blockers.append(f"gate:{item.get('code')}")
    for item in validation_checks:
        if item.get("status") == "fail":
            blockers.append(f"validation:{item.get('code')}")

    return {
        "ready_for_filing": len(blockers) == 0,
        "filing_blockers": blockers,
        "pre_generation_gate_checks": gate_checks,
        "processual_validation_checks": validation_checks,
    }
