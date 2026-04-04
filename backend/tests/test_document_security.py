from __future__ import annotations

from pathlib import Path
import sys

from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import Base, DocumentVersion, GeneratedDocument, User
from app.services import document_crypto
from app.services.document_versions import create_document_version, get_document_version, get_version_generated_text
from app.services.generated_documents import (
    create_generated_document,
    get_accessible_user_ids,
    get_document_form_data,
    get_document_generated_text,
    get_generated_document,
)


def _session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False), engine


def test_document_crypto_roundtrip_and_storage_encrypted(monkeypatch) -> None:
    monkeypatch.setattr(document_crypto, "_fernet", Fernet(Fernet.generate_key()))

    SessionLocal, engine = _session_factory()
    try:
        with SessionLocal() as db:
            db.add(User(id="u1", email="u1@example.com", workspace_id="ws-1", role="owner"))
            db.commit()

            row = create_generated_document(
                db,
                user_id="u1",
                document_type="claim",
                document_category="lawsuit",
                form_data={"tax_id": "1234567890", "address": "Kyiv"},
                generated_text="Secret body",
                preview_text="Preview body",
                calculations={},
                ai_model="test-model",
                used_ai=True,
                ai_error=None,
            )

            raw_row = db.get(GeneratedDocument, row.id)
            assert raw_row is not None
            assert raw_row.generated_text != "Secret body"
            assert "__encrypted__" in (raw_row.form_data or {})

            assert get_document_generated_text(raw_row) == "Secret body"
            assert get_document_form_data(raw_row) == {"tax_id": "1234567890", "address": "Kyiv"}
    finally:
        Base.metadata.drop_all(bind=engine)


def test_workspace_acl_allows_same_workspace_and_blocks_other_workspace(monkeypatch) -> None:
    monkeypatch.setattr(document_crypto, "_fernet", None)

    SessionLocal, engine = _session_factory()
    try:
        with SessionLocal() as db:
            db.add_all(
                [
                    User(id="owner-a", email="owner-a@example.com", workspace_id="ws-a", role="owner"),
                    User(id="member-a", email="member-a@example.com", workspace_id="ws-a", role="lawyer"),
                    User(id="owner-b", email="owner-b@example.com", workspace_id="ws-b", role="owner"),
                ]
            )
            db.commit()

            doc = create_generated_document(
                db,
                user_id="owner-a",
                document_type="claim",
                document_category="lawsuit",
                form_data={"party": "A"},
                generated_text="Workspace A secret",
                preview_text="Workspace A preview",
                calculations={},
                ai_model="test-model",
                used_ai=False,
                ai_error=None,
            )

            assert set(get_accessible_user_ids(db, "member-a")) == {"owner-a", "member-a"}
            assert get_generated_document(db, "member-a", doc.id) is not None
            assert get_generated_document(db, "owner-b", doc.id) is None
    finally:
        Base.metadata.drop_all(bind=engine)


def test_document_versions_are_encrypted_and_workspace_scoped(monkeypatch) -> None:
    monkeypatch.setattr(document_crypto, "_fernet", Fernet(Fernet.generate_key()))

    SessionLocal, engine = _session_factory()
    try:
        with SessionLocal() as db:
            db.add_all(
                [
                    User(id="owner-a", email="owner-a@example.com", workspace_id="ws-a", role="owner"),
                    User(id="member-a", email="member-a@example.com", workspace_id="ws-a", role="lawyer"),
                    User(id="owner-b", email="owner-b@example.com", workspace_id="ws-b", role="owner"),
                ]
            )
            db.commit()

            doc = create_generated_document(
                db,
                user_id="owner-a",
                document_type="claim",
                document_category="lawsuit",
                form_data={"party": "A"},
                generated_text="Versioned text",
                preview_text="Preview",
                calculations={},
                ai_model="test-model",
                used_ai=True,
                ai_error=None,
            )

            version = create_document_version(db, document=doc, action="generate")
            raw_version = db.get(DocumentVersion, version.id)
            assert raw_version is not None
            assert raw_version.generated_text != "Versioned text"
            assert get_version_generated_text(raw_version) == "Versioned text"

            assert get_document_version(db, user_id="member-a", document_id=doc.id, version_id=version.id) is not None
            assert get_document_version(db, user_id="owner-b", document_id=doc.id, version_id=version.id) is None
    finally:
        Base.metadata.drop_all(bind=engine)