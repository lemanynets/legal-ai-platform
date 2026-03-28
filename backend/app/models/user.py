"""User model — SQLAlchemy ORM + Pydantic schema."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    company = Column(String(255))
    role = Column(String(50), default="user")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class UserSchema(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    company: str | None = None
    role: str = "user"

    class Config:
        from_attributes = True
