from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class ContractAnalysis(Base):
    __tablename__ = "contract_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contract_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    critical_risks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    medium_risks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ok_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship("User", back_populates="contract_analyses")
