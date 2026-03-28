"""Case model — SQLAlchemy ORM + Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    case_number = Column(String(100))
    status = Column(String(50), default="open")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    case_number: Optional[str] = None
    status: str = "open"


class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    case_number: Optional[str] = None
    status: Optional[str] = None


class CaseInDB(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    case_number: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CaseDetail(CaseInDB):
    pass
