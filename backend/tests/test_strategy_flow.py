from __future__ import annotations

from datetime import date
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
from app.models import Base, CaseLawCache, Subscription, User


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
        db.add_all(
            [
                CaseLawCache(
                    source="manual_seed",
                    decision_id="vs-625-01",
                    court_name="Supreme Court",
                    court_type="civil",
                    decision_date=date(2025, 11, 10),
                    case_number="123/100/25",
                    subject_categories=["debt", "article 625", "appeal"],
                    summary="Суд задовольнив вимоги про стягнення 3% річних за ст. 625 ЦК України.",
                    reference_count=11,
                ),
                CaseLawCache(
                    source="manual_seed",
                    decision_id="vs-appeal-02",
                    court_name="Supreme Court",
                    court_type="civil",
                    decision_date=date(2025, 9, 2),
                    case_number="123/101/25",
                    subject_categories=["appeal", "deadline", "procedure"],
                    summary="У задоволенні позову відмовлено через пропуск процесуального строку.",
                    reference_count=7,
                ),
                CaseLawCache(
                    source="manual_seed",
                    decision_id="uksc-debt-01",
                    court_name="UK Supreme Court",
                    court_type="civil",
                    decision_date=date(2025, 10, 18),
                    case_number="UKSC-2025-10",
                    subject_categories=["debt", "judgment", "damages"],
                    summary="Judgment for claimant in a debt recovery and damages dispute.",
                    reference_count=5,
                ),
                CaseLawCache(
                    source="manual_seed",
                    decision_id="uksc-debt-02",
                    court_name="UK Supreme Court",
                    court_type="civil",
                    decision_date=date(2025, 8, 9),
                    case_number="UKSC-2025-11",
                    subject_categories=["debt", "appeal"],
                    summary="Appeal dismissed in a debt judgment dispute after service objections failed.",
                    reference_count=4,
                ),
            ]
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


def test_strategy_flow_end_to_end(client: TestClient) -> None:
    source_text = (
        "Рішення суду від 01.02.2026. Позивач: АТ Укрсиббанк. Відповідач: ОСОБА_1.\n"
        "Стягнення заборгованості 843772.95 грн, ст. 625 ЦК України.\n"
        "Потрібно підготувати апеляційну скаргу на рішення суду."
    )
    intake_response = client.post(
        "/api/analyze/intake",
        files={"file": ("decision.txt", source_text.encode("utf-8"), "text/plain")},
        headers={"X-Demo-User": "demo-user"},
    )
    assert intake_response.status_code == 200
    intake_payload = intake_response.json()
    assert intake_payload["classified_type"] in {
        "court_decision",
        "procedural_document",
        "contract",
        "claim_notice",
        "other",
    }
    intake_id = intake_payload["id"]

    map_response = client.post(
        f"/api/analyze/{intake_id}/precedent-map",
        headers={"X-Demo-User": "demo-user"},
    )
    assert map_response.status_code == 200
    map_payload = map_response.json()
    assert map_payload["intake_id"] == intake_id
    assert len(map_payload["groups"]) >= 1

    strategy_response = client.post(
        "/api/strategy/blueprint",
        json={
            "intake_id": intake_id,
            "regenerate": True,
            "refresh_precedent_map": True,
            "precedent_limit": 10,
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert strategy_response.status_code == 200
    strategy_payload = strategy_response.json()
    assert strategy_payload["intake_id"] == intake_id
    assert len(strategy_payload["immediate_actions"]) >= 1
    strategy_id = strategy_payload["id"]

    generation_response = client.post(
        "/api/generate-with-strategy",
        json={
            "strategy_blueprint_id": strategy_id,
            "doc_type": "appeal_complaint",
            "form_data": {},
            "extra_prompt_context": "Тестовий контекст для генерації.",
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert generation_response.status_code == 200
    generation_payload = generation_response.json()
    assert generation_payload["strategy_blueprint_id"] == strategy_id
    assert generation_payload["document_id"]
    assert generation_payload["strategy_audit_id"]

    audit_response = client.get(
        f"/api/documents/{generation_payload['document_id']}/strategy-audit",
        headers={"X-Demo-User": "demo-user"},
    )
    assert audit_response.status_code == 200
    audit_payload = audit_response.json()
    assert audit_payload["document_id"] == generation_payload["document_id"]


def test_strategy_flow_supports_uk_intake_and_keeps_uk_reasoning(client: TestClient) -> None:
    source_text = (
        "IN THE HIGH COURT OF JUSTICE\n"
        "Claimant: ACME Ltd\n"
        "Defendant: John Doe\n"
        "Judgment dated 31 January 2026.\n"
        "Damages in the sum of GBP 125,000.50.\n"
        "Response due by 14/02/2026.\n"
        "The claimant seeks judgment for unpaid loan obligations.\n"
    )

    intake_response = client.post(
        "/api/analyze/intake",
        files={"file": ("uk-judgment.txt", source_text.encode("utf-8"), "text/plain")},
        headers={"X-Demo-User": "demo-user"},
    )
    assert intake_response.status_code == 200
    intake_payload = intake_response.json()
    assert intake_payload["jurisdiction"] == "EW"
    assert intake_payload["document_language"] == "en"
    assert intake_payload["classified_type"] == "court_decision"
    assert intake_payload["financial_exposure_currency"] == "GBP"
    assert intake_payload["deadline_from_document"] == "2026-02-14"

    map_response = client.post(
        f"/api/analyze/{intake_payload['id']}/precedent-map",
        headers={"X-Demo-User": "demo-user"},
    )
    assert map_response.status_code == 200
    map_payload = map_response.json()
    assert map_payload["query_used"]
    assert len(map_payload["refs"]) >= 1
    assert any("UK Supreme Court" in str(item["court_name"]) for item in map_payload["refs"])

    strategy_response = client.post(
        "/api/strategy/blueprint",
        json={
            "intake_id": intake_payload["id"],
            "regenerate": True,
            "refresh_precedent_map": True,
            "precedent_limit": 10,
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert strategy_response.status_code == 200
    strategy_payload = strategy_response.json()
    assert "intake risk profile" in strategy_payload["confidence_rationale"].lower()
    assert any("deadline" in str(item.get("action", "")).lower() for item in strategy_payload["immediate_actions"])
    assert strategy_payload["procedural_roadmap"][0]["legal_action"].startswith("Validate jurisdiction")


def test_strategy_flow_normalizes_registry_export_into_key_values_brief(client: TestClient) -> None:
    source_text = (
        "Апеляційна скарга\n"
        'ДО META NAME="COURTNAME" CONTENT="Закарпатський апеляційний суд"> через META NAME="COURTNAME" '
        'CONTENT="Закарпатський апеляційний суд">\n'
        "Апелянт: акціонерного товариства «Укрсиббанк»\n"
        "Інший учасник: Бокоч Ольги Михайлівни та Роман Нанії Федорівни\n"
        "Представник: Леманинець Вячеслав Миколайович\n"
        '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">\n'
        '<html><head><META NAME="FILENAME" CONTENT="4806_47909624.html">\n'
        '<META NAME="DOCID" CONTENT="47909624">\n'
        '<META NAME="COURTNAME" CONTENT="Закарпатський апеляційний суд">\n'
        '<META NAME="CAUSENUM" CONTENT="307/1542/25">\n'
        '<META NAME="CAUSEDATE" CONTENT="02.12.2025">\n'
        '<META NAME="PROCNUM" CONTENT="22-ц/4806/1479/25">\n'
        '<META NAME="DOCDATE" CONTENT="02.03.2026">\n'
        '<META NAME="PREVCOURTNAME" CONTENT="Тячівський районний суд Закарпатської області">\n'
        "Закарпатський апеляційний суд у складі колегії суддів розглянув цивільну справу "
        "за апеляційною скаргою Бокоч Ольги Михайлівни, в інтересах якої діє Леманинець Вячеслав Миколайович, "
        "на рішення Тячівського районного суду Закарпатської області.\n"
    )

    intake_response = client.post(
        "/api/analyze/intake",
        files={"file": ("registry-export.txt", source_text.encode("utf-8"), "text/plain")},
        headers={"X-Demo-User": "demo-user"},
    )
    assert intake_response.status_code == 200
    intake_payload = intake_response.json()
    preview = str(intake_payload["raw_text_preview"] or "")
    assert "Тип документа: Апеляційна скарга" in preview
    assert "Суд: Закарпатський апеляційний суд" in preview
    assert "Суд першої інстанції: Тячівський районний суд Закарпатської області" in preview
    assert "Номер справи: 307/1542/25" in preview
    assert "Номер провадження: 22-ц/4806/1479/25" in preview
    assert "Позивач: акціонерного товариства «Укрсиббанк»" in preview
    assert "Відповідач: Бокоч Ольги Михайлівни та Роман Нанії Федорівни" in preview
    assert "META NAME" not in preview
    assert "<!DOCTYPE" not in preview

    strategy_response = client.post(
        "/api/strategy/blueprint",
        json={
            "intake_id": intake_payload["id"],
            "regenerate": True,
            "refresh_precedent_map": True,
            "precedent_limit": 10,
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert strategy_response.status_code == 200
    strategy_payload = strategy_response.json()

    generation_response = client.post(
        "/api/generate-with-strategy",
        json={
            "strategy_blueprint_id": strategy_payload["id"],
            "doc_type": "appeal_complaint",
            "form_data": {},
            "extra_prompt_context": "Перевірка structured intake brief.",
        },
        headers={"X-Demo-User": "demo-user"},
    )
    assert generation_response.status_code == 200
    generation_payload = generation_response.json()
    assert "META NAME" not in str(generation_payload["preview_text"] or "")
