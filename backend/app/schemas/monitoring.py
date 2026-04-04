from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class RegistryWatchCreateRequest(BaseModel):
    source: str = Field(default="opendatabot", max_length=50)
    registry_type: str = Field(min_length=2, max_length=50)
    identifier: str = Field(min_length=2, max_length=120)
    entity_name: str = Field(min_length=2, max_length=255)
    check_interval_hours: int = Field(default=24, ge=1, le=720)
    notes: str | None = Field(default=None, max_length=1000)


class RegistryWatchCheckRequest(BaseModel):
    observed_status: str | None = Field(default=None, max_length=50)
    summary: str | None = Field(default=None, max_length=500)
    details: dict[str, Any] = Field(default_factory=dict)


class RegistryWatchItem(BaseModel):
    id: str
    user_id: str
    source: str
    registry_type: str
    identifier: str
    entity_name: str
    status: str
    check_interval_hours: int
    last_checked_at: str | None = None
    next_check_at: str | None = None
    last_change_at: str | None = None
    latest_snapshot: dict[str, Any] | None = None
    notes: str | None = None
    created_at: str
    updated_at: str


class RegistryWatchCreateResponse(BaseModel):
    status: str
    item: RegistryWatchItem


class RegistryWatchCheckResponse(BaseModel):
    status: str
    item: RegistryWatchItem
    event_id: str
    event_type: str


class RegistryWatchDeleteResponse(BaseModel):
    status: str
    id: str


class RegistryWatchListResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1
    items: list[RegistryWatchItem] = Field(default_factory=list)


class RegistryMonitorEventItem(BaseModel):
    id: str
    watch_item_id: str
    user_id: str
    event_type: str
    severity: str
    title: str
    details: dict[str, Any] = Field(default_factory=dict)
    observed_at: str
    created_at: str


class RegistryMonitorEventsResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1
    items: list[RegistryMonitorEventItem] = Field(default_factory=list)


class RegistryCheckDueRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)


class RegistryCheckDueResponse(BaseModel):
    status: str
    scanned: int
    checked: int
    state_changed: int


class RegistryMonitoringStatusResponse(BaseModel):
    total_watch_items: int
    active_watch_items: int
    due_watch_items: int
    warning_watch_items: int
    state_changed_events_24h: int
    last_event_at: str | None = None
    by_status: dict[str, int] = Field(default_factory=dict)
