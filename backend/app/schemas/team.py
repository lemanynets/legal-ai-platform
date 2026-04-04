from __future__ import annotations
from pydantic import BaseModel, Field

class TeamUserItem(BaseModel):
    user_id: str
    email: str
    workspace_id: str
    role: str
    full_name: str | None = None
    company: str | None = None
    created_at: str


class TeamUsersResponse(BaseModel):
    workspace_id: str
    actor_role: str
    total: int
    items: list[TeamUserItem] = Field(default_factory=list)


class TeamUserRoleUpdateRequest(BaseModel):
    target_user_id: str = Field(min_length=2, max_length=64)
    role: str = Field(min_length=2, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)


class TeamUserRoleUpdateResponse(BaseModel):
    status: str
    item: TeamUserItem
