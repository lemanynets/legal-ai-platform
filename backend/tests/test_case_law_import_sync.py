from __future__ import annotations

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


def test_case_law_import_upsert_and_validation(client: TestClient) -> None:
    payload = {
        "records": [
            {
                "source": "manual",
                "decision_id": "imp-001",
                "court_name": "Supreme Court",
                "court_type": "civil",
                "decision_date": "2025-01-11",
                "case_number": "200/1/25",
                "subject_categories": ["loan", "debt"],
                "legal_positions": {"article 625": "3% interest recoverable"},
                "summary": "Initial summary",
            }
        ]
    }
    response = client.post("/api/case-law/import", json=payload, headers={"X-Demo-User": "demo-user"})
    assert response.status_code == 200
    first = response.json()
    assert first["created"] == 1
    assert first["updated"] == 0
    assert first["total"] == 1

    payload["records"][0]["summary"] = "Updated summary"
    response_again = client.post("/api/case-law/import", json=payload, headers={"X-Demo-User": "demo-user"})
    assert response_again.status_code == 200
    second = response_again.json()
    assert second["created"] == 0
    assert second["updated"] == 1
    assert second["total"] == 1

    search = client.get(
        "/api/case-law/search",
        params={"query": "imp-001", "page": 1, "page_size": 10},
        headers={"X-Demo-User": "demo-user"},
    )
    assert search.status_code == 200
    search_payload = search.json()
    assert search_payload["total"] == 1
    assert search_payload["items"][0]["summary"] == "Updated summary"

    invalid = client.post("/api/case-law/import", json={"records": [{"source": "manual"}]}, headers={"X-Demo-User": "demo-user"})
    assert invalid.status_code == 422


def test_case_law_sync_seed_fallback_is_idempotent(client: TestClient) -> None:
    first_sync = client.post(
        "/api/case-law/sync",
        json={"limit": 2},
        headers={"X-Demo-User": "demo-user"},
    )
    assert first_sync.status_code == 200
    first_payload = first_sync.json()
    assert first_payload["status"] == "ok"
    assert first_payload["created"] == 2
    assert first_payload["updated"] == 0
    assert first_payload["total"] == 2
    assert first_payload["seed_fallback_used"] is True
    assert "manual_seed" in (first_payload.get("fetched_counts") or {})

    second_sync = client.post(
        "/api/case-law/sync",
        json={"limit": 2},
        headers={"X-Demo-User": "demo-user"},
    )
    assert second_sync.status_code == 200
    second_payload = second_sync.json()
    assert second_payload["status"] == "ok"
    assert second_payload["created"] == 0
    assert second_payload["updated"] == 2
    assert second_payload["total"] == 2
    assert second_payload["seed_fallback_used"] is True

    search = client.get(
        "/api/case-law/search",
        params={"query": "vs-625-civil-001", "page": 1, "page_size": 10},
        headers={"X-Demo-User": "demo-user"},
    )
    assert search.status_code == 200
    result = search.json()
    assert result["total"] == 1
    assert result["items"][0]["source"] == "manual_seed"


def test_case_law_sync_status_endpoint(client: TestClient) -> None:
    status_before = client.get("/api/case-law/sync/status", headers={"X-Demo-User": "demo-user"})
    assert status_before.status_code == 200
    before_payload = status_before.json()
    assert before_payload["total_records"] == 0
    assert before_payload["last_sync_at"] is None

    sync_response = client.post(
        "/api/case-law/sync",
        json={"limit": 2},
        headers={"X-Demo-User": "demo-user"},
    )
    assert sync_response.status_code == 200
    sync_payload = sync_response.json()
    assert sync_payload["total"] == 2

    status_after = client.get("/api/case-law/sync/status", headers={"X-Demo-User": "demo-user"})
    assert status_after.status_code == 200
    after_payload = status_after.json()
    assert after_payload["total_records"] >= 2
    assert after_payload["last_sync_action"] == "case_law_sync"
    assert after_payload["last_sync_total"] == 2
    assert isinstance(after_payload["last_sync_sources"], list)
    assert "manual_seed" in (after_payload["sources"] or {})


def test_case_law_sync_can_disable_seed_fallback(client: TestClient) -> None:
    sync_response = client.post(
        "/api/case-law/sync",
        json={"limit": 2, "allow_seed_fallback": False, "sources": ["opendatabot", "json_feed"]},
        headers={"X-Demo-User": "demo-user"},
    )
    assert sync_response.status_code == 200
    payload = sync_response.json()
    assert payload["status"] == "ok"
    assert payload["seed_fallback_used"] is False
    assert payload["total"] == 0


def test_case_law_digest_endpoint(client: TestClient) -> None:
    synced = client.post(
        "/api/case-law/sync",
        json={"limit": 3},
        headers={"X-Demo-User": "demo-user"},
    )
    assert synced.status_code == 200

    digest = client.get(
        "/api/case-law/digest",
        params={"days": 3650, "limit": 5, "only_supreme": "true"},
        headers={"X-Demo-User": "demo-user"},
    )
    assert digest.status_code == 200
    payload = digest.json()
    assert payload["days"] == 3650
    assert payload["limit"] == 5
    assert payload["only_supreme"] is True
    assert payload["total"] >= 1
    assert len(payload["items"]) >= 1
    assert all("supreme" in (item["court_name"] or "").lower() for item in payload["items"])
    assert payload["items"][0]["prompt_snippet"]
    assert payload["saved"] is False
    assert payload["digest_id"] is None


def test_case_law_digest_save_and_history(client: TestClient) -> None:
    synced = client.post(
        "/api/case-law/sync",
        json={"limit": 3},
        headers={"X-Demo-User": "demo-user"},
    )
    assert synced.status_code == 200

    generated = client.post(
        "/api/case-law/digest/generate",
        json={
            "days": 3650,
            "limit": 5,
            "only_supreme": True,
            "save": True,
            "title": "Weekly SC digest",
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert generated.status_code == 200
    generated_payload = generated.json()
    assert generated_payload["saved"] is True
    digest_id = generated_payload["digest_id"]
    assert digest_id
    assert generated_payload["title"] == "Weekly SC digest"

    history = client.get("/api/case-law/digest/history", headers={"X-Demo-User": "demo-user"})
    assert history.status_code == 200
    history_payload = history.json()
    assert history_payload["total"] >= 1
    assert any(item["id"] == digest_id for item in history_payload["items"])

    detail = client.get(f"/api/case-law/digest/history/{digest_id}", headers={"X-Demo-User": "demo-user"})
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["digest_id"] == digest_id
    assert detail_payload["saved"] is True
    assert detail_payload["title"] == "Weekly SC digest"
    assert len(detail_payload["items"]) >= 1


def test_case_law_sync_requires_pro_plus_plan(client: TestClient, test_session_factory) -> None:
    with test_session_factory() as db:
        row = db.execute(select(Subscription).where(Subscription.user_id == "demo-user")).scalar_one()
        row.plan = "PRO"
        db.commit()

    response = client.post(
        "/api/case-law/sync",
        json={"limit": 2},
        headers={"X-Demo-User": "demo-user"},
    )
    assert response.status_code == 403
    assert "requires at least PRO_PLUS plan" in response.json()["detail"]


def test_case_law_saved_digest_history_requires_pro_plan(client: TestClient, test_session_factory) -> None:
    with test_session_factory() as db:
        row = db.execute(select(Subscription).where(Subscription.user_id == "demo-user")).scalar_one()
        row.plan = "START"
        db.commit()

    response = client.get("/api/case-law/digest/history", headers={"X-Demo-User": "demo-user"})
    assert response.status_code == 403
    assert "requires at least PRO plan" in response.json()["detail"]
