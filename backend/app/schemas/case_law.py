from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class CaseLawSearchItem(BaseModel):
    id: str
    source: str
    decision_id: str
    court_name: str | None = None
    court_type: str | None = None
    decision_date: str | None = None
    case_number: str | None = None
    subject_categories: list[str] = Field(default_factory=list)
    legal_positions: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
    reference_count: int = 0


class CaseLawSearchResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1
    sort_by: str = "decision_date"
    sort_dir: str = "desc"
    items: list[CaseLawSearchItem]


class CaseLawDigestItem(BaseModel):
    id: str
    source: str
    decision_id: str
    court_name: str | None = None
    court_type: str | None = None
    decision_date: str | None = None
    case_number: str | None = None
    subject_categories: list[str] = Field(default_factory=list)
    summary: str | None = None
    legal_positions: dict[str, Any] = Field(default_factory=dict)
    prompt_snippet: str


class CaseLawDigestResponse(BaseModel):
    digest_id: str | None = None
    saved: bool = False
    title: str | None = None
    days: int
    limit: int
    total: int
    only_supreme: bool
    court_type: str | None = None
    source: list[str] = Field(default_factory=list)
    generated_at: str
    items: list[CaseLawDigestItem] = Field(default_factory=list)


class CaseLawDigestGenerateRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=3650)
    limit: int = Field(default=20, ge=1, le=100)
    court_type: str | None = None
    source: list[str] = Field(default_factory=list)
    only_supreme: bool = True
    save: bool = False
    title: str | None = None


class CaseLawDigestHistoryItem(BaseModel):
    id: str
    title: str | None = None
    days: int
    limit: int
    total: int
    item_count: int
    only_supreme: bool
    court_type: str | None = None
    source: list[str] = Field(default_factory=list)
    created_at: str


class CaseLawDigestHistoryResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1
    items: list[CaseLawDigestHistoryItem] = Field(default_factory=list)


class CaseLawImportRecord(BaseModel):
    source: str = "manual"
    decision_id: str
    court_name: str | None = None
    court_type: str | None = None
    decision_date: str | None = None
    case_number: str | None = None
    subject_categories: list[str] = Field(default_factory=list)
    legal_positions: dict[str, Any] = Field(default_factory=dict)
    full_text: str | None = None
    summary: str | None = None


class CaseLawImportRequest(BaseModel):
    records: list[CaseLawImportRecord] = Field(default_factory=list)


class CaseLawImportResponse(BaseModel):
    created: int
    updated: int
    total: int


class CaseLawSyncRequest(BaseModel):
    query: str | None = None
    limit: int = Field(default=100, ge=1, le=200)
    sources: list[str] = Field(default_factory=list)
    allow_seed_fallback: bool | None = None


class CaseLawSyncResponse(BaseModel):
    status: str
    created: int
    updated: int
    total: int
    sources: list[str] = Field(default_factory=list)
    seed_fallback_used: bool = False
    fetched_counts: dict[str, int] = Field(default_factory=dict)


class CaseLawSyncStatusResponse(BaseModel):
    total_records: int
    sources: dict[str, int] = Field(default_factory=dict)
    latest_decision_date: str | None = None
    oldest_decision_date: str | None = None
    last_sync_at: str | None = None
    last_sync_action: str | None = None
    last_sync_query: str | None = None
    last_sync_limit: int | None = None
    last_sync_created: int | None = None
    last_sync_updated: int | None = None
    last_sync_total: int | None = None
    last_sync_sources: list[str] = Field(default_factory=list)
    last_sync_seed_fallback_used: bool | None = None
