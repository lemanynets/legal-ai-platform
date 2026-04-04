from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class CaseLawCache(Base):
    __tablename__ = "case_law_cache"
    __table_args__ = (UniqueConstraint("source", "decision_id", name="uq_case_law_cache_source_decision_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    decision_id: Mapped[str] = mapped_column(String(255), nullable=False)
    court_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    court_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    decision_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    case_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject_categories: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    legal_positions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    document_refs = relationship("DocumentCaseLawRef", back_populates="case_law", cascade="all, delete-orphan")


class DocumentCaseLawRef(Base):
    __tablename__ = "document_case_law_refs"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generated_documents.id", ondelete="CASCADE"), primary_key=True
    )
    case_law_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("case_law_cache.id", ondelete="CASCADE"), primary_key=True
    )
    relevance_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    document = relationship("GeneratedDocument", back_populates="case_law_refs")
    case_law = relationship("CaseLawCache", back_populates="document_refs")
