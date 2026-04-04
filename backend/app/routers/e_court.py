from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.config import settings
from app.database import get_db
from app.schemas import (
    ECourtCourtsResponse,
    ECourtHearingsResponse,
    ECourtHistoryResponse,
    ECourtStatusResponse,
    ECourtSubmitRequest,
    ECourtSubmitResponse,
    ECourtSyncStatusResponse,
)
from app.services.audit import log_action
from app.services.public_court_scraper import scraper as public_scraper
from app.services.court_submissions import (
    create_court_submission,
    evaluate_document_filing_readiness,
    get_court_submission,
    get_owned_document,
    list_court_submissions,
    sync_submission_status,
)
from app.services.entitlements import ensure_feature_access

router = APIRouter(prefix="/api/e-court", tags=["e-court"])


def _serialize_submission(row) -> dict:
    return {
        "id": row.id,
        "document_id": row.document_id,
        "provider": row.provider,
        "external_submission_id": row.external_submission_id,
        "status": row.status,
        "court_name": row.court_name,
        "signer_method": row.signer_method,
        "tracking_url": row.tracking_url,
        "error_message": row.error_message,
        "submitted_at": row.submitted_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


@router.post("/submit", response_model=ECourtSubmitResponse)
def submit_to_e_court(
    payload: ECourtSubmitRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ECourtSubmitResponse:
    ensure_feature_access(db, current_user=user, feature="e_court_submission")
    document = get_owned_document(db, user_id=user.user_id, document_id=payload.document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    readiness = evaluate_document_filing_readiness(document)
    if settings.strict_filing_mode and not bool(readiness.get("ready_for_filing")):
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Strict filing mode blocked submission. Resolve processual blockers first.",
                "blockers": readiness.get("filing_blockers") or [],
                "pre_generation_gate_checks": readiness.get("pre_generation_gate_checks") or [],
                "processual_validation_checks": readiness.get("processual_validation_checks") or [],
            },
        )

    from app.services.document_generation import export_document
    from app.services.signer import sign_document

    # Export document to physical file
    # This prepares the final PDF or DOCX to be signed
    export_result = export_document(
        db,
        user_id=user.user_id,
        document_id=document.id,
        format="pdf",  # e-court prefers pdf
    )
    
    signed_payload_path = None
    if payload.signer_method == "file_key" and settings.ecp_key_path:
        # Apply strict cryptographic signature
        try:
            signed_payload_path = sign_document(
                file_path=str(export_result.file_path),
                key_path=settings.ecp_key_path,
                password=settings.ecp_key_password,
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to sign document with provided ECP key: {str(e)}",
            )
            
    request_payload = {
        "document_type": document.document_type,
        "document_category": document.document_category,
        "court_name": payload.court_name,
        "signer_method": (payload.signer_method or "").strip() or None,
        "note": (payload.note or "").strip() or None,
        "signed_file_path": signed_payload_path, # Track the generated signature file
    }
    submission = create_court_submission(
        db,
        user_id=user.user_id,
        document_id=document.id,
        court_name=payload.court_name.strip(),
        signer_method=(payload.signer_method or "").strip() or None,
        request_payload=request_payload,
    )
    log_action(
        db,
        user_id=user.user_id,
        action="e_court_submit",
        entity_type="court_submission",
        entity_id=submission.id,
        metadata={
            "document_id": submission.document_id,
            "external_submission_id": submission.external_submission_id,
            "status": submission.status,
            "provider": submission.provider,
            "ready_for_filing": bool(readiness.get("ready_for_filing")),
            "filing_blockers": readiness.get("filing_blockers") or [],
            "signed_crypto_file": bool(signed_payload_path),
        },
    )
    return ECourtSubmitResponse(status="submitted", submission=_serialize_submission(submission))


@router.get("/history", response_model=ECourtHistoryResponse)
def e_court_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ECourtHistoryResponse:
    ensure_feature_access(db, current_user=user, feature="e_court_history")
    rows, total, normalized_page, pages = list_court_submissions(
        db,
        user_id=user.user_id,
        page=page,
        page_size=page_size,
        status=status,
    )
    log_action(
        db,
        user_id=user.user_id,
        action="e_court_history",
        entity_type="court_submission",
        entity_id=None,
        metadata={"page": normalized_page, "page_size": page_size, "status": status, "returned": len(rows), "total": total},
    )
    return ECourtHistoryResponse(
        total=total,
        page=normalized_page,
        page_size=page_size,
        pages=pages,
        items=[_serialize_submission(item) for item in rows],
    )


@router.get("/courts", response_model=ECourtCourtsResponse)
def list_courts(
    user: CurrentUser = Depends(get_current_user),
) -> ECourtCourtsResponse:
    """Return a list of available court names.

    When court.gov.ua credentials are configured, fetches the live catalogue.
    Falls back to a curated list of Ukrainian courts when no credentials are set.
    """
    from app.services.court_gov_ua_client import list_courts as _list
    courts = _list()
    return ECourtCourtsResponse(
        courts=courts,
        source="court_gov_ua" if settings.court_gov_ua_client_id else "fallback",
    )


@router.get("/hearings", response_model=ECourtHearingsResponse)
def list_hearings(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ECourtHearingsResponse:
    """Return a list of scheduled court hearings.
    
    This feature integrates with court.gov.ua to show judge-scheduled sessions.
    """
    ensure_feature_access(db, current_user=user, feature="e_court_history")
    from app.services.court_gov_ua_client import list_hearings as _list
    items = _list()
    return ECourtHearingsResponse(
        items=items,
        total=len(items)
    )


@router.get("/{submission_id}/status", response_model=ECourtStatusResponse)
def e_court_status(
    submission_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ECourtStatusResponse:
    ensure_feature_access(db, current_user=user, feature="e_court_history")
    row = get_court_submission(db, user_id=user.user_id, submission_id=submission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    log_action(
        db,
        user_id=user.user_id,
        action="e_court_status",
        entity_type="court_submission",
        entity_id=row.id,
        metadata={"status": row.status, "external_submission_id": row.external_submission_id},
    )
    return ECourtStatusResponse(submission=_serialize_submission(row))


@router.post("/{submission_id}/sync-status", response_model=ECourtSyncStatusResponse)
def e_court_sync_status(
    submission_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ECourtSyncStatusResponse:
    """Poll court.gov.ua for the latest status of this submission and update DB.

    When real credentials are configured, this makes a live API call.
    In stub mode, the existing DB record is returned unchanged.
    """
    ensure_feature_access(db, current_user=user, feature="e_court_history")
    row = get_court_submission(db, user_id=user.user_id, submission_id=submission_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    updated = sync_submission_status(db, row)
    synced_live = bool(settings.court_gov_ua_client_id)

    log_action(
        db,
        user_id=user.user_id,
        action="e_court_sync_status",
        entity_type="court_submission",
        entity_id=updated.id,
        metadata={
            "status": updated.status,
            "external_submission_id": updated.external_submission_id,
            "synced_live": synced_live,
        },
    )
    return ECourtSyncStatusResponse(
        submission=_serialize_submission(updated),
        synced_live=synced_live,
    )

@router.get("/public-search")
def public_search(
    case_number: str = Query(..., description="Case number to search"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search court.gov.ua public portals (fair/assignments) directly by case number.
    Returns both upcoming assignments and historical fair status.
    """
    assignments = public_scraper.search_assignments(case_number)
    fair_history = public_scraper.search_fair(case_number)
    
    log_action(
        db,
        user_id=user.user_id,
        action="e_court_public_search",
        entity_type="search",
        entity_id=None,
        metadata={"case_number": case_number, "assignments": len(assignments), "history": len(fair_history)}
    )
    
    return {
        "status": "success",
        "case_number": case_number,
        "assignments": assignments,
        "history": fair_history
    }
