"""
Wave 4 · STORY-8 — Unified layout/compliance gate before final render.

Aggregates all five preconditions for final document rendering.  Every
condition is evaluated independently so the response always contains the
complete list of failed_gates — never just the first failure.

Conditions checked (in order):
  1. IR_VALID          — validate_ir() passes without violations
  2. NO_PROC_BLOCKERS  — no critical processual checks are failing
  3. CONSISTENCY_GREEN — ir.inconsistencies is empty
  4. CITATIONS_COVERED — all legal_basis theses are grounded (if ir_pipeline=on)
  5. LAYOUT_FIELDS     — export_readiness checklist passes on rendered text

On any failure: raises HTTP 422 with:
    {
      "error_code": "LAYOUT_COMPLIANCE_FAIL",
      "message": "...",
      "failed_gates": ["IR_VALID", "CITATIONS_COVERED", ...]
    }

Usage inside the render / export endpoint:

    from .final_render_gate import validate_final_render_gate
    validate_final_render_gate(ir, doc_type=document.doc_type)
    # only proceeds if all gates pass
    docx_bytes = renderer.render_docx(ir)

Unit tests: tests/test_final_render_gate.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fastapi import HTTPException

from .consistency_checker import check_all
from .error_codes import LAYOUT_COMPLIANCE_FAIL
from .export_gates import _run_checks as _run_layout_checks
from .feature_flags import flags
from .ir_validator import IRValidationError, validate_ir
from .processual_gates import _severity_for_code

if TYPE_CHECKING:
    from .document_ir import DocumentIR


# ---------------------------------------------------------------------------
# Gate identifiers
# ---------------------------------------------------------------------------

GATE_IR_VALID         = "IR_VALID"
GATE_NO_PROC_BLOCKERS = "NO_PROC_BLOCKERS"
GATE_CONSISTENCY      = "CONSISTENCY_GREEN"
GATE_CITATIONS        = "CITATIONS_COVERED"
GATE_LAYOUT           = "LAYOUT_FIELDS"

ALL_GATES = [
    GATE_IR_VALID,
    GATE_NO_PROC_BLOCKERS,
    GATE_CONSISTENCY,
    GATE_CITATIONS,
    GATE_LAYOUT,
]


@dataclass
class GateResult:
    gate: str
    passed: bool
    detail: str = ""


@dataclass
class RenderGateReport:
    """Full gate evaluation report.  `failed_gates` is machine-readable."""
    passed: bool
    gates: list[GateResult] = field(default_factory=list)

    @property
    def failed_gates(self) -> list[str]:
        return [g.gate for g in self.gates if not g.passed]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_render_gate(
    ir: "DocumentIR",
    doc_type: str = "",
    generated_text: str = "",
    processual_checks: list[dict] | None = None,
) -> RenderGateReport:
    """Evaluate all five render gates and return a full report.

    Args:
        ir:                 DocumentIR to evaluate.
        doc_type:           Document type (defaults to ir.document_type).
        generated_text:     Raw generated text for Gate 5 layout check.
                            If empty, a plain-text rendering of the IR is used.
        processual_checks:  List of processual validation check dicts
                            (from generated_document.processual_validation_checks).
                            Each dict must contain at least {"code": str, "status": str}.
                            When None, only IR-native inconsistencies are checked.

    Does NOT raise — returns a RenderGateReport whose `passed` flag
    indicates whether rendering is allowed.  Use validate_final_render_gate()
    for the raising variant.
    """
    dt = doc_type or ir.document_type
    results: list[GateResult] = []

    # ── Gate 1: IR structural validity ───────────────────────────────────
    try:
        validate_ir(ir, dt)
        results.append(GateResult(gate=GATE_IR_VALID, passed=True))
    except IRValidationError as exc:
        results.append(GateResult(
            gate=GATE_IR_VALID, passed=False,
            detail=f"{len(exc.violations)} порушень: {'; '.join(exc.violations[:3])}",
        ))

    # ── Gate 2: No critical processual blockers ───────────────────────────
    # Source 1: processual_validation_checks passed from generated_document
    ext_blockers: list[str] = []
    if processual_checks:
        for chk in processual_checks:
            code = chk.get("code", "")
            status = chk.get("status", "")
            if status in ("fail", "error") and _severity_for_code(code) == "critical":
                ext_blockers.append(code)

    # Source 2: IR-native inconsistencies (Inconsistency objects)
    ir_blockers = [i.code for i in ir.inconsistencies if _severity_for_code(i.code) == "critical"]

    all_blocker_codes = ext_blockers + ir_blockers
    if all_blocker_codes:
        results.append(GateResult(
            gate=GATE_NO_PROC_BLOCKERS, passed=False,
            detail=(
                f"{len(all_blocker_codes)} критичних блокерів: "
                f"{', '.join(all_blocker_codes[:5])}"
            ),
        ))
    else:
        results.append(GateResult(gate=GATE_NO_PROC_BLOCKERS, passed=True))

    # ── Gate 3: Consistency green ─────────────────────────────────────────
    fresh_inconsistencies = check_all(ir)
    if fresh_inconsistencies:
        results.append(GateResult(
            gate=GATE_CONSISTENCY, passed=False,
            detail=f"{len(fresh_inconsistencies)} неузгодженостей: "
                   f"{', '.join(i.code for i in fresh_inconsistencies[:3])}",
        ))
    else:
        results.append(GateResult(gate=GATE_CONSISTENCY, passed=True))

    # ── Gate 4: Citations covered (only when ir_pipeline=on) ──────────────
    if flags.ir_pipeline(dt) == "on":
        ungrounded = ir.ungrounded_theses()
        if ungrounded:
            results.append(GateResult(
                gate=GATE_CITATIONS, passed=False,
                detail=f"{len(ungrounded)} непідкріплених тез (grounding_status != grounded).",
            ))
        else:
            results.append(GateResult(gate=GATE_CITATIONS, passed=True))
    else:
        results.append(GateResult(gate=GATE_CITATIONS, passed=True, detail="skipped (ir_pipeline != on)"))

    # ── Gate 5: Layout/filing fields present ─────────────────────────────
    text = generated_text or _render_plain_text(ir)
    layout_fails = _run_layout_checks(dt, text)
    if layout_fails:
        results.append(GateResult(
            gate=GATE_LAYOUT, passed=False,
            detail=f"Відсутні елементи: {', '.join(f['code'] for f in layout_fails)}",
        ))
    else:
        results.append(GateResult(gate=GATE_LAYOUT, passed=True))

    all_passed = all(r.passed for r in results)
    return RenderGateReport(passed=all_passed, gates=results)


def validate_final_render_gate(
    ir: "DocumentIR",
    doc_type: str = "",
    generated_text: str = "",
    processual_checks: list[dict] | None = None,
) -> None:
    """Raise HTTP 422 LAYOUT_COMPLIANCE_FAIL if any render gate fails.

    Args:
        ir:                 DocumentIR to validate.
        doc_type:           Document type (defaults to ir.document_type).
        generated_text:     Raw generated text for Gate 5 layout check.
        processual_checks:  Real processual_validation_checks from the DB row
                            (generated_document.processual_validation_checks).
                            Pass these from the export endpoint so Gate 2
                            evaluates actual processual blockers, not just
                            IR-native inconsistencies.

    Call immediately before renderer.render_docx() / render_pdf():

        validate_final_render_gate(
            ir,
            doc_type=document.document_type,
            generated_text=document.generated_text,
            processual_checks=document.processual_validation_checks,
        )
        docx_bytes = renderer.render_docx(ir)
    """
    report = evaluate_render_gate(
        ir,
        doc_type=doc_type,
        generated_text=generated_text,
        processual_checks=processual_checks,
    )
    if not report.passed:
        failed = report.failed_gates
        details = [
            {"gate": g.gate, "detail": g.detail}
            for g in report.gates if not g.passed
        ]
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": LAYOUT_COMPLIANCE_FAIL,
                "message": (
                    f"Документ не може бути рендерений: "
                    f"{len(failed)} умов не виконано ({', '.join(failed)})."
                ),
                "failed_gates": failed,
                "gate_details": details,
            },
        )


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _render_plain_text(ir: "DocumentIR") -> str:
    """Produce a minimal plain-text representation of the IR for layout checks."""
    parts: list[str] = []
    if ir.header.court_name:
        parts.append(ir.header.court_name)
    for party in ir.parties:
        parts.append(f"{party.role}: {party.name}")
    parts.append(ir.header.title)
    for claim in ir.claims:
        parts.append(claim.text)
    if ir.signature_block:
        parts.append("_________________________")
    return "\n".join(parts)
