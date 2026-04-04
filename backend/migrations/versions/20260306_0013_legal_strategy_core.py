"""add legal strategy core tables (intake, precedent groups, blueprints, generation audit)

Revision ID: 20260306_0013
Revises: 20260303_0012
Create Date: 2026-03-06 09:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260306_0013"
down_revision = "20260303_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_analysis_intake",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("source_file_name", sa.String(length=500), nullable=True),
        sa.Column("classified_type", sa.String(length=80), nullable=False),
        sa.Column("document_language", sa.String(length=20), nullable=True),
        sa.Column("jurisdiction", sa.String(length=20), nullable=False, server_default="UA"),
        sa.Column("primary_party_role", sa.String(length=50), nullable=True),
        sa.Column("identified_parties", sa.JSON(), nullable=True),
        sa.Column("subject_matter", sa.String(length=80), nullable=True),
        sa.Column("financial_exposure_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("financial_exposure_currency", sa.String(length=10), nullable=True),
        sa.Column("financial_exposure_type", sa.String(length=50), nullable=True),
        sa.Column("document_date", sa.Date(), nullable=True),
        sa.Column("deadline_from_document", sa.Date(), nullable=True),
        sa.Column("urgency_level", sa.String(length=20), nullable=True),
        sa.Column("risk_level_legal", sa.String(length=20), nullable=True),
        sa.Column("risk_level_procedural", sa.String(length=20), nullable=True),
        sa.Column("risk_level_financial", sa.String(length=20), nullable=True),
        sa.Column("detected_issues", sa.JSON(), nullable=True),
        sa.Column("classifier_confidence", sa.Float(), nullable=True),
        sa.Column("classifier_model", sa.String(length=100), nullable=True),
        sa.Column("raw_text_preview", sa.Text(), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_analysis_intake_user_id", "document_analysis_intake", ["user_id"], unique=False)

    op.create_table(
        "case_law_precedent_groups",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("intake_id", sa.String(length=36), nullable=False),
        sa.Column("pattern_type", sa.String(length=40), nullable=False),
        sa.Column("pattern_description", sa.Text(), nullable=True),
        sa.Column("precedent_ids", sa.JSON(), nullable=True),
        sa.Column("precedent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pattern_strength", sa.Float(), nullable=True),
        sa.Column("counter_arguments", sa.JSON(), nullable=True),
        sa.Column("mitigation_strategy", sa.Text(), nullable=True),
        sa.Column("strategic_advantage", sa.Text(), nullable=True),
        sa.Column("vulnerability_to_appeal", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["intake_id"], ["document_analysis_intake.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_law_precedent_groups_user_id", "case_law_precedent_groups", ["user_id"], unique=False)
    op.create_index("ix_case_law_precedent_groups_intake_id", "case_law_precedent_groups", ["intake_id"], unique=False)

    op.create_table(
        "legal_strategy_blueprint",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("intake_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column("precedent_group_id", sa.String(length=36), nullable=True),
        sa.Column("immediate_actions", sa.JSON(), nullable=True),
        sa.Column("procedural_roadmap", sa.JSON(), nullable=True),
        sa.Column("evidence_strategy", sa.JSON(), nullable=True),
        sa.Column("negotiation_playbook", sa.JSON(), nullable=True),
        sa.Column("risk_heat_map", sa.JSON(), nullable=True),
        sa.Column("critical_deadlines", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("confidence_rationale", sa.Text(), nullable=True),
        sa.Column("recommended_next_steps", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["generated_documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["intake_id"], ["document_analysis_intake.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["precedent_group_id"], ["case_law_precedent_groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_legal_strategy_blueprint_user_id", "legal_strategy_blueprint", ["user_id"], unique=False)
    op.create_index("ix_legal_strategy_blueprint_intake_id", "legal_strategy_blueprint", ["intake_id"], unique=False)
    op.create_index(
        "ix_legal_strategy_blueprint_document_id", "legal_strategy_blueprint", ["document_id"], unique=False
    )
    op.create_index(
        "ix_legal_strategy_blueprint_precedent_group_id",
        "legal_strategy_blueprint",
        ["precedent_group_id"],
        unique=False,
    )

    op.create_table(
        "document_generation_audit",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("strategy_blueprint_id", sa.String(length=36), nullable=True),
        sa.Column("precedent_citations", sa.JSON(), nullable=True),
        sa.Column("counter_argument_addresses", sa.JSON(), nullable=True),
        sa.Column("evidence_positioning_notes", sa.Text(), nullable=True),
        sa.Column("procedure_optimization_notes", sa.Text(), nullable=True),
        sa.Column("appeal_proofing_notes", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["generated_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["strategy_blueprint_id"], ["legal_strategy_blueprint.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_generation_audit_document_id", "document_generation_audit", ["document_id"], unique=False)
    op.create_index(
        "ix_document_generation_audit_strategy_blueprint_id",
        "document_generation_audit",
        ["strategy_blueprint_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_generation_audit_strategy_blueprint_id", table_name="document_generation_audit")
    op.drop_index("ix_document_generation_audit_document_id", table_name="document_generation_audit")
    op.drop_table("document_generation_audit")

    op.drop_index("ix_legal_strategy_blueprint_precedent_group_id", table_name="legal_strategy_blueprint")
    op.drop_index("ix_legal_strategy_blueprint_document_id", table_name="legal_strategy_blueprint")
    op.drop_index("ix_legal_strategy_blueprint_intake_id", table_name="legal_strategy_blueprint")
    op.drop_index("ix_legal_strategy_blueprint_user_id", table_name="legal_strategy_blueprint")
    op.drop_table("legal_strategy_blueprint")

    op.drop_index("ix_case_law_precedent_groups_intake_id", table_name="case_law_precedent_groups")
    op.drop_index("ix_case_law_precedent_groups_user_id", table_name="case_law_precedent_groups")
    op.drop_table("case_law_precedent_groups")

    op.drop_index("ix_document_analysis_intake_user_id", table_name="document_analysis_intake")
    op.drop_table("document_analysis_intake")
