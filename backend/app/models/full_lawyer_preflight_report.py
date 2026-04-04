from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class FullLawyerPreflightReport(Base):
    __tablename__ = "full_lawyer_preflight_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False, default="upload", index=True)
    source_file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extracted_chars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    final_submission_gate_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    consume_quota: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    format: Mapped[str | None] = mapped_column(String(10), nullable=True)
    report_title: Mapped[str] = mapped_column(String(500), nullable=False)
    report_text: Mapped[str] = mapped_column(Text, nullable=False)
    meta_json: Mapped[dict | None] = mapped_column("meta", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    user = relationship("User", back_populates="full_lawyer_preflight_reports")

