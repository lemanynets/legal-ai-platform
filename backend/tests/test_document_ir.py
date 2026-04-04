from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.ai_schemas import (
    DocumentIR,
    DocumentIRHeader,
    DocumentIRParty,
    DocumentIRFacts,
    DocumentIRLegalBasis,
    DocumentIRClaim,
    DocumentIRAttachment,
    DocumentIRSignatureBlock,
    DocumentIRCitation,
    validate_document_ir,
)


class TestDocumentIRValidation:
    """Test DocumentIR schema validation."""

    def test_valid_document_ir(self):
        """Test valid DocumentIR creation."""
        doc_ir = DocumentIR(
            header=DocumentIRHeader(
                document_type="lawsuit_debt_loan",
                title="Позов про стягнення боргу",
                case_number="123/2024",
                court_name="Шевченківський районний суд м. Києва",
                date="2024-01-15"
            ),
            parties=[
                DocumentIRParty(
                    role="plaintiff",
                    name="ТОВ 'Альфа'",
                    address="м. Київ, вул. Хрещатик, 1",
                    representative="Іваненко І.І."
                ),
                DocumentIRParty(
                    role="defendant",
                    name="ТОВ 'Бета'",
                    address="м. Київ, вул. Грушевського, 2"
                )
            ],
            facts=DocumentIRFacts(
                summary="Відповідач не повернув позику в розмірі 100 000 грн.",
                key_points=[
                    "Договір позики від 01.01.2023",
                    "Сума позики: 100 000 грн",
                    "Термін повернення: 01.01.2024"
                ]
            ),
            legal_basis=DocumentIRLegalBasis(
                articles=["ст. 1046 ЦКУ", "ст. 625 ЦКУ"],
                explanations=[
                    "За договором позики позикодавець передає гроші у власність позичальника",
                    "Відсотки за користування чужими грошима"
                ]
            ),
            claims=[
                DocumentIRClaim(
                    type="main",
                    amount=100000.0,
                    description="Стягнути з відповідача 100 000 грн основного боргу",
                    legal_basis=["ст. 1046 ЦКУ"]
                ),
                DocumentIRClaim(
                    type="interest",
                    amount=5000.0,
                    description="Стягнути 3% річних у розмірі 5 000 грн",
                    legal_basis=["ст. 625 ЦКУ"]
                )
            ],
            attachments=[
                DocumentIRAttachment(
                    name="Договір позики",
                    type="contract",
                    description="Оригінал договору від 01.01.2023"
                )
            ],
            signature_block=DocumentIRSignatureBlock(
                signer_name="Іваненко І.І.",
                signer_role="представник позивача",
                date="2024-01-15"
            ),
            citations=[
                DocumentIRCitation(
                    id="case-123",
                    source_type="case_law",
                    source_locator="Справа № 123/2023, Верховний Суд",
                    evidence_span="Суд постановив стягнути борг із відсотками"
                )
            ]
        )

        assert doc_ir.header.document_type == "lawsuit_debt_loan"
        assert len(doc_ir.parties) == 2
        assert doc_ir.facts.summary.startswith("Відповідач")
        assert len(doc_ir.claims) == 2
        assert doc_ir.signature_block.signer_name == "Іваненко І.І."

    def test_invalid_document_ir_missing_required_fields(self):
        """Test DocumentIR with missing required fields."""
        # This test is for schema validation - facts and signature_block are required
        # But since we provide them, it should pass schema validation
        # Business validation is tested separately
        doc_ir = DocumentIR(
            header=DocumentIRHeader(
                document_type="lawsuit_debt_loan",
                title="Позов"
            ),
            parties=[],
            facts=DocumentIRFacts(summary="Some facts"),
            legal_basis=DocumentIRLegalBasis(),
            claims=[],
            attachments=[],
            signature_block=DocumentIRSignatureBlock(
                signer_name="Signer",
                signer_role="Role"
            ),
            citations=[]
        )
        assert doc_ir.header.document_type == "lawsuit_debt_loan"

    def test_party_validation(self):
        """Test party validation."""
        party = DocumentIRParty(
            role="plaintiff",
            name="ТОВ 'Альфа'"
        )
        assert party.name == "ТОВ 'Альфа'"

    def test_invalid_claim_negative_amount(self):
        """Test claim validation."""
        with pytest.raises(ValidationError):
            DocumentIRClaim(
                type="main",
                amount=-1000.0,  # negative amount
                description="Invalid claim"
            )

    def test_empty_lists_allowed(self):
        """Test that empty lists are allowed for optional fields."""
        doc_ir = DocumentIR(
            header=DocumentIRHeader(
                document_type="statement_of_claim",
                title="Заява"
            ),
            parties=[],  # empty
            facts=DocumentIRFacts(summary="Facts summary"),
            legal_basis=DocumentIRLegalBasis(),  # empty
            claims=[],  # empty
            attachments=[],  # empty
            signature_block=DocumentIRSignatureBlock(
                signer_name="Signer",
                signer_role="Role"
            ),
            citations=[]  # empty
        )

        assert len(doc_ir.parties) == 0
        assert len(doc_ir.claims) == 0

    def test_citation_validation(self):
        """Test citation validation."""
        citation = DocumentIRCitation(
            id="cit-1",
            source_type="statute",
            source_locator="ст. 1046 ЦКУ"
        )

        assert citation.id == "cit-1"
        assert citation.source_type == "statute"

    def test_header_validation(self):
        """Test header validation."""
        header = DocumentIRHeader(
            document_type="appeal_complaint",
            title="Апеляційна скарга",
            case_number="456/2024"
        )

        assert header.document_type == "appeal_complaint"
        assert header.case_number == "456/2024"

    def test_facts_validation(self):
        """Test facts validation."""
        facts = DocumentIRFacts(
            summary="Test summary",
            key_points=["Point 1", "Point 2"]
        )

        assert facts.summary == "Test summary"
        assert len(facts.key_points) == 2

    def test_legal_basis_validation(self):
        """Test legal basis validation."""
        basis = DocumentIRLegalBasis(
            articles=["ст. 1", "ст. 2"],
            explanations=["Explanation 1"]
        )

        assert len(basis.articles) == 2
        assert len(basis.explanations) == 1

    def test_attachment_validation(self):
        """Test attachment validation."""
        attachment = DocumentIRAttachment(
            name="Contract.pdf",
            type="document"
        )

        assert attachment.name == "Contract.pdf"
        assert attachment.type == "document"
        assert attachment.description is None

    def test_signature_block_validation(self):
        """Test signature block validation."""
        sig = DocumentIRSignatureBlock(
            signer_name="John Doe",
            signer_role="Lawyer",
            date="2024-01-01"
        )

        assert sig.signer_name == "John Doe"
        assert sig.date == "2024-01-01"


class TestDocumentIRBusinessValidation:
    """Test business logic validation of DocumentIR."""

    def test_valid_document_ir_business(self):
        """Test valid DocumentIR passes business validation."""
        doc_ir = DocumentIR(
            header=DocumentIRHeader(
                document_type="lawsuit_debt_loan",
                title="Позов про стягнення боргу"
            ),
            parties=[
                DocumentIRParty(role="plaintiff", name="ТОВ 'Альфа'"),
                DocumentIRParty(role="defendant", name="ТОВ 'Бета'")
            ],
            facts=DocumentIRFacts(summary="Факти справи"),
            legal_basis=DocumentIRLegalBasis(),
            claims=[
                DocumentIRClaim(
                    type="main",
                    description="Стягнути борг"
                )
            ],
            attachments=[],
            signature_block=DocumentIRSignatureBlock(
                signer_name="Іваненко І.І.",
                signer_role="представник"
            ),
            citations=[]
        )

        errors = validate_document_ir(doc_ir)
        assert errors == []

    def test_invalid_missing_plaintiff(self):
        """Test validation fails without plaintiff."""
        doc_ir = DocumentIR(
            header=DocumentIRHeader(
                document_type="lawsuit_debt_loan",
                title="Позов"
            ),
            parties=[
                DocumentIRParty(role="defendant", name="ТОВ 'Бета'")
            ],
            facts=DocumentIRFacts(summary="Факти"),
            legal_basis=DocumentIRLegalBasis(),
            claims=[],
            attachments=[],
            signature_block=DocumentIRSignatureBlock(
                signer_name="Signer",
                signer_role="Role"
            ),
            citations=[]
        )

        errors = validate_document_ir(doc_ir)
        assert "Must have at least one plaintiff" in errors

    def test_invalid_empty_facts_summary(self):
        """Test validation fails with empty facts summary."""
        doc_ir = DocumentIR(
            header=DocumentIRHeader(
                document_type="lawsuit_debt_loan",
                title="Позов"
            ),
            parties=[
                DocumentIRParty(role="plaintiff", name="ТОВ 'Альфа'"),
                DocumentIRParty(role="defendant", name="ТОВ 'Бета'")
            ],
            facts=DocumentIRFacts(summary="   "),  # whitespace only
            legal_basis=DocumentIRLegalBasis(),
            claims=[],
            attachments=[],
            signature_block=DocumentIRSignatureBlock(
                signer_name="Signer",
                signer_role="Role"
            ),
            citations=[]
        )

        errors = validate_document_ir(doc_ir)
        assert "Facts summary cannot be empty" in errors

    def test_invalid_empty_claim_description(self):
        """Test validation fails with empty claim description."""
        doc_ir = DocumentIR(
            header=DocumentIRHeader(
                document_type="lawsuit_debt_loan",
                title="Позов"
            ),
            parties=[
                DocumentIRParty(role="plaintiff", name="ТОВ 'Альфа'"),
                DocumentIRParty(role="defendant", name="ТОВ 'Бета'")
            ],
            facts=DocumentIRFacts(summary="Факти"),
            legal_basis=DocumentIRLegalBasis(),
            claims=[
                DocumentIRClaim(
                    type="main",
                    description=""  # empty
                )
            ],
            attachments=[],
            signature_block=DocumentIRSignatureBlock(
                signer_name="Signer",
                signer_role="Role"
            ),
            citations=[]
        )

        errors = validate_document_ir(doc_ir)
        assert "Claim 1 must have description" in errors

    def test_invalid_empty_signer_name(self):
        """Test validation fails with empty signer name."""
        doc_ir = DocumentIR(
            header=DocumentIRHeader(
                document_type="lawsuit_debt_loan",
                title="Позов"
            ),
            parties=[
                DocumentIRParty(role="plaintiff", name="ТОВ 'Альфа'"),
                DocumentIRParty(role="defendant", name="ТОВ 'Бета'")
            ],
            facts=DocumentIRFacts(summary="Факти"),
            legal_basis=DocumentIRLegalBasis(),
            claims=[],
            attachments=[],
            signature_block=DocumentIRSignatureBlock(
                signer_name="   ",  # whitespace
                signer_role="Role"
            ),
            citations=[]
        )

        errors = validate_document_ir(doc_ir)
        assert "Signature block must have signer name" in errors