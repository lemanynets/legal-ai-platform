from __future__ import annotations

from datetime import date
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
from app.models import Base, CaseLawCache, User


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


def _seed_case_law(session_factory) -> None:
    with session_factory() as db:
        db: Session
        db.add(
            User(
                id="demo-user",
                email="demo-user@local.dev",
            )
        )
        db.add_all(
            [
                CaseLawCache(
                    source="manual",
                    decision_id="d-001",
                    court_name="Supreme Court",
                    court_type="civil",
                    decision_date=date(2025, 1, 10),
                    case_number="100/1/25",
                    subject_categories=["loan", "debt"],
                    summary="Loan debt case from civil court.",
                    reference_count=9,
                ),
                CaseLawCache(
                    source="manual",
                    decision_id="d-002",
                    court_name="Supreme Court",
                    court_type="civil",
                    decision_date=date(2024, 12, 10),
                    case_number="100/2/25",
                    subject_categories=["loan", "procedure"],
                    summary="Civil procedure on debt dispute.",
                    reference_count=4,
                ),
                CaseLawCache(
                    source="manual",
                    decision_id="d-003",
                    court_name="Commercial Court",
                    court_type="commercial",
                    decision_date=date(2024, 11, 10),
                    case_number="100/3/25",
                    subject_categories=["penalty", "contract"],
                    summary="Commercial penalty dispute.",
                    reference_count=15,
                ),
            ]
        )
        db.commit()


def test_case_law_search_server_pagination_and_sort(client, test_session_factory) -> None:
    _seed_case_law(test_session_factory)

    response = client.get(
        "/api/case-law/search",
        params={
            "page": 1,
            "page_size": 2,
            "sort_by": "decision_date",
            "sort_dir": "desc",
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["page"] == 1
    assert payload["page_size"] == 2
    assert payload["pages"] == 2
    assert payload["sort_by"] == "decision_date"
    assert payload["sort_dir"] == "desc"
    assert len(payload["items"]) == 2
    assert payload["items"][0]["decision_id"] == "d-001"
    assert payload["items"][1]["decision_id"] == "d-002"

    response_page_2 = client.get(
        "/api/case-law/search",
        params={
            "page": 2,
            "page_size": 2,
            "sort_by": "decision_date",
            "sort_dir": "desc",
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert response_page_2.status_code == 200
    payload_page_2 = response_page_2.json()
    assert payload_page_2["page"] == 2
    assert len(payload_page_2["items"]) == 1
    assert payload_page_2["items"][0]["decision_id"] == "d-003"


def test_case_law_search_filters_and_reference_sort(client, test_session_factory) -> None:
    _seed_case_law(test_session_factory)

    response = client.get(
        "/api/case-law/search",
        params={
            "court_type": "civil",
            "tags": "loan",
            "sort_by": "reference_count",
            "sort_dir": "desc",
            "page": 1,
            "page_size": 10,
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["pages"] == 1
    assert len(payload["items"]) == 2
    assert all(item["court_type"] == "civil" for item in payload["items"])
    assert payload["items"][0]["reference_count"] >= payload["items"][1]["reference_count"]
    assert payload["items"][0]["decision_id"] == "d-001"
    assert payload["items"][1]["decision_id"] == "d-002"


def test_case_law_search_source_and_date_filters(client, test_session_factory) -> None:
    _seed_case_law(test_session_factory)

    today = date.today()
    with test_session_factory() as db:
        db: Session
        db.add(
            CaseLawCache(
                source="opendatabot",
                decision_id="d-004",
                court_name="Supreme Court",
                court_type="civil",
                decision_date=today,
                case_number="100/4/25",
                subject_categories=["loan", "debt"],
                summary="Recent source-specific row.",
                reference_count=1,
            )
        )
        db.commit()

    response = client.get(
        "/api/case-law/search",
        params={
            "source": "opendatabot",
            "date_from": today.isoformat(),
            "date_to": today.isoformat(),
            "fresh_days": 7,
            "page": 1,
            "page_size": 10,
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["decision_id"] == "d-004"
    assert payload["items"][0]["source"] == "opendatabot"


def test_case_law_search_only_supreme_filter(client, test_session_factory) -> None:
    _seed_case_law(test_session_factory)
    response = client.get(
        "/api/case-law/search",
        params={
            "only_supreme": "true",
            "page": 1,
            "page_size": 10,
            "sort_by": "decision_date",
            "sort_dir": "desc",
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert [item["decision_id"] for item in payload["items"]] == ["d-001", "d-002"]
