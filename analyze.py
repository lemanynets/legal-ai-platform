from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.services.auth import get_current_user
from app.models.user import User
from app.services.gdpr_analyzer import analyze_gdpr_compliance
from app.services.intake_analyzer import run_intake_analysis # Припускаємо, що цей сервіс існує

router = APIRouter()

class GdprComplianceRequest(BaseModel):
    text: str

class GdprComplianceResponse(BaseModel):
    report: str
    issues_found: int

@router.post(
    "/analyze/gdpr-compliance",
    response_model=GdprComplianceResponse,
    summary="Analyze text for GDPR compliance",
)
async def gdpr_compliance_endpoint(
    request: GdprComplianceRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Takes a block of text and analyzes it for potential GDPR compliance issues.
    """
    try:
        session_id = f"user:{current_user.id}"
        report_data = await analyze_gdpr_compliance(request.text, session_id=session_id)
        return report_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="An unexpected error occurred during GDPR analysis.")

@router.post("/analyze/intake")
async def intake_endpoint(
    file: UploadFile = File(...),
    jurisdiction: str = Form("UA"),
    mode: str = Form("standard"),
    case_id: str | None = Form(None),
    current_user: User = Depends(get_current_user),
):
    """
    Аналізує один документ, класифікує його та може прив'язати до справи.
    """
    try:
        result = await run_intake_analysis(
            file=file,
            user_id=current_user.id,
            mode=mode,
            jurisdiction=jurisdiction,
            case_id=case_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="An unexpected error occurred during intake analysis.")