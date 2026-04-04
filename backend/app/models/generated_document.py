from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    document_category: Mapped[str] = mapped_column(String(50), nullable=False)
    form_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    generated_text: Mapped[str] = mapped_column(Text, nullable=False)
    preview_text: Mapped[str] = mapped_column(Text, nullable=False)
    calculations: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    court_fee_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    used_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    docx_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True)

    user = relationship("User", back_populates="generated_documents")
    case = relationship("Case", back_populates="documents")
    deadlines = relationship("Deadline", back_populates="document")
    case_law_refs = relationship("DocumentCaseLawRef", back_populates="document", cascade="all, delete-orphan")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    court_submissions = relationship("CourtSubmission", back_populates="document")
