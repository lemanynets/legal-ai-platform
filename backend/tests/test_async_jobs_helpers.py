from app.tasks.ai_jobs import _run_intake_analysis, _template_document


def test_template_document_contains_label() -> None:
    text = _template_document("appeal_complaint", {"court": "Київський апеляційний"})
    assert "АПЕЛЯЦІЙНА СКАРГА" in text
    assert "court: Київський апеляційний" in text


def test_run_intake_analysis_returns_shape() -> None:
    result = _run_intake_analysis("dGVzdA==", "test.txt", "UA", "standard")
    assert result["source_file_name"] == "test.txt"
    assert result["jurisdiction"] == "UA"
    assert isinstance(result["tags"], list)
