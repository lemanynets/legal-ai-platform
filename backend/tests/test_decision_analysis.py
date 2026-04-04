from __future__ import annotations

from datetime import date, timedelta
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
        db: Session
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
                decision_id="decision-analysis-001",
                court_name="Supreme Court",
                court_type="civil",
                decision_date=date.today(),
                case_number="307/1542/25",
                subject_categories=["debt", "article 625"],
                summary="Debt recovery dispute with article 625 legal reasoning.",
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


def _post_decision_analysis(
    client: TestClient,
    *,
    content: str,
    file_name: str = "decision.txt",
    content_type: str = "text/plain",
    include_recent_case_law: bool = True,
    case_law_days: int = 3650,
):
    return client.post(
        "/api/auto/decision-analysis",
        data={
            "include_recent_case_law": str(include_recent_case_law).lower(),
            "case_law_days": str(case_law_days),
            "case_law_limit": "5",
            "only_supreme_case_law": "false",
            "ai_enhance": "false",
        },
        files={"file": (file_name, content.encode("utf-8"), content_type)},
        headers={"X-Demo-User": "demo-user"},
    )


def _post_decision_analysis_export(
    client: TestClient,
    *,
    content: str,
    format: str = "pdf",
    file_name: str = "decision.txt",
    content_type: str = "text/plain",
):
    return client.post(
        "/api/auto/decision-analysis/export",
        data={
            "format": format,
            "include_recent_case_law": "true",
            "case_law_days": "3650",
            "case_law_limit": "5",
            "only_supreme_case_law": "false",
            "ai_enhance": "false",
            "consume_quota": "false",
        },
        files={"file": (file_name, content.encode("utf-8"), content_type)},
        headers={"X-Demo-User": "demo-user"},
    )


def _post_decision_analysis_package(
    client: TestClient,
    *,
    content: str,
    file_name: str = "decision.txt",
    content_type: str = "text/plain",
):
    return client.post(
        "/api/auto/decision-analysis/package",
        data={
            "max_documents": "3",
            "include_warn_readiness": "true",
            "include_recent_case_law": "true",
            "case_law_days": "3650",
            "case_law_limit": "5",
            "only_supreme_case_law": "false",
            "ai_enhance": "false",
            "consume_analysis_quota": "false",
        },
        files={"file": (file_name, content.encode("utf-8"), content_type)},
        headers={"X-Demo-User": "demo-user"},
    )


def test_decision_analysis_returns_structured_payload(client: TestClient) -> None:
    file_content = (
        "Case No. 307/1542/25\n"
        "Court decision about debt recovery under article 625.\n"
        "The judgment and enforcement delay are disputed.\n"
        "Plaintiff requests 3% annual interest and inflation losses.\n"
    )
    response = _post_decision_analysis(client, content=file_content, case_law_days=365)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["source_file_name"] == "decision.txt"
    assert payload["extracted_chars"] > 20
    assert isinstance(payload["dispute_summary"], str) and payload["dispute_summary"]
    assert isinstance(payload["procedural_context"], str) and payload["procedural_context"]
    assert isinstance(payload["key_issues"], list) and len(payload["key_issues"]) >= 1
    assert isinstance(payload["key_questions"], list) and len(payload["key_questions"]) >= 1
    assert isinstance(payload["side_assessment"], dict)
    assert payload["side_assessment"]["side"] in {"plaintiff", "defendant", "guarantor", "unknown"}
    assert isinstance(payload["side_assessment"]["confidence"], float)
    assert isinstance(payload["side_assessment"]["rationale"], list)
    assert isinstance(payload["defense_plan"], list) and len(payload["defense_plan"]) >= 1
    assert isinstance(payload["evidence_gaps"], list) and len(payload["evidence_gaps"]) >= 1
    assert isinstance(payload["document_preparation"], list) and len(payload["document_preparation"]) >= 1
    assert isinstance(payload["cassation_vulnerabilities"], list) and len(payload["cassation_vulnerabilities"]) >= 1
    assert isinstance(payload["final_conclusion"], str) and payload["final_conclusion"]
    assert isinstance(payload["stage_recommendations"], list) and len(payload["stage_recommendations"]) == 5
    assert isinstance(payload["stage_packets"], list) and len(payload["stage_packets"]) == 5
    assert isinstance(payload["recent_practice"], list) and len(payload["recent_practice"]) >= 1
    assert isinstance(payload["practice_coverage"], dict)
    assert payload["practice_coverage"]["total_items"] >= 1
    assert "instance_levels" in payload["practice_coverage"]
    assert isinstance(payload["quality_blocks"], list) and len(payload["quality_blocks"]) == 5
    assert isinstance(payload["traceability"], list) and len(payload["traceability"]) >= 1
    assert isinstance(payload["overall_confidence_score"], float)
    assert isinstance(payload["quality_gate"], dict)
    assert payload["quality_gate"]["status"] in {"pass", "blocked"}
    assert isinstance(payload["usage"], dict)


def test_decision_analysis_accepts_html_upload(client: TestClient) -> None:
    html = """
    <html>
      <body>
        <h1>Court decision</h1>
        <p>Debt dispute and article 625 legal issue.</p>
      </body>
    </html>
    """
    response = _post_decision_analysis(
        client,
        content=html,
        file_name="decision.html",
        content_type="text/html",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source_file_name"] == "decision.html"
    assert payload["extracted_chars"] > 20


def test_decision_analysis_can_skip_recent_case_law(client: TestClient) -> None:
    file_content = (
        "Court decision text with debt and procedural reasoning.\n"
        "A party requests cassation review due to legal misapplication.\n"
    )
    response = _post_decision_analysis(
        client,
        content=file_content,
        include_recent_case_law=False,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["recent_practice"] == []
    assert any("пошук" in warning.lower() and "вимкн" in warning.lower() for warning in payload["warnings"])


def test_decision_analysis_quality_gate_can_block_low_quality_input(client: TestClient) -> None:
    file_content = "Debt issue text without legal references or detailed chronology."
    response = _post_decision_analysis(
        client,
        content=file_content,
        include_recent_case_law=False,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["quality_gate"]["status"] == "blocked"
    assert payload["quality_gate"]["can_proceed_to_filing"] is False
    assert len(payload["quality_gate"]["blockers"]) >= 1
    assert sum(1 for item in payload["evidence_gaps"] if item["status"] == "missing") >= 1


def test_decision_analysis_blocks_stale_practice_coverage(client: TestClient, test_session_factory) -> None:
    with test_session_factory() as db:
        db: Session
        db.query(CaseLawCache).delete()
        db.add(
            CaseLawCache(
                source="manual",
                decision_id="decision-analysis-old-001",
                court_name="Supreme Court",
                court_type="civil",
                decision_date=date.today() - timedelta(days=900),
                case_number="307/1542/25",
                subject_categories=["debt", "article 625"],
                summary="Debt recovery dispute with article 625 legal reasoning.",
            )
        )
        db.commit()

    file_content = (
        "Case No. 307/1542/25\n"
        "Court decision about debt recovery under article 625.\n"
        "The judgment and enforcement delay are disputed.\n"
    )
    response = _post_decision_analysis(client, content=file_content, case_law_days=365)
    assert response.status_code == 200
    payload = response.json()
    assert payload["practice_coverage"]["stale"] is True
    assert payload["quality_gate"]["status"] == "blocked"
    assert any(
        ("застаріл" in str(item).lower()) or ("практик" in str(item).lower())
        for item in payload["quality_gate"]["blockers"]
    )


def test_decision_analysis_export_and_history(client: TestClient) -> None:
    file_content = (
        "Case No. 307/1542/25\n"
        "Court decision about debt recovery under article 625.\n"
        "Plaintiff requests 3% annual interest and inflation losses.\n"
    )
    export_response = _post_decision_analysis_export(client, content=file_content, format="pdf")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("application/pdf")
    assert len(export_response.content) > 100

    history_response = client.get(
        "/api/auto/decision-analysis/history",
        params={"event": "all", "page": 1, "page_size": 20},
        headers={"X-Demo-User": "demo-user"},
    )
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload["total"] >= 1
    assert len(history_payload["items"]) >= 1
    first = history_payload["items"][0]
    assert first["event_type"] in {"upload", "export"}
    assert isinstance(first["has_report_snapshot"], bool)
    assert "practice_total" in first

    snapshot_item = next((item for item in history_payload["items"] if item["has_report_snapshot"]), None)
    assert snapshot_item is not None

    history_export = client.get(
        f"/api/auto/decision-analysis/history/{snapshot_item['id']}/export",
        params={"format": "docx"},
        headers={"X-Demo-User": "demo-user"},
    )
    assert history_export.status_code == 200
    assert history_export.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(history_export.content) > 100


def test_decision_analysis_package_generates_documents(client: TestClient) -> None:
    file_content = (
        "Case No. 307/1542/25\n"
        "Court decision about debt recovery under article 625.\n"
        "The judgment and enforcement delay are disputed.\n"
        "Plaintiff requests 3% annual interest and inflation losses.\n"
    )
    response = _post_decision_analysis_package(client, content=file_content)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["source_file_name"] == "decision.txt"
    assert payload["extracted_chars"] > 20
    assert isinstance(payload["selected_doc_types"], list) and len(payload["selected_doc_types"]) >= 1
    assert isinstance(payload["generated_documents"], list) and len(payload["generated_documents"]) >= 1
    assert isinstance(payload["side_assessment"], dict)
    assert payload["side_assessment"]["side"] in {"plaintiff", "defendant", "guarantor", "unknown"}
    assert isinstance(payload["evidence_gaps_missing_count"], int)
    assert isinstance(payload["warnings"], list)
    assert isinstance(payload["usage"], dict)


def test_decision_analysis_package_keeps_raw_text_for_form_parser(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.routers import auto_process as auto_process_router

    captured_source_texts: list[str] = []
    original_builder = auto_process_router.build_form_data_for_doc_type

    def spy_build_form_data(doc_type: str, source_text: str):
        captured_source_texts.append(source_text)
        return original_builder(doc_type, source_text)

    monkeypatch.setattr(auto_process_router, "build_form_data_for_doc_type", spy_build_form_data)

    file_content = (
        "Case No. 307/1542/25\n"
        "Zakarpattia appellate court reviewed debt recovery dispute.\n"
        "Plaintiff requests 3% annual interest under article 625.\n"
    )
    response = _post_decision_analysis_package(client, content=file_content)
    assert response.status_code == 200
    assert captured_source_texts
    assert all(
        "КОНТЕКСТ ДЛЯ ГЕНЕРАЦІЇ ПРОЦЕСУАЛЬНИХ ДОКУМЕНТІВ:" not in text
        for text in captured_source_texts
    )
