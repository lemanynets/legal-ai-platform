from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.contract_analyses import _normalize_analysis_payload, _parse_json_object  # noqa: E402


def test_parse_json_object_from_markdown_fence():
    raw = """```json
    {"contract_type":"Loan","overall_risk":"high","critical_risks":["r1"],"medium_risks":[],"ok_points":[],"recommendations":[]}
    ```"""
    parsed = _parse_json_object(raw)
    assert isinstance(parsed, dict)
    assert parsed.get("contract_type") == "Loan"
    assert parsed.get("overall_risk") == "high"


def test_normalize_analysis_payload_clamps_invalid_risk_but_keeps_content():
    payload = {
        "contract_type": "Supply",
        "overall_risk": "super_high",
        "critical_risks": ["r1"],
        "medium_risks": ["r2"],
        "ok_points": ["r3"],
        "recommendations": ["r4"],
    }
    normalized = _normalize_analysis_payload(payload)
    assert normalized["contract_type"] == "Supply"
    assert normalized["risk_level"] == "medium"
    assert normalized["critical_risks"] == ["r1"]


def test_normalize_analysis_payload_falls_back_on_invalid_shape():
    normalized = _normalize_analysis_payload(
        {"contract_type": "Loan", "overall_risk": "low", "critical_risks": "not_a_list"}
    )
    assert normalized["contract_type"] == "Невизначений тип"
    assert normalized["risk_level"] == "medium"
    assert len(normalized["recommendations"]) > 0
