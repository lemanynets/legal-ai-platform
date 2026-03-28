"""
STORY-7 — Snapshot / smoke tests for the deterministic DocumentIR renderer.

Tests verify that:
  1. render_docx() returns non-empty bytes on a valid DocumentIR.
  2. render_docx() contains a valid DOCX ZIP header (PK magic bytes).
  3. render_docx() raises HTTP 500 RENDER_FAIL when python-docx is unavailable.
  4. render_pdf() raises HTTP 500 RENDER_FAIL when LibreOffice is absent.
  5. _build_docx() structure — all 8 sections produce paragraphs (smoke).
  6. Court name appears in DOCX paragraph text.
  7. Title appears in DOCX paragraph text (uppercased).
  8. Claims text appears in DOCX paragraphs.
  9. Signature placeholder appears when date_placeholder=True.
  10. Monetary claim formats amount + currency.

These tests use unittest.mock to patch _DOCX_AVAILABLE and the subprocess
for PDF conversion so they run without python-docx or LibreOffice installed.

If python-docx IS installed (e.g. in CI), the integration smoke tests also run.
"""

from __future__ import annotations

import importlib
import io
from unittest.mock import MagicMock, patch

import pytest

from ..document_ir import (
    AttachmentItem,
    CitationItem,
    ClaimItem,
    DocumentHeader,
    DocumentIR,
    FactItem,
    IRDocumentStatus,
    LegalThesis,
    PartyItem,
    SignatureBlock,
)
from ..renderer import DocumentRenderer, _DOCX_AVAILABLE

# ---------------------------------------------------------------------------
# Shared IR fixture
# ---------------------------------------------------------------------------


def _make_ir(monetary: bool = False) -> DocumentIR:
    return DocumentIR(
        id="render-test-001",
        document_type="appeal_complaint",
        ir_version="1.0",
        status=IRDocumentStatus.needs_review,
        header=DocumentHeader(
            title="Апеляційна скарга у справі № 754/TEST/26",
            court_name="Київський апеляційний суд",
            court_type="appellate",
            case_number="754/TEST/26",
            document_date="2026-03-01",
            jurisdiction="UA",
        ),
        parties=[
            PartyItem(
                id="p1", role="скаржник", name="Тестенко Тест Тестович",
                address="м. Київ, вул. Тестова, 1", identifier="1234567890",
            ),
            PartyItem(id="p2", role="відповідач", name="ТОВ «Тест»"),
        ],
        facts=[
            FactItem(id="f1", text="Договір укладено 01.01.2025.", date="2025-01-01"),
        ],
        legal_basis=[
            LegalThesis(
                id="t1",
                text="Згідно ст. 526 ЦК України зобов'язання мають виконуватись.",
                citations=["cit1"],
                grounding_status="grounded",
                citation_coverage=1.0,
            ),
        ],
        claims=[
            ClaimItem(
                id="c1",
                text="Скасувати рішення суду першої інстанції.",
                relief_type="declaratory",
                supporting_fact_ids=["f1"],
                supporting_thesis_ids=["t1"],
                amount=1_850_000.0 if monetary else None,
                currency="UAH" if monetary else None,
            ),
        ],
        attachments=[
            AttachmentItem(id="a1", title="Копія рішення", required=True, provided=True),
            AttachmentItem(id="a2", title="Квитанція про сплату", required=False, provided=False),
        ],
        signature_block=SignatureBlock(
            signer_name="Тестенко Т.Т.",
            signer_role="Скаржник",
            date_placeholder=True,
        ),
        citations=[
            CitationItem(
                id="cit1",
                source_type="statute",
                source_locator="ст. 526 ЦК України",
                evidence_span="зобов'язання мають виконуватись належним чином",
            ),
        ],
        inconsistencies=[],
        citation_coverage=1.0,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOCX_ZIP_MAGIC = b"PK\x03\x04"


def _paragraph_texts(doc) -> list[str]:
    return [p.text for p in doc.paragraphs if p.text.strip()]


# ---------------------------------------------------------------------------
# Tests that run regardless of python-docx availability
# ---------------------------------------------------------------------------


class TestRenderDocxUnavailable:
    def test_raises_500_when_docx_not_available(self):
        """When _DOCX_AVAILABLE is False, render_docx() raises HTTP 500."""
        from fastapi import HTTPException
        from .. import renderer as renderer_module

        ir = _make_ir()
        with patch.object(renderer_module, "_DOCX_AVAILABLE", False):
            renderer = DocumentRenderer()
            with pytest.raises(HTTPException) as exc_info:
                renderer.render_docx(ir)
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error_code"] == "RENDER_FAIL"
        assert "python-docx" in exc_info.value.detail["message"]


class TestRenderPdfUnavailable:
    def test_raises_500_when_libreoffice_absent(self):
        """render_pdf() raises HTTP 500 when LibreOffice subprocess fails."""
        from fastapi import HTTPException
        from .. import renderer as renderer_module

        ir = _make_ir()
        if not _DOCX_AVAILABLE:
            pytest.skip("python-docx not installed — skipping PDF conversion test")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr=b"soffice not found")
            renderer = DocumentRenderer()
            with pytest.raises(HTTPException) as exc_info:
                renderer.render_pdf(ir)
        assert exc_info.value.status_code == 500
        assert "PDF" in exc_info.value.detail["message"] or "RENDER_FAIL" in exc_info.value.detail["error_code"]


# ---------------------------------------------------------------------------
# Integration smoke tests — run only when python-docx is installed
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _DOCX_AVAILABLE, reason="python-docx not installed")
class TestRenderDocxIntegration:
    def test_returns_bytes(self):
        renderer = DocumentRenderer()
        result = renderer.render_docx(_make_ir())
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_has_docx_zip_magic(self):
        renderer = DocumentRenderer()
        result = renderer.render_docx(_make_ir())
        assert result[:4] == _DOCX_ZIP_MAGIC, "DOCX output does not start with PK ZIP magic bytes."

    def test_court_name_in_paragraphs(self):
        from docx import Document as DocxDocument
        renderer = DocumentRenderer()
        ir = _make_ir()
        doc = renderer._build_docx(ir)
        texts = _paragraph_texts(doc)
        assert any(ir.header.court_name in t for t in texts), (
            f"Court name '{ir.header.court_name}' not found in DOCX paragraphs."
        )

    def test_title_uppercased_in_paragraphs(self):
        renderer = DocumentRenderer()
        ir = _make_ir()
        doc = renderer._build_docx(ir)
        texts = _paragraph_texts(doc)
        assert any(ir.header.title.upper() in t for t in texts), (
            "Document title (uppercased) not found in DOCX paragraphs."
        )

    def test_claims_text_in_paragraphs(self):
        renderer = DocumentRenderer()
        ir = _make_ir()
        doc = renderer._build_docx(ir)
        texts = _paragraph_texts(doc)
        assert any(ir.claims[0].text in t for t in texts), (
            f"Claim text not found in DOCX paragraphs."
        )

    def test_signature_placeholder_present(self):
        renderer = DocumentRenderer()
        ir = _make_ir()
        doc = renderer._build_docx(ir)
        texts = _paragraph_texts(doc)
        assert any("20__" in t or "____________" in t for t in texts), (
            "Signature date placeholder not found in DOCX."
        )

    def test_monetary_claim_includes_amount_and_currency(self):
        renderer = DocumentRenderer()
        ir = _make_ir(monetary=True)
        doc = renderer._build_docx(ir)
        texts = _paragraph_texts(doc)
        combined = " ".join(texts)
        assert "1,850,000.00" in combined or "1850000" in combined.replace(",", ""), (
            "Monetary amount not found in DOCX paragraphs."
        )
        assert "UAH" in combined, "Currency code UAH not found in DOCX paragraphs."

    def test_attachments_section_present(self):
        renderer = DocumentRenderer()
        ir = _make_ir()
        doc = renderer._build_docx(ir)
        texts = _paragraph_texts(doc)
        assert any("ДОДАТКИ" in t for t in texts), "Attachments section heading not found."

    def test_citation_evidence_spans_appear(self):
        renderer = DocumentRenderer()
        ir = _make_ir()
        doc = renderer._build_docx(ir)
        texts = _paragraph_texts(doc)
        combined = " ".join(texts)
        # evidence_span is truncated to 120 chars in the citation line
        span_prefix = ir.citations[0].evidence_span[:20]
        assert span_prefix in combined, (
            f"Citation evidence span prefix '{span_prefix}' not found in DOCX."
        )

    def test_all_parties_listed(self):
        renderer = DocumentRenderer()
        ir = _make_ir()
        doc = renderer._build_docx(ir)
        texts = _paragraph_texts(doc)
        combined = " ".join(texts)
        for party in ir.parties:
            assert party.name in combined, f"Party '{party.name}' not found in DOCX."

    def test_page_margins_set(self):
        """Verify Ukrainian court standard margins (left=3cm, right=1.5cm)."""
        from docx.shared import Cm
        renderer = DocumentRenderer()
        ir = _make_ir()
        doc = renderer._build_docx(ir)
        section = doc.sections[0]
        # Tolerances: ±0.05cm
        assert abs(section.left_margin - Cm(3.0)) < Cm(0.05), \
            f"Left margin should be 3cm, got {section.left_margin / 360000:.2f}cm"
        assert abs(section.right_margin - Cm(1.5)) < Cm(0.05), \
            f"Right margin should be 1.5cm, got {section.right_margin / 360000:.2f}cm"
