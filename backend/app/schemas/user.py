from __future__ import annotations
from pydantic import BaseModel, Field

class ProfileUpdateRequest(BaseModel):
    logo_url: str | None = None
    company: str | None = None
