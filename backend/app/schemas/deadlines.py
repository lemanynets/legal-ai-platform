from __future__ import annotations
from datetime import date
from pydantic import BaseModel, Field

class DeadlineCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    document_id: str | None = None
    deadline_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None


class DeadlineUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    deadline_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    reminder_sent: bool | None = None
    notes: str | None = None


class DeadlineItem(BaseModel):
    id: str
    user_id: str
    title: str
    document_id: str | None = None
    deadline_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    reminder_sent: bool
    notes: str | None = None
    created_at: str


class DeadlineListResponse(BaseModel):
    total: int
    items: list[DeadlineItem]
