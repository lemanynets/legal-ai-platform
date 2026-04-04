from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
import sys
import zipfile

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import get_db
from app.config import settings
from app.main import app
from app.models import Base, CaseLawCache, DocumentCaseLawRef, DocumentVersion, GeneratedDocument, Subscription, User


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


@pytest.fixture(autouse=True)
def temp_document_storage(tmp_path):
    previous = settings.document_storage_root
    object.__setattr__(settings, "document_storage_root", str(tmp_path))
    try:
        yield
    finally:
        object.__setattr__(settings, "document_storage_root", previous)


def test_generate_document_creates_case_law_references(client: TestClient, test_session_factory) -> None:
    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "FREE",
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
    data = response.json()
    assert data["document_id"]
    assert isinstance(data["case_law_refs"], list)
    assert len(data["case_law_refs"]) >= 1
    assert data["case_law_refs"][0]["decision_id"] == "ref-001"
    assert isinstance(data["pre_generation_gate_checks"], list)
    assert isinstance(data["processual_validation_checks"], list)
    assert "quality_guard_applied" in data

    with test_session_factory() as db:
        db: Session
        generated = db.execute(
            select(GeneratedDocument).where(GeneratedDocument.id == data["document_id"])
        ).scalar_one_or_none()
        assert generated is not None

        refs = db.execute(
            select(DocumentCaseLawRef).where(DocumentCaseLawRef.document_id == data["document_id"])
        ).scalars().all()
        assert len(refs) >= 1

        case_row = db.execute(
            select(CaseLawCache).where(CaseLawCache.decision_id == "ref-001")
        ).scalar_one()
        assert int(case_row.reference_count or 0) >= 1


def test_generate_document_blocks_when_pre_generation_gate_fails(client: TestClient) -> None:
    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "FREE",
        "form_data": {
            "plaintiff_name": "Ivan",
            "defendant_name": "Petro",
            "debt_basis": "loan",
            "debt_start_date": "",
            "principal_debt_uah": 0,
            "claim_requests": [],
        },
    }
    response = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert response.status_code == 422
    detail = response.json().get("detail") or {}
    assert detail.get("message") == "Pre-generation gate failed. Required fields are missing or invalid."
    assert detail.get("auto_fix_applied") is True
    checks = detail.get("checks") or []
    assert any(item.get("status") == "fail" for item in checks)


def test_generate_document_applies_extra_context_and_digest(client: TestClient) -> None:
    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "PRO",
        "form_data": {
            "plaintiff_name": "Digest User",
            "defendant_name": "Digest Defendant",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-15",
            "principal_debt_uah": 10000,
            "accrued_interest_uah": 500,
            "claim_requests": ["recover debt", "recover court fee"],
        },
        "extra_prompt_context": "Manual legal context block.",
        "include_digest": True,
        "digest_days": 1000,
        "digest_limit": 5,
        "digest_only_supreme": True,
    }
    response = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert response.status_code == 200
    data = response.json()
    assert "Manual legal context block." in data["prompt_user"]
    assert "Use these digest decisions as additional legal context" in data["prompt_user"]
    assert "case 300/1/25" in data["prompt_user"]
    assert "Case law references for motivation section" in data["generated_text"]


def test_generate_document_uses_saved_digest_id_context(client: TestClient) -> None:
    saved = client.post(
        "/api/case-law/digest/generate",
        json={"days": 3650, "limit": 5, "only_supreme": True, "save": True, "title": "Saved for generation"},
        headers={"X-Demo-User": "demo-user"},
    )
    assert saved.status_code == 200
    digest_id = saved.json()["digest_id"]
    assert digest_id

    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "PRO",
        "form_data": {
            "plaintiff_name": "Saved Digest User",
            "defendant_name": "Saved Digest Defendant",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-15",
            "principal_debt_uah": 10000,
            "accrued_interest_uah": 500,
            "claim_requests": ["recover debt", "recover court fee"],
        },
        "saved_digest_id": digest_id,
        "include_digest": False,
    }
    response = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert response.status_code == 200
    data = response.json()
    assert "Use this saved case-law digest as additional legal context" in data["prompt_user"]
    assert "Weekly case-law digest" in data["prompt_user"]
    assert "case 300/1/25" in data["prompt_user"]


def test_generate_document_rejects_unknown_saved_digest_id(client: TestClient) -> None:
    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "PRO",
        "form_data": {
            "plaintiff_name": "Unknown Digest User",
            "defendant_name": "Unknown Digest Defendant",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-15",
            "principal_debt_uah": 10000,
            "accrued_interest_uah": 500,
            "claim_requests": ["recover debt", "recover court fee"],
        },
        "saved_digest_id": "missing-digest-id",
    }
    response = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Saved digest not found"


def test_generate_document_export_docx_and_pdf(client: TestClient, test_session_factory) -> None:
    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "FREE",
        "form_data": {
            "plaintiff_name": "Ivan",
            "defendant_name": "Petro",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-15",
            "principal_debt_uah": 10000,
            "accrued_interest_uah": 500,
            "claim_requests": ["recover debt"],
        },
    }
    generated = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert generated.status_code == 200
    document_id = generated.json()["document_id"]

    docx_response = client.get(f"/api/documents/{document_id}/export?format=docx", headers={"X-Demo-User": "demo-user"})
    assert docx_response.status_code == 200
    assert docx_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert docx_response.content[:2] == b"PK"

    pdf_response = client.get(f"/api/documents/{document_id}/export?format=pdf", headers={"X-Demo-User": "demo-user"})
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"].startswith("application/pdf")
    assert pdf_response.content[:4] == b"%PDF"

    # The second DOCX export should come from stored file and keep the same bytes.
    docx_response_second = client.get(
        f"/api/documents/{document_id}/export?format=docx",
        headers={"X-Demo-User": "demo-user"},
    )
    assert docx_response_second.status_code == 200
    assert docx_response_second.content == docx_response.content

    history_response = client.get("/api/documents/history", headers={"X-Demo-User": "demo-user"})
    assert history_response.status_code == 200
    history_item = history_response.json()["items"][0]
    assert history_item["has_docx_export"] is True
    assert history_item["has_pdf_export"] is True
    assert history_item["last_exported_at"] is not None

    with test_session_factory() as db:
        row = db.execute(select(GeneratedDocument).where(GeneratedDocument.id == document_id)).scalar_one()
        assert row.docx_storage_path
        assert row.pdf_storage_path
        assert Path(settings.document_storage_root, row.docx_storage_path).exists()
        assert Path(settings.document_storage_root, row.pdf_storage_path).exists()


def test_generate_document_export_processual_report_formats(client: TestClient) -> None:
    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "PRO",
        "form_data": {
            "plaintiff_name": "Report",
            "defendant_name": "Target",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-10",
            "principal_debt_uah": 5000,
            "accrued_interest_uah": 150,
            "claim_requests": ["recover debt"],
        },
    }
    generated = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert generated.status_code == 200
    document_id = generated.json()["document_id"]

    report_docx = client.get(
        f"/api/documents/{document_id}/export?format=docx&report=true",
        headers={"X-Demo-User": "demo-user"},
    )
    assert report_docx.status_code == 200
    assert report_docx.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert report_docx.content[:2] == b"PK"
    assert "processual-report.docx" in report_docx.headers.get("content-disposition", "")

    report_pdf = client.get(
        f"/api/documents/{document_id}/export?format=pdf&report=true",
        headers={"X-Demo-User": "demo-user"},
    )
    assert report_pdf.status_code == 200
    assert report_pdf.headers["content-type"].startswith("application/pdf")
    assert report_pdf.content[:4] == b"%PDF"
    assert "processual-report.pdf" in report_pdf.headers.get("content-disposition", "")


def test_update_document_invalidates_export_cache(client: TestClient, test_session_factory) -> None:
    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "FREE",
        "form_data": {
            "plaintiff_name": "Ivan",
            "defendant_name": "Petro",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-15",
            "principal_debt_uah": 10000,
            "accrued_interest_uah": 500,
            "claim_requests": ["recover debt"],
        },
    }
    generated = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert generated.status_code == 200
    document_id = generated.json()["document_id"]

    exported = client.get(f"/api/documents/{document_id}/export?format=docx", headers={"X-Demo-User": "demo-user"})
    assert exported.status_code == 200

    with test_session_factory() as db:
        row = db.execute(select(GeneratedDocument).where(GeneratedDocument.id == document_id)).scalar_one()
        assert row.docx_storage_path is not None
        old_docx_path = Path(settings.document_storage_root, row.docx_storage_path)
        assert old_docx_path.exists()

    update_response = client.patch(
        f"/api/documents/{document_id}",
        json={"generated_text": "Updated legal text."},
        headers={"X-Demo-User": "demo-user"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "updated"

    with test_session_factory() as db:
        row = db.execute(select(GeneratedDocument).where(GeneratedDocument.id == document_id)).scalar_one()
        assert row.generated_text == "Updated legal text."
        assert row.docx_storage_path is None
        assert row.pdf_storage_path is None
        assert row.last_exported_at is None
    assert not old_docx_path.exists()

    exported_again = client.get(f"/api/documents/{document_id}/export?format=docx", headers={"X-Demo-User": "demo-user"})
    assert exported_again.status_code == 200
    with test_session_factory() as db:
        row = db.execute(select(GeneratedDocument).where(GeneratedDocument.id == document_id)).scalar_one()
        assert row.docx_storage_path is not None
        new_docx_path = Path(settings.document_storage_root, row.docx_storage_path)
        assert new_docx_path.exists()


def test_document_processual_repair_endpoint_repairs_weak_text(client: TestClient, test_session_factory) -> None:
    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "FREE",
        "form_data": {
            "plaintiff_name": "Ivan",
            "defendant_name": "Petro",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-15",
            "principal_debt_uah": 10000,
            "accrued_interest_uah": 500,
            "claim_requests": ["recover debt"],
        },
    }
    generated = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert generated.status_code == 200
    document_id = generated.json()["document_id"]

    weak_update = client.patch(
        f"/api/documents/{document_id}",
        json={"generated_text": "Short English draft without processual structure."},
        headers={"X-Demo-User": "demo-user"},
    )
    assert weak_update.status_code == 200

    repair = client.post(f"/api/documents/{document_id}/processual-repair", headers={"X-Demo-User": "demo-user"})
    assert repair.status_code == 200
    repair_payload = repair.json()
    assert repair_payload["status"] == "repaired"
    assert repair_payload["repaired"] is True
    assert all(item["status"] == "pass" for item in repair_payload["processual_validation_checks"])

    with test_session_factory() as db:
        row = db.execute(select(GeneratedDocument).where(GeneratedDocument.id == document_id)).scalar_one()
        assert "ПОЗОВНА ЗАЯВА" in (row.generated_text or "")
        assert "ПРОШУ СУД" in (row.generated_text or "")
        versions = db.execute(
            select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version_number.asc())
        ).scalars().all()
        assert any(item.action == "repair_processual" for item in versions)


def test_document_processual_check_endpoint_returns_blockers(client: TestClient) -> None:
    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "FREE",
        "form_data": {
            "plaintiff_name": "Ivan",
            "defendant_name": "Petro",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-15",
            "principal_debt_uah": 10000,
            "accrued_interest_uah": 500,
            "claim_requests": ["recover debt"],
        },
    }
    generated = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert generated.status_code == 200
    document_id = generated.json()["document_id"]

    weak_update = client.patch(
        f"/api/documents/{document_id}",
        json={"generated_text": "Short english text."},
        headers={"X-Demo-User": "demo-user"},
    )
    assert weak_update.status_code == 200

    check_response = client.get(f"/api/documents/{document_id}/processual-check", headers={"X-Demo-User": "demo-user"})
    assert check_response.status_code == 200
    check_payload = check_response.json()
    assert check_payload["id"] == document_id
    assert check_payload["is_valid"] is False
    assert len(check_payload["blockers"]) >= 1
    assert any(item["status"] != "pass" for item in check_payload["processual_validation_checks"])


def test_bulk_processual_repair_endpoint_processes_selected_ids(client: TestClient, test_session_factory) -> None:
    ids: list[str] = []
    for principal in (12000, 22000):
        payload = {
            "doc_type": "lawsuit_debt_loan",
            "tariff": "FREE",
            "form_data": {
                "plaintiff_name": "Ivan",
                "defendant_name": "Petro",
                "debt_basis": "loan",
                "debt_start_date": "2024-01-15",
                "principal_debt_uah": principal,
                "accrued_interest_uah": 0,
                "claim_requests": ["recover debt"],
            },
        }
        generated = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
        assert generated.status_code == 200
        ids.append(generated.json()["document_id"])

    for document_id in ids:
        weak_update = client.patch(
            f"/api/documents/{document_id}",
            json={"generated_text": "Short english text."},
            headers={"X-Demo-User": "demo-user"},
        )
        assert weak_update.status_code == 200

    response = client.post(
        "/api/documents/bulk-processual-repair",
        json={"ids": [ids[0], "missing-doc", ids[1]]},
        headers={"X-Demo-User": "demo-user"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["requested"] == 3
    assert payload["processed"] == 2
    assert payload["repaired"] == 2
    assert payload["missing_ids"] == ["missing-doc"]
    assert len(payload["items"]) == 2
    assert all(item["is_valid"] is True for item in payload["items"])

    with test_session_factory() as db:
        versions = db.execute(
            select(DocumentVersion).where(DocumentVersion.document_id.in_(ids))
        ).scalars().all()
        assert any(item.action == "repair_processual_bulk" for item in versions)


def test_documents_history_supports_pagination_and_filters(client: TestClient) -> None:
    payloads = [
        {
            "doc_type": "lawsuit_debt_loan",
            "tariff": "PRO",
            "form_data": {
                "plaintiff_name": "A",
                "defendant_name": "B",
                "debt_basis": "loan",
                "debt_start_date": "2024-01-15",
                "principal_debt_uah": 1000,
                "accrued_interest_uah": 50,
                "claim_requests": ["recover debt"],
            },
        },
        {
            "doc_type": "contract_services",
            "tariff": "PRO",
            "form_data": {
                "party_a": "Company A",
                "party_b": "Company B",
                "fact_summary": "Service scope",
                "request_summary": "Execute services",
            },
        },
        {
            "doc_type": "appeal_complaint",
            "tariff": "PRO",
            "form_data": {
                "party_a": "Client",
                "party_b": "Court",
                "fact_summary": "Appeal facts",
                "request_summary": "Cancel decision",
            },
        },
    ]
    for payload in payloads:
        response = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
        assert response.status_code == 200

    page_one = client.get("/api/documents/history?page=1&page_size=2", headers={"X-Demo-User": "demo-user"})
    assert page_one.status_code == 200
    page_one_data = page_one.json()
    assert page_one_data["total"] == 3
    assert page_one_data["page"] == 1
    assert page_one_data["page_size"] == 2
    assert page_one_data["pages"] == 2
    assert len(page_one_data["items"]) == 2
    assert "e_court_ready" in page_one_data["items"][0]
    assert isinstance(page_one_data["items"][0]["filing_blockers"], list)

    page_two = client.get("/api/documents/history?page=2&page_size=2", headers={"X-Demo-User": "demo-user"})
    assert page_two.status_code == 200
    page_two_data = page_two.json()
    assert page_two_data["page"] == 2
    assert len(page_two_data["items"]) == 1

    filtered = client.get(
        "/api/documents/history?doc_type=contract_services&page_size=10",
        headers={"X-Demo-User": "demo-user"},
    )
    assert filtered.status_code == 200
    filtered_data = filtered.json()
    assert filtered_data["total"] == 1
    assert filtered_data["items"][0]["document_type"] == "contract_services"


def test_delete_document_removes_row_and_files(client: TestClient, test_session_factory) -> None:
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
            "claim_requests": ["recover debt"],
        },
    }
    generated = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert generated.status_code == 200
    document_id = generated.json()["document_id"]

    exported = client.get(f"/api/documents/{document_id}/export?format=docx", headers={"X-Demo-User": "demo-user"})
    assert exported.status_code == 200

    with test_session_factory() as db:
        row = db.execute(select(GeneratedDocument).where(GeneratedDocument.id == document_id)).scalar_one()
        assert row.docx_storage_path is not None
        docx_path = Path(settings.document_storage_root, row.docx_storage_path)
        assert docx_path.exists()

    deleted = client.delete(f"/api/documents/{document_id}", headers={"X-Demo-User": "demo-user"})
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"

    with test_session_factory() as db:
        row = db.execute(select(GeneratedDocument).where(GeneratedDocument.id == document_id)).scalar_one_or_none()
        assert row is None
    assert not docx_path.exists()


def test_get_document_detail_and_clone(client: TestClient, test_session_factory) -> None:
    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "PRO",
        "form_data": {
            "plaintiff_name": "Olena",
            "defendant_name": "Mykola",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-10",
            "principal_debt_uah": 4500,
            "accrued_interest_uah": 200,
            "claim_requests": ["recover debt", "recover court fee"],
        },
    }
    generated = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert generated.status_code == 200
    source_id = generated.json()["document_id"]

    detail = client.get(f"/api/documents/{source_id}", headers={"X-Demo-User": "demo-user"})
    assert detail.status_code == 200
    detail_data = detail.json()
    assert detail_data["id"] == source_id
    assert detail_data["document_type"] == "lawsuit_debt_loan"
    assert detail_data["generated_text"]
    assert "e_court_ready" in detail_data
    assert isinstance(detail_data["filing_blockers"], list)

    cloned = client.post(f"/api/documents/{source_id}/clone", headers={"X-Demo-User": "demo-user"})
    assert cloned.status_code == 200
    clone_data = cloned.json()
    assert clone_data["status"] == "created"
    assert clone_data["source_id"] == source_id
    clone_id = clone_data["document_id"]
    assert clone_id != source_id

    with test_session_factory() as db:
        source_row = db.execute(select(GeneratedDocument).where(GeneratedDocument.id == source_id)).scalar_one()
        clone_row = db.execute(select(GeneratedDocument).where(GeneratedDocument.id == clone_id)).scalar_one()
        assert clone_row.generated_text == source_row.generated_text
        assert clone_row.preview_text == source_row.preview_text
        assert clone_row.form_data == source_row.form_data
        assert clone_row.calculations == source_row.calculations
        clone_versions = db.execute(
            select(DocumentVersion).where(DocumentVersion.document_id == clone_id).order_by(DocumentVersion.version_number)
        ).scalars().all()
        assert len(clone_versions) == 1
        assert clone_versions[0].action == "clone"


def test_document_versions_and_restore_flow(client: TestClient, test_session_factory) -> None:
    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "PRO",
        "form_data": {
            "plaintiff_name": "Version",
            "defendant_name": "Flow",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-20",
            "principal_debt_uah": 7000,
            "accrued_interest_uah": 100,
            "claim_requests": ["recover debt"],
        },
    }
    generated = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert generated.status_code == 200
    document_id = generated.json()["document_id"]
    original_text = generated.json()["generated_text"]

    versions_initial = client.get(f"/api/documents/{document_id}/versions", headers={"X-Demo-User": "demo-user"})
    assert versions_initial.status_code == 200
    initial_payload = versions_initial.json()
    assert initial_payload["total"] == 1
    assert initial_payload["items"][0]["action"] == "generate"
    first_version_id = initial_payload["items"][0]["id"]

    updated = client.patch(
        f"/api/documents/{document_id}",
        json={"generated_text": "New updated text"},
        headers={"X-Demo-User": "demo-user"},
    )
    assert updated.status_code == 200

    versions_after_update = client.get(f"/api/documents/{document_id}/versions", headers={"X-Demo-User": "demo-user"})
    assert versions_after_update.status_code == 200
    updated_payload = versions_after_update.json()
    assert updated_payload["total"] == 2
    assert updated_payload["items"][0]["action"] == "update"

    restored = client.post(
        f"/api/documents/{document_id}/versions/{first_version_id}/restore",
        headers={"X-Demo-User": "demo-user"},
    )
    assert restored.status_code == 200
    restore_payload = restored.json()
    assert restore_payload["status"] == "restored"
    assert restore_payload["restored_from_version_id"] == first_version_id
    assert restore_payload["restored_to_version_number"] == 4

    detail = client.get(f"/api/documents/{document_id}", headers={"X-Demo-User": "demo-user"})
    assert detail.status_code == 200
    assert detail.json()["generated_text"] == original_text

    with test_session_factory() as db:
        rows = db.execute(
            select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version_number)
        ).scalars().all()
        assert [row.action for row in rows] == ["generate", "update", "snapshot_before_restore", "restore"]


def test_document_version_detail_and_diff_endpoints(client: TestClient) -> None:
    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "PRO",
        "form_data": {
            "plaintiff_name": "Diff",
            "defendant_name": "Check",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-21",
            "principal_debt_uah": 3000,
            "accrued_interest_uah": 120,
            "claim_requests": ["recover debt"],
        },
    }
    generated = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert generated.status_code == 200
    document_id = generated.json()["document_id"]

    versions = client.get(f"/api/documents/{document_id}/versions", headers={"X-Demo-User": "demo-user"})
    assert versions.status_code == 200
    version_id = versions.json()["items"][0]["id"]

    detail = client.get(f"/api/documents/{document_id}/versions/{version_id}", headers={"X-Demo-User": "demo-user"})
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["id"] == version_id
    assert detail_payload["version_number"] == 1
    assert detail_payload["action"] == "generate"
    assert detail_payload["generated_text"]

    # Change current document text, then compare old version against current.
    updated = client.patch(
        f"/api/documents/{document_id}",
        json={"generated_text": "Totally changed content for diff"},
        headers={"X-Demo-User": "demo-user"},
    )
    assert updated.status_code == 200

    diff_response = client.get(
        f"/api/documents/{document_id}/versions/{version_id}/diff?against=current",
        headers={"X-Demo-User": "demo-user"},
    )
    assert diff_response.status_code == 200
    diff_payload = diff_response.json()
    assert diff_payload["document_id"] == document_id
    assert diff_payload["target_version_id"] == version_id
    assert diff_payload["against"] == "current"
    assert isinstance(diff_payload["added_lines"], int)
    assert isinstance(diff_payload["removed_lines"], int)
    assert diff_payload["diff_text"]

    versions_after_update = client.get(f"/api/documents/{document_id}/versions", headers={"X-Demo-User": "demo-user"})
    assert versions_after_update.status_code == 200
    update_version_id = versions_after_update.json()["items"][0]["id"]
    diff_against_version = client.get(
        f"/api/documents/{document_id}/versions/{version_id}/diff?against={update_version_id}",
        headers={"X-Demo-User": "demo-user"},
    )
    assert diff_against_version.status_code == 200
    diff_against_payload = diff_against_version.json()
    assert diff_against_payload["against"] == update_version_id
    assert diff_against_payload["against_version_number"] == 2
    assert diff_against_payload["diff_text"]


def test_documents_history_filter_by_export_flags(client: TestClient) -> None:
    payload_a = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "PRO",
        "form_data": {
            "plaintiff_name": "Filter",
            "defendant_name": "A",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-15",
            "principal_debt_uah": 1000,
            "accrued_interest_uah": 50,
            "claim_requests": ["recover debt"],
        },
    }
    payload_b = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "PRO",
        "form_data": {
            "plaintiff_name": "Filter",
            "defendant_name": "B",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-16",
            "principal_debt_uah": 1500,
            "accrued_interest_uah": 70,
            "claim_requests": ["recover debt"],
        },
    }
    generated_a = client.post("/api/documents/generate", json=payload_a, headers={"X-Demo-User": "demo-user"})
    generated_b = client.post("/api/documents/generate", json=payload_b, headers={"X-Demo-User": "demo-user"})
    assert generated_a.status_code == 200
    assert generated_b.status_code == 200
    doc_a = generated_a.json()["document_id"]
    doc_b = generated_b.json()["document_id"]

    exported_docx = client.get(f"/api/documents/{doc_a}/export?format=docx", headers={"X-Demo-User": "demo-user"})
    exported_pdf = client.get(f"/api/documents/{doc_a}/export?format=pdf", headers={"X-Demo-User": "demo-user"})
    assert exported_docx.status_code == 200
    assert exported_pdf.status_code == 200

    has_docx = client.get("/api/documents/history?has_docx_export=true", headers={"X-Demo-User": "demo-user"})
    assert has_docx.status_code == 200
    ids_docx = [item["id"] for item in has_docx.json()["items"]]
    assert doc_a in ids_docx
    assert doc_b not in ids_docx

    no_docx = client.get("/api/documents/history?has_docx_export=false", headers={"X-Demo-User": "demo-user"})
    assert no_docx.status_code == 200
    ids_no_docx = [item["id"] for item in no_docx.json()["items"]]
    assert doc_b in ids_no_docx

    has_pdf = client.get("/api/documents/history?has_pdf_export=true", headers={"X-Demo-User": "demo-user"})
    assert has_pdf.status_code == 200
    ids_pdf = [item["id"] for item in has_pdf.json()["items"]]
    assert doc_a in ids_pdf


def test_documents_history_export_csv_and_zip(client: TestClient) -> None:
    payloads = [
        {
            "doc_type": "lawsuit_debt_loan",
            "tariff": "PRO",
            "form_data": {
                "plaintiff_name": "A",
                "defendant_name": "B",
                "debt_basis": "loan",
                "debt_start_date": "2024-01-15",
                "principal_debt_uah": 1200,
                "accrued_interest_uah": 80,
                "claim_requests": ["recover debt"],
            },
        },
        {
            "doc_type": "contract_services",
            "tariff": "PRO",
            "form_data": {
                "party_a": "Firm A",
                "party_b": "Firm B",
                "fact_summary": "Service task",
                "request_summary": "Execute task",
            },
        },
    ]
    for payload in payloads:
        response = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
        assert response.status_code == 200

    csv_response = client.get("/api/documents/history/export?format=csv", headers={"X-Demo-User": "demo-user"})
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    csv_text = csv_response.content.decode("utf-8-sig")
    assert "document_type" in csv_text
    assert "lawsuit_debt_loan" in csv_text
    assert "contract_services" in csv_text

    zip_response = client.get(
        "/api/documents/history/export?format=zip&doc_type=contract_services",
        headers={"X-Demo-User": "demo-user"},
    )
    assert zip_response.status_code == 200
    assert zip_response.headers["content-type"].startswith("application/zip")
    assert zip_response.content[:2] == b"PK"

    with zipfile.ZipFile(BytesIO(zip_response.content)) as archive:
        names = archive.namelist()
        assert "history.csv" in names
        assert any(name.startswith("documents/") and name.endswith(".txt") for name in names)
        history_csv = archive.read("history.csv").decode("utf-8")
        assert "contract_services" in history_csv
        assert "lawsuit_debt_loan" not in history_csv


def test_bulk_delete_documents(client: TestClient, test_session_factory) -> None:
    generated_ids: list[str] = []
    for principal in (900, 1100):
        payload = {
            "doc_type": "lawsuit_debt_loan",
            "tariff": "PRO",
            "form_data": {
                "plaintiff_name": "Bulk",
                "defendant_name": "Delete",
                "debt_basis": "loan",
                "debt_start_date": "2024-01-15",
                "principal_debt_uah": principal,
                "accrued_interest_uah": 50,
                "claim_requests": ["recover debt"],
            },
        }
        generated = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
        assert generated.status_code == 200
        generated_ids.append(generated.json()["document_id"])

    delete_response = client.post(
        "/api/documents/bulk-delete",
        json={"ids": [generated_ids[0], generated_ids[1], "missing-doc-id"]},
        headers={"X-Demo-User": "demo-user"},
    )
    assert delete_response.status_code == 200
    payload = delete_response.json()
    assert payload["status"] == "completed"
    assert payload["requested"] == 3
    assert payload["deleted"] == 2
    assert set(payload["deleted_ids"]) == set(generated_ids)
    assert payload["missing_ids"] == ["missing-doc-id"]

    with test_session_factory() as db:
        remaining = db.execute(select(GeneratedDocument).where(GeneratedDocument.id.in_(generated_ids))).scalars().all()
        assert len(remaining) == 0


def test_audit_history_endpoint(client: TestClient) -> None:
    payload = {
        "doc_type": "lawsuit_debt_loan",
        "tariff": "PRO",
        "form_data": {
            "plaintiff_name": "Audit",
            "defendant_name": "User",
            "debt_basis": "loan",
            "debt_start_date": "2024-01-15",
            "principal_debt_uah": 2500,
            "accrued_interest_uah": 100,
            "claim_requests": ["recover debt"],
        },
    }
    generated = client.post("/api/documents/generate", json=payload, headers={"X-Demo-User": "demo-user"})
    assert generated.status_code == 200
    doc_id = generated.json()["document_id"]

    bulk_delete = client.post("/api/documents/bulk-delete", json={"ids": [doc_id]}, headers={"X-Demo-User": "demo-user"})
    assert bulk_delete.status_code == 200

    audit = client.get("/api/audit/history?page=1&page_size=50", headers={"X-Demo-User": "demo-user"})
    assert audit.status_code == 200
    data = audit.json()
    assert data["total"] >= 2
    actions = [item["action"] for item in data["items"]]
    assert "document_generate" in actions
    assert "document_bulk_delete" in actions

    filtered = client.get(
        "/api/audit/history?action=document_bulk_delete&page_size=10",
        headers={"X-Demo-User": "demo-user"},
    )
    assert filtered.status_code == 200
    filtered_data = filtered.json()
    assert filtered_data["total"] >= 1
    assert all(item["action"] == "document_bulk_delete" for item in filtered_data["items"])
