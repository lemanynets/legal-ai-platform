from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.services.auto_processor import (
    auto_repair_form_data_for_generation,
    build_decision_document_preparation,
    build_deadline_alert_board,
    build_deadline_control,
    build_document_fact_pack,
    build_final_submission_gate,
    build_form_data_for_doc_type,
    build_law_context_refs_for_doc_types,
    build_rule_validation_checks,
    extract_parties_and_facts,
    suggest_document_types,
)
from app.services.prompt_builder import build_pre_generation_gate_checks
from app.services.calculators import calculate_deadline


def test_suggest_document_types_detects_motion_claim_security() -> None:
    text = (
        "Позивач просить вжити заходи забезпечення позову, "
        "оскільки є ризик відчуження майна відповідача та невиконання рішення."
    )
    recommended = suggest_document_types(text, max_documents=3, processual_only=True)
    assert "motion_claim_security" in recommended


def test_suggest_document_types_detects_motion_evidence_request() -> None:
    text = (
        "Сторона не може самостійно отримати документи, тому просить суд "
        "витребувати докази у банку."
    )
    recommended = suggest_document_types(text, max_documents=3, processual_only=True)
    assert "motion_evidence_request" in recommended


def test_build_form_data_for_motion_expertise_has_required_keys() -> None:
    text = "Для встановлення обставин спору необхідні спеціальні знання експерта."
    form_data = build_form_data_for_doc_type("motion_expertise", text)
    assert "court_name" in form_data
    assert "expert_questions" in form_data
    assert isinstance(form_data["expert_questions"], list)
    assert "legal_basis" in form_data


def test_build_law_context_refs_for_motion_doc_types() -> None:
    refs = build_law_context_refs_for_doc_types(
        ["motion_claim_security", "motion_court_fee_deferral"]
    )
    assert len(refs) >= 2
    references = [item["reference"] for item in refs]
    assert any("149-151" in ref for ref in references)
    assert any("art. 136" in ref or "Law of Ukraine On Court Fee" in ref for ref in references)


def test_suggest_document_types_detects_cassation_complaint() -> None:
    text = "Потрібно підготувати касаційну скаргу до Верховного Суду."
    recommended = suggest_document_types(text, max_documents=3, processual_only=True)
    assert "cassation_complaint" in recommended


def test_build_form_data_for_lawsuit_alimony_has_party_fields() -> None:
    text = "Мати просить стягнути аліменти на утримання дитини."
    form_data = build_form_data_for_doc_type("lawsuit_alimony", text)
    assert "plaintiff_name" in form_data
    assert "defendant_name" in form_data
    assert "claim_requests" in form_data


def test_suggest_document_types_detects_objection_response() -> None:
    text = "Потрібно підготувати заперечення на відзив у цивільній справі."
    recommended = suggest_document_types(text, max_documents=3, processual_only=True)
    assert "objection_response" in recommended


def test_suggest_document_types_detects_executor_complaint() -> None:
    text = "Потрібна скарга на дії виконавця у виконавчому провадженні."
    recommended = suggest_document_types(text, max_documents=3, processual_only=True)
    assert "complaint_executor_actions" in recommended


def test_build_form_data_for_statement_enforcement_opening_has_core_fields() -> None:
    text = "Стягувач подає заяву про відкриття виконавчого провадження."
    form_data = build_form_data_for_doc_type("statement_enforcement_opening", text)
    assert "court_name" in form_data
    assert "request_summary" in form_data
    assert "attachments" in form_data


def test_extract_parties_and_facts_builds_non_empty_fact_and_request_summary() -> None:
    text = (
        "Справа №307/1542/25. Закарпатський апеляційний суд розглянув апеляційну скаргу. "
        "За позовом АТ Укрсиббанк до ОСОБА_1 про стягнення заборгованості за кредитним договором. "
        "Суд встановив прострочення виконання грошового зобов'язання. "
        "Позивач просить стягнути 3% річних та інфляційні втрати."
    )
    extracted = extract_parties_and_facts(text)
    assert extracted.get("plaintiff_name")
    assert extracted.get("defendant_name")
    assert extracted.get("case_number")
    assert len(str(extracted.get("fact_summary") or "")) > 80
    assert any(
        marker in str(extracted.get("request_summary") or "").lower()
        for marker in ("прос", "вимаг", "стяг")
    )


def test_build_form_data_for_appeal_uses_extracted_case_number_and_court() -> None:
    text = (
        "Справа №307/1542/25. Закарпатський апеляційний суд. "
        "За позовом АТ Укрсиббанк до ОСОБА_1 про стягнення боргу. "
        "Скаржник просить скасувати рішення суду першої інстанції."
    )
    form_data = build_form_data_for_doc_type("appeal_complaint", text)
    assert "307/1542/25" in str(form_data.get("case_number") or "")
    assert "суд" in str(form_data.get("court_name") or "").lower()
    assert len(str(form_data.get("fact_summary") or "")) > 40


def test_extract_parties_and_facts_repairs_mojibake_input() -> None:
    original = (
        "Позивач: АТ Укрсиббанк\n"
        "Відповідач: ОСОБА_1\n"
        "За позовом про стягнення заборгованості за кредитним договором.\n"
        "Позивач просить стягнути 3% річних та інфляційні втрати."
    )
    mojibake = original.encode("utf-8").decode("latin1")
    extracted = extract_parties_and_facts(mojibake)
    assert "Укрсиббанк" in str(extracted.get("plaintiff_name") or "")
    assert "ОСОБА_1" in str(extracted.get("defendant_name") or "")
    assert "стяг" in str(extracted.get("request_summary") or "").lower()


def test_extract_parties_and_facts_filters_non_court_question_lines() -> None:
    text = (
        "Ключові юридичні питання: Чи правильно суд застосував ст. 625 ЦК України?\n"
        "Тячівський районний суд Закарпатської області розглянув справу №307/1542/25.\n"
        "За позовом АТ Укрсиббанк до ОСОБА_1 про стягнення заборгованості."
    )
    extracted = extract_parties_and_facts(text)
    court_name = str(extracted.get("court_name") or "")
    assert court_name
    assert "ключові юридичні питання" not in court_name.lower()
    assert court_name.lower().startswith("тячівський районний суд")


def test_build_decision_document_preparation_first_instance_keeps_appeal_focus() -> None:
    recent_decision_date = (date.today() - timedelta(days=3)).strftime("%d.%m.%Y")
    text = (
        f"Тячівський районний суд Закарпатської області, рішення від {recent_decision_date}. "
        "Апеляційна скарга може бути подана протягом тридцяти днів."
    )
    items = build_decision_document_preparation(
        source_text=text,
        side_assessment={"side": "defendant"},
        evidence_gaps=[],
    )
    doc_types = [str(item.get("doc_type") or "") for item in items]
    assert doc_types == ["appeal_complaint"]


def test_build_decision_document_preparation_adds_renewal_when_appeal_deadline_missed() -> None:
    text = (
        "Тячівський районний суд Закарпатської області, рішення від 01.01.2020. "
        "Апеляційна скарга може бути подана протягом тридцяти днів."
    )
    items = build_decision_document_preparation(
        source_text=text,
        side_assessment={"side": "defendant"},
        evidence_gaps=[],
    )
    doc_types = [str(item.get("doc_type") or "") for item in items]
    assert "appeal_complaint" in doc_types
    assert "motion_appeal_deadline_renewal" in doc_types


def test_build_form_data_for_motion_evidence_request_fills_contextual_fields() -> None:
    text = (
        "За позовом ТОВ Альфа до ТОВ Бета про стягнення заборгованості. "
        "Для підтвердження розміру боргу необхідно витребувати у АТ Укрсиббанк банківські виписки. "
        "Позивач не може самостійно отримати ці документи, оскільки вони перебувають у володінні третьої особи."
    )
    form_data = build_form_data_for_doc_type("motion_evidence_request", text)
    assert "витреб" in str(form_data.get("request_summary") or "").lower()
    assert "виписк" in str(form_data.get("evidence_description") or "").lower()
    assert "укрсиббанк" in str(form_data.get("holder_of_evidence") or "").lower()
    assert "не може" in str(form_data.get("inability_reason") or "").lower()


def test_build_document_fact_pack_extracts_structured_points() -> None:
    text = (
        "Справа №307/1542/25. 15.01.2025 між сторонами укладено кредитний договір. "
        "Позивач передав 120000 грн, що підтверджується банківською випискою. "
        "Відповідач не повернув кошти у строк до 15.03.2025. "
        "Позивач просить стягнути основний борг, 3% річних та судові витрати."
    )
    pack = build_document_fact_pack(text, max_items=6)
    assert pack["factual_points"]
    assert pack["chronology_points"]
    assert pack["request_points"]
    all_points = [*pack["factual_points"], *pack["evidence_points"], *pack["chronology_points"]]
    assert any("120000" in item for item in all_points)


def test_build_form_data_for_lawsuit_contains_factual_pack_fields() -> None:
    text = (
        "За позовом АТ Укрсиббанк до ОСОБА_1 про стягнення заборгованості. "
        "01.02.2025 укладено договір позики, 10.02.2025 передано 90000 грн. "
        "До 10.05.2025 борг не повернуто. Позивач просить стягнути борг і судові витрати."
    )
    form_data = build_form_data_for_doc_type("lawsuit_debt_loan", text)
    assert isinstance(form_data.get("factual_points"), list)
    assert len(form_data.get("factual_points") or []) >= 1
    assert isinstance(form_data.get("chronology_points"), list)
    assert len(form_data.get("chronology_points") or []) >= 1
    assert str(form_data.get("facts_context_digest") or "").strip()
    claim_requests = form_data.get("claim_requests") or []
    assert isinstance(claim_requests, list)
    assert len(claim_requests) >= 1


def test_auto_repair_form_data_reduces_pre_generation_failures_for_lawsuit() -> None:
    source_text = (
        "За позовом АТ Укрсиббанк до ОСОБА_1 про стягнення заборгованості. "
        "01.02.2025 передано 120000 грн за договором позики. "
        "До 15.03.2025 кошти не повернуто. Позивач просить стягнути борг та судові витрати."
    )
    broken_form_data = {
        "plaintiff_name": "",
        "defendant_name": "",
        "debt_start_date": "",
        "principal_debt_uah": 0,
        "fact_summary": "",
        "request_summary": "",
        "claim_requests": [],
    }
    before = build_pre_generation_gate_checks("lawsuit_debt_loan", broken_form_data)
    repaired, notes = auto_repair_form_data_for_generation("lawsuit_debt_loan", source_text, broken_form_data)
    after = build_pre_generation_gate_checks("lawsuit_debt_loan", repaired)

    before_fail = sum(1 for item in before if item["status"] == "fail")
    after_fail = sum(1 for item in after if item["status"] == "fail")
    assert after_fail < before_fail
    assert float(repaired.get("principal_debt_uah") or 0) > 0
    assert str(repaired.get("debt_start_date") or "").strip()
    assert notes


def test_build_deadline_control_adds_appeal_and_cassation_deadlines() -> None:
    deadlines = build_deadline_control(
        source_text="Decision date 2026-01-10. Need both appeal and cassation checks.",
        recommended_doc_types=["appeal_complaint", "cassation_complaint"],
        unresolved_questions=[],
        unresolved_review_items=[],
    )
    codes = {item["code"] for item in deadlines}
    assert "appeal_deadline" in codes
    assert "cassation_deadline" in codes


def test_build_deadline_control_respects_configured_appeal_days() -> None:
    original_days = settings.appeal_deadline_days
    try:
        object.__setattr__(settings, "appeal_deadline_days", 45)
        deadlines = build_deadline_control(
            source_text="Decision date 2026-01-10. Appeal is planned.",
            recommended_doc_types=["appeal_complaint"],
            unresolved_questions=[],
            unresolved_review_items=[],
        )
        appeal_item = next(item for item in deadlines if item["code"] == "appeal_deadline")
        expected_due_date = calculate_deadline(date.fromisoformat("2026-01-10"), 45).isoformat()
        assert appeal_item["due_date"] == expected_due_date
    finally:
        object.__setattr__(settings, "appeal_deadline_days", original_days)


def test_build_deadline_control_marks_missing_appellate_date_as_urgent() -> None:
    deadlines = build_deadline_control(
        source_text="Need to prepare appellate filing package quickly.",
        recommended_doc_types=["appeal_complaint"],
        unresolved_questions=[],
        unresolved_review_items=[],
    )
    missing_item = next(item for item in deadlines if item["code"] == "appellate_decision_date_missing")
    assert missing_item["status"] == "urgent"
    assert missing_item["due_date"] is None


def test_build_rule_validation_checks_warns_when_cassation_dates_missing() -> None:
    checks = build_rule_validation_checks(
        "Need cassation complaint to Supreme Court. Please prepare quickly.",
        {"dispute_type": "Cassation challenge", "procedure": "civil"},
    )
    cassation_check = next(item for item in checks if item["code"] == "cassation_deadline_precheck")
    assert cassation_check["status"] == "warn"
    message = cassation_check["message"].lower()
    assert ("no reliable" in message) or ("надійних дат" in message)


def test_deadline_alert_board_marks_missing_critical_deadline_as_critical() -> None:
    board = build_deadline_alert_board(
        deadline_control=[
            {
                "code": "appeal_deadline",
                "title": "Appeal filing window checkpoint",
                "due_date": None,
                "status": "urgent",
                "basis": "Procedural appeal timeline control",
                "note": "Missing date",
            }
        ]
    )
    assert board[0]["level"] == "critical"


def test_final_submission_gate_blocks_on_urgent_appeal_deadline() -> None:
    gate = build_final_submission_gate(
        filing_decision_card={"decision": "go"},
        e_court_packet_readiness={"status": "ready"},
        digital_signature_readiness={"status": "ready"},
        procedural_consistency_scorecard={"score": 90},
        deadline_control=[
            {
                "code": "appeal_deadline",
                "title": "Appeal filing window checkpoint",
                "due_date": "2026-03-05",
                "status": "urgent",
                "basis": "Procedural appeal timeline control",
                "note": "Short window",
            }
        ],
        recommended_doc_types=["appeal_complaint"],
    )
    assert gate["status"] == "blocked"
    assert gate["hard_stop"] is True
    assert any("appeal_deadline" in blocker for blocker in gate["blockers"])
    assert "appeal_deadline:urgent:2026-03-05" in gate["critical_deadlines"]


def test_final_submission_gate_in_strict_mode_blocks_conditional_pass() -> None:
    gate = build_final_submission_gate(
        filing_decision_card={"decision": "conditional_go"},
        e_court_packet_readiness={"status": "ready"},
        digital_signature_readiness={"status": "ready"},
        procedural_consistency_scorecard={"score": 92},
        deadline_control=[],
        recommended_doc_types=[],
    )
    assert gate["status"] == "blocked"
    assert gate["hard_stop"] is True
    assert any("Strict filing mode requires PASS status" in blocker for blocker in gate["blockers"])


def test_final_submission_gate_marks_missing_required_deadline_as_critical() -> None:
    gate = build_final_submission_gate(
        filing_decision_card={"decision": "go"},
        e_court_packet_readiness={"status": "ready"},
        digital_signature_readiness={"status": "ready"},
        procedural_consistency_scorecard={"score": 90},
        deadline_control=[],
        recommended_doc_types=["cassation_complaint"],
    )
    assert gate["status"] == "blocked"
    assert "cassation_deadline:missing" in gate["critical_deadlines"]



