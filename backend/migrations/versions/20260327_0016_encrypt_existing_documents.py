"""Encrypt existing generated document payloads when DOCUMENT_ENCRYPTION_KEY is configured.

Revision ID: 20260327_0016
Revises: 58aebf14af7c
Create Date: 2026-03-27 14:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.services.document_crypto import encrypt_json, encrypt_text


# revision identifiers, used by Alembic.
revision = "20260327_0016"
down_revision = "58aebf14af7c"
branch_labels = None
depends_on = None


generated_documents = sa.table(
    "generated_documents",
    sa.column("id", sa.String(length=36)),
    sa.column("form_data", sa.JSON()),
    sa.column("generated_text", sa.Text()),
)

document_versions = sa.table(
    "document_versions",
    sa.column("id", sa.String(length=36)),
    sa.column("generated_text", sa.Text()),
)


def upgrade() -> None:
    bind = op.get_bind()

    generated_rows = list(
        bind.execute(
            sa.select(
                generated_documents.c.id,
                generated_documents.c.form_data,
                generated_documents.c.generated_text,
            )
        )
        .mappings()
        .all()
    )
    for row in generated_rows:
        bind.execute(
            generated_documents.update()
            .where(generated_documents.c.id == row["id"])
            .values(
                form_data=encrypt_json(row["form_data"] or {}),
                generated_text=encrypt_text(row["generated_text"] or ""),
            )
        )

    version_rows = list(
        bind.execute(
            sa.select(document_versions.c.id, document_versions.c.generated_text)
        )
        .mappings()
        .all()
    )
    for row in version_rows:
        bind.execute(
            document_versions.update()
            .where(document_versions.c.id == row["id"])
            .values(generated_text=encrypt_text(row["generated_text"] or ""))
        )


def downgrade() -> None:
    # Intentionally no-op: encrypted data should not be downgraded back to plaintext automatically.
    pass
