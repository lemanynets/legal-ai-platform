from __future__ import annotations

import json
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


def _post_full_lawyer(
    client: TestClient,
    *,
    content: str,
    max_documents: int = 3,
    clarifications: dict[str, str] | None = None,
    review_confirmations: dict[str, bool] | None = None,
    generate_package: bool = False,
    generate_package_draft_on_hard_stop: bool = False,
):
    data: dict[str, str] = {
        "max_documents": str(max_documents),
        "generate_package": str(generate_package).lower(),
        "generate_package_draft_on_hard_stop": str(generate_package_draft_on_hard_stop).lower(),
    }
    if clarifications is not None:
        data["clarifications_json"] = json.dumps(clarifications)
    if review_confirmations is not None:
        data["review_confirmations_json"] = json.dumps(review_confirmations)
    return client.post(
        "/api/auto/full-lawyer",
        data=data,
        files={"file": ("sample.txt", content.encode("utf-8"), "text/plain")},
        headers={"X-Demo-User": "demo-user"},
    )


def _post_full_lawyer_preflight(
    client: TestClient,
    *,
    content: str,
    max_documents: int = 3,
    clarifications: dict[str, str] | None = None,
    review_confirmations: dict[str, bool] | None = None,
):
    data: dict[str, str] = {"max_documents": str(max_documents)}
    if clarifications is not None:
        data["clarifications_json"] = json.dumps(clarifications)
    if review_confirmations is not None:
        data["review_confirmations_json"] = json.dumps(review_confirmations)
    return client.post(
        "/api/auto/full-lawyer/preflight",
        data=data,
        files={"file": ("sample.txt", content.encode("utf-8"), "text/plain")},
        headers={"X-Demo-User": "demo-user"},
    )


def test_full_lawyer_requires_clarifications_before_generation(client: TestClient) -> None:
    file_content = (
        "Plaintiff: Ivan Ivanov\n"
        "Defendant: Petro Petrov\n"
        "Debt under loan agreement is 125000 UAH.\n"
        "Please recover debt and court fee.\n"
    )
    response = _post_full_lawyer(client, content=file_content, max_documents=3)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_clarification"
    assert payload["clarification_required"] is True
    assert len(payload["unresolved_questions"]) >= 1
    assert len(payload["generated_documents"]) == 0
    assert len(payload["workflow_stages"]) == 4
    assert payload["ready_for_filing"] is False
    assert payload["workflow_stages"][-1]["status"] == "blocked"
    assert isinstance(payload["procedural_timeline"], list)
    assert isinstance(payload["evidence_matrix"], list)
    assert isinstance(payload["fact_chronology_matrix"], list)
    assert len(payload["fact_chronology_matrix"]) >= 1
    assert isinstance(payload["burden_of_proof_map"], list)
    assert len(payload["burden_of_proof_map"]) >= 1
    assert isinstance(payload["drafting_instructions"], list)
    assert len(payload["drafting_instructions"]) >= 1
    assert isinstance(payload["opponent_weakness_map"], list)
    assert len(payload["opponent_weakness_map"]) >= 1
    assert isinstance(payload["evidence_collection_plan"], list)
    assert len(payload["evidence_collection_plan"]) >= 1
    assert isinstance(payload["factual_circumstances_blocks"], list)
    assert len(payload["factual_circumstances_blocks"]) >= 1
    assert isinstance(payload["legal_qualification_blocks"], list)
    assert len(payload["legal_qualification_blocks"]) >= 1
    assert isinstance(payload["prayer_part_variants"], list)
    assert len(payload["prayer_part_variants"]) >= 1
    assert isinstance(payload["counterargument_response_matrix"], list)
    assert len(payload["counterargument_response_matrix"]) >= 1
    assert isinstance(payload["document_narrative_completeness"], list)
    assert len(payload["document_narrative_completeness"]) >= 1
    assert isinstance(payload["case_law_application_matrix"], list)
    assert len(payload["case_law_application_matrix"]) >= 1
    assert isinstance(payload["procedural_violation_hypotheses"], list)
    assert len(payload["procedural_violation_hypotheses"]) >= 1
    assert isinstance(payload["document_fact_enrichment_plan"], list)
    assert len(payload["document_fact_enrichment_plan"]) >= 1
    assert isinstance(payload["hearing_positioning_notes"], list)
    assert len(payload["hearing_positioning_notes"]) >= 1
    assert isinstance(payload["process_stage_action_map"], list)
    assert len(payload["process_stage_action_map"]) >= 1
    assert isinstance(payload["legal_argument_map"], list)
    assert isinstance(payload["readiness_breakdown"], dict)
    assert isinstance(payload["post_filing_plan"], list)
    assert isinstance(payload["party_profile"], dict)
    assert isinstance(payload["jurisdiction_recommendation"], dict)
    assert isinstance(payload["generated_docs_quality"], list)
    assert isinstance(payload["e_court_submission_preview"], dict)
    assert isinstance(payload["priority_queue"], list)
    assert isinstance(payload["consistency_report"], list)
    assert isinstance(payload["remedy_coverage"], list)
    assert isinstance(payload["citation_pack"], dict)
    assert isinstance(payload["fee_scenarios"], list)
    assert isinstance(payload["filing_risk_simulation"], list)
    assert isinstance(payload["procedural_defect_scan"], list)
    assert isinstance(payload["evidence_admissibility_map"], list)
    assert isinstance(payload["motion_recommendations"], list)
    assert isinstance(payload["hearing_preparation_plan"], list)
    assert isinstance(payload["package_completeness"], dict)
    assert isinstance(payload["opponent_objections"], list)
    assert isinstance(payload["settlement_strategy"], dict)
    assert isinstance(payload["enforcement_plan"], list)
    assert isinstance(payload["cpc_compliance_check"], list)
    assert isinstance(payload["procedural_document_blueprint"], list)
    assert isinstance(payload["deadline_control"], list)
    assert isinstance(payload["court_fee_breakdown"], dict)
    assert isinstance(payload["filing_attachments_register"], list)
    assert isinstance(payload["cpc_175_requisites_map"], list)
    assert isinstance(payload["cpc_177_attachments_map"], list)
    assert isinstance(payload["prayer_part_audit"], dict)
    assert isinstance(payload["fact_norm_evidence_chain"], list)
    assert isinstance(payload["pre_filing_red_flags"], list)
    assert isinstance(payload["text_section_audit"], list)
    assert isinstance(payload["service_plan"], list)
    assert isinstance(payload["prayer_rewrite_suggestions"], list)
    assert isinstance(payload["contradiction_hotspots"], list)
    assert isinstance(payload["judge_questions_simulation"], list)
    assert isinstance(payload["citation_quality_gate"], dict)
    assert isinstance(payload["filing_decision_card"], dict)
    assert isinstance(payload["processual_language_audit"], dict)
    assert isinstance(payload["evidence_gap_actions"], list)
    assert isinstance(payload["deadline_alert_board"], list)
    assert isinstance(payload["filing_packet_order"], list)
    assert isinstance(payload["opponent_response_playbook"], list)
    assert isinstance(payload["limitation_period_card"], dict)
    assert isinstance(payload["jurisdiction_challenge_guard"], dict)
    assert isinstance(payload["claim_formula_card"], dict)
    assert isinstance(payload["filing_cover_letter"], dict)
    assert isinstance(payload["execution_step_tracker"], list)
    assert isinstance(payload["version_control_card"], dict)
    assert isinstance(payload["e_court_packet_readiness"], dict)
    assert isinstance(payload["hearing_script_pack"], list)
    assert isinstance(payload["settlement_offer_card"], dict)
    assert isinstance(payload["appeal_reserve_card"], dict)
    assert isinstance(payload["procedural_costs_allocator_card"], dict)
    assert isinstance(payload["document_export_readiness"], dict)
    assert isinstance(payload["filing_submission_checklist_card"], list)
    assert isinstance(payload["post_filing_monitoring_board"], list)
    assert isinstance(payload["legal_research_backlog"], list)
    assert isinstance(payload["procedural_consistency_scorecard"], dict)
    assert isinstance(payload["hearing_evidence_order_card"], list)
    assert isinstance(payload["digital_signature_readiness"], dict)
    assert isinstance(payload["case_law_update_watchlist"], list)
    assert isinstance(payload["final_submission_gate"], dict)
    assert isinstance(payload["court_behavior_forecast_card"], dict)
    assert isinstance(payload["evidence_pack_compression_plan"], list)
    assert isinstance(payload["filing_channel_strategy_card"], dict)
    assert isinstance(payload["legal_budget_timeline_card"], dict)
    assert isinstance(payload["counterparty_pressure_map"], list)
    assert isinstance(payload["courtroom_timeline_scenarios"], list)
    assert isinstance(payload["evidence_authenticity_checklist"], list)
    assert isinstance(payload["remedy_priority_matrix"], list)
    assert isinstance(payload["judge_question_drill_card"], dict)
    assert isinstance(payload["client_instruction_packet"], list)
    assert isinstance(payload["procedural_risk_heatmap"], list)
    assert isinstance(payload["evidence_disclosure_plan"], list)
    assert isinstance(payload["settlement_negotiation_script"], list)
    assert isinstance(payload["hearing_readiness_scorecard"], dict)
    assert isinstance(payload["advocate_signoff_packet"], dict)


def test_full_lawyer_generates_after_clarifications_and_package(client: TestClient) -> None:
    file_content = (
        "Plaintiff: Ivan Ivanov\n"
        "Defendant: Petro Petrov\n"
        "Debt under loan agreement is 125000 UAH.\n"
        "Please recover debt and court fee.\n"
    )
    first = _post_full_lawyer(client, content=file_content, max_documents=3)
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["status"] == "needs_clarification"
    unresolved = first_payload["unresolved_questions"]
    answers = {question: "Confirmed." for question in unresolved}
    review_map = {item["code"]: True for item in first_payload["review_checklist"]}

    second = _post_full_lawyer(
        client,
        content=file_content,
        max_documents=3,
        clarifications=answers,
        review_confirmations=review_map,
        generate_package=True,
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["status"] == "ok"
    assert payload["clarification_required"] is False
    assert len(payload["generated_documents"]) >= 1
    if payload["final_submission_gate"]["hard_stop"]:
        assert payload["filing_package"]["generated"] is False
        assert any(
            ("hard-stop" in item.lower()) and ("gate" in item.lower() or "гейт" in item.lower())
            for item in payload["warnings"]
        )
    else:
        assert payload["filing_package"]["generated"] is True
        assert len(payload["filing_package"]["items"]) >= 1
    assert isinstance(payload["validation_checks"], list)
    assert isinstance(payload["context_refs"], list)
    assert isinstance(payload["next_actions"], list)
    assert isinstance(payload["confidence_score"], float)
    assert len(payload["workflow_stages"]) == 4
    assert all("status" in stage for stage in payload["workflow_stages"])
    assert isinstance(payload["procedural_timeline"], list)
    assert isinstance(payload["evidence_matrix"], list)
    assert isinstance(payload["fact_chronology_matrix"], list)
    assert len(payload["fact_chronology_matrix"]) >= 1
    assert isinstance(payload["burden_of_proof_map"], list)
    assert len(payload["burden_of_proof_map"]) >= 1
    assert isinstance(payload["drafting_instructions"], list)
    assert len(payload["drafting_instructions"]) >= 1
    assert isinstance(payload["opponent_weakness_map"], list)
    assert len(payload["opponent_weakness_map"]) >= 1
    assert isinstance(payload["evidence_collection_plan"], list)
    assert len(payload["evidence_collection_plan"]) >= 1
    assert isinstance(payload["factual_circumstances_blocks"], list)
    assert len(payload["factual_circumstances_blocks"]) >= 1
    assert isinstance(payload["legal_qualification_blocks"], list)
    assert len(payload["legal_qualification_blocks"]) >= 1
    assert isinstance(payload["prayer_part_variants"], list)
    assert len(payload["prayer_part_variants"]) >= 1
    assert isinstance(payload["counterargument_response_matrix"], list)
    assert len(payload["counterargument_response_matrix"]) >= 1
    assert isinstance(payload["document_narrative_completeness"], list)
    assert len(payload["document_narrative_completeness"]) >= 1
    assert isinstance(payload["case_law_application_matrix"], list)
    assert len(payload["case_law_application_matrix"]) >= 1
    assert isinstance(payload["procedural_violation_hypotheses"], list)
    assert len(payload["procedural_violation_hypotheses"]) >= 1
    assert isinstance(payload["document_fact_enrichment_plan"], list)
    assert len(payload["document_fact_enrichment_plan"]) >= 1
    assert isinstance(payload["hearing_positioning_notes"], list)
    assert len(payload["hearing_positioning_notes"]) >= 1
    assert isinstance(payload["process_stage_action_map"], list)
    assert len(payload["process_stage_action_map"]) >= 1
    assert isinstance(payload["legal_argument_map"], list)
    assert isinstance(payload["readiness_breakdown"], dict)
    assert isinstance(payload["post_filing_plan"], list)
    assert isinstance(payload["party_profile"], dict)
    assert isinstance(payload["jurisdiction_recommendation"], dict)
    assert isinstance(payload["generated_docs_quality"], list)
    assert isinstance(payload["e_court_submission_preview"], dict)
    assert isinstance(payload["priority_queue"], list)
    assert isinstance(payload["consistency_report"], list)
    assert isinstance(payload["remedy_coverage"], list)
    assert isinstance(payload["citation_pack"], dict)
    assert isinstance(payload["fee_scenarios"], list)
    assert isinstance(payload["filing_risk_simulation"], list)
    assert isinstance(payload["procedural_defect_scan"], list)
    assert isinstance(payload["evidence_admissibility_map"], list)
    assert isinstance(payload["motion_recommendations"], list)
    assert isinstance(payload["hearing_preparation_plan"], list)
    assert isinstance(payload["package_completeness"], dict)
    assert isinstance(payload["opponent_objections"], list)
    assert isinstance(payload["settlement_strategy"], dict)
    assert isinstance(payload["enforcement_plan"], list)
    assert isinstance(payload["cpc_compliance_check"], list)
    assert isinstance(payload["procedural_document_blueprint"], list)
    assert isinstance(payload["deadline_control"], list)
    assert isinstance(payload["court_fee_breakdown"], dict)
    assert isinstance(payload["filing_attachments_register"], list)
    assert isinstance(payload["cpc_175_requisites_map"], list)
    assert isinstance(payload["cpc_177_attachments_map"], list)
    assert isinstance(payload["prayer_part_audit"], dict)
    assert isinstance(payload["fact_norm_evidence_chain"], list)
    assert isinstance(payload["pre_filing_red_flags"], list)
    assert isinstance(payload["text_section_audit"], list)
    assert isinstance(payload["service_plan"], list)
    assert isinstance(payload["prayer_rewrite_suggestions"], list)
    assert isinstance(payload["contradiction_hotspots"], list)
    assert isinstance(payload["judge_questions_simulation"], list)
    assert isinstance(payload["citation_quality_gate"], dict)
    assert isinstance(payload["filing_decision_card"], dict)
    assert isinstance(payload["processual_language_audit"], dict)
    assert isinstance(payload["evidence_gap_actions"], list)
    assert isinstance(payload["deadline_alert_board"], list)
    assert isinstance(payload["filing_packet_order"], list)
    assert isinstance(payload["opponent_response_playbook"], list)
    assert isinstance(payload["limitation_period_card"], dict)
    assert isinstance(payload["jurisdiction_challenge_guard"], dict)
    assert isinstance(payload["claim_formula_card"], dict)
    assert isinstance(payload["filing_cover_letter"], dict)
    assert isinstance(payload["execution_step_tracker"], list)
    assert isinstance(payload["version_control_card"], dict)
    assert isinstance(payload["e_court_packet_readiness"], dict)
    assert isinstance(payload["hearing_script_pack"], list)
    assert isinstance(payload["settlement_offer_card"], dict)
    assert isinstance(payload["appeal_reserve_card"], dict)
    assert isinstance(payload["procedural_costs_allocator_card"], dict)
    assert isinstance(payload["document_export_readiness"], dict)
    assert isinstance(payload["filing_submission_checklist_card"], list)
    assert isinstance(payload["post_filing_monitoring_board"], list)
    assert isinstance(payload["legal_research_backlog"], list)
    assert isinstance(payload["procedural_consistency_scorecard"], dict)
    assert isinstance(payload["hearing_evidence_order_card"], list)
    assert isinstance(payload["digital_signature_readiness"], dict)
    assert isinstance(payload["case_law_update_watchlist"], list)
    assert isinstance(payload["final_submission_gate"], dict)
    assert isinstance(payload["court_behavior_forecast_card"], dict)
    assert isinstance(payload["evidence_pack_compression_plan"], list)
    assert isinstance(payload["filing_channel_strategy_card"], dict)
    assert isinstance(payload["legal_budget_timeline_card"], dict)
    assert isinstance(payload["counterparty_pressure_map"], list)
    assert isinstance(payload["courtroom_timeline_scenarios"], list)
    assert isinstance(payload["evidence_authenticity_checklist"], list)
    assert isinstance(payload["remedy_priority_matrix"], list)
    assert isinstance(payload["judge_question_drill_card"], dict)
    assert isinstance(payload["client_instruction_packet"], list)
    assert isinstance(payload["procedural_risk_heatmap"], list)
    assert isinstance(payload["evidence_disclosure_plan"], list)
    assert isinstance(payload["settlement_negotiation_script"], list)
    assert isinstance(payload["hearing_readiness_scorecard"], dict)
    assert isinstance(payload["advocate_signoff_packet"], dict)


def test_full_lawyer_requires_review_gate_after_clarifications(client: TestClient) -> None:
    file_content = (
        "Plaintiff: Ivan Ivanov\n"
        "Defendant: Petro Petrov\n"
        "Debt under loan agreement is 82000 UAH.\n"
    )
    first = _post_full_lawyer(client, content=file_content, max_documents=2)
    assert first.status_code == 200
    first_payload = first.json()
    answers = {question: "Confirmed." for question in first_payload["unresolved_questions"]}

    second = _post_full_lawyer(client, content=file_content, max_documents=2, clarifications=answers)
    assert second.status_code == 200
    payload = second.json()
    assert payload["status"] == "needs_review"
    assert payload["review_required"] is True
    assert len(payload["unresolved_review_items"]) >= 1
    assert len(payload["generated_documents"]) == 0


def test_full_lawyer_preflight_returns_gates_and_hint(client: TestClient) -> None:
    file_content = (
        "Plaintiff: Ivan Ivanov\n"
        "Defendant: Petro Petrov\n"
        "Debt under loan agreement is 93000 UAH.\n"
        "Need to recover debt and court fee.\n"
    )
    response = _post_full_lawyer_preflight(client, content=file_content, max_documents=3)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"needs_clarification", "needs_review", "ok"}
    assert isinstance(payload["recommended_doc_types"], list)
    assert isinstance(payload["deadline_control"], list)
    assert isinstance(payload["processual_package_gate"], dict)
    assert payload["processual_package_gate"]["status"] == "pending"
    assert payload["package_generation_hint"]["can_generate_final_package"] is False
    assert isinstance(payload["package_generation_hint"]["can_generate_draft_package"], bool)
    assert payload["package_generation_hint"]["recommended_package_mode"] in {"none", "draft", "final"}
    assert isinstance(payload["final_submission_gate"], dict)
    assert len(payload["next_actions"]) >= 1


def test_full_lawyer_preflight_allows_draft_hint_after_answers(client: TestClient) -> None:
    file_content = (
        "Plaintiff: Ivan Ivanov\n"
        "Defendant: Petro Petrov\n"
        "Debt under loan agreement is 93000 UAH.\n"
        "Need to recover debt and court fee.\n"
    )
    first = _post_full_lawyer_preflight(client, content=file_content, max_documents=3)
    assert first.status_code == 200
    first_payload = first.json()
    answers = {question: "Confirmed." for question in first_payload["unresolved_questions"]}
    review_map = {item["code"]: True for item in first_payload["review_checklist"]}

    second = _post_full_lawyer_preflight(
        client,
        content=file_content,
        max_documents=3,
        clarifications=answers,
        review_confirmations=review_map,
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["status"] == "ok"
    assert payload["package_generation_hint"]["can_generate_draft_package"] is True
    assert payload["package_generation_hint"]["can_generate_final_package"] is False
    assert payload["package_generation_hint"]["recommended_package_mode"] == "draft"


def test_full_lawyer_preflight_export_pdf(client: TestClient) -> None:
    file_content = (
        "Plaintiff: Ivan Ivanov\n"
        "Defendant: Petro Petrov\n"
        "Debt under loan agreement is 93000 UAH.\n"
    )
    response = client.post(
        "/api/auto/full-lawyer/preflight/export",
        data={"max_documents": "3", "format": "pdf"},
        files={"file": ("sample.txt", file_content.encode("utf-8"), "text/plain")},
        headers={"X-Demo-User": "demo-user"},
    )
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/pdf"
    assert response.headers.get("content-disposition", "").startswith("attachment;")
    assert len(response.content) > 100


def test_full_lawyer_preflight_export_docx(client: TestClient) -> None:
    file_content = (
        "Plaintiff: Ivan Ivanov\n"
        "Defendant: Petro Petrov\n"
        "Debt under loan agreement is 93000 UAH.\n"
    )
    response = client.post(
        "/api/auto/full-lawyer/preflight/export",
        data={"max_documents": "3", "format": "docx"},
        files={"file": ("sample.txt", file_content.encode("utf-8"), "text/plain")},
        headers={"X-Demo-User": "demo-user"},
    )
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert response.headers.get("content-disposition", "").startswith("attachment;")
    assert len(response.content) > 100


def test_full_lawyer_preflight_history_lists_upload_and_export(client: TestClient) -> None:
    file_content = (
        "Plaintiff: Ivan Ivanov\n"
        "Defendant: Petro Petrov\n"
        "Debt under loan agreement is 93000 UAH.\n"
    )
    upload = _post_full_lawyer_preflight(client, content=file_content, max_documents=3)
    assert upload.status_code == 200

    export = client.post(
        "/api/auto/full-lawyer/preflight/export",
        data={"max_documents": "3", "format": "pdf"},
        files={"file": ("sample.txt", file_content.encode("utf-8"), "text/plain")},
        headers={"X-Demo-User": "demo-user"},
    )
    assert export.status_code == 200

    all_history = client.get(
        "/api/auto/full-lawyer/preflight/history?page=1&page_size=20&event=all",
        headers={"X-Demo-User": "demo-user"},
    )
    assert all_history.status_code == 200
    all_payload = all_history.json()
    assert all_payload["total"] >= 2
    event_types = {item["event_type"] for item in all_payload["items"]}
    assert "upload" in event_types
    assert "export" in event_types

    upload_history = client.get(
        "/api/auto/full-lawyer/preflight/history?page=1&page_size=20&event=upload",
        headers={"X-Demo-User": "demo-user"},
    )
    assert upload_history.status_code == 200
    upload_payload = upload_history.json()
    assert upload_payload["event"] == "upload"
    assert all(item["event_type"] == "upload" for item in upload_payload["items"])

    first_item = next((item for item in upload_payload["items"] if item.get("has_report_snapshot")), None)
    assert first_item is not None
    audit_id = first_item["id"]

    history_export = client.get(
        f"/api/auto/full-lawyer/preflight/history/{audit_id}/export?format=pdf",
        headers={"X-Demo-User": "demo-user"},
    )
    assert history_export.status_code == 200
    assert history_export.headers.get("content-type") == "application/pdf"
    assert history_export.headers.get("content-disposition", "").startswith("attachment;")
    assert len(history_export.content) > 100


def test_full_lawyer_blocks_appeal_submission_when_decision_date_missing(client: TestClient) -> None:
    file_content = (
        "Plaintiff: Ivan Ivanov\n"
        "Defendant: Petro Petrov\n"
        "Need to prepare appeal complaint against first instance decision.\n"
        "Debt under loan agreement is 91000 UAH.\n"
    )
    first = _post_full_lawyer(client, content=file_content, max_documents=3)
    assert first.status_code == 200
    first_payload = first.json()
    answers = {question: "Confirmed." for question in first_payload["unresolved_questions"]}
    review_map = {item["code"]: True for item in first_payload["review_checklist"]}

    second = _post_full_lawyer(
        client,
        content=file_content,
        max_documents=3,
        clarifications=answers,
        review_confirmations=review_map,
        generate_package=True,
    )
    assert second.status_code == 200
    payload = second.json()
    assert "appeal_complaint" in payload["recommended_doc_types"]
    assert payload["final_submission_gate"]["status"] == "blocked"
    assert payload["filing_package"]["generated"] is False
    assert payload["filing_package"]["status"] == "blocked_final_gate"
    assert any("Missing decision/service date" in item for item in payload["final_submission_gate"]["blockers"])
    assert any(
        ("hard-stop" in item.lower()) and ("gate" in item.lower() or "гейт" in item.lower())
        for item in payload["warnings"]
    )
    assert "appellate_decision_date_missing" in payload["final_submission_gate"]["critical_deadlines"]
    assert any(item["code"] == "appellate_decision_date_missing" for item in payload["deadline_control"])


def test_full_lawyer_blocks_cassation_submission_when_decision_date_missing(client: TestClient) -> None:
    file_content = (
        "Plaintiff: Ivan Ivanov\n"
        "Defendant: Petro Petrov\n"
        "Need to prepare cassation complaint to Supreme Court.\n"
        "Cassation complaint concerns appellate act and cassation grounds.\n"
        "No reliable decision date is provided in this text.\n"
    )
    first = _post_full_lawyer(client, content=file_content, max_documents=5)
    assert first.status_code == 200
    first_payload = first.json()
    answers = {question: "Confirmed." for question in first_payload["unresolved_questions"]}
    review_map = {item["code"]: True for item in first_payload["review_checklist"]}

    second = _post_full_lawyer(
        client,
        content=file_content,
        max_documents=5,
        clarifications=answers,
        review_confirmations=review_map,
        generate_package=True,
    )
    assert second.status_code == 200
    payload = second.json()
    assert "cassation_complaint" in payload["recommended_doc_types"]
    assert payload["final_submission_gate"]["status"] == "blocked"
    assert payload["final_submission_gate"]["hard_stop"] is True
    assert payload["filing_package"]["generated"] is False
    assert payload["filing_package"]["status"] == "blocked_final_gate"
    assert any("Missing decision/service date" in item for item in payload["final_submission_gate"]["blockers"])
    assert any(
        ("hard-stop" in item.lower()) and ("gate" in item.lower() or "гейт" in item.lower())
        for item in payload["warnings"]
    )
    assert "appellate_decision_date_missing" in payload["final_submission_gate"]["critical_deadlines"]
    assert any(item["code"] == "appellate_decision_date_missing" for item in payload["deadline_control"])


def test_full_lawyer_generates_draft_package_when_hard_stop_and_draft_enabled(client: TestClient) -> None:
    file_content = (
        "Plaintiff: Ivan Ivanov\n"
        "Defendant: Petro Petrov\n"
        "Need to prepare appeal complaint against first instance decision.\n"
        "Debt under loan agreement is 91000 UAH.\n"
    )
    first = _post_full_lawyer(client, content=file_content, max_documents=3)
    assert first.status_code == 200
    first_payload = first.json()
    answers = {question: "Confirmed." for question in first_payload["unresolved_questions"]}
    review_map = {item["code"]: True for item in first_payload["review_checklist"]}

    second = _post_full_lawyer(
        client,
        content=file_content,
        max_documents=3,
        clarifications=answers,
        review_confirmations=review_map,
        generate_package=True,
        generate_package_draft_on_hard_stop=True,
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["final_submission_gate"]["hard_stop"] is True
    assert payload["filing_package"]["generated"] is True
    assert payload["filing_package"]["is_draft"] is True
    assert payload["filing_package"]["status"] == "draft_generated"
    assert any(
        ("draft" in item.lower() or "чернетк" in item.lower())
        and ("package" in item.lower() or "пакет" in item.lower())
        for item in payload["warnings"]
    )


def test_full_lawyer_respects_doc_quota(client: TestClient, test_session_factory) -> None:
    with test_session_factory() as db:
        subscription = db.execute(select(Subscription).where(Subscription.user_id == "demo-user")).scalar_one()
        subscription.plan = "FREE"
        subscription.docs_limit = 1
        subscription.analyses_limit = 3
        subscription.docs_used = 0
        subscription.analyses_used = 0
        db.commit()

    file_content = "Plaintiff: A\nDefendant: B\nDebt 10000 UAH under loan agreement."
    first = _post_full_lawyer(client, content=file_content, max_documents=5)
    assert first.status_code == 200
    first_payload = first.json()
    answers = {question: "Confirmed." for question in first_payload["unresolved_questions"]}
    review_map = {item["code"]: True for item in first_payload["review_checklist"]}

    second = _post_full_lawyer(
        client,
        content=file_content,
        max_documents=5,
        clarifications=answers,
        review_confirmations=review_map,
    )
    assert second.status_code == 200
    payload = second.json()
    assert payload["status"] == "ok"
    assert len(payload["generated_documents"]) == 1
    assert len(payload["warnings"]) >= 1
    assert len(payload["workflow_stages"]) == 4
