"""
STORY-9 — Golden legal quality suite.

Runs the full IR validation + consistency + citation coverage pipeline
against three known-good appeal_complaint fixtures and asserts quality metrics.

Metrics per golden case
-----------------------
structure_completeness   float  0-1   fraction of mandatory IR sections populated
citation_faithfulness    float  0-1   ir.citation_coverage (all theses grounded)
procedural_compliance    bool         validate_ir() passes without violations
critical_blockers        int          count of critical inconsistencies

DoD gate (pytest -q must be green in CI):
  - citation_coverage == 1.0 for every golden case
  - structure_completeness >= 1.0 for every golden case
  - procedural_compliance is True for every golden case
  - critical_blockers == 0 for every golden case

Run:
    pytest frontend/app/dashboard/analyze/tests/test_golden_suite.py -v
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import List

import pytest

from ..consistency_checker import check_all
from ..document_ir import DocumentIR, IRDocumentStatus
from ..ir_validator import IRValidationError, validate_ir
from ..processual_gates import _severity_for_code

# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

GOLDEN_DIR = pathlib.Path(__file__).parent / "golden"

GOLDEN_CASES = sorted(GOLDEN_DIR.glob("appeal_complaint_*.json"))


def _load_ir(path: pathlib.Path) -> DocumentIR:
    data = json.loads(path.read_text(encoding="utf-8"))
    return DocumentIR(**data)


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

_MANDATORY_SECTIONS = [
    "header",
    "parties",
    "facts",
    "legal_basis",
    "claims",
    "signature_block",
    "citations",
]


def _structure_completeness(ir: DocumentIR) -> float:
    """Fraction of mandatory sections that are non-empty."""
    populated = 0
    total = len(_MANDATORY_SECTIONS)
    for section in _MANDATORY_SECTIONS:
        value = getattr(ir, section, None)
        if value is None:
            continue
        # header / signature_block are objects — count as populated if not None
        if isinstance(value, list):
            if value:
                populated += 1
        else:
            populated += 1
    return populated / total


def _citation_faithfulness(ir: DocumentIR) -> float:
    """ir.citation_coverage field (pre-computed during fixture creation)."""
    return ir.citation_coverage


def _procedural_compliance(ir: DocumentIR) -> bool:
    """True when validate_ir() raises no violations."""
    try:
        validate_ir(ir, ir.document_type)
        return True
    except IRValidationError:
        return False


def _critical_blocker_count(ir: DocumentIR) -> int:
    """Count inconsistencies (fresh-run) with critical severity."""
    inconsistencies = check_all(ir)
    return sum(
        1 for i in inconsistencies if _severity_for_code(i.code) == "critical"
    )


# ---------------------------------------------------------------------------
# Report dataclass (printed as part of pytest output)
# ---------------------------------------------------------------------------


@dataclass
class GoldenReport:
    case_id: str
    path: str
    document_type: str
    structure_completeness: float
    citation_faithfulness: float
    procedural_compliance: bool
    critical_blockers: int
    notes: List[str] = field(default_factory=list)

    def to_table_row(self) -> str:
        pc = "PASS" if self.procedural_compliance else "FAIL"
        return (
            f"{self.case_id:<14} | "
            f"completeness={self.structure_completeness:.2f} | "
            f"citation_cov={self.citation_faithfulness:.2f} | "
            f"proc={pc} | "
            f"critical_blockers={self.critical_blockers}"
        )


# ---------------------------------------------------------------------------
# Parametrised per-case tests
# ---------------------------------------------------------------------------


@pytest.fixture(params=GOLDEN_CASES, ids=lambda p: p.stem)
def golden_ir(request) -> tuple[pathlib.Path, DocumentIR]:
    path: pathlib.Path = request.param
    ir = _load_ir(path)
    return path, ir


def test_structure_completeness(golden_ir):
    """All mandatory IR sections must be populated (completeness == 1.0)."""
    path, ir = golden_ir
    score = _structure_completeness(ir)
    assert score == 1.0, (
        f"{path.name}: structure_completeness={score:.2f} — "
        f"one or more mandatory sections are empty."
    )


def test_citation_coverage_full(golden_ir):
    """citation_coverage must be exactly 1.0 for every golden case."""
    path, ir = golden_ir
    cov = _citation_faithfulness(ir)
    assert cov == 1.0, (
        f"{path.name}: citation_coverage={cov:.2f} — "
        f"not all legal_basis theses are grounded."
    )


def test_all_theses_grounded(golden_ir):
    """Every LegalThesis must have grounding_status == 'grounded'."""
    path, ir = golden_ir
    ungrounded = ir.ungrounded_theses()
    assert not ungrounded, (
        f"{path.name}: {len(ungrounded)} ungrounded thesis/theses: "
        f"{[t.id for t in ungrounded]}"
    )


def test_procedural_compliance(golden_ir):
    """validate_ir() must pass without any violations."""
    path, ir = golden_ir
    ok = _procedural_compliance(ir)
    assert ok, f"{path.name}: validate_ir() raised IRValidationError."


def test_no_critical_blockers(golden_ir):
    """Consistency checker must find zero critical-severity inconsistencies."""
    path, ir = golden_ir
    count = _critical_blocker_count(ir)
    assert count == 0, (
        f"{path.name}: {count} critical blocker(s) found by consistency_checker."
    )


def test_no_inconsistencies_at_all(golden_ir):
    """Golden fixtures declare inconsistencies=[] and check_all() must agree."""
    path, ir = golden_ir
    fresh = check_all(ir)
    assert not fresh, (
        f"{path.name}: consistency_checker found {len(fresh)} inconsistency/ies "
        f"on a supposedly clean golden fixture: "
        f"{[i.code for i in fresh]}"
    )


def test_ir_status_needs_review(golden_ir):
    """Golden fixtures carry status='needs_review' (not draft, not final)."""
    path, ir = golden_ir
    assert ir.status == IRDocumentStatus.needs_review, (
        f"{path.name}: expected status=needs_review, got {ir.status!r}"
    )


def test_all_citations_referenced_by_theses(golden_ir):
    """Every CitationItem must be referenced by at least one LegalThesis."""
    path, ir = golden_ir
    used_cit_ids = {
        cit_id
        for thesis in ir.legal_basis
        for cit_id in thesis.citations
    }
    orphan_cit_ids = [c.id for c in ir.citations if c.id not in used_cit_ids]
    assert not orphan_cit_ids, (
        f"{path.name}: orphan citation(s) not referenced by any thesis: "
        f"{orphan_cit_ids}"
    )


def test_all_claims_reference_existing_facts(golden_ir):
    """supporting_fact_ids in every claim must point to existing fact IDs."""
    path, ir = golden_ir
    fact_ids = {f.id for f in ir.facts}
    for claim in ir.claims:
        bad = [fid for fid in claim.supporting_fact_ids if fid not in fact_ids]
        assert not bad, (
            f"{path.name}: claim {claim.id!r} references non-existent fact(s): {bad}"
        )


def test_all_claims_reference_existing_theses(golden_ir):
    """supporting_thesis_ids in every claim must point to existing thesis IDs."""
    path, ir = golden_ir
    thesis_ids = {t.id for t in ir.legal_basis}
    for claim in ir.claims:
        bad = [tid for tid in claim.supporting_thesis_ids if tid not in thesis_ids]
        assert not bad, (
            f"{path.name}: claim {claim.id!r} references non-existent thesis/theses: {bad}"
        )


# ---------------------------------------------------------------------------
# Aggregate report (always runs, prints a summary table)
# ---------------------------------------------------------------------------


def test_aggregate_metrics_report():
    """Print a metrics table for all golden cases and assert aggregate thresholds."""
    reports: list[GoldenReport] = []

    for path in GOLDEN_CASES:
        ir = _load_ir(path)
        reports.append(GoldenReport(
            case_id=ir.id or path.stem,
            path=path.name,
            document_type=ir.document_type,
            structure_completeness=_structure_completeness(ir),
            citation_faithfulness=_citation_faithfulness(ir),
            procedural_compliance=_procedural_compliance(ir),
            critical_blockers=_critical_blocker_count(ir),
        ))

    # Print summary table (visible with pytest -s or -v)
    print("\n\n=== STORY-9 Golden Quality Suite — Metrics ===")
    print(f"{'Case':<14} | {'Completeness':>12} | {'Citation Cov':>12} | {'Proc':>6} | {'Critical':>8}")
    print("-" * 75)
    for r in reports:
        print(r.to_table_row())
    print("-" * 75)

    # Aggregate assertions
    n = len(reports)
    assert n == 3, f"Expected 3 golden cases, found {n}."

    avg_completeness = sum(r.structure_completeness for r in reports) / n
    avg_citation_cov = sum(r.citation_faithfulness for r in reports) / n
    proc_pass_rate   = sum(1 for r in reports if r.procedural_compliance) / n
    total_blockers   = sum(r.critical_blockers for r in reports)

    print(f"\nAvg completeness : {avg_completeness:.2f}")
    print(f"Avg citation_cov : {avg_citation_cov:.2f}")
    print(f"Proc pass rate   : {proc_pass_rate:.0%}")
    print(f"Total critical   : {total_blockers}")

    assert avg_completeness == 1.0,  f"avg structure_completeness={avg_completeness:.2f} < 1.0"
    assert avg_citation_cov == 1.0,  f"avg citation_coverage={avg_citation_cov:.2f} < 1.0"
    assert proc_pass_rate == 1.0,    f"procedural_compliance_pass_rate={proc_pass_rate:.0%} < 100%"
    assert total_blockers == 0,      f"total critical_blockers={total_blockers} > 0"
