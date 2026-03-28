"""
Package init for the analyze backend stubs.

Re-exports the public schema contracts so any router can import with:

    from app.dashboard.analyze import AnalyzeBatchProcessRequest

The separate backend must replicate these exports in its own
app/schemas/__init__.py (see schemas.py for the Pydantic definitions).
"""

from .schemas import (
    AnalyzeBatchProcessRequest,
    AnalyzeBatchProcessResponse,
    AnalyzeBatchProcessResponseItem,
    AnalyzeIntakeRequest,
    CheckSeverity,
    ExportReadinessResponse,
    ProcessualCheckItem,
    ProcessualGateCheckRequest,
    ProcessualGateCheckResponse,
    ReadinessCheckResult,
    # Wave 1 — DocumentIR (re-exported from document_ir.py via schemas.py)
    AttachmentItem,
    CitationItem,
    ClaimItem,
    DocumentHeader,
    DocumentIR,
    FactItem,
    IRDocumentStatus,
    Inconsistency,
    LegalThesis,
    PartyItem,
    SignatureBlock,
)

__all__ = [
    # STORY-0A — intake
    "AnalyzeIntakeRequest",
    "AnalyzeBatchProcessRequest",
    "AnalyzeBatchProcessResponse",
    "AnalyzeBatchProcessResponseItem",
    # STORY-0B — processual gates
    "CheckSeverity",
    "ProcessualCheckItem",
    "ProcessualGateCheckRequest",
    "ProcessualGateCheckResponse",
    # STORY-0C — export readiness
    "ReadinessCheckResult",
    "ExportReadinessResponse",
    # STORY-1 — DocumentIR
    "DocumentIR",
    "DocumentHeader",
    "PartyItem",
    "FactItem",
    "LegalThesis",
    "ClaimItem",
    "AttachmentItem",
    "SignatureBlock",
    "CitationItem",
    "Inconsistency",
    "IRDocumentStatus",
]
