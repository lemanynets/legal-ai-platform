from backend.main import _build_intake_structured_json, _extract_contract_pain_points


def test_build_intake_structured_json_has_expected_blocks() -> None:
    ai_result = {
        "classified_type": "appeal_complaint",
        "document_language": "uk",
        "identified_parties": [{"role": "plaintiff", "name": "Іван"}],
        "document_date": "2026-04-04",
        "deadline_from_document": "2026-04-10",
        "urgency_level": "high",
        "risk_level_legal": "high",
        "risk_level_procedural": "medium",
        "risk_level_financial": "low",
        "detected_issues": [{"issue_type": "missing_fact"}],
        "subject_matter": "Оскарження рішення",
        "tags": ["appeal"],
    }
    out = _build_intake_structured_json(ai_result, "doc.pdf", "UA")
    assert out["meta"]["file_name"] == "doc.pdf"
    assert out["meta"]["classified_type"] == "appeal_complaint"
    assert out["risk_profile"]["issues_count"] == 1
    assert out["timeline"]["urgency_level"] == "high"


def test_extract_contract_pain_points_detects_flags() -> None:
    text = "Договір передбачає штраф і пеня, одностороннє розірвання та автоматичну пролонгацію."
    out = _extract_contract_pain_points(text)
    assert out["total_flags"] >= 3
    assert out["risk_score"] > 0
