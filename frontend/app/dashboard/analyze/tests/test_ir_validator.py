"""
STORY-1 — Unit tests for ir_validator.py.

Run:  pytest frontend/app/dashboard/analyze/tests/test_ir_validator.py -v
Coverage target: ≥ 90%
"""

import uuid
import pytest

from ..document_ir import (
    AttachmentItem, CitationItem, ClaimItem, DocumentHeader,
    DocumentIR, FactItem, LegalThesis, PartyItem, SignatureBlock,
)
from ..ir_validator import IRParseError, IRValidationError, parse_ir_from_llm_output, validate_ir


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ir(**overrides) -> DocumentIR:
    """Return a minimal valid pozov_do_sudu IR."""
    defaults = dict(
        id=str(uuid.uuid4()),
        document_type="pozov_do_sudu",
        header=DocumentHeader(title="Позовна заява", court_name="Київський районний суд"),
        parties=[
            PartyItem(id="p1", role="позивач", name="Петренко Іван Іванович"),
            PartyItem(id="p2", role="відповідач", name="ТОВ Ромашка"),
        ],
        facts=[FactItem(id="f1", text="Відповідач не виконав умови договору від 01.01.2023")],
        legal_basis=[
            LegalThesis(id="t1", text="Відповідно до ст. 526 ЦК України зобов'язання мають виконуватися належним чином.")
        ],
        claims=[ClaimItem(id="c1", text="Стягнути з відповідача 50 000 грн", relief_type="monetary", amount=50000.0)],
        signature_block=SignatureBlock(),
    )
    defaults.update(overrides)
    return DocumentIR(**defaults)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_valid_ir_passes():
    ir = _make_ir()
    validate_ir(ir, "pozov_do_sudu")  # should not raise


def test_valid_ir_default_doc_type():
    ir = _make_ir(document_type="unknown_type")
    validate_ir(ir, "unknown_type")  # falls back to _default


# ---------------------------------------------------------------------------
# Required sections
# ---------------------------------------------------------------------------

def test_missing_parties_section_raises():
    ir = _make_ir(parties=[])
    with pytest.raises(IRValidationError) as exc_info:
        validate_ir(ir, "pozov_do_sudu")
    assert any("parties" in v for v in exc_info.value.violations)


def test_missing_facts_section_raises():
    ir = _make_ir(facts=[])
    with pytest.raises(IRValidationError) as exc_info:
        validate_ir(ir, "pozov_do_sudu")
    assert any("facts" in v.lower() or "фактичн" in v for v in exc_info.value.violations)


def test_missing_legal_basis_raises():
    ir = _make_ir(legal_basis=[])
    with pytest.raises(IRValidationError) as exc_info:
        validate_ir(ir, "pozov_do_sudu")
    assert any("правов" in v for v in exc_info.value.violations)


def test_missing_claims_raises():
    ir = _make_ir(claims=[])
    with pytest.raises(IRValidationError) as exc_info:
        validate_ir(ir, "pozov_do_sudu")
    assert any("прохальн" in v or "вимог" in v for v in exc_info.value.violations)


# ---------------------------------------------------------------------------
# Required party roles
# ---------------------------------------------------------------------------

def test_missing_plaintiff_raises():
    ir = _make_ir(parties=[PartyItem(id="p2", role="відповідач", name="ТОВ Ромашка")])
    with pytest.raises(IRValidationError) as exc_info:
        validate_ir(ir, "pozov_do_sudu")
    assert any("позивач" in v for v in exc_info.value.violations)


def test_missing_defendant_raises():
    ir = _make_ir(parties=[PartyItem(id="p1", role="позивач", name="Петренко І.І.")])
    with pytest.raises(IRValidationError) as exc_info:
        validate_ir(ir, "pozov_do_sudu")
    assert any("відповідач" in v for v in exc_info.value.violations)


# ---------------------------------------------------------------------------
# Required header fields
# ---------------------------------------------------------------------------

def test_missing_court_name_raises():
    ir = _make_ir(header=DocumentHeader(title="Позовна заява", court_name=None))
    with pytest.raises(IRValidationError) as exc_info:
        validate_ir(ir, "pozov_do_sudu")
    assert any("court_name" in v for v in exc_info.value.violations)


def test_missing_title_raises():
    ir = _make_ir(header=DocumentHeader(title="", court_name="Київський суд"))
    with pytest.raises(IRValidationError) as exc_info:
        validate_ir(ir, "pozov_do_sudu")
    assert any("title" in v for v in exc_info.value.violations)


# ---------------------------------------------------------------------------
# Signature block
# ---------------------------------------------------------------------------

def test_missing_signature_raises():
    ir = _make_ir(signature_block=None)
    with pytest.raises(IRValidationError) as exc_info:
        validate_ir(ir, "pozov_do_sudu")
    assert any("підпис" in v.lower() for v in exc_info.value.violations)


# ---------------------------------------------------------------------------
# Citation referential integrity
# ---------------------------------------------------------------------------

def test_dangling_citation_reference_raises():
    ir = _make_ir(
        legal_basis=[
            LegalThesis(id="t1", text="Відповідно до ст. 526 ЦК", citations=["nonexistent-uuid"])
        ]
    )
    with pytest.raises(IRValidationError) as exc_info:
        validate_ir(ir, "pozov_do_sudu")
    assert any("nonexistent-uuid" in v for v in exc_info.value.violations)


def test_valid_citation_reference_passes():
    cit = CitationItem(id="cit1", source_type="statute", source_locator="ст. 526 ЦК", evidence_span="...")
    ir = _make_ir(
        citations=[cit],
        legal_basis=[LegalThesis(id="t1", text="Відповідно до ст. 526 ЦК", citations=["cit1"])],
    )
    validate_ir(ir, "pozov_do_sudu")  # should not raise


# ---------------------------------------------------------------------------
# Final status constraints
# ---------------------------------------------------------------------------

def test_final_status_with_inconsistencies_raises():
    from ..document_ir import Inconsistency
    ir = _make_ir(
        status="final",
        inconsistencies=[Inconsistency(code="PARTY_NAME_MISMATCH", description="test")],
    )
    with pytest.raises(IRValidationError) as exc_info:
        validate_ir(ir, "pozov_do_sudu")
    assert any("final" in v for v in exc_info.value.violations)


def test_final_status_with_ungrounded_thesis_raises():
    ir = _make_ir(
        status="final",
        legal_basis=[LegalThesis(id="t1", text="Відповідно до ст. 526 ЦК", grounding_status="ungrounded")],
    )
    with pytest.raises(IRValidationError) as exc_info:
        validate_ir(ir, "pozov_do_sudu")
    assert any("ungrounded" in v.lower() or "непідкріплен" in v for v in exc_info.value.violations)


def test_final_status_all_conditions_met_passes():
    cit = CitationItem(id="cit1", source_type="statute", source_locator="ст. 526 ЦК", evidence_span="...")
    ir = _make_ir(
        status="final",
        citations=[cit],
        legal_basis=[LegalThesis(id="t1", text="Відповідно до ст. 526 ЦК", citations=["cit1"], grounding_status="grounded")],
    )
    validate_ir(ir, "pozov_do_sudu")  # should not raise


# ---------------------------------------------------------------------------
# parse_ir_from_llm_output
# ---------------------------------------------------------------------------

def test_parse_ir_invalid_json_raises():
    with pytest.raises(IRParseError, match="not valid JSON"):
        parse_ir_from_llm_output("this is not json")


def test_parse_ir_invalid_schema_raises():
    with pytest.raises(IRParseError, match="does not match"):
        parse_ir_from_llm_output('{"id": "x", "document_type": 123}')  # wrong type


def test_parse_ir_valid_json():
    import json
    data = {
        "id": str(uuid.uuid4()),
        "document_type": "pozov_do_sudu",
        "header": {"title": "Позов"},
        "status": "draft",
    }
    ir = parse_ir_from_llm_output(json.dumps(data))
    assert ir.document_type == "pozov_do_sudu"


# ---------------------------------------------------------------------------
# Contract: contract type does NOT need court_name
# ---------------------------------------------------------------------------

def test_contract_no_court_name_passes():
    ir = DocumentIR(
        id=str(uuid.uuid4()),
        document_type="dohovir_kupivli_prodazhu",
        header=DocumentHeader(title="Договір купівлі-продажу"),
        parties=[
            PartyItem(id="p1", role="продавець", name="Коваленко І.І."),
            PartyItem(id="p2", role="покупець", name="Бондаренко О.О."),
        ],
        claims=[ClaimItem(id="c1", text="Продати майно за 100 000 грн", relief_type="monetary", amount=100000.0)],
        signature_block=SignatureBlock(),
    )
    validate_ir(ir, "dohovir_kupivli_prodazhu")
