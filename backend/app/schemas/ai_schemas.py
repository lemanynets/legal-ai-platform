from __future__ import annotations
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

class ProceduralCode(str, Enum):
    CPC = "CPC"  # Цивільний процесуальний кодекс
    CCC = "CCC"  # Господарський процесуальний кодекс (Commercial)
    CAC = "CAC"  # Кодекс адміністративного судочинства
    CPC_CRIMINAL = "CPC_criminal"  # Кримінальний процесуальний кодекс
    UNKNOWN = "unknown"

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class DocumentType(str, Enum):
    STATEMENT_OF_CLAIM = "statement_of_claim"
    RESPONSE = "response"
    PETITION = "petition"
    APPEAL = "appeal"
    COURT_ORDER = "court_order"
    UNKNOWN = "unknown"

class RiskSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class RiskFlag(BaseModel):
    severity: RiskSeverity
    risk: str
    recommendation: str

class Party(BaseModel):
    role: str
    name: str = "уточнюється"
    edrpou: str | None = None
    inn: str | None = None
    address: str | None = None

class ClaimBreakdown(BaseModel):
    principal: float = 0.0
    penalty: float = 0.0
    fine: float = 0.0
    three_percent_annual: float = 0.0
    inflation_losses: float = 0.0
    total: float = 0.0

class ClassifierResult(BaseModel):
    document_type: DocumentType
    procedural_code: ProceduralCode | None = None
    extraction_quality: float = Field(ge=0.0, le=1.0)
    confidence: ConfidenceLevel
    court_fee: float | None = None
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    preliminary_score: float = Field(default=0.0, ge=0.0, le=1.0)
    parties: list[Party] = Field(default_factory=list)
    claim: ClaimBreakdown | None = None
    next_actions: list[str] = Field(default_factory=list)
    e_court_routing: dict[str, Any] = Field(default_factory=dict)


# DocumentIR schemas for structured document representation

class DocumentIRHeader(BaseModel):
    document_type: str
    title: str
    case_number: str | None = None
    court_name: str | None = None
    date: str | None = None


class DocumentIRParty(BaseModel):
    role: str  # plaintiff, defendant, etc.
    name: str
    address: str | None = None
    representative: str | None = None


class DocumentIRFacts(BaseModel):
    summary: str
    key_points: list[str] = Field(default_factory=list)


class DocumentIRLegalBasis(BaseModel):
    articles: list[str] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)


class DocumentIRClaim(BaseModel):
    type: str  # main, counter, etc.
    amount: float | None = Field(default=None, ge=0.0)
    description: str
    legal_basis: list[str] = Field(default_factory=list)


class DocumentIRAttachment(BaseModel):
    name: str
    type: str  # document, evidence, etc.
    description: str | None = None


class DocumentIRSignatureBlock(BaseModel):
    signer_name: str
    signer_role: str
    date: str | None = None


class DocumentIRCitation(BaseModel):
    id: str
    source_type: str  # case_law, statute, etc.
    source_locator: str  # case number, article, etc.
    evidence_span: str | None = None  # relevant text snippet


class DocumentIR(BaseModel):
    header: DocumentIRHeader
    parties: list[DocumentIRParty] = Field(default_factory=list)
    facts: DocumentIRFacts
    legal_basis: DocumentIRLegalBasis
    claims: list[DocumentIRClaim] = Field(default_factory=list)
    attachments: list[DocumentIRAttachment] = Field(default_factory=list)
    signature_block: DocumentIRSignatureBlock
    citations: list[DocumentIRCitation] = Field(default_factory=list)


def validate_document_ir(doc_ir: DocumentIR) -> list[str]:
    """Validate DocumentIR for business logic rules.

    Returns list of validation errors (empty if valid).
    """
    errors = []

    # Check that header has required fields
    if not doc_ir.header.document_type:
        errors.append("Header must have document_type")
    if not doc_ir.header.title:
        errors.append("Header must have title")

    # Check parties have at least one plaintiff and defendant
    plaintiff_count = sum(1 for p in doc_ir.parties if p.role.lower() == "plaintiff")
    defendant_count = sum(1 for p in doc_ir.parties if p.role.lower() == "defendant")

    if plaintiff_count == 0:
        errors.append("Must have at least one plaintiff")
    if defendant_count == 0:
        errors.append("Must have at least one defendant")

    # Check facts are not empty
    if not doc_ir.facts.summary.strip():
        errors.append("Facts summary cannot be empty")

    # Check claims have descriptions
    for i, claim in enumerate(doc_ir.claims):
        if not claim.description.strip():
            errors.append(f"Claim {i+1} must have description")

    # Check signature block
    if not doc_ir.signature_block.signer_name.strip():
        errors.append("Signature block must have signer name")

    return errors
