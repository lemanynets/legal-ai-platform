"""
Wave 3 · STORY-6 — Citation grounding in the DocumentIR.

Every LegalThesis in ir.legal_basis must be backed by at least one
CitationItem before the document can reach 'final' status.

Public API:

    attach_citations(ir, retrieved_docs)   → mutates ir.citations + thesis.citations
    validate_citation_coverage(ir)         → raises HTTP 422 CITATION_GROUNDING_FAIL
                                             if any thesis is ungrounded
    compute_coverage(ir)                   → float (covered / total)

Coverage metric:
    citation_coverage = len(grounded_theses) / len(all_theses)
    Stored in ir.citation_coverage and returned in the generate response.

Gate:
    validate_citation_coverage() is called AFTER attach_citations().
    An ungrounded thesis (grounding_status != "grounded") blocks finalisation.
    Gate only fires when ENABLE_CITATION_GROUNDING_GATE=true (default false
    for Wave 3 rollout).

Telemetry key:
    citation_coverage  (float, logged per document)
"""

from __future__ import annotations

import logging
import os
import uuid
from difflib import SequenceMatcher
from typing import Any

from fastapi import HTTPException

from .document_ir import CitationItem, DocumentIR, GroundingStatus, LegalThesis
from .retrieval import RetrievalResult

logger = logging.getLogger("legal_ai.citation_grounding")

_GATE_FLAG = os.getenv("ENABLE_CITATION_GROUNDING_GATE", "false").lower() in ("1", "true", "yes")

# Minimum similarity between thesis text and evidence_span to accept grounding
_MIN_SIMILARITY = 0.20


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def attach_citations(
    ir: DocumentIR,
    retrieved_docs: list[RetrievalResult],
) -> None:
    """Match each LegalThesis to the most relevant RetrievalResult.

    For each thesis, the function:
      1. Picks the retrieved doc with the highest text similarity to the thesis.
      2. If similarity ≥ _MIN_SIMILARITY, creates a CitationItem and links it.
      3. Sets thesis.grounding_status = "grounded" | "ungrounded".
      4. Updates thesis.citation_coverage.

    Mutates ir.citations and ir.legal_basis in-place.
    Sets ir.citation_coverage.

    In production, replace _score_similarity() with an embedding-based
    cross-encoder for much better precision.
    """
    for thesis in ir.legal_basis:
        best_doc, best_score = _find_best_match(thesis.text, retrieved_docs)

        if best_doc is not None and best_score >= _MIN_SIMILARITY:
            citation = CitationItem(
                id=str(uuid.uuid4()),
                source_type="case_law",
                source_locator=best_doc.decision_id,
                evidence_span=_extract_evidence_span(thesis.text, best_doc.summary or ""),
                decision_id=best_doc.decision_id,
                court_name=best_doc.court_name,
                decision_date=best_doc.decision_date,
            )
            ir.citations.append(citation)
            thesis.citations.append(citation.id)
            thesis.grounding_status = "grounded"
            thesis.citation_coverage = best_score
        else:
            thesis.grounding_status = "ungrounded"
            thesis.citation_coverage = 0.0

    ir.citation_coverage = compute_coverage(ir)
    logger.info(
        _log(
            "citation_grounding_complete",
            ir_id=ir.id,
            citation_coverage=ir.citation_coverage,
            total_theses=len(ir.legal_basis),
            grounded=sum(1 for t in ir.legal_basis if t.grounding_status == "grounded"),
        )
    )


def validate_citation_coverage(ir: DocumentIR) -> None:
    """Raise HTTP 422 CITATION_GROUNDING_FAIL if any thesis is ungrounded.

    No-op when ENABLE_CITATION_GROUNDING_GATE is false (default).
    Always no-op for documents with no legal_basis.
    """
    if not _GATE_FLAG or not ir.legal_basis:
        return

    ungrounded = [t for t in ir.legal_basis if t.grounding_status != "grounded"]
    if ungrounded:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "CITATION_GROUNDING_FAIL",
                "message": (
                    "Правова теза не підкріплена джерелом. "
                    "Документ не може бути фіналізований."
                ),
                "ungrounded_theses": [
                    {"id": t.id, "text": t.text[:120]}
                    for t in ungrounded
                ],
                "citation_coverage": ir.citation_coverage,
            },
        )


def compute_coverage(ir: DocumentIR) -> float:
    """Return fraction of theses that have grounding_status == 'grounded'."""
    total = len(ir.legal_basis)
    if total == 0:
        return 1.0  # vacuously true — no theses to ground
    grounded = sum(1 for t in ir.legal_basis if t.grounding_status == "grounded")
    return round(grounded / total, 4)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_best_match(
    thesis_text: str,
    docs: list[RetrievalResult],
) -> tuple[RetrievalResult | None, float]:
    """Return the doc with the highest similarity to thesis_text."""
    best: RetrievalResult | None = None
    best_score = 0.0
    for doc in docs:
        score = _score_similarity(thesis_text, doc.summary or "")
        if score > best_score:
            best_score = score
            best = doc
    return best, best_score


def _score_similarity(a: str, b: str) -> float:
    """SequenceMatcher-based similarity (placeholder for embedding model)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower()[:300], b.lower()[:300]).ratio()


def _extract_evidence_span(thesis_text: str, source_text: str, max_chars: int = 200) -> str:
    """Return the most relevant excerpt from source_text for this thesis."""
    if not source_text:
        return ""

    # Find the window in source_text most similar to thesis_text
    thesis_words = set(thesis_text.lower().split())
    best_start, best_overlap = 0, 0

    words = source_text.split()
    window = 30  # compare 30-word windows
    for i in range(0, max(1, len(words) - window)):
        chunk = set(words[i:i + window])
        overlap = len(thesis_words & chunk)
        if overlap > best_overlap:
            best_overlap = overlap
            best_start = i

    span = " ".join(words[best_start: best_start + window])
    return span[:max_chars]


def _log(event: str, **kwargs: Any) -> str:
    import json
    return json.dumps({"event": event, **kwargs})
