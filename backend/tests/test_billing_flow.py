from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import Base, Subscription, User
from app.services.liqpay import create_signature


@pytest.fixture(autouse=True)
def liqpay_test_keys():
    prev_public = settings.liqpay_public_key
    prev_private = settings.liqpay_private_key
    object.__setattr__(settings, "liqpay_public_key", "test_public_key")
    object.__setattr__(settings, "liqpay_private_key", "test_private_key")
    try:
        yield
    finally:
        object.__setattr__(settings, "liqpay_public_key", prev_public)
        object.__setattr__(settings, "liqpay_private_key", prev_private)


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


def test_paid_subscribe_does_not_activate_plan_before_success_webhook(client: TestClient) -> None:
    subscribe = client.post(
        "/api/billing/subscribe",
        json={"plan": "PRO", "mode": "subscription"},
        headers={"X-Demo-User": "billing-user"},
    )
    assert subscribe.status_code == 200
    payload = subscribe.json()
    assert payload["plan"] == "PRO"
    assert payload["usage"]["plan"] == "FREE"
    assert payload["payment_id"] is not None
    assert payload["liqpay_order_id"] is not None

    before_webhook = client.get("/api/billing/subscription", headers={"X-Demo-User": "billing-user"})
    assert before_webhook.status_code == 200
    assert before_webhook.json()["plan"] == "FREE"

    webhook_payload = {
        "order_id": payload["liqpay_order_id"],
        "status": "success",
    }
    data_b64 = base64.b64encode(json.dumps(webhook_payload).encode("utf-8")).decode("utf-8")
    signature = create_signature(data_b64)
    webhook = client.post(
        "/api/billing/webhook/liqpay",
        json={"data": data_b64, "signature": signature},
    )
    assert webhook.status_code == 200
    assert webhook.json()["payment_status"] == "success"

    after_webhook = client.get("/api/billing/subscription", headers={"X-Demo-User": "billing-user"})
    assert after_webhook.status_code == 200
    after_payload = after_webhook.json()
    assert after_payload["plan"] == "PRO"
    assert after_payload["status"] == "active"


def test_special_dev_token_gets_pro_plus_subscription(client: TestClient) -> None:
    response = client.get(
        "/api/billing/subscription",
        headers={"Authorization": "Bearer dev-token-dev-lemaninets1985"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["plan"] == "PRO_PLUS"
    assert payload["status"] == "active"
    assert payload["usage"]["plan"] == "PRO_PLUS"


def test_subscription_period_rollover_resets_usage(client: TestClient, test_session_factory) -> None:
    now = datetime.now(timezone.utc)
    with test_session_factory() as db:
        db.add(User(id="expired-user", email="expired-user@local.dev"))
        db.add(
            Subscription(
                user_id="expired-user",
                plan="FREE",
                status="active",
                analyses_used=1,
                analyses_limit=1,
                docs_used=1,
                docs_limit=1,
                current_period_start=now - timedelta(days=40),
                current_period_end=now - timedelta(days=10),
            )
        )
        db.commit()

    response = client.get("/api/billing/subscription", headers={"X-Demo-User": "expired-user"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["plan"] == "FREE"
    assert payload["status"] == "active"
    assert payload["usage"]["docs_used"] == 0
    assert payload["usage"]["analyses_used"] == 0
    assert payload["usage"]["current_period_end"] is not None


def test_non_active_subscription_blocks_generation(client: TestClient, test_session_factory) -> None:
    now = datetime.now(timezone.utc)
    with test_session_factory() as db:
        db.add(User(id="blocked-user", email="blocked-user@local.dev"))
        db.add(
            Subscription(
                user_id="blocked-user",
                plan="PRO",
                status="payment_failed",
                analyses_used=0,
                analyses_limit=None,
                docs_used=0,
                docs_limit=None,
                current_period_start=now - timedelta(days=1),
                current_period_end=now + timedelta(days=29),
            )
        )
        db.commit()

    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "PRO",
        "form_data": {
            "plaintiff_name": "Blocked",
            "defendant_name": "User",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-15",
            "principal_debt_uah": 10000,
            "accrued_interest_uah": 500,
            "claim_requests": ["recover debt"],
        },
    }
    response = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "blocked-user"})
    assert response.status_code == 402
    assert "Subscription is not active" in response.json()["detail"]


def test_webhook_duplicate_success_is_idempotent(client: TestClient) -> None:
    subscribe = client.post(
        "/api/billing/subscribe",
        json={"plan": "PRO", "mode": "subscription"},
        headers={"X-Demo-User": "idempotent-user"},
    )
    assert subscribe.status_code == 200
    order_id = subscribe.json()["liqpay_order_id"]
    assert order_id

    webhook_payload = {"order_id": order_id, "status": "success"}
    data_b64 = base64.b64encode(json.dumps(webhook_payload).encode("utf-8")).decode("utf-8")
    signature = create_signature(data_b64)

    first_webhook = client.post("/api/billing/webhook/liqpay", json={"data": data_b64, "signature": signature})
    assert first_webhook.status_code == 200
    assert first_webhook.json()["duplicate"] is False
    first_event_id = first_webhook.json()["webhook_event_id"]
    assert first_event_id

    generate_payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "PRO",
        "form_data": {
            "plaintiff_name": "Idempotent",
            "defendant_name": "User",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-15",
            "principal_debt_uah": 5000,
            "accrued_interest_uah": 200,
            "claim_requests": ["recover debt"],
        },
    }
    generated = client.post("/api/documents/generate", json=generate_payload, headers={"X-Demo-User": "idempotent-user"})
    assert generated.status_code == 200

    before_duplicate = client.get("/api/billing/subscription", headers={"X-Demo-User": "idempotent-user"})
    assert before_duplicate.status_code == 200
    docs_used_before = before_duplicate.json()["usage"]["docs_used"]
    assert docs_used_before == 1

    duplicate_webhook = client.post("/api/billing/webhook/liqpay", json={"data": data_b64, "signature": signature})
    assert duplicate_webhook.status_code == 200
    assert duplicate_webhook.json()["duplicate"] is True
    assert duplicate_webhook.json()["webhook_event_id"] == first_event_id

    after_duplicate = client.get("/api/billing/subscription", headers={"X-Demo-User": "idempotent-user"})
    assert after_duplicate.status_code == 200
    payload = after_duplicate.json()
    assert payload["plan"] == "PRO"
    assert payload["status"] == "active"
    assert payload["usage"]["docs_used"] == docs_used_before
