from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import get_db
from app.main import app
from app.models import AuditLog, Base, User


@pytest.fixture()
def test_session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    try:
        yield SessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(test_session_factory):
    with test_session_factory() as db:
        db: Session
        db.add(User(id="demo-user", email="demo-user@local.dev"))
        db.commit()

    def override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def _generate_audit_events(client: TestClient) -> None:
    response_1 = client.get("/api/case-law/search?page=1&page_size=5", headers={"X-Demo-User": "demo-user"})
    assert response_1.status_code == 200
    response_2 = client.get(
        "/api/case-law/search?page=1&page_size=5&query=debt",
        headers={"X-Demo-User": "demo-user"},
    )
    assert response_2.status_code == 200


def test_audit_integrity_passes_for_clean_chain(client: TestClient) -> None:
    _generate_audit_events(client)
    response = client.get("/api/audit/integrity?max_rows=2000", headers={"X-Demo-User": "demo-user"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "user:demo-user"
    assert payload["status"] == "pass"
    assert payload["rows_checked"] >= 2
    assert payload["issues"] == []
    assert isinstance(payload["head_hash"], str) and len(payload["head_hash"]) == 64


def test_audit_integrity_detects_tampering(client: TestClient, test_session_factory) -> None:
    _generate_audit_events(client)
    with test_session_factory() as db:
        db: Session
        row = db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == "demo-user", AuditLog.action == "case_law_search")
            .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
            .limit(1)
        ).scalar_one()
        row.metadata_json = {"tampered": True}
        db.commit()

    response = client.get("/api/audit/integrity?max_rows=2000", headers={"X-Demo-User": "demo-user"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fail"
    assert len(payload["issues"]) >= 1
    issue_codes = [str(item.get("code") or "") for item in payload["issues"]]
    assert ("PAYLOAD_HASH_MISMATCH" in issue_codes) or ("ROW_HASH_MISMATCH" in issue_codes)
