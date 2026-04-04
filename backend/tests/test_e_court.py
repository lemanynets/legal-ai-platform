from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest
import unittest.mock
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import get_db
from app.config import settings
from app.main import app
from app.models import Base, GeneratedDocument, Subscription, User


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
        db.add(
            GeneratedDocument(
                user_id="demo-user",
                document_type="lawsuit_debt_loan",
                document_category="judicial",
                form_data={
                    "plaintiff_name": "Ivan",
                    "defendant_name": "Petro",
                    "debt_start_date": "2024-01-10",
                    "principal_debt_uah": 10000,
                    "claim_requests": ["recover debt"],
                },
                generated_text=(
                    "ПОЗОВНА ЗАЯВА\n"
                    "1. Обставини справи\n"
                    "2. Правове обґрунтування\n"
                    "3. Відомості відповідно до ст. 175 ЦПК України\n"
                    "4. ПРОШУ СУД\n"
                    "1. Стягнути борг.\n"
                    "2. Стягнути судовий збір.\n"
                    "5. Перелік документів, що додаються (ст. 177 ЦПК України)\n"
                    "Дата: __________\n"
                    "Підпис: __________\n"
                    + " ".join(["зміст"] * 220)
                ),
                preview_text="Preview legal text",
                calculations={},
                ai_model="gpt-4o-mini",
                used_ai=True,
                ai_error=None,
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


def _first_document_id(session_factory) -> str:
    with session_factory() as db:
        row = db.execute(select(GeneratedDocument).where(GeneratedDocument.user_id == "demo-user")).scalar_one()
        return row.id


def test_e_court_submit_and_history_and_status(client: TestClient, test_session_factory) -> None:
    document_id = _first_document_id(test_session_factory)
    with unittest.mock.patch("app.services.document_generation.export_document") as mock_exp:
        mock_exp.return_value = unittest.mock.MagicMock(file_path="mock/path.pdf")
        with unittest.mock.patch("app.services.signer.sign_document", return_value="mock/path.pdf.p7s"):
            submit = client.post(
                "/api/e-court/submit",
                json={
                    "document_id": document_id,
                    "court_name": "Kyiv district court",
                    "signer_method": "file_key",
                    "note": "Urgent filing",
                },
                headers={"X-Demo-User": "demo-user"},
            )
    assert submit.status_code == 200
    submit_payload = submit.json()
    assert submit_payload["status"] == "submitted"
    assert submit_payload["submission"]["document_id"] == document_id
    submission_id = submit_payload["submission"]["id"]
    assert submission_id

    history = client.get("/api/e-court/history?page=1&page_size=10", headers={"X-Demo-User": "demo-user"})
    assert history.status_code == 200
    history_payload = history.json()
    assert history_payload["total"] == 1
    assert history_payload["items"][0]["id"] == submission_id

    status = client.get(f"/api/e-court/{submission_id}/status", headers={"X-Demo-User": "demo-user"})
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload["submission"]["id"] == submission_id
    assert status_payload["submission"]["status"] == "submitted"
    assert status_payload["submission"]["tracking_url"]


def test_e_court_submit_requires_pro_plus(client: TestClient, test_session_factory) -> None:
    document_id = _first_document_id(test_session_factory)
    with test_session_factory() as db:
        subscription = db.execute(select(Subscription).where(Subscription.user_id == "demo-user")).scalar_one()
        subscription.plan = "PRO"
        db.commit()

    with unittest.mock.patch("app.services.document_generation.export_document") as mock_exp:
        mock_exp.return_value = unittest.mock.MagicMock(file_path="mock/path.pdf")
        submit = client.post(
            "/api/e-court/submit",
            json={"document_id": document_id, "court_name": "Kyiv district court"},
            headers={"X-Demo-User": "demo-user"},
        )
    assert submit.status_code == 403
    assert "requires at least PRO_PLUS plan" in submit.json()["detail"]


def test_e_court_history_requires_active_subscription(client: TestClient, test_session_factory) -> None:
    with test_session_factory() as db:
        subscription = db.execute(select(Subscription).where(Subscription.user_id == "demo-user")).scalar_one()
        subscription.status = "payment_failed"
        db.commit()

    response = client.get("/api/e-court/history", headers={"X-Demo-User": "demo-user"})
    assert response.status_code == 402
    assert "Subscription is not active" in response.json()["detail"]


def test_e_court_submit_blocked_in_strict_mode_for_invalid_document(client: TestClient, test_session_factory) -> None:
    original_mode = settings.strict_filing_mode
    try:
        object.__setattr__(settings, "strict_filing_mode", True)
        with test_session_factory() as db:
            row = db.execute(select(GeneratedDocument).where(GeneratedDocument.user_id == "demo-user")).scalar_one()
            row.generated_text = "short invalid text"
            row.form_data = {}
            db.commit()
            document_id = row.id

        with unittest.mock.patch("app.services.document_generation.export_document") as mock_exp:
            mock_exp.return_value = unittest.mock.MagicMock(file_path="mock/path.pdf")
            submit = client.post(
                "/api/e-court/submit",
                json={"document_id": document_id, "court_name": "Kyiv district court"},
                headers={"X-Demo-User": "demo-user"},
            )
        assert submit.status_code == 422
        detail = submit.json().get("detail") or {}
        assert detail.get("message") == "Strict filing mode blocked submission. Resolve processual blockers first."
        blockers = detail.get("blockers") or []
        assert len(blockers) >= 1
    finally:
        object.__setattr__(settings, "strict_filing_mode", original_mode)


def test_e_court_submit_allows_invalid_document_when_strict_mode_disabled(client: TestClient, test_session_factory) -> None:
    original_mode = settings.strict_filing_mode
    try:
        object.__setattr__(settings, "strict_filing_mode", False)
        with test_session_factory() as db:
            row = db.execute(select(GeneratedDocument).where(GeneratedDocument.user_id == "demo-user")).scalar_one()
            row.generated_text = "short invalid text"
            row.form_data = {}
            db.commit()
            document_id = row.id

        with unittest.mock.patch("app.services.document_generation.export_document") as mock_exp:
            mock_exp.return_value = unittest.mock.MagicMock(file_path="mock/path.pdf")
            submit = client.post(
                "/api/e-court/submit",
                json={"document_id": document_id, "court_name": "Kyiv district court"},
                headers={"X-Demo-User": "demo-user"},
            )
        assert submit.status_code == 200
        payload = submit.json()
        assert payload["status"] == "submitted"
        assert payload["submission"]["document_id"] == document_id
    finally:
        object.__setattr__(settings, "strict_filing_mode", original_mode)
