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
                plan="PRO",
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


def test_auto_process_generates_documents(client: TestClient) -> None:
    file_content = (
        "Позивач: Іван Іванов\n"
        "Відповідач: Петро Петров\n"
        "Заборгованість за договором позики становить 150000 грн.\n"
    )
    response = client.post(
        "/api/auto/process",
        data={"max_documents": "2"},
        files={"file": ("sample.txt", file_content.encode("utf-8"), "text/plain")},
        headers={"X-Demo-User": "demo-user"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["source_file_name"] == "sample.txt"
    assert payload["extracted_chars"] > 20
    assert len(payload["recommended_doc_types"]) >= 1
    assert len(payload["procedural_conclusions"]) >= 1
    assert len(payload["generated_documents"]) >= 1


def test_auto_process_respects_doc_quota(client: TestClient, test_session_factory) -> None:
    with test_session_factory() as db:
        subscription = db.execute(select(Subscription).where(Subscription.user_id == "demo-user")).scalar_one()
        subscription.plan = "FREE"
        subscription.docs_limit = 1
        subscription.analyses_limit = 1
        subscription.docs_used = 0
        subscription.analyses_used = 0
        db.commit()

    response = client.post(
        "/api/auto/process",
        data={"max_documents": "3"},
        files={
            "file": (
                "sample.txt",
                "Позивач: A\nВідповідач: B\nБорг 10000 грн за договором позики".encode("utf-8"),
                "text/plain",
            )
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["generated_documents"]) == 1
    assert len(payload["warnings"]) >= 1


def test_auto_process_requires_active_subscription(client: TestClient, test_session_factory) -> None:
    with test_session_factory() as db:
        subscription = db.execute(select(Subscription).where(Subscription.user_id == "demo-user")).scalar_one()
        subscription.status = "payment_failed"
        db.commit()

    response = client.post(
        "/api/auto/process",
        data={"max_documents": "1"},
        files={"file": ("sample.txt", "Борг 10000 грн".encode("utf-8"), "text/plain")},
        headers={"X-Demo-User": "demo-user"},
    )
    assert response.status_code == 402
    assert "Subscription is not active" in response.json()["detail"]
