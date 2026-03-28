"""
Wave 2 · STORY-3 — Per-section validation rules.

Each function validates one section of the DocumentIR and raises
IRValidationError with a list of violations on failure.

Called by sectional_generator._run_step() after each LLM step.
Unit tests in tests/test_section_validators.py.
"""

from __future__ import annotations

from .document_ir import DocumentIR
from .ir_validator import IRValidationError, _doc_config


def validate_header_parties(ir: DocumentIR, doc_type: str = "") -> None:
    violations: list[str] = []
    cfg = _doc_config(doc_type)

    # Header
    required_header = cfg.get("required_header_fields", ["title"])
    for f in required_header:
        if not getattr(ir.header, f, None):
            violations.append(f"Заголовок: поле '{f}' порожнє.")

    # Parties
    required_roles = {r.lower() for r in cfg.get("required_party_roles", [])}
    present_roles = {p.role.lower() for p in ir.parties}
    for role in required_roles:
        if role not in present_roles:
            violations.append(f"Сторони: відсутня роль '{role}'.")

    for party in ir.parties:
        if not party.name.strip():
            violations.append(f"Сторона '{party.id}' ({party.role}): ім'я порожнє.")

    if violations:
        raise IRValidationError(violations=violations)


def validate_facts(ir: DocumentIR, doc_type: str = "") -> None:
    violations: list[str] = []
    cfg = _doc_config(doc_type)
    min_facts = cfg.get("min_facts", 0)

    if len(ir.facts) < min_facts:
        violations.append(
            f"Фактичні обставини: потрібно мінімум {min_facts}, є {len(ir.facts)}."
        )
    for fact in ir.facts:
        if not fact.text.strip():
            violations.append(f"Факт '{fact.id}' має порожній текст.")
        if len(fact.text) < 20:
            violations.append(
                f"Факт '{fact.id}' підозріло короткий ({len(fact.text)} символів). "
                "Мінімум 20 символів."
            )

    if violations:
        raise IRValidationError(violations=violations)


def validate_legal_basis(ir: DocumentIR, doc_type: str = "") -> None:
    violations: list[str] = []
    cfg = _doc_config(doc_type)
    min_legal = cfg.get("min_legal_basis", 0)

    if len(ir.legal_basis) < min_legal:
        violations.append(
            f"Правова підстава: потрібно мінімум {min_legal}, є {len(ir.legal_basis)}."
        )
    for thesis in ir.legal_basis:
        if not thesis.text.strip():
            violations.append(f"Теза '{thesis.id}' має порожній текст.")
        if len(thesis.text) < 30:
            violations.append(
                f"Теза '{thesis.id}' підозріло коротка ({len(thesis.text)} символів)."
            )

    if violations:
        raise IRValidationError(violations=violations)


def validate_claims(ir: DocumentIR, doc_type: str = "") -> None:
    violations: list[str] = []
    cfg = _doc_config(doc_type)
    min_claims = cfg.get("min_claims", 1)

    if len(ir.claims) < min_claims:
        violations.append(
            f"Прохальна частина: потрібно мінімум {min_claims}, є {len(ir.claims)}."
        )
    for claim in ir.claims:
        if not claim.text.strip():
            violations.append(f"Вимога '{claim.id}' має порожній текст.")
        if claim.relief_type not in (
            "monetary", "injunctive", "declaratory", "procedural", "other"
        ):
            violations.append(
                f"Вимога '{claim.id}': невідомий тип relief_type='{claim.relief_type}'."
            )
        if claim.relief_type == "monetary" and claim.amount is None:
            violations.append(
                f"Грошова вимога '{claim.id}' не має суми (amount=None)."
            )

    if violations:
        raise IRValidationError(violations=violations)


def validate_attachments_sig(ir: DocumentIR, doc_type: str = "") -> None:
    violations: list[str] = []
    cfg = _doc_config(doc_type)

    if cfg.get("signature_required", True) and ir.signature_block is None:
        violations.append("Блок підпису відсутній.")

    for att in ir.attachments:
        if not att.title.strip():
            violations.append(f"Додаток '{att.id}' має порожній заголовок.")

    if violations:
        raise IRValidationError(violations=violations)
