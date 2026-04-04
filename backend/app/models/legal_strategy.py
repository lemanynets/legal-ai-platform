from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class DocumentAnalysisIntake(Base):
    __tablename__ = "document_analysis_intake"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)

    classified_type: Mapped[str] = mapped_column(String(80), nullable=False)
    document_language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    jurisdiction: Mapped[str] = mapped_column(String(20), nullable=False, default="UA")

    primary_party_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    identified_parties: Mapped[list | None] = mapped_column(JSON, nullable=True)
    subject_matter: Mapped[str | None] = mapped_column(String(80), nullable=True)

    financial_exposure_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    financial_exposure_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    financial_exposure_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline_from_document: Mapped[date | None] = mapped_column(Date, nullable=True)
    urgency_level: Mapped[str | None] = mapped_column(String(20), nullable=True)

    risk_level_legal: Mapped[str | None] = mapped_column(String(20), nullable=True)
    risk_level_procedural: Mapped[str | None] = mapped_column(String(20), nullable=True)
    risk_level_financial: Mapped[str | None] = mapped_column(String(20), nullable=True)

    detected_issues: Mapped[list | None] = mapped_column(JSON, nullable=True)
    classifier_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    classifier_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    raw_text_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    user = relationship("User", back_populates="analysis_intakes")
    precedent_groups = relationship("CaseLawPrecedentGroup", back_populates="intake", cascade="all, delete-orphan")
    strategy_blueprints = relationship(
        "LegalStrategyBlueprint", back_populates="intake", cascade="all, delete-orphan"
    )


class CaseLawPrecedentGroup(Base):
    __tablename__ = "case_law_precedent_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    intake_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_analysis_intake.id", ondelete="CASCADE"), index=True
    )

    pattern_type: Mapped[str] = mapped_column(String(40), nullable=False)
    pattern_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    precedent_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    precedent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pattern_strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    counter_arguments: Mapped[list | None] = mapped_column(JSON, nullable=True)
    mitigation_strategy: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategic_advantage: Mapped[str | None] = mapped_column(Text, nullable=True)
    vulnerability_to_appeal: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship("User")
    intake = relationship("DocumentAnalysisIntake", back_populates="precedent_groups")
    strategy_blueprints = relationship("LegalStrategyBlueprint", back_populates="precedent_group")


class LegalStrategyBlueprint(Base):
    __tablename__ = "legal_strategy_blueprint"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    intake_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_analysis_intake.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("generated_documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    precedent_group_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("case_law_precedent_groups.id", ondelete="SET NULL"), nullable=True, index=True
    )

    immediate_actions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    procedural_roadmap: Mapped[list | None] = mapped_column(JSON, nullable=True)
    evidence_strategy: Mapped[list | None] = mapped_column(JSON, nullable=True)
    negotiation_playbook: Mapped[list | None] = mapped_column(JSON, nullable=True)
    risk_heat_map: Mapped[list | None] = mapped_column(JSON, nullable=True)
    critical_deadlines: Mapped[list | None] = mapped_column(JSON, nullable=True)
    swot_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    win_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    financial_strategy: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timeline_projection: Mapped[list | None] = mapped_column(JSON, nullable=True)
    penalty_forecast: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_next_steps: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    user = relationship("User")
    intake = relationship("DocumentAnalysisIntake", back_populates="strategy_blueprints")
    document = relationship("GeneratedDocument")
    precedent_group = relationship("CaseLawPrecedentGroup", back_populates="strategy_blueprints")
    generation_audits = relationship("DocumentGenerationAudit", back_populates="strategy_blueprint")


class DocumentGenerationAudit(Base):
    __tablename__ = "document_generation_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("generated_documents.id", ondelete="CASCADE"), index=True
    )
    strategy_blueprint_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("legal_strategy_blueprint.id", ondelete="SET NULL"), nullable=True, index=True
    )

    precedent_citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    counter_argument_addresses: Mapped[list | None] = mapped_column(JSON, nullable=True)
    evidence_positioning_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    procedure_optimization_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    appeal_proofing_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    document = relationship("GeneratedDocument")
    strategy_blueprint = relationship("LegalStrategyBlueprint", back_populates="generation_audits")
