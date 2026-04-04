from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import get_db
from app.main import app
from app.models import Base, Subscription, User


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
        db.add(
            User(
                id="viewer-user",
                email="viewer-user@local.dev",
                role="viewer",
                workspace_id="ws-viewer-user",
            )
        )
        db.add(
            Subscription(
                user_id="viewer-user",
                plan="PRO_PLUS",
                status="active",
                analyses_used=0,
                analyses_limit=None,
                docs_used=0,
                docs_limit=None,
            )
        )
        db.add(
            User(
                id="owner-user",
                email="owner-user@local.dev",
                role="owner",
                workspace_id="ws-owner-user",
            )
        )
        db.add(
            Subscription(
                user_id="owner-user",
                plan="PRO_PLUS",
                status="active",
                analyses_used=0,
                analyses_limit=None,
                docs_used=0,
                docs_limit=None,
            )
        )
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


def test_viewer_can_read_case_law_search(client: TestClient) -> None:
    response = client.get(
        "/api/case-law/search?page=1&page_size=5",
        headers={"X-Demo-User": "viewer-user"},
    )
    assert response.status_code == 200


def test_viewer_cannot_sync_case_law(client: TestClient) -> None:
    response = client.post(
        "/api/case-law/sync",
        json={"query": "debt", "limit": 10, "sources": ["manual_seed"]},
        headers={"X-Demo-User": "viewer-user"},
    )
    assert response.status_code == 403
    assert "role" in str(response.json().get("detail", "")).lower()


def test_viewer_cannot_manage_subscription(client: TestClient) -> None:
    response = client.post(
        "/api/billing/subscribe",
        json={"plan": "FREE", "mode": "subscription"},
        headers={"X-Demo-User": "viewer-user"},
    )
    assert response.status_code == 403
    assert "role" in str(response.json().get("detail", "")).lower()


def test_viewer_cannot_run_audit_integrity(client: TestClient) -> None:
    response = client.get(
        "/api/audit/integrity?max_rows=100",
        headers={"X-Demo-User": "viewer-user"},
    )
    assert response.status_code == 403
    assert "role" in str(response.json().get("detail", "")).lower()


def test_owner_can_sync_case_law(client: TestClient) -> None:
    response = client.post(
        "/api/case-law/sync",
        json={"query": "debt", "limit": 5, "allow_seed_fallback": True},
        headers={"X-Demo-User": "owner-user"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
