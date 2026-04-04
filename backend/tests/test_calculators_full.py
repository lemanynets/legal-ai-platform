from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import get_db
from app.main import app
from app.models import Base


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


def _payload(save: bool = True) -> dict:
    return {
        "claim_amount_uah": 100000,
        "principal_uah": 100000,
        "debt_start_date": "2025-01-01",
        "debt_end_date": "2025-12-31",
        "process_start_date": "2026-02-22",
        "process_days": 30,
        "violation_date": "2025-01-01",
        "limitation_years": 3,
        "save": save,
        "title": "Debt recovery calculation",
    }


def test_full_calculation_save_history_and_detail(client: TestClient) -> None:
    response = client.post("/api/calculate/full", json=_payload(save=True), headers={"X-Demo-User": "demo-user"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["saved"] is True
    assert data["calculation_id"]
    assert data["result"]["court_fee_uah"] > 0
    assert data["result"]["penalty_uah"] > 0

    history = client.get("/api/calculate/history", headers={"X-Demo-User": "demo-user"})
    assert history.status_code == 200
    history_data = history.json()
    assert history_data["total"] == 1
    calculation_id = history_data["items"][0]["id"]
    assert calculation_id == data["calculation_id"]

    detail = client.get(f"/api/calculate/{calculation_id}", headers={"X-Demo-User": "demo-user"})
    assert detail.status_code == 200
    detail_data = detail.json()["item"]
    assert detail_data["calculation_type"] == "full_claim"
    assert detail_data["input_payload"]["claim_amount_uah"] == 100000
    assert detail_data["output_payload"]["total_with_fee_uah"] >= detail_data["output_payload"]["total_claim_uah"]


def test_full_calculation_without_saving(client: TestClient) -> None:
    response = client.post("/api/calculate/full", json=_payload(save=False), headers={"X-Demo-User": "demo-user"})
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is False
    assert data["calculation_id"] is None

    history = client.get("/api/calculate/history", headers={"X-Demo-User": "demo-user"})
    assert history.status_code == 200
    assert history.json()["total"] == 0
