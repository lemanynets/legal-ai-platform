from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import get_db
from app.main import app
from app.models import Base, RegistryWatchItem, Subscription, User


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
        db.add(User(id="demo-user", email="demo-user@local.dev"))
        db.add(
            Subscription(
                user_id="demo-user",
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


def test_registry_monitoring_create_list_check_events(client: TestClient) -> None:
    created = client.post(
        "/api/monitoring/watch-items",
        json={
            "source": "opendatabot",
            "registry_type": "edr",
            "identifier": "12345678",
            "entity_name": "Demo LLC",
            "check_interval_hours": 24,
            "notes": "Watch legal changes",
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert created.status_code == 200
    created_payload = created.json()
    assert created_payload["status"] == "created"
    assert created_payload["item"]["identifier"] == "12345678"
    watch_item_id = created_payload["item"]["id"]

    listed = client.get("/api/monitoring/watch-items", headers={"X-Demo-User": "demo-user"})
    assert listed.status_code == 200
    listed_payload = listed.json()
    assert listed_payload["total"] == 1
    assert listed_payload["items"][0]["id"] == watch_item_id

    checked = client.post(
        f"/api/monitoring/watch-items/{watch_item_id}/check",
        json={
            "observed_status": "risk_detected",
            "summary": "New court case found",
            "details": {"case_number": "123/45/26"},
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert checked.status_code == 200
    checked_payload = checked.json()
    assert checked_payload["status"] == "checked"
    assert checked_payload["item"]["status"] == "risk_detected"
    assert checked_payload["event_type"] == "state_changed"

    events = client.get(
        f"/api/monitoring/events?watch_item_id={watch_item_id}",
        headers={"X-Demo-User": "demo-user"},
    )
    assert events.status_code == 200
    events_payload = events.json()
    assert events_payload["total"] == 2
    event_types = [item["event_type"] for item in events_payload["items"]]
    assert "watch_created" in event_types
    assert "state_changed" in event_types


def test_registry_monitoring_requires_pro_plus(client: TestClient, test_session_factory) -> None:
    with test_session_factory() as db:
        subscription = db.execute(select(Subscription).where(Subscription.user_id == "demo-user")).scalar_one()
        subscription.plan = "PRO"
        db.commit()

    response = client.post(
        "/api/monitoring/watch-items",
        json={
            "source": "opendatabot",
            "registry_type": "edr",
            "identifier": "12345678",
            "entity_name": "Demo LLC",
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert response.status_code == 403
    assert "requires at least PRO_PLUS plan" in response.json()["detail"]


def test_registry_monitoring_requires_active_subscription(client: TestClient, test_session_factory) -> None:
    with test_session_factory() as db:
        subscription = db.execute(select(Subscription).where(Subscription.user_id == "demo-user")).scalar_one()
        subscription.status = "payment_failed"
        db.commit()

    response = client.get("/api/monitoring/watch-items", headers={"X-Demo-User": "demo-user"})
    assert response.status_code == 402
    assert "Subscription is not active" in response.json()["detail"]


def test_registry_monitoring_status_and_check_due(client: TestClient, test_session_factory) -> None:
    created = client.post(
        "/api/monitoring/watch-items",
        json={
            "source": "opendatabot",
            "registry_type": "edr",
            "identifier": "risk-12345678",
            "entity_name": "Risk Demo LLC",
            "check_interval_hours": 24,
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert created.status_code == 200
    watch_item_id = created.json()["item"]["id"]

    with test_session_factory() as db:
        row = db.execute(select(RegistryWatchItem).where(RegistryWatchItem.id == watch_item_id)).scalar_one()
        row.next_check_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

    due = client.post(
        "/api/monitoring/check-due",
        json={"limit": 10},
        headers={"X-Demo-User": "demo-user"},
    )
    assert due.status_code == 200
    due_payload = due.json()
    assert due_payload["status"] == "ok"
    assert due_payload["scanned"] == 1
    assert due_payload["checked"] == 1

    status = client.get("/api/monitoring/status", headers={"X-Demo-User": "demo-user"})
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload["total_watch_items"] == 1
    assert status_payload["warning_watch_items"] == 1
    assert status_payload["due_watch_items"] == 0
    assert status_payload["by_status"].get("risk_detected", 0) == 1
