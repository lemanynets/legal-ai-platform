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
from app.models import Base, User


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
                id="owner-user",
                email="owner-user@local.dev",
                role="owner",
                workspace_id="ws-alpha",
            )
        )
        db.add(
            User(
                id="admin-user",
                email="admin-user@local.dev",
                role="admin",
                workspace_id="ws-alpha",
            )
        )
        db.add(
            User(
                id="viewer-user",
                email="viewer-user@local.dev",
                role="viewer",
                workspace_id="ws-alpha",
            )
        )
        db.add(
            User(
                id="external-user",
                email="external-user@local.dev",
                role="viewer",
                workspace_id="ws-beta",
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


def test_owner_can_list_workspace_users(client: TestClient) -> None:
    response = client.get("/api/auth/team/users", headers={"X-Demo-User": "owner-user"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == "ws-alpha"
    ids = {item["user_id"] for item in payload["items"]}
    assert "owner-user" in ids
    assert "admin-user" in ids
    assert "viewer-user" in ids
    assert "external-user" not in ids


def test_auth_me_includes_workspace_and_role(client: TestClient) -> None:
    response = client.get("/api/auth/me", headers={"X-Demo-User": "admin-user"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == "ws-alpha"
    assert payload["role"] == "admin"


def test_viewer_cannot_list_workspace_users(client: TestClient) -> None:
    response = client.get("/api/auth/team/users", headers={"X-Demo-User": "viewer-user"})
    assert response.status_code == 403


def test_admin_cannot_assign_owner_role(client: TestClient) -> None:
    response = client.post(
        "/api/auth/team/users/role",
        json={"target_user_id": "viewer-user", "role": "owner"},
        headers={"X-Demo-User": "admin-user"},
    )
    assert response.status_code == 403


def test_owner_can_update_team_role(client: TestClient, test_session_factory) -> None:
    response = client.post(
        "/api/auth/team/users/role",
        json={
            "target_user_id": "viewer-user",
            "role": "lawyer",
            "full_name": "New Lawyer",
            "company": "Top Legal LLC",
        },
        headers={"X-Demo-User": "owner-user"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["item"]["role"] == "lawyer"
    with test_session_factory() as db:
        row = db.execute(select(User).where(User.id == "viewer-user")).scalar_one()
        assert row.role == "lawyer"
        assert row.full_name == "New Lawyer"


def test_admin_cannot_update_other_workspace_user(client: TestClient) -> None:
    response = client.post(
        "/api/auth/team/users/role",
        json={"target_user_id": "external-user", "role": "analyst"},
        headers={"X-Demo-User": "admin-user"},
    )
    assert response.status_code == 403
