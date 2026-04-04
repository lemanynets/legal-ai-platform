from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class AuditLogItem(BaseModel):
    id: str
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    integrity_scope: str | None = None
    integrity_prev_hash: str | None = None
    integrity_hash: str | None = None
    created_at: str


class AuditHistoryResponse(BaseModel):
    user_id: str
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1
    action: str | None = None
    entity_type: str | None = None
    query: str | None = None
    items: list[AuditLogItem] = Field(default_factory=list)


class AuditIntegrityIssue(BaseModel):
    row_id: str
    created_at: str | None = None
    code: str
    message: str


class AuditIntegrityResponse(BaseModel):
    scope: str
    status: str
    rows_total: int = 0
    rows_checked: int = 0
    truncated: bool = False
    head_hash: str | None = None
    tail_hash: str | None = None
    issues: list[AuditIntegrityIssue] = Field(default_factory=list)
    verified_at: str
