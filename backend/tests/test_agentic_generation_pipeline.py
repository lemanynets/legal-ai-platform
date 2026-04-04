from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import json

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import get_db
from app.main import app
from app.models import Base, CaseLawCache, Subscription, User
from app.services.ai_generator import AIResult


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
        db.add(
            CaseLawCache(
                source="opendatabot",
                decision_id="ref-001",
                court_name="Supreme Court",
                court_type="civil",
                decision_date=date(2025, 2, 1),
                case_number="300/1/25",
                subject_categories=["loan", "debt", "article 625"],
                legal_positions={"article 625": "3% and inflation losses are recoverable."},
                summary="Debt recovery position for loan agreements.",
                reference_count=0,
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


def test_documents_generate_invokes_three_roles(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def fake_generate(role: str, user_prompt: str, **_: object) -> AIResult:
        calls.append(role)
        if role == "intake":
            return AIResult(
                text=json.dumps(
                    {
                        "jurisdiction": "UA",
                        "court_type": "civil",
                        "dispute_type": "debt_recovery",
                        "parties": [{"role": "plaintiff", "name": "Ivan"}, {"role": "defendant", "name": "Petro"}],
                        "key_facts": ["Позика, прострочення платежу"],
                        "key_dates": ["2024-01-15"],
                        "amounts": [{"label": "principal", "value": "10000 UAH"}],
                        "requested_action": "позов",
                        "keywords": ["loan", "debt", "625"],
                        "case_law_query": "loan debt 625",
                    },
                    ensure_ascii=False,
                ),
                used_ai=True,
                model="fake-intake",
                error="",
            )
        if role == "research":
            parsed = json.loads(user_prompt)
            candidates = parsed.get("candidates") or []
            selected_id = candidates[0]["id"] if candidates else ""
            return AIResult(
                text=json.dumps({"selected": [{"id": selected_id, "score": 0.9, "why": "relevant"}]}),
                used_ai=True,
                model="fake-research",
                error="",
            )
        return AIResult(text="", used_ai=False, model="fake-draft", error="")

    import app.services.agentic_generation as agentic_generation
    import app.routers.documents as documents_router

    monkeypatch.setattr(agentic_generation, "generate_legal_document_for_role", fake_generate)
    monkeypatch.setattr(documents_router, "generate_legal_document_for_role", fake_generate)

    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "PRO",
        "form_data": {
            "plaintiff_name": "Ivan",
            "defendant_name": "Petro",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-15",
            "principal_debt_uah": 10000,
            "accrued_interest_uah": 500,
            "claim_requests": ["recover debt", "recover court fee"],
        },
    }
    response = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert response.status_code == 200

    assert calls == ["intake", "research", "draft"]


def test_documents_generate_skips_research_when_intake_is_rate_limited(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def fake_generate(role: str, user_prompt: str, **_: object) -> AIResult:
        calls.append(role)
        if role == "intake":
            return AIResult(
                text="",
                used_ai=False,
                model="fake-intake",
                error="429 Too Many Requests",
            )
        if role == "research":
            raise AssertionError("research agent must be skipped when intake is rate-limited")
        return AIResult(text="", used_ai=False, model="fake-draft", error="429 Too Many Requests")

    import app.services.agentic_generation as agentic_generation
    import app.routers.documents as documents_router

    monkeypatch.setattr(agentic_generation, "generate_legal_document_for_role", fake_generate)
    monkeypatch.setattr(documents_router, "generate_legal_document_for_role", fake_generate)

    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "PRO",
        "form_data": {
            "plaintiff_name": "Ivan",
            "defendant_name": "Petro",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-15",
            "principal_debt_uah": 10000,
            "accrued_interest_uah": 500,
            "claim_requests": ["recover debt", "recover court fee"],
        },
    }
    response = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert response.status_code == 200
    assert calls == ["intake", "draft"]
