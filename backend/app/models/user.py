from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workspace_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="personal"
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    branding_config: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON config

    # User Profile Extensions
    entity_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # "individual" or "legal_entity"
    tax_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # ІПН або ЄДРПОУ
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    subscriptions = relationship("Subscription", back_populates="user")
    generated_documents = relationship("GeneratedDocument", back_populates="user")
    contract_analyses = relationship("ContractAnalysis", back_populates="user")
    analysis_cache = relationship("AnalysisCache", back_populates="user")
    intake_cache = relationship("IntakeCache", back_populates="user")
    analytics_events = relationship("AnalyticsEvent", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    deadlines = relationship("Deadline", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    document_versions = relationship("DocumentVersion", back_populates="user")
    case_law_digests = relationship("CaseLawDigest", back_populates="user")
    court_submissions = relationship("CourtSubmission", back_populates="user")
    registry_watch_items = relationship("RegistryWatchItem", back_populates="user")
    registry_monitor_events = relationship(
        "RegistryMonitorEvent", back_populates="user"
    )
    calculation_runs = relationship("CalculationRun", back_populates="user")
    full_lawyer_preflight_reports = relationship(
        "FullLawyerPreflightReport", back_populates="user"
    )
    analysis_intakes = relationship("DocumentAnalysisIntake", back_populates="user")
    forum_posts = relationship("ForumPost", back_populates="user")
    forum_comments = relationship("ForumComment", back_populates="user")
    cases = relationship("Case", back_populates="user")
