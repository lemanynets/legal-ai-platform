"""
Wave 1 · STORY-1 — DocumentIR Pydantic schema.

DocumentIR is the canonical intermediate representation for all generated
legal documents.  Once Wave 1 is complete, generated_text is derived FROM
the IR — never the other way around.

  generated_documents.ir_json  ← JSONB, nullable, added in migration 001
  DocumentIR.status            ← "draft" | "needs_review" | "final"

Import contract (backend must mirror in app/schemas/document_ir.py):

    from app.dashboard.analyze.document_ir import (
        DocumentIR, DocumentHeader, PartyItem, FactItem,
        LegalThesis, ClaimItem, AttachmentItem, SignatureBlock,
        CitationItem, Inconsistency, IRDocumentStatus,
    )
"""

from __future__ import annotations

from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Supporting value types
# ---------------------------------------------------------------------------

IRDocumentStatus = Literal["draft", "needs_review", "final"]
SourceType = Literal["case_law", "statute", "regulation", "doctrine", "other"]
GroundingStatus = Literal["grounded", "ungrounded", "draft"]

IR_VERSION = "1.0"


class CitationItem(BaseModel):
    """A single legal citation attached to a thesis in legal_basis.

    STORY-6: every LegalThesis.citations entry must resolve to one of these.
    """

    id: str = Field(description="Stable UUID within the IR (not the court decision UUID).")
    source_type: SourceType = "case_law"
    source_locator: str = Field(
        description=(
            "For case_law: case number or URL to the decision. "
            "For statute: article reference (e.g. 'ст. 16 ЦК України'). "
        )
    )
    evidence_span: str = Field(
        description="Exact quoted excerpt from the source supporting the thesis."
    )
    decision_id: Optional[str] = None
    court_name: Optional[str] = None
    decision_date: Optional[str] = None


class DocumentHeader(BaseModel):
    """Document title block and court/case identifiers."""

    title: str
    court_name: Optional[str] = None
    court_type: Optional[str] = None
    case_number: Optional[str] = None
    document_date: Optional[str] = None
    jurisdiction: str = "UA"


class PartyItem(BaseModel):
    """One party to the legal proceeding or contract."""

    id: str
    role: str = Field(
        description=(
            "Ukrainian role label: 'позивач', 'відповідач', 'продавець', "
            "'покупець', 'орендодавець', 'орендар', 'довіритель', 'представник', …"
        )
    )
    name: str
    identifier: Optional[str] = None
    """ЄДРПОУ, паспорт, ІПН, …"""
    address: Optional[str] = None
    representative: Optional[str] = None


class FactItem(BaseModel):
    """One factual circumstance (background facts section)."""

    id: str
    text: str
    date: Optional[str] = None
    supporting_evidence: List[str] = Field(default_factory=list)
    """CitationItem IDs or free-text evidence references."""


class LegalThesis(BaseModel):
    """One legal argument in the legal_basis section.

    STORY-6: grounding_status must be 'grounded' for status='final'.
    """

    id: str
    text: str
    citations: List[str] = Field(
        default_factory=list,
        description="List of CitationItem IDs supporting this thesis.",
    )
    grounding_status: GroundingStatus = "draft"
    citation_coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of thesis claims supported by at least one citation.",
    )


class ClaimItem(BaseModel):
    """One specific item of relief requested (прохальна частина)."""

    id: str
    text: str
    relief_type: str = Field(
        description="'monetary', 'injunctive', 'declaratory', 'procedural', 'other'"
    )
    amount: Optional[float] = None
    currency: Optional[str] = "UAH"
    supporting_fact_ids: List[str] = Field(default_factory=list)
    supporting_thesis_ids: List[str] = Field(default_factory=list)


class AttachmentItem(BaseModel):
    """One item in the attachments / додатки list."""

    id: str
    title: str
    required: bool = False
    provided: bool = False


class SignatureBlock(BaseModel):
    """Signature section at the end of the document."""

    signer_name: Optional[str] = None
    signer_role: Optional[str] = None
    date_placeholder: bool = True
    """True ↔ document has a signature line ("_______ / дата")."""


class Inconsistency(BaseModel):
    """One cross-section inconsistency found by consistency_checker.py.

    STORY-4: if this list is non-empty the document cannot be 'final'.
    """

    code: str
    """E.g. 'PARTY_NAME_MISMATCH', 'DATE_CONTRADICTION', 'AMOUNT_MISMATCH'."""
    description: str
    affected_sections: List[str] = Field(default_factory=list)
    """E.g. ['parties', 'facts'], ['facts', 'claims']."""


# ---------------------------------------------------------------------------
# Main IR model
# ---------------------------------------------------------------------------

class DocumentIR(BaseModel):
    """Intermediate representation of a generated legal document.

    The generation pipeline produces this; the renderer consumes it.
    Never stored as raw text — always as JSONB in generated_documents.ir_json.
    """

    id: str = Field(description="UUID of this IR instance.")
    doc_id: Optional[str] = None
    """FK → generated_documents.id (set after persisting the parent document)."""
    document_type: str
    ir_version: str = IR_VERSION
    status: IRDocumentStatus = "draft"

    # ── Core sections ──────────────────────────────────────────────────────
    header: DocumentHeader
    parties: List[PartyItem] = Field(default_factory=list)
    facts: List[FactItem] = Field(default_factory=list)
    legal_basis: List[LegalThesis] = Field(default_factory=list)
    claims: List[ClaimItem] = Field(default_factory=list)
    attachments: List[AttachmentItem] = Field(default_factory=list)
    signature_block: Optional[SignatureBlock] = None

    # ── Cross-cutting ──────────────────────────────────────────────────────
    citations: List[CitationItem] = Field(
        default_factory=list,
        description="Full citation objects; referenced by ID from LegalThesis.citations.",
    )
    inconsistencies: List[Inconsistency] = Field(
        default_factory=list,
        description="Populated by consistency_checker; non-empty blocks 'final' status.",
    )

    # ── Metrics ───────────────────────────────────────────────────────────
    citation_coverage: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="covered_theses / total_theses; populated by citation_grounding.",
    )

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at: str = ""
    updated_at: str = ""

    # ── Computed helpers ──────────────────────────────────────────────────

    def ungrounded_theses(self) -> List[LegalThesis]:
        """Return legal_basis items with grounding_status != 'grounded'."""
        return [t for t in self.legal_basis if t.grounding_status != "grounded"]

    def can_be_final(self) -> bool:
        """True only when all conditions for 'final' status are met."""
        return (
            not self.inconsistencies
            and not self.ungrounded_theses()
            and self.signature_block is not None
        )
