"""
STORY-8 — Unit tests for the unified layout/compliance render gate.

Each test verifies that a single failing gate produces the correct
failed_gates entry AND that all other gates remain independent.

Tests:
  - All gates pass → report.passed is True, failed_gates is empty
  - Gate 1 (IR_VALID) fails when ir has structural violations
  - Gate 2 (NO_PROC_BLOCKERS) fails when ir.inconsistencies contain a critical code
  - Gate 3 (CONSISTENCY_GREEN) fails when check_all() returns inconsistencies
  - Gate 4 (CITATIONS_COVERED) fails when a thesis is ungrounded (ir_pipeline=on)
  - Gate 4 is skipped (passes) when ir_pipeline != on
  - Gate 5 (LAYOUT_FIELDS) fails when generated_text is missing court name
  - Multiple gates fail simultaneously — failed_gates contains all failing codes
  - validate_final_render_gate() raises HTTP 422 on failure
  - validate_final_render_gate() raises nothing on success
"""

from __future__ import annotations

import copy
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from ..document_ir import (
    AttachmentItem,
    CitationItem,
    ClaimItem,
    DocumentHeader,
    DocumentIR,
    FactItem,
    Inconsistency,
    IRDocumentStatus,
    LegalThesis,
    PartyItem,
    SignatureBlock,
)
from ..final_render_gate import (
    GATE_CITATIONS,
    GATE_CONSISTENCY,
    GATE_IR_VALID,
    GATE_LAYOUT,
    GATE_NO_PROC_BLOCKERS,
    evaluate_render_gate,
    validate_final_render_gate,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_valid_ir(**overrides) -> DocumentIR:
    """Return a minimal but structurally valid appeal_complaint IR."""
    base = DocumentIR(
        id="test-001",
        document_type="appeal_complaint",
        ir_version="1.0",
        status=IRDocumentStatus.needs_review,
        header=DocumentHeader(
            title="Апеляційна скарга",
            court_name="Київський апеляційний суд",
            court_type="appellate",
            case_number="754/0001/26",
            document_date="2026-03-01",
            jurisdiction="UA",
        ),
        parties=[
            PartyItem(id="p1", role="скаржник", name="Тест Тест Тестович"),
            PartyItem(id="p2", role="відповідач", name="ТОВ «Тест»"),
        ],
        facts=[
            FactItem(id="f1", text="Договір укладено 01.01.2025.", date="2025-01-01"),
        ],
        legal_basis=[
            LegalThesis(
                id="t1",
                text="Відповідно до ст. 526 ЦК України.",
                citations=["cit1"],
                grounding_status="grounded",
                citation_coverage=1.0,
            ),
        ],
        claims=[
            ClaimItem(
                id="c1",
                text="Скасувати рішення суду.",
                relief_type="declaratory",
                supporting_fact_ids=["f1"],
                supporting_thesis_ids=["t1"],
            ),
        ],
        attachments=[
            AttachmentItem(id="a1", title="Копія рішення", required=True, provided=True),
        ],
        signature_block=SignatureBlock(
            signer_name="Тестович Т.Т.",
            signer_role="Скаржник",
            date_placeholder=True,
        ),
        citations=[
            CitationItem(
                id="cit1",
                source_type="statute",
                source_locator="ст. 526 ЦК України",
                evidence_span="зобов'язання мають виконуватись",
            ),
        ],
        inconsistencies=[],
        citation_coverage=1.0,
    )
    for k, v in overrides.items():
        object.__setattr__(base, k, v)
    return base


def _valid_generated_text(ir: DocumentIR) -> str:
    """Minimal text that satisfies layout checks for appeal_complaint."""
    return (
        f"{ir.header.court_name}\n"
        f"скаржник: {ir.parties[0].name}\n"
        f"{ir.header.title}\n"
        "Скасувати рішення суду.\n"
        "_________________________\n"
    )


# ---------------------------------------------------------------------------
# Gate 1 — IR_VALID
# ---------------------------------------------------------------------------

class TestGate1IRValid:
    def test_passes_on_valid_ir(self):
        ir = _make_valid_ir()
        report = evaluate_render_gate(ir, generated_text=_valid_generated_text(ir))
        assert GATE_IR_VALID not in report.failed_gates

    def test_fails_when_ir_has_no_parties(self):
        ir = _make_valid_ir(parties=[])
        report = evaluate_render_gate(ir, generated_text=_valid_generated_text(ir))
        assert GATE_IR_VALID in report.failed_gates

    def test_fails_when_ir_has_no_claims(self):
        ir = _make_valid_ir(claims=[])
        report = evaluate_render_gate(ir, generated_text=_valid_generated_text(ir))
        assert GATE_IR_VALID in report.failed_gates


# ---------------------------------------------------------------------------
# Gate 2 — NO_PROC_BLOCKERS
# ---------------------------------------------------------------------------

class TestGate2NoProcBlockers:
    def test_passes_when_no_inconsistencies(self):
        ir = _make_valid_ir(inconsistencies=[])
        report = evaluate_render_gate(ir, generated_text=_valid_generated_text(ir))
        assert GATE_NO_PROC_BLOCKERS not in report.failed_gates

    def test_fails_when_critical_inconsistency_present(self):
        # JURISDICTION_MISMATCH is mapped to critical in processual_severity.yaml
        ir = _make_valid_ir(inconsistencies=[
            Inconsistency(
                code="JURISDICTION_MISMATCH",
                description="Jurisdiction mismatch.",
                affected_sections=["header"],
            )
        ])
        report = evaluate_render_gate(ir, generated_text=_valid_generated_text(ir))
        assert GATE_NO_PROC_BLOCKERS in report.failed_gates

    def test_passes_when_only_warning_inconsistency(self):
        # MISSING_FEE_RECEIPT is a warning code — should not block
        ir = _make_valid_ir(inconsistencies=[
            Inconsistency(
                code="MISSING_FEE_RECEIPT",
                description="Court fee receipt not attached.",
                affected_sections=["attachments"],
            )
        ])
        report = evaluate_render_gate(ir, generated_text=_valid_generated_text(ir))
        assert GATE_NO_PROC_BLOCKERS not in report.failed_gates


# ---------------------------------------------------------------------------
# Gate 3 — CONSISTENCY_GREEN
# ---------------------------------------------------------------------------

class TestGate3ConsistencyGreen:
    def test_passes_on_consistent_ir(self):
        ir = _make_valid_ir()
        report = evaluate_render_gate(ir, generated_text=_valid_generated_text(ir))
        assert GATE_CONSISTENCY not in report.failed_gates

    def test_fails_when_claim_references_nonexistent_fact(self):
        """check_claims_reference_facts detects this and check_all returns an inconsistency."""
        ir = _make_valid_ir(claims=[
            ClaimItem(
                id="c1",
                text="Скасувати рішення.",
                relief_type="declaratory",
                supporting_fact_ids=["f999"],  # does not exist
                supporting_thesis_ids=["t1"],
            ),
        ])
        report = evaluate_render_gate(ir, generated_text=_valid_generated_text(ir))
        assert GATE_CONSISTENCY in report.failed_gates

    def test_gate3_independent_from_gate1(self):
        """Gate 3 runs even when Gate 1 fails."""
        ir = _make_valid_ir(
            parties=[],  # triggers IR_VALID failure
            claims=[
                ClaimItem(
                    id="c1",
                    text="Скасувати рішення.",
                    relief_type="declaratory",
                    supporting_fact_ids=["f999"],  # triggers CONSISTENCY failure
                    supporting_thesis_ids=["t1"],
                ),
            ],
        )
        report = evaluate_render_gate(ir, generated_text=_valid_generated_text(ir))
        assert GATE_IR_VALID in report.failed_gates
        assert GATE_CONSISTENCY in report.failed_gates


# ---------------------------------------------------------------------------
# Gate 4 — CITATIONS_COVERED
# ---------------------------------------------------------------------------

class TestGate4CitationsCovered:
    def test_passes_when_all_grounded_and_pipeline_on(self):
        ir = _make_valid_ir()
        with patch("frontend.app.dashboard.analyze.final_render_gate.flags") as mock_flags:
            mock_flags.ir_pipeline.return_value = "on"
            report = evaluate_render_gate(ir, generated_text=_valid_generated_text(ir))
        assert GATE_CITATIONS not in report.failed_gates

    def test_fails_when_ungrounded_thesis_and_pipeline_on(self):
        ir = _make_valid_ir(legal_basis=[
            LegalThesis(
                id="t1",
                text="Деякий аргумент.",
                citations=[],
                grounding_status="ungrounded",
                citation_coverage=0.0,
            ),
        ])
        with patch("frontend.app.dashboard.analyze.final_render_gate.flags") as mock_flags:
            mock_flags.ir_pipeline.return_value = "on"
            report = evaluate_render_gate(ir, generated_text=_valid_generated_text(ir))
        assert GATE_CITATIONS in report.failed_gates

    def test_skipped_when_pipeline_off(self):
        ir = _make_valid_ir(legal_basis=[
            LegalThesis(
                id="t1",
                text="Деякий аргумент.",
                citations=[],
                grounding_status="ungrounded",
                citation_coverage=0.0,
            ),
        ])
        with patch("frontend.app.dashboard.analyze.final_render_gate.flags") as mock_flags:
            mock_flags.ir_pipeline.return_value = "off"
            report = evaluate_render_gate(ir, generated_text=_valid_generated_text(ir))
        # Gate is skipped → passes (not in failed_gates)
        assert GATE_CITATIONS not in report.failed_gates
        skipped_gate = next(g for g in report.gates if g.gate == GATE_CITATIONS)
        assert "skipped" in skipped_gate.detail.lower()


# ---------------------------------------------------------------------------
# Gate 5 — LAYOUT_FIELDS
# ---------------------------------------------------------------------------

class TestGate5LayoutFields:
    def test_passes_when_all_elements_present(self):
        ir = _make_valid_ir()
        report = evaluate_render_gate(ir, generated_text=_valid_generated_text(ir))
        assert GATE_LAYOUT not in report.failed_gates

    def test_fails_when_generated_text_missing_court(self):
        ir = _make_valid_ir()
        text_without_court = "скаржник: Тест\nСкасувати рішення.\n_________________________"
        report = evaluate_render_gate(ir, generated_text=text_without_court)
        assert GATE_LAYOUT in report.failed_gates

    def test_fails_when_generated_text_empty(self):
        ir = _make_valid_ir()
        report = evaluate_render_gate(ir, generated_text="")
        # Empty text will fail layout checks (no court, no parties, no claims, no sig)
        assert GATE_LAYOUT in report.failed_gates

    def test_uses_plain_text_render_when_no_generated_text(self):
        """When generated_text='', _render_plain_text(ir) is used as fallback."""
        ir = _make_valid_ir()
        # Default render includes court_name, parties, title, claims, signature
        # so this should pass layout checks
        report = evaluate_render_gate(ir, doc_type="appeal_complaint")
        # With a valid IR the plain-text fallback should include court name
        assert GATE_LAYOUT not in report.failed_gates


# ---------------------------------------------------------------------------
# Multi-gate simultaneous failure
# ---------------------------------------------------------------------------

class TestMultipleGateFailures:
    def test_all_failed_gates_reported(self):
        """When multiple gates fail, all their codes appear in failed_gates."""
        ir = _make_valid_ir(
            parties=[],              # → IR_VALID fails
            claims=[
                ClaimItem(
                    id="c1",
                    text="Скасувати.",
                    relief_type="declaratory",
                    supporting_fact_ids=["f999"],  # → CONSISTENCY fails
                    supporting_thesis_ids=["t1"],
                ),
            ],
        )
        report = evaluate_render_gate(
            ir,
            generated_text="no court here",  # → LAYOUT fails
        )
        assert not report.passed
        assert GATE_IR_VALID in report.failed_gates
        assert GATE_CONSISTENCY in report.failed_gates
        assert GATE_LAYOUT in report.failed_gates

    def test_report_contains_all_five_gate_results(self):
        """evaluate_render_gate always returns exactly 5 GateResult entries."""
        ir = _make_valid_ir()
        report = evaluate_render_gate(ir, generated_text=_valid_generated_text(ir))
        gate_names = [g.gate for g in report.gates]
        from ..final_render_gate import ALL_GATES
        for gate in ALL_GATES:
            assert gate in gate_names, f"Gate {gate!r} missing from report.gates"
        assert len(report.gates) == 5


# ---------------------------------------------------------------------------
# validate_final_render_gate() raising behaviour
# ---------------------------------------------------------------------------

class TestValidateFinalRenderGate:
    def test_raises_422_on_failure(self):
        ir = _make_valid_ir(parties=[])
        with pytest.raises(HTTPException) as exc_info:
            validate_final_render_gate(ir, generated_text=_valid_generated_text(ir))
        assert exc_info.value.status_code == 422
        detail = exc_info.value.detail
        assert detail["error_code"] == "LAYOUT_COMPLIANCE_FAIL"
        assert GATE_IR_VALID in detail["failed_gates"]

    def test_raises_422_with_gate_details(self):
        ir = _make_valid_ir(parties=[])
        with pytest.raises(HTTPException) as exc_info:
            validate_final_render_gate(ir, generated_text=_valid_generated_text(ir))
        detail = exc_info.value.detail
        assert "gate_details" in detail
        failing_detail = next(
            (d for d in detail["gate_details"] if d["gate"] == GATE_IR_VALID), None
        )
        assert failing_detail is not None

    def test_does_not_raise_on_valid_ir(self):
        ir = _make_valid_ir()
        try:
            validate_final_render_gate(ir, generated_text=_valid_generated_text(ir))
        except HTTPException:
            pytest.fail("validate_final_render_gate() raised HTTPException on a valid IR.")
