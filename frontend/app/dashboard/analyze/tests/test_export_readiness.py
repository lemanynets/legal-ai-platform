"""
STORY-0C — Unit tests for export_gates.py.

DoD test: відсутній суд → 422 LAYOUT_COMPLIANCE_FAIL

Run:  pytest frontend/app/dashboard/analyze/tests/test_export_readiness.py -v
"""

import pytest
from fastapi import HTTPException

from ..export_gates import validate_export_readiness, _run_checks


# ---------------------------------------------------------------------------
# Core gate: 422 when required elements are missing
# ---------------------------------------------------------------------------

def test_missing_court_raises_422():
    """DoD: відсутній суд → 422."""
    text = "Позивач: Іванченко І.І.\nВідповідач: ТОВ Ромашка\nПРОШУ стягнути 50 000 грн\n_________"
    with pytest.raises(HTTPException) as exc_info:
        validate_export_readiness("pozov_do_sudu", text)
    assert exc_info.value.status_code == 422
    detail = exc_info.value.detail
    assert detail["error_code"] == "LAYOUT_COMPLIANCE_FAIL"
    codes = [b["code"] for b in detail["blockers"]]
    assert "MISSING_COURT" in codes


def test_missing_parties_raises_422():
    text = "Київський районний суд\nПРОШУ задовольнити позов\n_________ підпис"
    with pytest.raises(HTTPException) as exc_info:
        validate_export_readiness("pozov_do_sudu", text)
    assert exc_info.value.status_code == 422
    codes = [b["code"] for b in exc_info.value.detail["blockers"]]
    assert "MISSING_PARTIES" in codes


def test_missing_claims_raises_422():
    text = "Київський суд\nПозивач: Іванченко\nВідповідач: ТОВ Ромашка\n_________ підпис"
    with pytest.raises(HTTPException) as exc_info:
        validate_export_readiness("pozov_do_sudu", text)
    codes = [b["code"] for b in exc_info.value.detail["blockers"]]
    assert "MISSING_CLAIMS" in codes


def test_missing_signature_raises_422():
    text = "Київський суд\nПозивач: Іванченко\nВідповідач: ТОВ Ромашка\nПРОШУ стягнути 50 000 грн"
    with pytest.raises(HTTPException) as exc_info:
        validate_export_readiness("pozov_do_sudu", text)
    codes = [b["code"] for b in exc_info.value.detail["blockers"]]
    assert "MISSING_SIGNATURE_BLOCK" in codes


def test_fully_valid_document_passes():
    text = (
        "До Київського районного суду\n"
        "Позивач: Іванченко Іван Іванович\n"
        "Відповідач: ТОВ Ромашка\n"
        "ПРОШУ суд стягнути 50 000 грн\n"
        "________________________ підпис\n"
        "Дата: 01.03.2026"
    )
    validate_export_readiness("pozov_do_sudu", text)  # should not raise


def test_empty_text_raises_422():
    with pytest.raises(HTTPException) as exc_info:
        validate_export_readiness("pozov_do_sudu", "")
    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Contract checks: skip_for logic
# ---------------------------------------------------------------------------

def test_contract_no_court_check():
    """Contracts skip the MISSING_COURT check."""
    text = "Продавець: Іванченко\nПокупець: Бондаренко\nПредмет: квартира за 1 000 000 грн\n_________"
    failing = _run_checks("dohovir_kupivli_prodazhu", text)
    failing_codes = [f["code"] for f in failing]
    assert "MISSING_COURT" not in failing_codes


def test_contract_passes_without_proshku():
    """Contracts (dohovir) have no MISSING_CLAIMS check for 'ПРОШУ'."""
    text = (
        "Договір купівлі-продажу\n"
        "Продавець: Іванченко І.І.\n"
        "Покупець: Бондаренко О.О.\n"
        "Предмет: земельна ділянка\n"
        "Вартість: 500 000 грн\n"
        "___________"
    )
    validate_export_readiness("dohovir_kupivli_prodazhu", text)  # no raise


# ---------------------------------------------------------------------------
# Power of attorney: уповноважую instead of ПРОШУ
# ---------------------------------------------------------------------------

def test_power_of_attorney_uponovazhuyu():
    text = (
        "ДОВІРЕНІСТЬ\n"
        "Довіритель: Мельник Василь Петрович\n"
        "Представник: Коваленко Олег Іванович\n"
        "Уповноважую представляти мої інтереси\n"
        "___________ підпис"
    )
    validate_export_readiness("dovirennist", text)  # no raise
