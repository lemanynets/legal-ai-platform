from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class CaseLawDigest(Base):
    __tablename__ = "case_law_digests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    limit: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    only_supreme: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    court_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sources_json: Mapped[list[str]] = mapped_column("sources", JSON, nullable=False, default=list)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="case_law_digests")
    items = relationship(
        "CaseLawDigestItem",
        back_populates="digest",
        cascade="all, delete-orphan",
        order_by="CaseLawDigestItem.sort_order",
    )


class CaseLawDigestItem(Base):
    __tablename__ = "case_law_digest_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    digest_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("case_law_digests.id", ondelete="CASCADE"), index=True
    )
    case_law_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("case_law_cache.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    decision_id: Mapped[str] = mapped_column(String(255), nullable=False)
    court_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    court_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decision_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    case_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject_categories: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    legal_positions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prompt_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    digest = relationship("CaseLawDigest", back_populates="items")
    case_law = relationship("CaseLawCache")
