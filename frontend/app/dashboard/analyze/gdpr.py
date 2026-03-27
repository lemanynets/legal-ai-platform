"""
FastAPI router for GDPR compliance checks.

Endpoint: POST /api/analyze/gdpr-check
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.auth import get_current_user
from app.models.user import User

from .gdpr_analyzer import analyze_gdpr_compliance, PiiCategory as PiiCategoryInternal

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class GdprCheckRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200_000)
    intake_id: Optional[str] = Field(None, description="Optional intake analysis ID for traceability")


class PersonalDataItem(BaseModel):
    type: str
    count: int
    examples: list[str] = []


class GdprCheckResponse(BaseModel):
    report: str
    compliant: bool
    issues: list[str]
    personal_data_found: list[PersonalDataItem] = []
    recommendations: list[str] = []
    intake_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post(
    "/gdpr-check",
    response_model=GdprCheckResponse,
    summary="Analyze text for GDPR compliance",
    description="Detects personal data (PII) in Ukrainian legal text and evaluates GDPR compliance risks.",
)
async def gdpr_check(
    payload: GdprCheckRequest,
    current_user: User = Depends(get_current_user),
):
    text = payload.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Text is required",
        )

    result = analyze_gdpr_compliance(text)

    return GdprCheckResponse(
        report=result.report,
        compliant=result.compliant,
        issues=result.issues,
        personal_data_found=[
            PersonalDataItem(type=c.type, count=c.count, examples=c.examples)
            for c in result.personal_data_found
        ],
        recommendations=result.recommendations,
        intake_id=payload.intake_id,
    )
