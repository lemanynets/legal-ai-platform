"""
STORY-4 — Unit tests for consistency_checker.py.

DoD: one test per checker verifying that inconsistencies are detected.

Run:  pytest frontend/app/dashboard/analyze/tests/test_consistency.py -v
"""

import uuid
import pytest

from ..document_ir import (
    ClaimItem, DocumentHeader, DocumentIR, FactItem,
    LegalThesis, PartyItem, SignatureBlock,
)
from ..consistency_checker import (
    check_all,
    check_amounts_consistent,
    check_claims_reference_facts,
    check_dates_consistent,
    check_party_names_consistent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ir(**overrides) -> DocumentIR:
    base = dict(
        id=str(uuid.uuid4()),
        document_type="pozov_do_sudu",
        header=DocumentHeader(title="Позов", court_name="Суд"),
        parties=[
            PartyItem(id="p1", role="позивач", name="Іванченко І.І."),
            PartyItem(id="p2", role="відповідач", name="ТОВ Ромашка"),
        ],
        facts=[FactItem(id="f1", text="Відповідач не виконав договір")],
        legal_basis=[LegalThesis(id="t1", text="ст. 526 ЦК")],
        claims=[ClaimItem(id="c1", text="Стягнути 50 000 грн", relief_type="monetary",
                          amount=50000.0, supporting_fact_ids=["f1"])],
        signature_block=SignatureBlock(),
    )
    base.update(overrides)
    return DocumentIR(**base)


# ---------------------------------------------------------------------------
# Checker 1 — Party name consistency
# ---------------------------------------------------------------------------

def test_same_role_different_names_is_inconsistency():
    """DoD: два 'позивач' з різними іменами → PARTY_NAME_MISMATCH."""
    ir = _ir(parties=[
        PartyItem(id="p1", role="позивач", name="Іванченко Іван"),
        PartyItem(id="p3", role="позивач", name="Петренко Петро"),  # different name, same role
        PartyItem(id="p2", role="відповідач", name="ТОВ Ромашка"),
    ])
    result = check_party_names_consistent(ir)
    assert any(i.code == "PARTY_NAME_MISMATCH" for i in result)


def test_same_role_same_name_passes():
    ir = _ir()
    result = check_party_names_consistent(ir)
    assert not any(i.code == "PARTY_NAME_MISMATCH" for i in result)


def test_party_name_case_insensitive():
    """Normalisation: 'іванченко іван' == 'Іванченко Іван'."""
    ir = _ir(parties=[
        PartyItem(id="p1", role="позивач", name="Іванченко Іван"),
        PartyItem(id="p2", role="позивач", name="іванченко іван"),
        PartyItem(id="p3", role="відповідач", name="ТОВ Ромашка"),
    ])
    result = check_party_names_consistent(ir)
    assert not any(i.code == "PARTY_NAME_MISMATCH" for i in result)


# ---------------------------------------------------------------------------
# Checker 2 — Date consistency
# ---------------------------------------------------------------------------

def test_out_of_order_dates_is_inconsistency():
    """DoD: fact[0].date = 2024-12-01, fact[1].date = 2023-01-01 → DATE_CONTRADICTION."""
    ir = _ir(facts=[
        FactItem(id="f1", text="Спочатку", date="2024-12-01"),
        FactItem(id="f2", text="Потім",    date="2023-01-01"),  # earlier date listed later
    ])
    result = check_dates_consistent(ir)
    assert any(i.code == "DATE_CONTRADICTION" for i in result)


def test_in_order_dates_passes():
    ir = _ir(facts=[
        FactItem(id="f1", text="Подія 1", date="2023-01-01"),
        FactItem(id="f2", text="Подія 2", date="2024-06-15"),
    ])
    result = check_dates_consistent(ir)
    assert not any(i.code == "DATE_CONTRADICTION" for i in result)


def test_no_dates_passes():
    ir = _ir(facts=[
        FactItem(id="f1", text="Факт без дати"),
        FactItem(id="f2", text="Ще один факт"),
    ])
    result = check_dates_consistent(ir)
    assert result == []


# ---------------------------------------------------------------------------
# Checker 3 — Amount consistency
# ---------------------------------------------------------------------------

def test_large_fact_amount_vs_small_claim_is_inconsistency():
    """DoD: facts mention 100 000 UAH, claim.amount = 50 000 → AMOUNT_MISMATCH."""
    ir = _ir(
        facts=[FactItem(id="f1", text="Відповідач завдав збитків на суму 100000 грн")],
        claims=[ClaimItem(id="c1", text="Стягнути 50000 грн", relief_type="monetary",
                          amount=50000.0, supporting_fact_ids=["f1"])],
    )
    result = check_amounts_consistent(ir)
    assert any(i.code == "AMOUNT_MISMATCH" for i in result)


def test_matching_amounts_passes():
    ir = _ir(
        facts=[FactItem(id="f1", text="Заборгованість складає 50000 грн")],
        claims=[ClaimItem(id="c1", text="Стягнути 50000 грн", relief_type="monetary",
                          amount=50000.0, supporting_fact_ids=["f1"])],
    )
    result = check_amounts_consistent(ir)
    assert not any(i.code == "AMOUNT_MISMATCH" for i in result)


def test_no_monetary_claims_passes():
    ir = _ir(
        claims=[ClaimItem(id="c1", text="Визнати договір недійсним", relief_type="declaratory")],
    )
    result = check_amounts_consistent(ir)
    assert result == []


# ---------------------------------------------------------------------------
# Checker 4 — Claims reference facts
# ---------------------------------------------------------------------------

def test_unreferenced_claim_is_inconsistency():
    """DoD: claim with supporting_fact_ids=[] and supporting_thesis_ids=[] → CLAIM_UNREFERENCED."""
    ir = _ir(
        claims=[ClaimItem(
            id="c1", text="Стягнути 50 000 грн", relief_type="monetary", amount=50000.0,
            supporting_fact_ids=[],   # intentionally empty
            supporting_thesis_ids=[],
        )],
    )
    result = check_claims_reference_facts(ir)
    assert any(i.code == "CLAIM_UNREFERENCED" for i in result)


def test_claim_with_fact_reference_passes():
    ir = _ir(
        claims=[ClaimItem(
            id="c1", text="Стягнути 50 000 грн", relief_type="monetary", amount=50000.0,
            supporting_fact_ids=["f1"],
        )],
    )
    result = check_claims_reference_facts(ir)
    assert not any(i.code == "CLAIM_UNREFERENCED" for i in result)


def test_claim_with_thesis_reference_passes():
    ir = _ir(
        claims=[ClaimItem(
            id="c1", text="Стягнути 50 000 грн", relief_type="monetary", amount=50000.0,
            supporting_thesis_ids=["t1"],
        )],
    )
    result = check_claims_reference_facts(ir)
    assert not any(i.code == "CLAIM_UNREFERENCED" for i in result)


def test_no_facts_or_legal_basis_skips_check():
    """If doc type has no facts/legal_basis, checker should be a no-op."""
    ir = _ir(facts=[], legal_basis=[])
    result = check_claims_reference_facts(ir)
    assert result == []


# ---------------------------------------------------------------------------
# check_all integration
# ---------------------------------------------------------------------------

def test_check_all_returns_all_inconsistencies():
    ir = _ir(
        parties=[
            PartyItem(id="p1", role="позивач", name="Іванченко Іван"),
            PartyItem(id="p3", role="позивач", name="Різне Ім'я"),
        ],
        facts=[FactItem(id="f1", text="Значна сума 200000 грн")],
        claims=[ClaimItem(id="c1", text="Стягнути 50000 грн", relief_type="monetary",
                          amount=50000.0, supporting_fact_ids=[], supporting_thesis_ids=[])],
    )
    results = check_all(ir)
    codes = [r.code for r in results]
    assert "PARTY_NAME_MISMATCH" in codes
    assert "AMOUNT_MISMATCH" in codes
    assert "CLAIM_UNREFERENCED" in codes
