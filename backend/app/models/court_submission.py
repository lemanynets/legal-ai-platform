from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class CourtSubmission(Base):
    __tablename__ = "court_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("generated_documents.id", ondelete="SET NULL"), index=True, nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="court_gov_ua")
    external_submission_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="submitted", index=True)
    court_name: Mapped[str] = mapped_column(String(255), nullable=False)
    signer_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    request_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tracking_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="court_submissions")
    document = relationship("GeneratedDocument", back_populates="court_submissions")
