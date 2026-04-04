from __future__ import annotations
from pydantic import BaseModel, Field

class ECourtSubmitRequest(BaseModel):
    document_id: str
    court_name: str = Field(min_length=2, max_length=255)
    signer_method: str | None = Field(default=None, max_length=50)
    note: str | None = Field(default=None, max_length=500)


class ECourtSubmissionItem(BaseModel):
    id: str
    document_id: str | None = None
    provider: str
    external_submission_id: str
    status: str
    court_name: str
    signer_method: str | None = None
    tracking_url: str | None = None
    error_message: str | None = None
    submitted_at: str
    updated_at: str


class ECourtSubmitResponse(BaseModel):
    status: str
    submission: ECourtSubmissionItem


class ECourtHistoryResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1
    items: list[ECourtSubmissionItem] = Field(default_factory=list)


class ECourtStatusResponse(BaseModel):
    submission: ECourtSubmissionItem


class ECourtCourtsResponse(BaseModel):
    courts: list[str] = Field(default_factory=list)
    source: str = "fallback"


class ECourtSyncStatusResponse(BaseModel):
    submission: ECourtSubmissionItem
    synced_live: bool = False


class ECourtHearingItem(BaseModel):
    id: str
    case_number: str
    court_name: str
    date: str  # ISO date string
    time: str | None = None
    subject: str | None = None
    judge: str | None = None
    status: str | None = None


class ECourtHearingsResponse(BaseModel):
    items: list[ECourtHearingItem] = Field(default_factory=list)
    total: int
