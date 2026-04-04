from __future__ import annotations

from pathlib import Path
import sys

from fastapi import HTTPException
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routers.auto_process import _extract_source_text
from app.services import file_text_extractor


def test_extract_pdf_text_falls_back_to_pdfminer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(file_text_extractor, "_extract_pdf_text_pypdf", lambda _: "")
    monkeypatch.setattr(file_text_extractor, "_extract_pdf_text_pdfminer", lambda _: "A" * 120)
    monkeypatch.setattr(file_text_extractor, "_extract_pdf_text_ocr", lambda _: "")

    result = file_text_extractor._extract_pdf_text(b"%PDF-fake%")
    assert len(result) == 120


def test_extract_pdf_text_uses_ocr_when_other_extractors_are_short(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(file_text_extractor, "_extract_pdf_text_pypdf", lambda _: "short")
    monkeypatch.setattr(file_text_extractor, "_extract_pdf_text_pdfminer", lambda _: "tiny")
    monkeypatch.setattr(file_text_extractor, "_extract_pdf_text_pdftotext", lambda _: "")
    monkeypatch.setattr(file_text_extractor, "_extract_pdf_text_ocr", lambda _: "B" * 90)

    result = file_text_extractor._extract_pdf_text(b"%PDF-fake%")
    assert len(result) == 90


def test_extract_pdf_text_uses_pdftotext_when_python_extractors_are_short(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(file_text_extractor, "_extract_pdf_text_pypdf", lambda _: "short")
    monkeypatch.setattr(file_text_extractor, "_extract_pdf_text_pdfminer", lambda _: "tiny")
    monkeypatch.setattr(file_text_extractor, "_extract_pdf_text_pdftotext", lambda _: "C" * 80)
    monkeypatch.setattr(file_text_extractor, "_extract_pdf_text_ocr", lambda _: "")

    result = file_text_extractor._extract_pdf_text(b"%PDF-fake%")
    assert len(result) == 80


def test_extract_pdf_text_prefers_higher_quality_english_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        file_text_extractor,
        "_extract_pdf_text_pypdf",
        lambda _: "IN THE HIGH COURT OF JUSTICE Claimant ACME Ltd Defendant John Doe Judgment entered for damages.",
    )
    monkeypatch.setattr(
        file_text_extractor,
        "_extract_pdf_text_pdfminer",
        lambda _: "ÄÄÄ ÄÄÄ ÄÄÄ ÄÄÄ ÄÄÄ ÄÄÄ ÄÄÄ",
    )
    monkeypatch.setattr(file_text_extractor, "_extract_pdf_text_pdftotext", lambda _: "")
    monkeypatch.setattr(file_text_extractor, "_extract_pdf_text_ocr", lambda _: "")

    result = file_text_extractor._extract_pdf_text(b"%PDF-fake%")
    assert "HIGH COURT OF JUSTICE" in result


def test_extract_source_text_pdf_error_message_for_scanned_files(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.routers.auto_process.extract_text_from_file",
        lambda **_: "",
    )

    with pytest.raises(HTTPException) as exc_info:
        _extract_source_text("scan.pdf", "application/pdf", b"fake")

    assert exc_info.value.status_code == 422
    assert "PDF" in str(exc_info.value.detail)
    assert "OCR" in str(exc_info.value.detail)


def test_clean_extracted_text_repairs_mojibake_sequences() -> None:
    source = (
        "\u041f\u043e\u0437\u0438\u0432\u0430\u0447: \u0406\u0432\u0430\u043d \u0406\u0432\u0430\u043d\u043e\u0432\n"
        "\u0412\u0456\u0434\u043f\u043e\u0432\u0456\u0434\u0430\u0447: \u041f\u0435\u0442\u0440\u043e \u041f\u0435\u0442\u0440\u043e\u0432\n"
    )
    mojibake = source.encode("utf-8").decode("latin1")
    repaired = file_text_extractor._clean_extracted_text(mojibake)
    assert "\u041f\u043e\u0437\u0438\u0432\u0430\u0447" in repaired
    assert "\u0412\u0456\u0434\u043f\u043e\u0432\u0456\u0434\u0430\u0447" in repaired

